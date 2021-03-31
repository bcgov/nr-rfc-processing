import os
import warnings
import logging

import rasterio as rio

import admin.constants as const

from osgeo import gdal
from multiprocessing import Pool
from glob import glob
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.merge import merge
from typing import List

logger = logging.getLogger('snow_mapping')

warnings.filterwarnings("ignore", category=rio.errors.NotGeoreferencedWarning)

def reproject_modis(date, name, pth, dst_crs):
    print(pth)
    """Reproject modis into the target CRS

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
    pthname = '.'.join(os.path.split(pth)[-1].split('.')[:-1])
    intermediate_tif = os.path.join(const.INTERMEDIATE_TIF_MODIS, date, f'{pthname}_{dst_crs.replace(":", "")}.tif')
    with rio.open(pth, 'r') as modis_scene:
        with rio.open(modis_scene.subdatasets[0], 'r') as src:
            # transform raster to dst_crs------
            transform, width, height = calculate_default_transform(
                                            src.crs, 
                                            dst_crs, 
                                            src.width, 
                                            src.height, 
                                            *src.bounds, 
                                            resolution=const.MODIS_EPSG4326_RES
                                        ) 
            kwargs = src.meta.copy()
            kwargs.update({
                'driver': 'GTiff',
                'crs': dst_crs,
                'transform': transform,
                'width': width,
                'height': height
            })
            # Write reprojected granule into GTiff format
            with rio.open(intermediate_tif, 'w', **kwargs) as dst:
                reproject(
                source=rio.band(src, 1),
                destination=rio.band(dst, 1),
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=transform,
                dst_crs=dst_crs,
                resampling=Resampling.nearest)
            # -------------------------------------

def create_modis_mosaic(pth: str):
    """
    Create a mosaic of all downloaded and reprojected tiffs

    Parameters
    ----------
    pth : str
        Path to directory of tiffs to be mosaic'ed
    """
    date = os.path.split(pth)[-1] # Get date var from path
    outputs = glob(os.path.join(pth, '*.tif')) # Get file paths to mosaic
    if len(outputs) != 0:
        src_files_to_mosaic = []
        for f in outputs:
            src = rio.open(f, 'r')
            src_files_to_mosaic.append(src)
        # Merge all granule tiffs into one
        mosaic, out_trans = merge(
            src_files_to_mosaic, 
            bounds=[*const.BBOX],
            res=const.MODIS_EPSG4326_RES
            )
        out_meta = src.meta.copy()
        out_meta.update({
                "driver": "GTiff",
                "height": mosaic.shape[1],
                "width": mosaic.shape[2],
                "transform": out_trans,
                      })
        # Write mosaic to disk
        out_pth = os.path.join(const.OUTPUT_TIF_MODIS,date.split('.')[0],f'{date}.tif')
        try:
            os.makedirs(os.path.split(out_pth)[0])
        except Exception as e:
            logger.debug(e)
        with rio.open(out_pth, "w", **out_meta) as dst:
            dst.write(mosaic)
        # Close all open tiffs that were mosaic'ed
        for f in src_files_to_mosaic:
            f.close()
    
def clean_intermediate(date):
    residual_files = glob(os.path.join(const.INTERMEDIATE_TIF_MODIS, date,'*.tif'))
    if len(residual_files) != 0:
        print('Cleaning up residual files...')
        for f in residual_files:
            os.remove(f)
            
def distribute(func, args):
    # Multiprocessing support to manage Pool scope
    with Pool(6) as p:
        p.starmap(func, args)

def process_modis(date: str):
    ws84 = 'EPSG:4326'
    bc_albers = 'EPSG:3005'
    dst_crs = 'EPSG:3005'
    pth = os.path.join(const.MODIS_TERRA,'MOD10A1.006')
    try:
        os.makedirs(os.path.join(const.INTERMEDIATE_TIF_MODIS,date))
    except:
        pass 
    modis_granules = glob(os.path.join(pth, date,'*.hdf'))
    clean_intermediate(date)

    logger.info(f'REPROJ GRANULES: {date}')
    reproj_args = []
    for gran in modis_granules:
        try:
            name = os.path.split(gran)[-1]
            reproj_args.append((date, name, gran, dst_crs))           
        except Exception as e:
            logger.error(f'Could not append {gran} : {e}')
            continue
    distribute(reproject_modis, reproj_args)
    
    logger.info(f'CREATING MOSAICS: {date}')
    create_modis_mosaic(os.path.join(const.INTERMEDIATE_TIF_MODIS, date))

    #clean(date)
