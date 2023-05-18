import os
import h5py
import logging

import numpy as np
import rasterio as rio

import admin.constants as const

from process.support import process_by_watershed_or_basin
from admin.color_ramp import color_ramp

from osgeo import gdal
from multiprocessing import Pool
from glob import glob
from rasterio.merge import merge
from rasterio.warp import calculate_default_transform, reproject, Resampling

import admin.snow_path_lib

logger = logging.getLogger(__name__)
snow_path = admin.snow_path_lib.SnowPathLib()


def build_viirs_tif(date: str, scene: str):
    """
    Build GTiff from raw HDF5 format so the pipeline can
    use the /data

    Parameters
    ----------
    date : str
        The aquisition date of the granule to be reprojected
        to set up intermediate files in format YYYY.MM.DD
    scene : str
        Raw/HDF5 granule path
    Ref:
        url: https://lpdaac.usgs.gov/resources/e-learning/working-daily-nasa-viirs-surface-reflectance-/data/
    """
    name = ".".join(os.path.split(scene)[-1].split('.')[:-1])
    logger.debug(f"name: {name}")
    dest = os.path.join(const.INTERMEDIATE_TIF_VIIRS, date, f'{name}.tif')
    logger.debug(f"dest file: {dest}")

    prj = 'PROJCS["unnamed",\
        GEOGCS["Unknown datum based upon the custom spheroid", \
        DATUM["Not specified (based on custom spheroid)", \
        SPHEROID["Custom spheroid",6371007.181,0]], \
        PRIMEM["Greenwich",0],\
        UNIT["degree",0.0174532925199433]],\
        PROJECTION["Sinusoidal"], \
        PARAMETER["longitude_of_center",0], \
        PARAMETER["false_easting",0], \
        PARAMETER["false_northing",0], \
        UNIT["Meter",1]]'

    f = h5py.File(scene, 'r')
    fileMetadata = f['HDFEOS INFORMATION']['StructMetadata.0'][()].split() # Read file metadata
    fileMetadata = [m.decode('utf-8') for m in fileMetadata]

    grids = list(f['HDFEOS']['GRIDS']) # List contents of GRIDS directory

    h5_objs = []            # Create empty list
    f.visit(h5_objs.append) # Walk through directory tree, retrieve objects and append to list

    all_datasets = [obj for grid in grids for obj in h5_objs if isinstance(f[obj],h5py.Dataset) and grid in obj]

    snow = f[[a for a in all_datasets if 'CGF_NDSI_Snow_Cover' in a][0]] # Cloud gap filled
    #snow = f[[a for a in all_datasets if 'VNP10A1_NDSI_Snow_Cover' in a][0]] # Non-cloud gap filled
    try: # Due to 2018 viirs missing a fill value: default to documented fillvalue
        fillValue = snow.attrs['_FillValue'][0] # Set fill value to a variable
    except:
        fillValue = 255
    snow = np.array(list(snow))
    ulc = [i for i in fileMetadata if 'UpperLeftPointMtrs' in i][0]    # Search file metadata for the upper left corner of the file
    ulcLon = float(ulc.split('=(')[-1].replace(')', '').split(',')[0]) # Parse metadata string for upper left corner lon value
    ulcLat = float(ulc.split('=(')[-1].replace(')', '').split(',')[1]) # Parse metadata string for upper left corner lat value

    yRes, xRes = -375,  375 # Define the x and y resolution
    geoInfo = (ulcLon, xRes, 0, ulcLat, 0, yRes)        # Define geotransform parameters

    nRow, nCol = snow.shape[0], snow.shape[1]
    driver = gdal.GetDriverByName('GTiff')
    options = ['PROFILE=GeoTIFF']
    outFile = driver.Create(dest, nCol, nRow, 1, options=options)
    band = outFile.GetRasterBand(1)
    band.WriteArray(snow)
    band.FlushCache
    band.SetNoDataValue(float(fillValue))
    outFile.SetGeoTransform(geoInfo)
    outFile.SetProjection(prj)
    f.close()

