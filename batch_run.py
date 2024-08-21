"""
This script is used to manually run a set of dates.  Under normal circumstances
you shouldn't need to use this script, but in the event that bad data is encountered
by the GHA runs, or if the GHA runs get disabled for a period of time and a bunch of
data needs to be generated, this script can be used to fill those holes.
"""

import datetime
import json
import logging

LOGGER = logging.getLogger(__name__)

# the range of dates to run
min_date = datetime.datetime(2024, 5, 18)
max_date =  datetime.datetime(2024, 6, 10)

class BulkRun():

    def __init__(self, min_date, max_date):
        self.min_date = min_date
        self.max_date = max_date

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
            LOGGER.info(f"running date: {date}")
            # do the run here
            # run_date(date)

    def run_date(self, date):
        """
        run the date
        """
        LOGGER.info(f"running date: {date}")
        

if __name__ == '__main__':
    br = BulkRun(min_date, max_date)
    date_list = br.get_date_list()
    LOGGER.info(f"running dates: {date_list}")
    print(json.dumps(date_list, default=str))
