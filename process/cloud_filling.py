from datetime import datetime, timedelta
import os
import NRUtil.NRObjStoreUtil as NRObjStoreUtil

import rasterio as rio
import rioxarray as rioxr
import geopandas as gpd
import numpy as np
import pandas as pd

import dotenv

envPath = '.env'
if os.path.exists(envPath):
    print("loading dot env...")
    dotenv.load_dotenv(override=True)

def cloud_fill_mosaic(sat: str, typ: str, startdate: str, date_list=None):
    # Gather respective data files and prepare path bases
    if sat == 'modis':
        # mosaic example: './data/intermediate_tif/modis/2023.03.23/modis_composite_2023.03.23_2023.03.22_2023.03.21_2023.03.20_2023.03.19.tif'
        # mosaic = snow_paths.get_modis_mosaic_composite(startdate)
        mosaic = snow_paths.get_modis_composite_mosaic_file_name(
            start_date=startdate,
            date_list=date_list)
    elif sat == 'viirs':
        # TODO: When run viirs make sure that this glob doesn't return unexpected files
        mosaic = glob(os.path.join(const.OUTPUT_TIF_VIIRS, startdate.split('.')[0], '*.tif'))[0]
    else: # @click will make sure this else is never hit
        return

def get_image(dt, path):
    file_path = dt.strftime(path)
    try:
        if not os.path.isfile(file_path):
            ostore.get_object(local_path=file_path, file_path=file_path)
        with rio.open(file_path, "r") as src:
            meta = src.meta.copy()
            data = src.read(1)
    except:
            meta = None
            data = None
    return data, meta

date = '2012/04/10'
dt = datetime.strptime(date,'%Y/%m/%d')
datelist = pd.date_range(datetime.strptime(date,'%Y/%m/%d'), periods=4000).tolist()
#dt_prev = dt - datetime.timedelta(days=1)

mosaic_path = 'norm/mosaics/modis/%Y'
cloud_filled_path = 'snowpack_archive/cloud_filled/%Y'
mosaic_fname = '%Y.%m.%d.tif'
mosaic_objpath = os.path.join(mosaic_path,mosaic_fname)
cloud_filled_objpath = os.path.join(cloud_filled_path,mosaic_fname)

ostore = NRObjStoreUtil.ObjectStoreUtil()
for dt in datelist:
    data, meta = get_image(dt, mosaic_objpath)
    data_prevday, meta_prevday = get_image(dt - timedelta(days=1), cloud_filled_objpath)
    if data is None:
        data = data_prevday
        meta = meta_prevday
    else:
        nodata_mask = data>100
        data[nodata_mask]=data_prevday[nodata_mask]

    out_path = dt.strftime(cloud_filled_objpath)
    if not os.path.isdir(dt.strftime(cloud_filled_path)):
        os.makedirs(dt.strftime(cloud_filled_path))

    with rio.open(out_path, "w", **meta) as dst:
        dst.write(data, indexes=1)
    ostore.put_object(ostore_path=out_path, local_path=out_path)
    print(f'Saving to {out_path}')