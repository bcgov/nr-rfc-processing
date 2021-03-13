import os

import rasterio as rio

from admin.constants import Constants

from glob import glob
from rasterio.warp import calculate_default_transform, reproject, Resampling

const = Constants()

def process_by_watershed_or_basin(sat: str, typ: str, sat_day: str, startdate: str):
    """
    Cut the mosaic to watershed/basin shapefile and output a clipped tiff

    Parameters
    ----------
    typ : str
        Indicate 'watersheds' or 'basins'
    sat_day : str
        Path to the sat composite to use as the base for all cutting
    startdate : str
        The target date to focus on and output directory
    """

    res = {'modis':(500,500), 'viirs':(375,375)}
    if typ == 'watersheds':
        base = const.watersheds
    if typ == 'basins':
        base = const.basins

    sheds = glob(os.path.join(base, '**', 'shape', 'EPSG4326', '*.shp'))
    for shed in sheds:
        name = os.path.split(shed)[-1].split('.')[0]
        print(name)
        pth = os.path.join(base, name, sat, startdate)
        if not os.path.exists(pth):
            os.makedirs(pth)
        else:
            for f in glob(os.path.join(pth, '*tif')):
                os.remove(f)
        # Cut to watershed/basin shapefile
        output_pth = os.path.join(base,name,sat,startdate,f'{name}_{sat}_{startdate}_EPSG4326.tif')
        gdal_str = f'gdalwarp -q -dstalpha --config GDALWARP_IGNORE_BAD_CUTLINE YES -cutline {shed} -crop_to_cutline \
                {sat_day} {output_pth}'
        os.system(gdal_str)

        # Reproject into BC Albers
        dst_crs = 'EPSG:3153'
        with rio.open(os.path.join(base,name,sat,startdate,os.path.split(output_pth)[-1]), 'r') as src:
            transform, width, height = calculate_default_transform(
                    src.crs, dst_crs, src.width, src.height, *src.bounds, resolution=res[sat]) 
            kwargs = src.meta.copy()
            kwargs.update({
                'driver': 'GTiff',
                'crs': dst_crs,
                'transform': transform,
                'width': width,
                'height': height
            })
            # Write reprojected granule into GTiff format
            with rio.open(os.path.join(base,name,sat,startdate,f'{name}_{sat}_{startdate}_{dst_crs.replace(":","")}.tif'), 'w', **kwargs) as dst:
                reproject(
                source=rio.band(src, 1),
                destination=rio.band(dst, 1),
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=transform,
                dst_crs=dst_crs,
                resampling=Resampling.nearest,
                )
        