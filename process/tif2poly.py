import datetime
import os
import sys
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import NRUtil.NRObjStoreUtil as NRObjStoreUtil
import rasterio
import geopandas
import rasterstats
import dotenv

envPath = '.env'
if os.path.exists(envPath):
    print("loading dot env...")
    dotenv.load_dotenv(override=True)


def objstore_to_df(objpath, local_path = None):
    filename = objpath.split("/")[-1]
    filetype = filename.split(".")[-1]
    local_folder = 'raw_data/temp_file'
    if not os.path.exists(local_folder):
        os.makedirs(local_folder)

    if not local_path:
        local_path = os.path.join(local_folder,filename)
    ostore.get_object(local_path=local_path, file_path=objpath)
    if filetype == 'csv':
        output = pd.read_csv(local_path)
    elif filetype == 'parquet':
        output = pd.read_parquet(local_path)
    os.remove(local_path)

    return output

def df_to_objstore(df, objpath, onprem=False):
    filename = objpath.split("/")[-1]
    filetype = filename.split(".")[-1]
    if onprem:
        local_path = objpath
    else:
        local_folder = 'raw_data/temp_file'
        if not os.path.exists(local_folder):
            os.makedirs(local_folder)
        local_path = os.path.join(local_folder,filename)
    if filetype == 'csv':
        df.to_csv(local_path)
    elif filetype == 'parquet':
        df.to_parquet(local_path)
    if not onprem:
        ostore.put_object(local_path=local_path, ostore_path=objpath)
        os.remove(local_path)

def update_data(data, newdata):
    #Add extra columns for any stations not already in dataframe:
    if len(data.columns)>0:
        old_col = set(data.columns)
        new_col = [x for x in newdata.columns if x not in old_col]
    else:
        new_col = newdata.columns
    if len(new_col)>0:
        new_col_df = pd.DataFrame(data=None,index=data.index,columns=new_col)
        data = pd.concat([data,new_col_df],axis=1)
    index_intersect = data.index.intersection(newdata.index)
    #newdata = newdata.loc[index_intersect]
    #data.loc[newdata.index,newdata.columns]=newdata
    data.loc[index_intersect,newdata.columns]=newdata.loc[index_intersect]

    return data

def get_summary(summary_fpath, year):
    summary_folder = os.path.dirname(summary_fpath)
    ostore_objs = ostore.list_objects(summary_folder,return_file_names_only=True)
    if summary_fpath not in ostore_objs:
        dt_range = pd.date_range(start = f'{year}/1/1', end = f'{year}/12/31', freq = 'D')
        summary = pd.DataFrame(data=None,index=dt_range,columns=None,dtype='float64')
    else:
        summary = objstore_to_df(summary_fpath)
        summary = summary.set_index(summary.columns[0])
        summary.index = pd.to_datetime(summary.index)
    return summary

def find_most_recent_image(obj_dirpath, obj_fpath, dt):
    olist = ostore.list_objects(dt.strftime(obj_dirpath),return_file_names_only=True)
    fname = dt.strftime(obj_fpath)
    while not any(fname in s for s in olist):
        dt = dt - timedelta(days=1)
        fname = dt.strftime(obj_fpath)
    return dt

#year = max([int(i.split('.')[0][-4:]) for i in ostore_objs]) + 1
#year = 2022

if __name__ == '__main__':
    ostore = NRObjStoreUtil.ObjectStoreUtil()

    today = datetime.today()
    year = int((today - timedelta(days=14)).strftime('%Y'))
    CLEVER_Summary_objfolder = 'snowpack_archive/summary'
    ostore_objs = ostore.list_objects(CLEVER_Summary_objfolder,return_file_names_only=True)
    CLEVER_summary_fpath = os.path.join(CLEVER_Summary_objfolder,f'CLEVER_Summary_{year}.csv')
    CLEVER_summary = get_summary(CLEVER_summary_fpath, year)

    if len(CLEVER_summary.columns) == 0:
        startdate = datetime(year,1,1)
    else:
        startdate = CLEVER_summary.index[CLEVER_summary.isna().any(axis=1)][0]

    objpath = 'snowpack_archive/cloud_filled/%Y/%Y.%m.%d.tif'

    clever_shp_path = 'aoi/clever_basins/CLEVER_BASINS.shp'
    clever_shp = geopandas.read_file(clever_shp_path)
    if int((today).strftime('%Y')) > year:
        enddate = datetime(year,12,31)
    else:
        enddate = find_most_recent_image(os.path.dirname(today.strftime(objpath)), objpath, today)
    importdates = pd.date_range(start = startdate, end = enddate)
    if len(importdates) > 0:
        output = pd.DataFrame(data=None, index = importdates, columns = clever_shp.WSDG_ID)
        colnames = output.columns
        for dt in importdates:
            objname = dt.strftime(objpath)
            filename = objname.split('/')[-1]
            local_filename = os.path.join('rawdata',filename)
            ostore.get_object(local_path=local_filename, file_path=objname)
            print(f'Reading {local_filename}')
            with rasterio.open(local_filename) as grib:
                    raster = grib.read(1)
                    affine = grib.transform
                    zone = clever_shp.to_crs(grib.crs)
                    #Rasterstats averages all pixels which touch the polygon, or all pixels whose centoids are within the polygon
                    #For exact averaging, weighting pixels by fraction within polygon, investigate this package:
                    #https://github.com/isciences/exactextract
                    raster[raster>100] = 255
                    stats = rasterstats.zonal_stats(zone, raster, affine=affine,stats="mean",all_touched=True,nodata=255)
                    for j in range(len(stats)):
                        output.loc[dt,colnames[j]] = stats[j]['mean']


        CLEVER_summary = update_data(CLEVER_summary, output)
        #df_to_objstore(CLEVER_summary, CLEVER_summary_fpath, onprem=False)
        df_to_objstore(CLEVER_summary, CLEVER_summary_fpath, onprem=False)



