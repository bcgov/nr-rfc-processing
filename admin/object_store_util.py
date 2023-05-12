import logging
import minio
import NRUtil.NRObjStoreUtil
import admin.snow_path_lib
import os.path
import admin.constants

LOGGER = logging.getLogger(__name__)


class OStore:
    def __init__(self):
        self.ostore = NRUtil.NRObjStoreUtil.ObjectStoreUtil()
        self.historical_norms_path = "norm/{sat}/daily/{period}/{month}.{day}.tif"
        self.snow_path = admin.snow_path_lib.SnowPathLib()

    def get_10yr_tif(self, sat, month, day, out_path):
        if not os.path.exists(out_path):
            ostore_path = self.historical_norms_path.format(
                period="10yr", month=month, day=day, sat=sat
            )
            LOGGER.debug(f"pulling the 10yr file: {ostore_path} down from obj store")
            self.ostore.get_object(file_path=ostore_path, local_path=out_path)

    def get_20yr_tif(self, sat, month, day, out_path):
        if not os.path.exists(out_path):

            ostore_path = self.historical_norms_path.format(
                period="20yr", month=month, day=day, sat=sat
            )
            LOGGER.debug(f"pulling the 20yr file: {ostore_path} down from obj store")
            self.ostore.get_object(file_path=ostore_path, local_path=out_path)

    def get_mosaic_plot_dir(self, date: str, sat: str):
        ostore_util = NRUtil.NRObjStoreUtil.ObjectStoragePathLib()

        if sat.lower() == 'modis':
            plot_dir = admin.constants.PLOT_MODIS_MOSAIC
        elif sat.lower() == 'viirs':
            plot_dir = admin.constants.PLOT_VIIRS_MOSAIC
        else:
            msg = f'unknown sat type: {sat}'
            raise ValueError(msg)
        # ./data/plot/modis/mosaic/2023.03.21/2023.03.21.png
        ostore_util = NRUtil.NRObjStoreUtil.ObjectStoragePathLib()
        os_plot_dir = ostore_util.remove_sr_root_dir(plot_dir, admin.constants.TOP)
        expected_ostore_path = os.path.join(
            admin.constants.OBJ_STORE_TOP, os_plot_dir, date)
        return expected_ostore_path

    def mosaic_plot_exists(self, date: str, sat: str):
        """returns a boolean if the expected plot exists in object storage or not

        :param date: date string in the format YYYY.MM.DD
        :type date: str
        :param sat: satellite type, allowed values (modis | viirs)
        :type sat: str
        :raises ValueError: _description_
        """
        file_exists = False
        plot_file_name = f'{date}.png'
        expected_ostore_path = self.get_mosaic_plot_dir(date=date, sat=sat)

        # ./data/plot/modis/mosaic/2023.03.21/2023.03.21.png
        files_in_ostore = self.ostore.list_objects(
            objstore_dir=expected_ostore_path,
            recursive=True,
            return_file_names_only=True)
        just_file_names = [os.path.basename(plot_file) for plot_file in files_in_ostore]
        if plot_file_name in just_file_names:
            file_exists = True
        return file_exists

    def push_daily_mosaic_plot(self, date, sat, local_path):
        """_summary_

        :param date: _description_
        :type date: _type_
        :param sat: _description_
        :type sat: _type_
        :param local_path: _description_
        :type local_path: _type_
        """
        if not os.path.exists(local_path):
            msg = f'Trying to push the file: {local_path} but it doesn\'t exist'
            ValueError(msg)
        plot_file_name = f'{date}.png'
        plot_dir_name = self.get_mosaic_plot_dir(date=date, sat=sat)
        ostore_full_path = os.path.join(plot_dir_name, plot_file_name)

        self.ostore.put_object(
            ostore_path=ostore_full_path,
            local_path=local_path
        )

    def process_modis_data_exists(self, date, dates):
        """identifies if the data that is going to be used to generate modis
        plots exists in object storage.

        :param date: _description_
        :type date: _type_
        :param dates: _description_
        :type dates: _type_
        """
        # self.snow_path.
        # self.get_mod
        pass
