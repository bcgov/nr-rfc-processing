import os
import logging

import rioxarray as rioxr
import geopandas as gpd
import numpy as np

import admin.constants as const

from admin.color_ramp import color_ramp

from glob import glob

logger = logging.getLogger(__name__)

def process_normals(norm: object, orig: object, geom: object, output_pth: str, sat: str):
    """Perform calculations on watersheds
    for percent change against normals of
    10 and 20 years.

    Parameters
    ----------
    norm : object
        Xarray Dataset object containing the norm
    orig : object
        Xarray Dataset object containing the current date data
    geom : object
        Polygon of watershed/basin to cut to
    output_pth : str
        Path to save % change calculated raster to
    sat : str
        Satellite source [modis | viirs]
    """
    norm.rio.to_raster(os.path.join(os.path.split(output_pth)[0], 'orig_'+os.path.split(output_pth)[-1]))
    cp = norm.data.copy()
    norm.data[(norm.data > 100)] = np.nan
    orig.data[(orig.data > 100)] = 0
    np.seterr(divide='ignore', invalid='ignore')
    set_val = np.nan
    # Calculate % change against respective normal
    norm.data = np.divide((orig.data-norm.data), norm.data, out=np.zeros(norm.data.shape))*100
    norm.data[norm.data == np.inf] = set_val # correct div by 0 and inf/nan
    norm.data = np.nan_to_num(norm.data, nan=set_val, posinf=set_val, neginf=set_val) # correct div by 0 and inf/nan
    norm.data[((norm.data > 100)&(norm.data != np.nan))] = 100
    norm.data[((norm.data < -100)&(norm.data != np.nan))] = -100
    norm.data[((orig.data > 100)|(cp > 100))] = set_val
    norm_clipped = norm.rio.clip([geom], drop=True, all_touched=True)
    norm_clipped = norm.rio.reproject('EPSG:3153', resolution=const.RES[sat])
    norm_clipped.rio.to_raster(output_pth)

def process_by_watershed_or_basin(sat: str, typ: str, startdate: str):
    """
    Cut the mosaic to watershed/basin shapefile and output a clipped tiff

    Parameters
    ----------
    sat : str
        Source satellite [modis | viirs]
    typ : str
        Indicate 'watersheds' or 'basins'
    startdate : str
        The target date to focus on and output directory
    """
    if typ == 'watersheds':
        base = const.WATERSHEDS
    if typ == 'basins':
        base = const.BASINS

    # Gather respective data files and prepare path bases
    if sat == 'modis':
        mosaic = glob(os.path.join(const.INTERMEDIATE_TIF_MODIS, startdate, 'modis_composite*.tif'))[0]
        norm10yr_base = os.path.join(const.MODIS_DAILY_10YR)
        norm20yr_base = os.path.join(const.MODIS_DAILY_20YR)
    elif sat == 'viirs':
        mosaic = glob(os.path.join(const.OUTPUT_TIF_VIIRS, startdate.split('.')[0], '*.tif'))[0]
        norm10yr_base = os.path.join(const.VIIRS_DAILY_10YR)
        norm20yr_base = os.path.join(const.VIIRS_DAILY_20YR)
    else: # @click will make sure this else is never hit
        return
    # base=basins root/basins
    # wrap this up into a script centralized pathlib
    # gets the shape files list in each basin
    sheds = glob(os.path.join(base, '**', 'shape', 'EPSG4326', '*.shp'))
    for shed in sheds:
        # shed = TOP/basins/<basin name>/shape/EPSG4326/<basin name>.shp
        # TODO: should have used basename!!! then splitext
        # filename operations could be centralized into a single library with
        # documentation and tests
        name = os.path.split(shed)[-1].split('.')[0]
        logger.debug(f'Processing {name} for {sat}')
        pth = os.path.join(base, name, sat, startdate)
        if not os.path.exists(pth):
            os.makedirs(pth)
        else:
            for f in glob(os.path.join(pth, '*tif')):
                os.remove(f)
        gdf = gpd.read_file(shed) # shapefile to cut to
        gdf = gdf.to_crs('EPSG:4326')
        for _, row in gdf.iterrows():
            output_pth = os.path.join(pth,f'{name}_{sat}_{startdate}_EPSG4326.tif')
            if typ == 'watersheds':
                name = "_".join(row.basinName.replace('.','').split(" "))
            else:
                name = "_".join(row.WSDG_NAME.replace('.','').split(" "))
            with rioxr.open_rasterio(mosaic) as src:
                clipped_ = src.rio.clip([row.geometry], drop=True, all_touched=True)
            clipped_.rio.to_raster(output_pth)
            color_ramp(output_pth)
            output_pth = os.path.join(pth,f'{name}_{sat}_{startdate}_EPSG3153.tif')
            clipped = clipped_.rio.reproject('EPSG:3153', resolution=const.RES[sat])
            clipped.rio.to_raster(output_pth)
            color_ramp(output_pth)
            d_splt = startdate.split('.')
            # Calculate % change against normals for each watershed/basin
            with rioxr.open_rasterio(os.path.join(norm10yr_base, f'{d_splt[1]}.{d_splt[2]}.tif')) as norm10yr:
                out_pth = os.path.join(os.path.split(output_pth)[0], f'{name}_10yrNorm.tif')
                norm = norm10yr.rio.clip([row.geometry], drop=True, all_touched=True)
            process_normals(norm, clipped_, row.geometry, out_pth, sat)
            with rioxr.open_rasterio(os.path.join(norm20yr_base, f'{d_splt[1]}.{d_splt[2]}.tif')) as norm20yr:
                out_pth = os.path.join(os.path.split(output_pth)[0], f'{name}_20yrNorm.tif')
                norm = norm20yr.rio.clip([row.geometry], drop=True, all_touched=True)
            process_normals(norm, clipped_, row.geometry, out_pth, sat)