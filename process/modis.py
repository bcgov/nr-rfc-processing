import os
import warnings
import logging

import rasterio as rio
import datetime

import admin.constants as const

from process.support import process_by_watershed_or_basin
from admin.color_ramp import color_ramp

# from osgeo import gdal
from multiprocessing import Pool
from glob import glob
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.merge import merge
from typing import List

import admin.snow_path_lib

LOGGER = logging.getLogger(__name__)
snow_path = admin.snow_path_lib.SnowPathLib()

# Suppress warning for GCP/RPC - inquiry does not affect workflow
warnings.filterwarnings("ignore", category=rio.errors.NotGeoreferencedWarning)


def reproject_modis(date, name, pth, dst_crs):
    """Reproject modis into the target CRS

    Creates data in the
    TOP ./intermediate_tif/modis/2023.03.23/MOD10A1.A2023082.h12v02.061.2023084034450_EPSG4326.tif'

    Parameters
    ----------
    name : str
        A name string of the granule to be reprojected
        to set up intermediate files
    date : str
        The aquisition date of the granule to be reprojected
        to set up intermediate files in format YYYY.MM.DD
    pth : str
        A string path to the granule
    dst_crs : str
        The destination CRS to be reprojected to
    """
    # OMG really!!!  Could you make this any more cryptic!!! (see commented out line below)
    # pth_file_noext = ".".join(os.path.split(pth)[-1].split(".")[:-1])
    # pth example data: ./data/modis-terra/MOD10A1.061/2023.03.21/MOD10A1.A2023080.h10v02.061.2023082033825.hdf
    pth_file = os.path.basename(pth)
    pth_file_noext = os.path.splitext(pth_file)[0]
    LOGGER.debug(f"pthname: {pth_file_noext}")
    # intermediate_tif is the output from this function
    intermediate_tif = os.path.join(
        const.INTERMEDIATE_TIF_MODIS,
        date,
        f'{pth_file_noext}_{dst_crs.replace(":", "")}.tif'
    )
    LOGGER.debug(f"intermediate_tif: {intermediate_tif}")
    LOGGER.debug(f"pth: {pth}")
    if not os.path.exists(intermediate_tif):
        LOGGER.debug(f"processing the modis granule: {pth_file_noext}")
        with rio.open(pth, "r") as modis_scene:
            with rio.open(modis_scene.subdatasets[0], "r") as src:
                # transform raster to dst_crs------
                transform, width, height = calculate_default_transform(
                    src.crs,
                    dst_crs,
                    src.width,
                    src.height,
                    *src.bounds,
                    resolution=const.MODIS_EPSG4326_RES,
                )
                kwargs = src.meta.copy()
                kwargs.update(
                    {
                        "driver": "GTiff",
                        "crs": dst_crs,
                        "transform": transform,
                        "width": width,
                        "height": height,
                    }
                )
                # Write reprojected granule into GTiff format
                with rio.open(intermediate_tif, "w", **kwargs) as dst:
                    reproject(
                        source=rio.band(src, 1),
                        destination=rio.band(dst, 1),
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=transform,
                        dst_crs=dst_crs,
                        resampling=Resampling.nearest,
                    )
                # -------------------------------------


