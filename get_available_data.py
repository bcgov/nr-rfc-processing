"""
to be used in conjunction with a pipeline, simple script that will return
to stdout a JSON data struct that identifies the difference between data that
is available and data that has already been processed.

To determine what data has been processes looks at the plots directory

"""

import admin.object_store_util
import admin.snow_path_lib
import logging
import datetime
import os

LOGGER = logging.getLogger(__name__)

# args that need to be sent
sat = 'modis'



class DataAvailability:

    def __init__(self):
        self.snow_path_lib = admin.snow_path_lib.SnowPathLib()
        self.ostore = admin.object_store_util.OStore()

    def get_latest_wat_bas_plot_dir(self, sat: str, wat_basin: str):
        """looks for the latest plot dir for either a watershed or
        basin.  Looks into the
        """
        wat_basin = 'watersheds'
        plot_dir = self.snow_path_lib.get_plot_dir(
            sat=sat,
            watershed_basin=wat_basin)
        LOGGER.debug(f"plot_dir : {plot_dir}")
        ostore_path = self.ostore.get_ostore_path(local_path=plot_dir)
        return ostore_path

    def get_latest_dir_date(self, ostore_dir):

        # get the latest folder date from obj store, will re-run that date to be certain.
        high_date = None
        cur_date = None
        ostore_dirs = self.ostore.ostore.list_objects(
            objstore_dir=ostore_dir,
            recursive=False,
            return_file_names_only=True)

        for ostore_dir in ostore_dirs:
            date_str = os.path.basename(ostore_dir)
            # remove any trailing '/' characters
            if (not date_str) and ostore_dir[-1] == os.path.sep:
                ostore_dir = ostore_dir[:-1]
                date_str = os.path.basename(ostore_dir)
            if (date_str) and date_str.replace('.', '').isdigit():
                cur_date = datetime.datetime.strptime(date_str, '%Y.%m.%d')
                if (high_date is None) or cur_date > high_date:
                    high_date = cur_date
        LOGGER.debug(f"high date: {high_date}")
        return high_date

    def run(self):
        # inlcude a more detailed check here as we don't want to re-run a date if it has
        # already been completed.
        pass
        LOGGER.debug("pass")

    def get_granules(self, sat: str, start_date_str: str):
        """once its known when the last date for data was calculated then

        :param sat: _description_
        :type sat: str
        :param start_date_str: _description_
        :type start_date_str: str
        """
        dates = []
        cur_date_str = start_date_str
        cur_date = datetime.datetime.strptime(cur_date_str, '%Y.%m.%d')
        while 1:
            grans = self.snow_path_lib.get_granules(date=cur_date_str, sat=sat, dates=[cur_date_str])
            if grans:
                dates.append(cur_date)
                cur_date = cur_date + datetime.timedelta(days=1)
                cur_date_str = cur_date.strftime('%Y.%m.%d')
            else:
                # exit
                break
        LOGGER.debug(f"dates to process {dates} for sat: {sat}")
        return dates


if __name__ == '__main__':

    # config root logger for debug for dev
    LOGGER = logging.getLogger()
    LOGGER.setLevel(logging.DEBUG)
    hndlr = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(lineno)d - %(message)s')
    hndlr.setFormatter(formatter)
    LOGGER.addHandler(hndlr)
    LOGGER.debug("test")


    sat = 'modis'
    wat_basin = 'watersheds'

    # this is a first kick at running based on availability.  Doesn't go into depth
    # on the files that are available to verify that the run for the sat/watershed
    # completed.
    # that said running the latest day provides some overlap and the script should skip
    # over a lot of stuff until it completes
    da = DataAvailability()
    ostr_dir = da.get_latest_wat_bas_plot_dir(sat=sat, wat_basin=wat_basin)
    latest_date = da.get_latest_dir_date(ostore_dir=ostr_dir)
    latest_date_str = latest_date.strftime('%Y.%m.%d')
    dates = da.get_granules(sat=sat, start_date_str=latest_date_str)
    LOGGER.debug(f"dates to process for modis: {dates}")

    # now try viirs
    sat = 'viirs'
    wat_basin = 'watersheds'
    ostr_dir = da.get_latest_wat_bas_plot_dir(sat=sat, wat_basin=wat_basin)
    latest_date = da.get_latest_dir_date(ostore_dir=ostr_dir)
    latest_date_str = latest_date.strftime('%Y.%m.%d')
    dates = da.get_granules(sat=sat, start_date_str=latest_date_str)
    LOGGER.debug(f"dates to process for viirs: {dates}")


