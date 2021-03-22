import click
import os
import datetime
import time
import calendar

from run import dailypipeline
from .support import date_fmt

from admin import buildup, teardown
from analysis import calculate_snow_coverage


def run(envpth: str, sat: str, year: int):
    dates = []
    for month in range(1,13):
        for day in range(1, (calendar.monthrange(int(year), int(month))[1])+1):
            dates.append(date_fmt(str(datetime.date(int(year), int(month), int(day)))))
    
    start = time.time()
    buildup.buildall()
    count = 0
    for date in dates:
        try:
            dash = '-'
            print(f'{dash*10}\n{date}\n{dash*10}')
            dailypipeline(envpth, date, sat)
            #if count % 5 == 0:
            #    teardown.clean_downloads()
        except Exception as e:
            print(e)
            continue

    #teardown.clean_intermediate()
    #teardown.cleanup_outputs()
    #buildup.build_dir_structure()
    print(f'{dash*20}\nTIME TAKEN: { datetime.timedelta(seconds=time.time()-start)}\n{dash*20}')
    