def create_modis_mosaic(pth: str):
    """
    Create a mosaic of all downloaded and reprojected tiffs

    Parameters
    ----------
    pth : str
        Path to directory of tiffs to be mosaic'ed
    """
    # example path: './data/intermediate_tif/modis/2023.03.21'
    LOGGER.debug(f"pth: {pth}")
    date = os.path.basename(pth) # Get date var from path
    # TODO: Evalute if this is working correctly...
    #       the tifs_to_mosaic includes values like:
    #           './data/intermediate_tif/modis/2023.03.21/MOD10A1.A2023080.h12v02.061.2023082034547_EPSG4326.tif'
    #       but also includes the following tif
    #           './data/intermediate_tif/modis/2023.03.21/modis_composite_2023.03.21_2023.03.20_2023.03.19_2023.03.18_2023.03.17.tif'
    #
    out_pth = snow_path.get_output_modis_path(date)
    if not os.path.exists(out_pth):

        files_in_dir = glob(os.path.join(pth, "*.tif"))  # Get file paths to mosaic
        tifs_to_mosaic = snow_path.filter_for_modis_granules(files_in_dir, suffix='tif')

        LOGGER.debug(f"example of single file to mosaic: {tifs_to_mosaic[0]}")
        if tifs_to_mosaic:
            src_files_to_mosaic = []
            # creating a list of rasterio / rio file handles
            for f in tifs_to_mosaic:
                LOGGER.debug(f"adding to mosaic: {f}")
                src = rio.open(f, "r")
                src_files_to_mosaic.append(src)
            # Merge all granule tiffs into one
            mosaic, out_trans = merge(
                src_files_to_mosaic,
                bounds=[*const.BBOX],
                res=const.MODIS_EPSG4326_RES
            )
            out_meta = src.meta.copy()
            out_meta.update(
                {
                    "driver": "GTiff",
                    "height": mosaic.shape[1],
                    "width": mosaic.shape[2],
                    "transform": out_trans,
                }
            )
            # Write mosaic to disk
            # out_pth = os.path.join(
            #     const.OUTPUT_TIF_MODIS, date.split(".")[0], f"{date}.tif"
            # )
            out_pth = snow_path.get_output_modis_path(date)
            LOGGER.debug(f"out_pth: {out_pth}")
            try:
                LOGGER.debug(f"out_pth: {out_pth}")
                # os.makedirs(os.path.split(out_pth)[0])
                dir2Create = os.path.dirname(out_pth)
                if not os.path.exists(dir2Create):
                    os.makedirs(dir2Create)
                    LOGGER.debug(f"creating dir: {dir2Create}")
            except Exception as e:
                LOGGER.debug(e)
            LOGGER.debug(f"creating: {out_pth}")
            with rio.open(out_pth, "w", **out_meta) as dst:
                dst.write(mosaic)
            # Close all open tiffs that were mosaic'ed
            for f in src_files_to_mosaic:
                f.close()


def composite_mosaics(startdate: str, dates: list):
    """
    Create a composite GTiff of the mosaics of a given range
    provided in the list of dates

    Parameters
    ----------
    dates : list
        Dates of mosaics to consider for compositing
    """
    LOGGER.debug(f"startdate: {startdate}")
    base = os.path.join(const.INTERMEDIATE_TIF_MODIS, startdate)
    LOGGER.debug(f"base dir: {base}")
    if not os.path.exists(base):
        os.makedirs(base)
        LOGGER.debug(f"created the directory {base}")
    out_pth = os.path.join(base, f'modis_composite_{"_".join(dates)}.tif')
    if not os.path.exists(out_pth):
        LOGGER.debug(f"out_pth: {out_pth}")
        mosaics = []
        for date in dates:
            mosaics.append(
                os.path.join(const.OUTPUT_TIF_MODIS, startdate.split(".")[0],
                            f"{date}.tif")
            )
        with rio.open(mosaics[0], "r") as src:
            meta = src.meta.copy()
            data = src.read(1)
            for i in range(1, len(mosaics)):
                with rio.open(mosaics[i], "r") as m:
                    try:
                        data_b = m.read(1)
                        mask = (data > 100) & (data_b <= 100)
                        data[mask] = data_b[mask]
                    except Exception as e:
                        LOGGER.error(e)
                        continue
            with rio.open(out_pth, "w", **meta) as dst:
                dst.write(data, indexes=1)
    return out_pth


def distribute(func, args):
    # Multiprocessing support to manage Pool scope
    with Pool(6) as p:
        p.starmap(func, args)


