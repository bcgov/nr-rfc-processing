import os
import warnings
import logging

import rasterio as rio
import datetime

import admin.constants as const

from process.support import process_by_watershed_or_basin
from admin.color_ramp import color_ramp
import admin.object_store_util

# from osgeo import gdal
import multiprocessing
from glob import glob
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.merge import merge
from typing import List

import admin.snow_path_lib

LOGGER = logging.getLogger(__name__)
snow_path = admin.snow_path_lib.SnowPathLib()
ostore_util = admin.object_store_util.OStore()


# Suppress warning for GCP/RPC - inquiry does not affect workflow
warnings.filterwarnings("ignore", category=rio.errors.NotGeoreferencedWarning)


def reproject_modis(date: str, name: str, pth: str, dst_crs: str):
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

    pth_file_noext = snow_path.file_name_no_suffix(pth)
    intermediate_tif = snow_path.get_modis_reprojected_tif(
        input_source_path=pth, date_str=date, projection=dst_crs
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


def create_modis_mosaic(
    input_granule_directory: str, output_mosaic_tif: str, tifs_to_mosaic
):
    """
    Create a mosaic of all downloaded and reprojected tiffs

    Parameters
    ----------
    pth : str
        Path to directory of tiffs to be mosaic'ed

    """
    # example path: './data/intermediate_tif/modis/2023.03.21'
    LOGGER.debug(f"pth: {input_granule_directory}")
    date = os.path.basename(input_granule_directory)  # Get date var from path
    # TODO: Evalute if this is working correctly...
    #       the tifs_to_mosaic includes values like:
    #           './data/intermediate_tif/modis/2023.03.21/MOD10A1.A2023080.h12v02.061.2023082034547_EPSG4326.tif'
    #       but also includes the following tif
    #           './data/intermediate_tif/modis/2023.03.21/modis_composite_2023.03.21_2023.03.20_2023.03.19_2023.03.18_2023.03.17.tif'
    #
    # output_mosaic_tif = snow_path.get_output_modis_path(date)
    if not os.path.exists(output_mosaic_tif):
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
                src_files_to_mosaic, bounds=[*const.BBOX], res=const.MODIS_EPSG4326_RES
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
            output_mosaic_tif = snow_path.get_output_modis_path(date)
            LOGGER.debug(f"out_pth: {output_mosaic_tif}")
            try:
                LOGGER.debug(f"out_pth: {output_mosaic_tif}")
                # os.makedirs(os.path.split(out_pth)[0])
                dir2Create = os.path.dirname(output_mosaic_tif)
                if not os.path.exists(dir2Create):
                    os.makedirs(dir2Create)
                    LOGGER.debug(f"creating dir: {dir2Create}")
            except Exception as e:
                LOGGER.debug(e)
            LOGGER.debug(f"creating: {output_mosaic_tif}")
            with rio.open(output_mosaic_tif, "w", **out_meta) as dst:
                dst.write(mosaic)
            # Close all open tiffs that were mosaic'ed
            for f in src_files_to_mosaic:
                f.close()


def composite_mosaics(startdate: str, dates: list, out_pth: str):
    """
    Create a composite GTiff of the mosaics of a given range
    provided in the list of dates

    Parameters
    ----------
    dates : list
        Dates of mosaics to consider for compositing
    """
    # TODO: rework so inputs and outputs are fed as args
    LOGGER.debug(f"startdate: {startdate}")
    base = snow_path.get_modis_int_tif_dir(date=startdate)
    if not os.path.exists(base):
        os.makedirs(base)
        LOGGER.debug(f"created the directory {base}")
    if not os.path.exists(out_pth):
        LOGGER.debug(f"out_pth: {out_pth}")
        mosaics = []
        for date in dates:
            # tif_by_date = os.path.join(const.OUTPUT_TIF_MODIS, startdate.split(".")[0],
            #                f"{date}.tif")
            tif_by_date = snow_path.get_output_modis_path(date=date)
            mosaics.append(tif_by_date)
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


def distribute(func, args):
    # Multiprocessing support to manage Pool scope
    with multiprocessing.Pool(6) as p:
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
    pydate = datetime.date(int(datelist[0]), int(datelist[1]), int(datelist[2]))
    fmt_date = lambda x: x.strftime("%Y.%m.%d")
    date_query = [date]
    for d in range(1, days):
        date_query.append(fmt_date(pydate - datetime.timedelta(days=d)))
    return date_query


def clean_intermediate(date):
    residual_files = glob(os.path.join(const.INTERMEDIATE_TIF_MODIS, date, "*.tif"))
    if residual_files:
        LOGGER.info("Cleaning up residual files...")
        for f in residual_files:
            LOGGER.debug(f"delete: {f}")
            os.remove(f)


def process_modis(startdate, days, mosaic_only='False'):
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
    # bc_albers = "EPSG:3153"
    dst_crs = "EPSG:4326"

    dates = get_datespan(startdate, days)

    # pull the date composite output if it exists
    pull_date_composite(datestr_list=dates, start_date=startdate)

    # pull watershed and basin processed data if exists
    if mosaic_only != 'True':
        pull_watershed_basin_data(
            start_date=startdate,
            sat='modis',
            wat_basin='watersheds',
            process_async=True)
        pull_watershed_basin_data(
            start_date=startdate,
            sat='modis',
            wat_basin='basins',
            process_async=True)

    # this function recieves a start date and a days arg.
    # the days tell it how many days back to process.
    #
    # iterates over each day creating a composite tif that combines all
    # the granules for that day.

    for date in dates:
        # for each date will:
        #  - create reprojected tif to EPSG:4326 in
        #      the intermediate tif directory for each granule
        #  - then mosaics all the granules together into

        # intTif = os.path.join(const.INTERMEDIATE_TIF_MODIS, date)
        # intTif is the local path for the intermediate tif directory
        int_tif_dir = snow_path.get_modis_int_tif_dir(date)
        LOGGER.debug(f"intTif: {int_tif_dir}")
        if not os.path.exists(int_tif_dir):
            os.makedirs(int_tif_dir)
            LOGGER.debug(f"created folder: {int_tif_dir}")
        # modis_granules = glob(os.path.join(pth, date,'*.hdf'))
        # gets the granules from what exists locally after the download step
        modis_granules = snow_path.get_modis_granules(date)
        # why delete these files?  why not pick up where left off?
        # commenting out, no need to delete
        # clean_intermediate(date)

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

        # if the data already exists in ostore then pull it from there
        pull_modis_data(reproj_args)

        LOGGER.debug("doing reprojections to EPSG:4326")

        # DEBUGGING... does same as distribute call but in sync.  useful for debugging
        #              Comment out for prod
        # for args in reproj_args:
        #     reproject_modis(*args)
        distribute(reproject_modis, reproj_args)

        LOGGER.info(f"CREATING MOSAICS: {date}")
        # os.path.join(const.INTERMEDIATE_TIF_MODIS,date)
        # creates the mosaic files:
        # ./data/norm/mosaics/modis/2023/<processing date>
        # example
        # ./data/norm/mosaics/modis/2023/2023.03.22.tif
        output_mosaic_tif = snow_path.get_output_modis_path(date)
        files_to_mosaic = snow_path.get_modis_intermediate_tifs(date)
        create_modis_mosaic(int_tif_dir, output_mosaic_tif, files_to_mosaic)

    LOGGER.info("COMPOSING MOSAICS INTO ONE TIF")
    # creates:
    # './data/intermediate_tif/modis/2023.03.23/modis_composite_2023.03.23_2023.03.22_2023.03.21_2023.03.20_2023.03.19.tif'
    composite_mosaic_path = snow_path.get_modis_composite_mosaic_file_name(
        start_date=startdate, date_list=dates
    )
    composite_mosaics(startdate, dates, composite_mosaic_path)
    color_ramp(composite_mosaic_path)  # just adds the color ramp to the output file

    # creates the watershed/basin clipped versions of the composite mosaic
    # in both EPSG4326 and EPSG3153
    if mosaic_only != 'True':
        for task in ["watersheds", "basins"]:
            LOGGER.info(f"CREATING {task.upper()}")
            # pull the 10y 20y data from object storage
            # send the dates along
            process_by_watershed_or_basin("modis", task, startdate, dates)


def pull_modis_epsg4326(local_file_list, process_async=False):
    """checks to see if the output files associated with the reproject step exist in
    object storage and if so then pulls those files from object storage vs. reprocessing
    them.

    :param local_file_list: list of the original source files that were downloaded from
        snow and ice data center.

        example path: './data/modis-terra/MOD10A1.061/2023.03.24/MOD10A1.A2023083.h09v03.061.2023085030249.hdf'
    :type local_file_list: list of files that should be created by the process/reproject
        step.
    :param process_async: indicates whether to process as syncronous or async process
    :type process_async: boolean
    """
    ostore_dir_file_cache = {}  # a dictionary to cache list queries
    arg_list = []

    for local_file in local_file_list:
        orig_dir, original_file = os.path.split(local_file)
        date_str = os.path.basename(orig_dir)
        modis_reproj_file = snow_path.get_modis_reprojected_tif(
            input_source_path=local_file, date_str=date_str
        )
        arg_list.append(modis_reproj_file)
    if process_async:
        LOGGER.debug("args")
        with multiprocessing.pool.ThreadPool(6) as p:
            p.map(ostore_util.get_file_if_exists, arg_list)

    else:
        for arg in arg_list:
            ostore_util.get_file_if_exists(arg)


        # if not os.path.exists(modis_reproj_file):
        #     if ostore_util.ostore_file_exists(local_path=modis_reproj_file):
        #         # file is in ostore so pull it
        #         LOGGER.debug(f"pulling {local_file} from ostore")
        #         ostore_util.get_file(local_file)


def pull_mosaics(datestr_list, process_async=True):
    """gets list of date strings, calculates the path that coresponsds with the mosaics
    for those dates, checks to see if they exist locally, and if they do not then looks
    to object storage bucket to get them.

    :param datestr_list: _description_
    :type datestr_list: _type_
    """
    # data/norm/mosaics/modis/2023/2023.03.22.tif
    arg_list = []

    for date in datestr_list:
        mosaic_dir = snow_path.get_mosaic_dir(sat="modis", date=date)
        mosaic_file = snow_path.get_mosaic_file(sat="modis", date=date)
        # TODO get the object store path, test to see if file is in object store, if
        # yes then pull it
        arg_list.append(mosaic_file)
    if process_async:
        with multiprocessing.pool.ThreadPool(6) as p:
            p.map(ostore_util.get_file_if_exists, arg_list)
    else:
        for arg in arg_list:
            ostore_util.get_file_if_exists(arg)


def pull_date_composite(datestr_list, start_date: str):
    """gets a list of date strings in the format YYYY.MM.DD, calculates the
    corresponding output file, tests to see if it already exists, if it does not then
    check to see if it exists in object storage.  If it does then it gets pulled down
    to the local path.

    :param datestr_list: _description_
    :type datestr_list: _type_
    """
    composite_mosaic_path = snow_path.get_modis_composite_mosaic_file_name(
        start_date=start_date, date_list=datestr_list
    )
    if not os.path.exists(composite_mosaic_path):
        if ostore_util.ostore_file_exists(composite_mosaic_path):
            ostore_util.get_file(composite_mosaic_path)


def pull_watershed_basin_data(start_date, sat, wat_basin, process_async=False):
    # data/watersheds/Stikine/modis/2023.03.23/Stikine_modis_2023.03.23_EPSG4326.tif
    # data/watersheds/Northwest/modis/2023.03.23/Northwest_modis_2023.03.23_EPSG4326.tif'
    # TODO: find references to the string EPSG:4326 and EPSG:3153 and replace with a
    #       reference to a constant from constants.
    arg_list = []
    wat_basin_names = snow_path.get_watershed_basin_list(wat_bas=wat_basin)
    for wat_basin_name in wat_basin_names:
        for projection in ['EPSG:4326', 'EPSG:3153']:
            local_path = snow_path.get_watershed_or_basin_path(
                start_date=start_date,
                sat=sat,
                watershed_basin=wat_basin,
                watershed_name=wat_basin_name,
                projection=projection
            )
            arg_list.append(local_path)
    if process_async:
        with multiprocessing.pool.ThreadPool(6) as p:
            p.map(ostore_util.get_file_if_exists, arg_list)
    else:
        for arg in arg_list:
            ostore_util.get_file_if_exists(arg)

def pull_modis_data(reproj_args):
    # pulling the files that generated by the reprojection step
    local_files = [arg[2] for arg in reproj_args]
    pull_modis_epsg4326(local_files, process_async=True)

    # pulling the mosaics of all the granules
    dates = list(set([arg[0] for arg in reproj_args]))
    pull_mosaics(dates, process_async=False)


