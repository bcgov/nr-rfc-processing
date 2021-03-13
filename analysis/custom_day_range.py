import click
import os
import datetime
import time

from run import dailypipeline
from .support import date_fmt

from admin import buildup, teardown
from analysis import calculate_snow_coverage

def run(envpth: str, sat: str, startdate: str, days: int):
    start = time.time()
    dash = '-'
    if startdate == date_fmt(str(datetime.datetime.today())):
        startdate = date_fmt(str(datetime.datetime.today()-datetime.timedelta(days=2)))
    dates = [startdate]
    datelist = list(map(int, startdate.split('.')))
    for i in range(1, days):
        dates.append(date_fmt(str(
            datetime.datetime(datelist[0], datelist[1], datelist[2]) 
            - datetime.timedelta(days=i))))

    #buildup.buildall()
    count = 0
    for date in dates:
        try:
            
            print(f'{dash*10}\n{date}\n{dash*10}')
            dailypipeline(envpth, date, sat)
            #if count % 5 == 0:
                #teardown.clean_downloads()
        except Exception as e:
            print(e)
            continue

    #teardown.clean_intermediate()
    #teardown.cleanup_outputs()
    #buildup.build_dir_structure()
    
    print(f'{dash*20}\nTIME TAKEN: { datetime.timedelta(seconds=time.time()-start)}\n{dash*20}')