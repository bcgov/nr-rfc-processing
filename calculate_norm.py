import os
import datetime
import calendar
import click
import logging

import numpy as np
import xarray as xr
import rioxarray as rioxr


from collections import defaultdict
from glob import glob

import admin.constants as const

from analysis.support import date_fmt

logger = logging.getLogger('snow_mapping')

def get_dates(start_year: int, months: int):
    """Get dates to calculate normals on

    Parameters
    ----------
    start_year : int
        Start year to start normal calculations from
    months : int
        Number of months from January to consider 

    Returns
    -------
    list
        List of dates to process
    """
    dates = []
    for year in range(start_year, start_year+1):
        for month in range(1,months+1):
            for day in range(1, (calendar.monthrange(int(year), int(month))[1])+1):
                dates.append(date_fmt(str(datetime.date(int(year), int(month), int(day)))))
    return dates

def get_days(rng: int):
    """Get days of each year

    Parameters
    ----------
    rng : int
        Range to consider for calculations [10 | 20]

    Returns
    -------
    defaultdict(list)
        Dictionary of lists containing annual temporal dates for month-day
    """
    dates = defaultdict(list)
    thisyr = datetime.datetime.now().year
    for year in range(thisyr-rng, thisyr):
        for month in range(1,13):
            for day in range(1, (calendar.monthrange(int(year), int(month))[1])+1):
                dates[f'{month}_{day}'].append(date_fmt(str(datetime.date(int(year), int(month), int(day)))))
    return dates

def get_file_pths(dates: list, sat: str):
    """Gather files to open

    Parameters
    ----------
    dates : list
        Dates to consider when gathering paths
    sat : str
        Target satellite [modis | viirs]

    Returns
    -------
    list
        list of all dates to process
    """
    mosaics = []
    for date in dates:
        try:
            year = date.split('.')[0]
            mosaics.append(glob(os.path.join(const.MODIS_TERRA,'mosaics',sat, year, f'{date}.tif'))[0])
        except:
            continue
    return mosaics

def read_lazy(pth: str):
    """Lazy read of geotiff to lessen pressure on memory

    Parameters
    ----------
    pth : str
        Path of geotiff to open

    Returns
    -------
    xr.DataArray
        opened xarray.DataArray
    """
    xchunk = 2048
    ychunk = 2048
    da = rioxr.open_rasterio(pth, chunks={'band': 1, 'x': xchunk, 'y': ychunk})
    da.data[(da.data > 100)] = np.nan
    return da

@click.command()
@click.option('--rng', type=click.Choice(['10','20']), help='Range to calculate normal for (10 or 20 years).')
@click.option('--sat', type=const.SATS, help='Target satellite to calculat seasonal normal for.')
def seasonal_norm(rng: str, sat: str):
    _seasonal_norm(rng, sat)

def _seasonal_norm(rng: int, sat: str):
    """Calculate Seasonal normals (Jan - July inclusive)

    Parameters
    ----------
    rng : int
        Range to consider to calculate normals [10 | 20]
    sat : str
        Target satellite [modis | viirs]
    """
    thisyr = datetime.datetime.now().year
    months = 7
    ds = xr.Dataset()
    for year in range(thisyr-int(rng), thisyr):
        dates = get_dates(year, months)
        mosaics = get_file_pths(year, dates)
        for pth in mosaics:
            src = os.path.split(pth)[-1]
            ds[src] = read_lazy(pth)
    mnth = ds.to_array(dim='mean').mean(dim='mean', skipna=True)
    out_pth = os.path.join(const.NORM, sat, 'seasonal', f'{rng}yr_seasonal.tif')
    try:
        os.makedirs(os.path.dirname(out_pth))
    except Exception as e:
        logger.debug(e)
    mnth.rio.to_raster(out_pth)
        
@click.command()
@click.option('--rng', type=click.Choice(['10','20']))
@click.option('--sat')
def daily_norm(rng: str, sat: str):
    _daily_norm(rng, sat)

def _daily_norm(rng: int, sat: str):
    """Calculate 10 or 20 year normals

    Parameters
    ----------
    rng : int
        Year range to consider [10 | 20]
    sat : str
        Target satellite [modis | viirs]
    """      
    dates = get_days(int(rng))
    base = os.path.join(const.NORM, sat, 'daily', f'{rng}yr')
    try:
        os.makedirs(os.path.dirname(base))
    except Exception as e:
        logger.debug(e)
    for k in dates.keys():
        mosaics = get_file_pths(dates[k], sat)
        ds = xr.Dataset()
        for pth in mosaics:
            src = os.path.split(pth)[-1]
            ds[src] = read_lazy(pth)
        el = os.path.split(mosaics[0])[-1].split('.')[:-1]
        day = ds.to_array(dim='mean').mean(dim='mean', skipna=True)
        day.rio.to_raster(os.path.join(base,f'{el[1]}.{el[2]}.tif'))

@click.command()
def build_dirs():
    _build_dirs()

def _build_dirs():
    """
    Local directory builder
    """
    top = os.path.join('/data','norm')
    modis = os.path.join(top, 'modis')
    mod_daily = os.path.join(modis, 'daily')
    mod_daily_10yr = os.path.join(mod_daily, '10yr')
    mod_daily_20yr = os.path.join(mod_daily, '20yr')
    mod_seasonal = os.path.join(modis, 'seasonal')
    viirs = os.path.join(top,'viirs')
    viirs_daily = os.path.join(viirs, 'daily')
    viirs_daily_10yr = os.path.join(viirs_daily, '10yr')
    viirs_daily_20yr = os.path.join(viirs_daily, '20yr')
    viirs_seasonal = os.path.join(viirs, 'seasonal')

    dirs = [
        mod_daily_10yr,
        mod_daily_20yr,
        mod_seasonal,
        viirs_daily_10yr,
        viirs_daily_20yr,
        viirs_seasonal
    ]

    for d in dirs:
        try:
            os.makedirs(d)
        except Exception as e:
            logger.debug(e)
    
@click.command()
def calculate_norms():
    """
    Trigger to calculate both 10 and 20 year normals
    """
    _build_dirs()
    for sat in ['modis','viirs']:
        for rng in [10, 20]: # years
            daily_norm(rng, sat)
            #seasonal_norm(rng, sat)

@click.group()
def cli():
    pass

cli.add_command(build_dirs)
cli.add_command(calculate_norms)
cli.add_command(daily_norm)
cli.add_command(seasonal_norm)

if __name__ == '__main__':
    cli()
