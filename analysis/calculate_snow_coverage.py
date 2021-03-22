import os
import datetime
import sqlite3
import csv

import pandas as pd
import rasterio as rio
import numpy as np

from glob import glob

from admin.constants import Constants

const = Constants()

def init_db():
    try:
        conn = sqlite3.connect(os.path.join(const.analysis,'analysis.db'))
        cur = conn.cursor()
    except sqlite3.Error as e:
        print(f'CONNECTION ERR: {e}')
        return 0
    try:   
        create_modis = """ CREATE TABLE IF NOT EXISTS modis (
                                        id integer PRIMARY KEY,
                                        name text NOT NULL,
                                        date_ date,
                                        snow_coverage real,
                                        nodata real,
                                        below_threshold real
                                    ); """
        cur.execute(create_modis)
        conn.commit()
    except sqlite3.Error as e:
        print(f'MODIS TABLE: {e}')
    try:
        create_virs = """ CREATE TABLE IF NOT EXISTS viirs (
                                        id integer PRIMARY KEY,
                                        name text NOT NULL,
                                        date_ date,
                                        snow_coverage real,
                                        nodata real,
                                        below_threshold real
                                    ); """
        cur.execute(create_virs)
        conn.commit()
    except sqlite3.Error as e:
        print(f'VIIRS TABLE: {e}')

def calc(typ, sat, date):
    try:
        conn = sqlite3.connect(os.path.join(const.analysis,'analysis.db'))
        c = conn.cursor()
    except sqlite3.Error as e:
        print(f'CONNECTION ERR: {e}')
        return 0

    watersheds = glob(os.path.join('/data',typ, '**'))

    cols = ['name', 'date', 'snow_coverage', 'nodata', 'below_threshold', 'satellite']

    for watershed in watersheds:
        watershed_name = os.path.split(watershed)[-1]
        watershed = glob(os.path.join(watershed, sat, date, '*_EPSG3153.tif'))
        if len(watershed) == 0:
            print(f"[MISSING] {watershed}")
            continue
        else:
            watershed = watershed[0]
            with rio.open(watershed) as src:
                print(f'ANALYZING {watershed_name}')
                src = src.read(1)
            nodata =  np.around(((src > 100).sum()/(src.shape[0]*src.shape[1]))*100, 6)
            below_threshold =  np.around(((src <= 20).sum()/(src.shape[0]*src.shape[1]))*100, 6)
            src[src > 100] = 0
            src[src <= 20] = 0
            src[src > 0] = 1
            land = src.shape[0]*src.shape[1]
            coverage = np.around(src.sum()/land, decimals=6)*100
            #date = datetime.datetime.strptime(date, "%Y.%m.%d").strftime(date, '%Y.%m.%d')
            insert = f"""INSERT OR REPLACE INTO {sat}(
                id, name, date_, snow_coverage, nodata, below_threshold
            ) VALUES(
                (SELECT id FROM {sat} WHERE name='{watershed_name}' AND date_='{date}'),'{watershed_name}', '{date}', {coverage}, {nodata}, {below_threshold}
            );
            """
            c.execute(insert)
            conn.commit()

    conn.close()

def db_to_csv():
    conn = sqlite3.connect(os.path.join('/data','analysis','analysis.db'))
    df_modis = pd.read_sql(f"SELECT * FROM modis", conn)
    df_modis['satellite'] = 'modis'
    df_viirs = pd.read_sql(f"SELECT * FROM viirs", conn)
    df_viirs['satellite'] = 'viirs'
    df = pd.concat([df_modis, df_viirs])
    df.to_csv(os.path.join('/data','analysis','analysis.csv'), index=False)
    conn.close()