def get_datespan(date: str, days: int) -> List[str]:
    """
    Build up date reference list for 5 or 8 day processing

    Parameters
    ----------
    date : str
        Starting date
    days: int
        Number of days to consider when building reference list (5 or 8)
    Returns
    ----------
    date_query: List
        Reference of all dates to consider when processing reprojetion and
        mosaic
    """
    datelist = date.split(".")
    pydate = datetime.date(int(datelist[0]), int(datelist[1]),
                           int(datelist[2]))
    fmt_date = lambda x: x.strftime("%Y.%m.%d")
    date_query = [date]
    for d in range(1, days):
        date_query.append(fmt_date(pydate - datetime.timedelta(days=d)))
    return date_query


def clean_intermediate(date):
    residual_files = glob(os.path.join(const.INTERMEDIATE_TIF_MODIS, date,
                                       "*.tif"))
    if residual_files:
        LOGGER.info("Cleaning up residual files...")
        for f in residual_files:
            LOGGER.debug(f"delete: {f}")
            os.remove(f)


def process_modis(startdate, days):
    """
    Main trigger for processing modis from HDF4 -> GTiff and
    then clipping to watersheds/basins

    Parameters
    ----------
    startdate : str
        The startdate which modis process will base it's 5 or 8 day processing
        from
    days : int
        Number of days to process raw HDF5 granules into mosaic -> composites
        before clipping to watersheds/basins. days = 5 or days = 8 only.
    """
    LOGGER.info("MODIS Process Started")
    #bc_albers = "EPSG:3153"
    dst_crs = "EPSG:4326"

    # pth = os.path.join(const.MODIS_TERRA,'MOD10A1.006')
    dates = get_datespan(startdate, days)
    for date in dates:
        # intTif = os.path.join(const.INTERMEDIATE_TIF_MODIS, date)
        # intTif is the local path for the intermediate tif directory
        int_tif_dir = snow_path.get_modis_int_tif(date)
        LOGGER.debug(f"intTif: {int_tif_dir}")
        if not os.path.exists(int_tif_dir):
            os.makedirs(int_tif_dir)
            LOGGER.debug(f"created folder: {int_tif_dir}")
        # modis_granules = glob(os.path.join(pth, date,'*.hdf'))
        # gets the granules from what exists locally after the download step
        modis_granules = snow_path.get_modis_granules(date)
        # why delete these files?  why not pick up where left off?
        # commenting out, no need to delete
        #clean_intermediate(date)

        LOGGER.info(f"REPROJ GRANULES: {date}")
        reproj_args = []
        for gran in modis_granules:
            try:
                # name = os.path.split(gran)[-1]
                name = os.path.basename(gran)
                reproj_args.append((date, name, gran, dst_crs))
            except Exception as e:
                LOGGER.error(f"Could not append {gran} : {e}")
                continue

        # reproject creates the projected granule files in intermediate tifs dir...
        # example:
        # /data/intermediate_tif/modis/2023.03.23/MOD10A1.A2023082.h12v02.061.2023084034450_EPSG4326.tif

        # debugging - run the reproject synchronously
        # pull from ostore if the data exists


        # LOGGER.debug("doing reprojections to EPSG:4326")
        # for args in reproj_args:
        #     reproject_modis(*args)



        # TODO: uncomment once things are working, taking out the async calls until
        #       figure out what's going on.
        distribute(reproject_modis, reproj_args)

        LOGGER.info(f"CREATING MOSAICS: {date}")
        # os.path.join(const.INTERMEDIATE_TIF_MODIS,date)
        # creates the mosaic files:
        # ./data/norm/mosaics/modis/2023/<processing date>
        # example
        # ./data/norm/mosaics/modis/2023/2023.03.22.tif
        create_modis_mosaic(int_tif_dir)

    LOGGER.info("COMPOSING MOSAICS INTO ONE TIF")
    # creates:
    # './data/intermediate_tif/modis/2023.03.23/modis_composite_2023.03.23_2023.03.22_2023.03.21_2023.03.20_2023.03.19.tif'
    out_pth = composite_mosaics(startdate, dates)
    color_ramp(out_pth) # just adds the color ramp to the output file

    for task in ["watersheds", "basins"]:
        LOGGER.info(f"CREATING {task.upper()}")
        # pull the 10y 20y data from object storage

        process_by_watershed_or_basin("modis", task, startdate)
