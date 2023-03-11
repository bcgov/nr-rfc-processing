# Centralize the calculation of file paths

import os.path
import admin.constants as const
import glob


import logging

class SnowPathLib:

    def __init__(self):
        pass

    def get_modis_MOD10A1V6(self):
        pth = os.path.join(const.MODIS_TERRA, 'MOD10A1.006')
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
        mod_path = self.get_modis_MOD10A1V6()
        modis_granules = glob.glob(os.path.join(mod_path, date,'*.hdf'))
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

