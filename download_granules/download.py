import datetime
import calendar

from analysis.support import date_fmt
from .download_granules import download_granules

def year(envpth: str, sat: str, year: str):
    """
    Download a year's worth of granules within the AOI bounding box
    for a given sattelite source

    Parameters
    ----------
    envpth : str
        Path to credential file
    sat : str
        Satellite [modis | viirs]
    year : str
        Target year to download
    """
    dates = []
    for month in range(1,13):
        for day in range(1, (calendar.monthrange(int(year), int(month))[1])+1):
            dates.append(date_fmt(str(datetime.date(int(year), int(month), int(day)))))
    for date in dates:
        download_granules(envpth, date, sat, 1)

def month(envpth: str, sat: str, month: str, year: str):
    """
    Download a month's worth of granules within the AOI bounding
    box for a given satellite source

    Parameters
    ----------
    envpth : str
        Path to credential file
    sat : str
        Satellite [modis | viirs]
    month : str
        Target month to download
    year : str
        Target year to download
    """
    days = calendar.monthrange(int(year), int(month))[1]
    dates = [date_fmt(str(datetime.date(int(year), int(month), int(day)))) for day in range(1, int(days)+1)]
    for date in dates:
        download_granules(envpth, date, sat, 1)

def twenty_year(envpth: str, sat: str):
    dates = []
    for year in range(2000, 2022):
        for month in range(1,13):
            for day in range(1, (calendar.monthrange(int(year), int(month))[1])+1):
                dates.append(date_fmt(str(datetime.date(int(year), int(month), int(day)))))
    for date in dates:
        download_granules(envpth, date, sat, 1)
