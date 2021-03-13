import click
import os
import datetime
import time
import calendar

from run import dailypipeline
from .support import date_fmt

from admin import buildup, teardown
from analysis import calculate_snow_coverage

def run(envpth: str, sat: str, year: int, month: int):
    days = calendar.monthrange(int(year), int(month))[1]
    dates = [date_fmt(str(datetime.date(int(year), int(month), int(day)))) for day in range(1, int(days)+1)]

    start = time.time()
    buildup.buildall()
    count = 0
    for date in dates:
        try:
            dash = '-'
            print(f'{dash*10}\n{date}\n{dash*10}')
            dailypipeline(envpth, date, sat)
        except Exception as e:
            print(e)
            continue

    #teardown.clean_intermediate()
    #teardown.cleanup_outputs()
    #buildup.build_dir_structure()
    print(f'{dash*20}\nTIME TAKEN: { datetime.timedelta(seconds=time.time()-start)}\n{dash*20}')

    