# Centralize the calculation of file paths

import os.path
import admin.constants as const
import glob
import re


import logging

LOGGER = logging.getLogger(__name__)

class SnowPathLib:

    def __init__(self):
        pass

    def get_modis_product_version(self):
        """
        The daily gridded snow cover product contains the ‘best’
        NDSI_Snow_Cover, snow albedo and QA observation selected from all the
        M*D10_L2 swaths mapped into a grid cell on the sinusoidal projection in
        the M*D10GA

        version 6 is discontinued... https://nsidc.org/data/mod10a1/versions/6
        revised / new version is 6.1 or 61

        product is MOD10A1
        version is 61
        """
        product, version = const.MODIS_PRODUCT.split('.')
        return product, version



    def get_modis_MOD10A1V6(self):
        # TODO: path should be derived from const.DEFAULT_PRODUCT
        product, version = self.get_modis_product_version()
        version_zero_padded = version.rjust(3, '0')
        modis_dir = f'{product}.{version_zero_padded}'

        pth = os.path.join(const.MODIS_TERRA, modis_dir)
        return pth

    def get_modis_int_tif(self, date):
        int_tif_dir = os.path.join(const.INTERMEDIATE_TIF_MODIS, date)
        return int_tif_dir

    def get_viirs_int_tif(self, date):
        int_tif_dir = os.path.join(const.INTERMEDIATE_TIF_VIIRS, date)
        return int_tif_dir

    def get_viirs_VNP10A1F_001(self):
        pth = os.path.join(const.MODIS_TERRA, 'VNP10A1F.001')
        return pth

    def get_viirs_granules(self, date):
        root_pth = self.get_viirs_VNP10A1F_001()
        glob_pattern = os.path.join(root_pth, date,  '*.h5')
        viirs_granules = glob.glob(os.path.join(glob_pattern))
        return viirs_granules

    def get_intermediate_viirs_files(self, date):
        viirs_dir = self.get_viirs_int_tif(date)
        glob_pattern = os.path.join(viirs_dir, '*.tif')
        int_viirs_tifs = glob.glob(glob_pattern)
        return int_viirs_tifs

    def get_modis_granules(self, date):
        """reads all the files in the directory defined for the modis data,
        runs a filter on the returned files looking for files that are similar to
        the following:

        * MOD10A1.A2023076.h10v03.061.2023078031536.hdf
        * MOD10A1.A2023076.h20v01.061.2023078032625.hdf
        * MOD10A1.A2023076.h23v02.061.2023078031918.hdf
        etc...

        Following is an example of a file that could be in the directory but should
        not be returned in the list:

        * modis_composite_2023.03.21_2023.03.20_2023.03.19_2023.03.18_2023.03.17.tif

        :param date: _description_
        :type date: _type_
        :return: _description_
        :rtype: _type_
        """
        mod_path = self.get_modis_MOD10A1V6()
        files_in_granule_directory = glob.glob(os.path.join(mod_path, date,'*.hdf'))
        modis_granules = self.filter_for_modis_granules(files_in_granule_directory, suffix='hdf')
        return modis_granules

    def filter_for_modis_granules(self, file_list, suffix='hdf'):
        """
        recievesd a list of files and filters out files that have the following name
        pattern:

        * MOD10A1.A2023076.h10v03.061.2023078031536.hdf
        * MOD10A1.A2023076.h20v01.061.2023078032625.hdf
        * MOD10A1.A2023076.h23v02.061.2023078031918.hdf
        etc...

        Following is an example of a file that could be in the directory but should
        not be returned in the list:

        * modis_composite_2023.03.21_2023.03.20_2023.03.19_2023.03.18_2023.03.17.tif


        :param file_list: _description_
        :type file_list: _type_
        """
        if suffix[0] == '.':
            suffix = suffix.replace('.', '')
        granule_regex_pattern = '^(MOD10A1\.)A\d{7}\.h\d{2}v\d{2}\.\d{3}\.\d{13}.*\.' + suffix
        granule_pattern = re.compile(granule_regex_pattern)
        modis_granules = []
        for granule in file_list:
            granule_file_only = os.path.basename(granule)
            if granule_pattern.match(granule_file_only):
                modis_granules.append(granule)
            else:
                LOGGER.warning(f"omitting the following file from list: {granule}")
        return modis_granules

    def get_output_modis_path(self, date:str):
        year = date.split(".")[0]
        file_name = f"{date}.tif"
        out_pth = os.path.join(
            const.OUTPUT_TIF_MODIS, year, file_name
        )
        return out_pth

    def get_modis_mosaic_composite(self, date):
        modis_dir = os.path.join(const.INTERMEDIATE_TIF_MODIS, date)
        modis_glob_pattern = os.path.join(modis_dir, "modis_composite*.tif")
        mosaic = glob.glob(modis_glob_pattern)
        # should only be one file, so grabbing the first one
        first_entry = mosaic[0]
        return first_entry

    def file_name_no_suffix(self, input_path):
        """expects a path that looks like this:
        './data/watersheds/Stikine/shape/EPSG4326/Stikine.shp'

        and extracts the file name at the end of the path without a suffix,
        so given path above returns 'Stikine'

        :param watershed_path: input path
        :type watershed_path: str / path
        """
        # name = os.path.split(shed)[-1].split('.')[0]
        path_base = os.path.basename(input_path)
        path_base_no_suffix = os.path.splitext(path_base)[0]
        return path_base_no_suffix

