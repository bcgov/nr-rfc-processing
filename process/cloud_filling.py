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
            print(f'Retrieving {file_path}')
        with rio.open(file_path, "r") as src:
            meta = src.meta.copy()
            data = src.read(1)
    except:
            meta = None
            data = None
    return data, meta

def find_most_recent_image(obj_dirpath, obj_fpath, dt):
    olist = ostore.list_objects(dt.strftime(obj_dirpath),return_file_names_only=True)
    fname = dt.strftime(obj_fpath)
    while not any(fname in s for s in olist):
        dt = dt - timedelta(days=1)
        fname = dt.strftime(obj_fpath)
    return dt

#date = '2022/05/07'
#dt = datetime.strptime(date,'%Y/%m/%d')
#datelist = pd.date_range(datetime.strptime(date,'%Y/%m/%d'), periods=90).tolist()
#dt_prev = dt - datetime.timedelta(days=1)

ostore = NRObjStoreUtil.ObjectStoreUtil()
mosaic_path = 'norm/mosaics/modis/%Y'
new_mosaic_path = 'snowpack_archive/intermediate_tif/modis/%Y.%m.%d'
cloud_filled_path = 'snowpack_archive/cloud_filled'
mosaic_fname = '%Y.%m.%d.tif'
mosaic_objpath = os.path.join(mosaic_path,mosaic_fname)
cloud_filled_objpath = os.path.join(cloud_filled_path,'%Y',mosaic_fname)

today = datetime.today()
startdate = find_most_recent_image(cloud_filled_path,cloud_filled_objpath,dt = today)
enddate = find_most_recent_image(os.path.dirname(new_mosaic_path),new_mosaic_path,dt = today)
datelist = pd.date_range(startdate, enddate).tolist()


for dt in datelist:
    if dt < datetime(2023,1,23):
    #if dt > datetime(2022,6,14):
        data, meta = get_image(dt, mosaic_objpath)
    else:
        olist = ostore.list_objects(dt.strftime(new_mosaic_path),return_file_names_only=True)
        matching = [s for s in olist if "modis_composite" in s]
        if len(matching)>0:
            data, meta = get_image(dt, matching[0])
        else:
            data = None
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