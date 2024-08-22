"""
This script is used to manually run a set of dates.  Under normal circumstances
you shouldn't need to use this script, but in the event that bad data is encountered
by the GHA runs, or if the GHA runs get disabled for a period of time and a bunch of
data needs to be generated, this script can be used to fill those holes.
"""

import datetime
import json
import logging
import sys
import run
import os

log_config_path = os.path.join(os.path.dirname(__file__), 'config', 'logging.config')
logging.config.fileConfig(log_config_path)

LOGGER = logging.getLogger(__name__)


class BulkRun():

    def __init__(self, min_date, max_date, sat):
        self.min_date = min_date
        self.max_date = max_date
        self.sat = sat

    def get_date_list(self):
        """
        get a list of dates between the min and max date, will include the min and
        the max dates in the list
        """
        date_list = []
        delta = max_date - min_date
        for i in range(delta.days + 1):
            day = min_date + datetime.timedelta(days=i)
            date_list.append(day)
        return date_list

    def do_run(self):
        date_list = self.get_date_list()
        for date in date_list:
            LOGGER.info(f"calling the running date: {date}")
            # do the run here
            self.run_date(date)

    def run_date(self, date):
        """
        run the date
        """
        LOGGER.info(f"running date: {date}")
        datestr = date.strftime("%Y.%m.%d")
        LOGGER.info(f'running download for date: {datestr}')
        run.down_load(sat=self.sat, date=datestr)
        LOGGER.info(f'running process for date: {datestr}')
        run.pro_cess(sat=self.sat, date=datestr, days=5)
        LOGGER.info(f'running plot for date: {datestr}')
        run.p_lot(sat=self.sat, date=datestr)

if __name__ == '__main__':

    # the range of dates to run
    min_date = datetime.datetime(2024, 5, 18)
    max_date =  datetime.datetime(2024, 6, 1)
    sat = 'viirs'

    br = BulkRun(min_date, max_date, sat)
    date_list = br.get_date_list()
    LOGGER.info(f"running dates: {date_list}")
    br.do_run()