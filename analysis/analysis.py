import os

import admin.constants as const

import rioxarray as rioxr
import geopandas as gpd

from glob import glob

def calculate_stats(typ: str, sat: str, date: str, db_handler):
    if sat == 'modis':
        mosaic = glob(os.path.join(const.INTERMEDIATE_TIF_MODIS, date, 'modis_composite*.tif'))[0]
    elif sat == 'viirs':
        mosaic = glob(os.path.join(const.OUTPUT_TIF_VIIRS, date.split('.')[0], f'{date}.tif'))[0]
    else:
        return
    gdf = gpd.read_file(glob(os.path.join(f'aoi', typ,'*.shp'))[0])
    gdf = gdf.to_crs('EPSG:3153')
    with rioxr.open_rasterio(mosaic) as src:
        src = src.rio.reproject('EPSG:3153', resolution=const.RES[sat])
        for _, row in gdf.iterrows():
            if typ == 'watersheds':
                name = "_".join(row.basinName.replace('.','').split(" "))
            else:
                name = "_".join(row.WSDG_NAME.replace('.','').split(" "))
            clipped = src.rio.clip([row.geometry], drop=False, all_touched=True)
            nodata = (((clipped.data > 100)&(clipped.data != 255)).sum())
            below = ((clipped.data <= 20).sum())
            snow = (((clipped.data <= 100)&(clipped.data > 20)).sum())
            area = nodata + below + snow

            # failing here when the snow/area are either or both 0
            coverage = 0
            if snow != 0 and area != 0:
                coverage = (snow/area)*100

            nodata = 0
            if nodata != 0 and area != 0:
                nodata = (nodata/area)*100

            below_threshold = 0
            if below != 0 and area != 0:
                below_threshold = (below/area)*100

            # TODO: 
            prepare = {
                'sat': sat,
                'name': name,
                'date_': date,
                'coverage': coverage,
                'nodata': nodata,
                'below_threshold': below_threshold
            }

            db_handler.insert(**prepare)