def reproject_viirs(date: str, name: str, src: str, dst_crs: str):
    """Reproject viirs into the target CRS

    Parameters
    ----------
    name : str
        A name string of the granule to be reprojected
        to set up intermediate files
    date : str
        The aquisition date of the granule to be reprojected
        to set up intermediate files in format YYYY.MM.DD
    src : str
        A string path to the granule
    dst_crs : str
        The destination CRS to be reprojected to
    """
    intermediate_tif = os.path.join(const.INTERMEDIATE_TIF_VIIRS,date,f'{name}_out.tif')
    with rio.open(src, 'r') as src:
        transform, width, height = calculate_default_transform(
                                        src.crs,
                                        dst_crs,
                                        src.width,
                                        src.height,
                                        src.bounds.left, src.bounds.bottom,
                                        src.bounds.right, src.bounds.top,
                                        resolution=const.VIIRS_EPSG4326_RES
                                    )
        kwargs = src.meta.copy()
        kwargs.update({
            'driver': 'GTiff',
            'crs': dst_crs,
            'transform': transform,
            'width': width,
            'height': height
        })
        with rio.open(intermediate_tif, 'w', **kwargs) as dst:
            for i in range(1, src.count + 1):
                reproject(
                    source=rio.band(src, i),
                    destination=rio.band(dst, i),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs=dst_crs,
                    resampling=Resampling.nearest
                )

def create_viirs_mosaic(pth: str, startdate: str):
    """
    Create a mosaic of all downloaded and reprojected tiffs

    Parameters
    ----------
    pth : str
        Path to directory of tiffs to be mosaic'ed
    """
    src_files_path = glob(os.path.join(pth,'*_out.tif'))
    name = os.path.split(pth)[-1]
    out_pth = os.path.join(const.OUTPUT_TIF_VIIRS,startdate.split('.')[0],f'{name}.tif')
    try:
        os.makedirs(os.path.split(out_pth)[0])
    except Exception as e:
        logger.debug(e)
    src_files_to_mosaic = []
    for f in src_files_path:
        src = rio.open(f, 'r')
        src_files_to_mosaic.append(src)
    if len(src_files_to_mosaic) != 0:
        mosaic, out_trans = merge(
            src_files_to_mosaic,
            bounds=[*const.BBOX],
            res=const.VIIRS_EPSG4326_RES
            )
        out_meta = src.meta.copy()
        out_meta.update({
                "driver": "GTiff",
                "height": mosaic.shape[1],
                "width": mosaic.shape[2],
                "transform": out_trans,
                      })
        with rio.open(out_pth, "w", **out_meta) as dst:
            dst.write(mosaic)
        for f in src_files_to_mosaic:
            f.close()
    return out_pth

def distribute(func, args):
    # Multiprocessing support to manage Pool scope
    with Pool(6) as p:
        p.starmap(func, args)

def process_viirs(date: str):
    """
    Main trigger for processing modis from HDF5 -> GTiff and
    then clipping to watersheds/basins

    Parameters
    ----------
    date : str
        The target date to process granules into mosaic
        and into watershed/basin GTiffs
    """
    logger.info('VIIRS Process Started')
    bc_alberes = 'EPSG:3153'
    dst_crs = 'EPSG:4326'
    #intermediate_pth = os.path.join(const.INTERMEDIATE_TIF_VIIRS, date)
    intermediate_pth = snow_path.get_viirs_int_tif(date)
    if not os.path.exists(intermediate_pth):
        os.makedirs(intermediate_pth)
    #viirs_granules = glob(os.path.join(const.MODIS_TERRA, 'VNP10A1F.001', date, '*.h5'))
    viirs_granules = snow_path.get_viirs_granules(date)
    logger.debug(f"int tif dir: {intermediate_pth}")


    #residual_files = glob(os.path.join(intermediate_pth, '*.tif'))
    residual_files = snow_path.get_intermediate_viirs_files(date)

    if len(residual_files) != 0:
        logger.info('Cleaning up residual files...')
        for f in residual_files:
            # TODO: uncomment once debugging complete, but WHY would they start with delete
            logger.debug(f"deleting residual file: {f}")
            #os.remove(f)


    logger.info('BUILDING INITIAL TIFS FROM HDF5')
    proc_inputs = []
    for i in range(len(viirs_granules)):
        proc_inputs.append((date, viirs_granules[i]))
    distribute(build_viirs_tif, proc_inputs)

    logger.info('REPROJECTING TIFFS')
    intermediate_tifs = snow_path.get_intermediate_viirs_files(date)
    #intermediate_tifs = glob(os.path.join(intermediate_pth, '*.tif'))

    reproj_args = []
    for tif in intermediate_tifs:
        name = ".".join(os.path.split(tif)[-1].split('.')[:-1])
        reproj_args.append((date, name, tif, dst_crs))
    distribute(reproject_viirs, reproj_args)

    logger.info('CREATING DAILY MOSAIC')
    out_pth = create_viirs_mosaic(intermediate_pth, date)
    color_ramp(out_pth)


    for task in ['watersheds', 'basins']:
        logger.info(f'CREATING {task.upper()}')
        process_by_watershed_or_basin('viirs', task, date)

