# Centralize the calculation of file paths

import os.path
import admin.constants as const
import glob
import re
import download_granules.download_granules_ostore_integration as dl_grans
import download_granules.download_config as dl_config
import osgeo.ogr

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

    def get_modis_int_tif_dir(self, date):
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

    def get_mosaic_dir(self, date, sat):
        """ returns the directory where the mosaic'd versions of the tif are located
        """
        if sat == 'modis':
            rootdir = const.MODIS_NORM
        else:
            rootdir = const.VIIRS_NORM
        mosaic_dir = os.path.join(rootdir, date)
        return mosaic_dir

    def get_mosaic_file(self, date, sat):
        mosaic_dir = self.get_mosaic_dir(date=date, sat=sat)
        mosaic_file = os.path.join(mosaic_dir, f"{date}.tif")
        return mosaic_file

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

    def get_modis_reprojected_tif(self, input_source_path: str, date_str: str, projection='EPSG:4326'):
        pth_file_noext = self.file_name_no_suffix(input_source_path)
        output_file_name = f'{pth_file_noext}_{projection.replace(":", "")}.tif'
        int_tif_dir = self.get_modis_int_tif_dir(date_str)
        intermediate_tif = os.path.join(
            int_tif_dir,
            output_file_name)
        return intermediate_tif

    def get_modis_composite_mosaic_file_name(self, start_date, date_list: list[str]):
        base = self.get_modis_int_tif_dir(start_date)
        file_name = f'modis_composite_{"_".join(date_list)}.tif'
        out_pth = os.path.join(base, file_name)
        return out_pth

    def get_modis_intermediate_tifs(self, date):
        """reads the source directory where the granules should be located
        and returns a list of file names for the corresponding file paths
        after they have been projected to EPSG:4326.

        :param date: _description_
        :type date: _type_
        :return: _description_
        :rtype: _type_
        """
        int_tifs = []
        comp_dir = self.get_modis_int_tif_dir(date)
        grans = self.get_modis_granules(date)
        modis_granules_src_files = self.get_modis_granules(date)
        modis_granules_src_files_filtered = self.filter_for_modis_granules(modis_granules_src_files)
        for granule_path in modis_granules_src_files_filtered:
            int_tif = self.get_modis_reprojected_tif(granule_path, date, 'EPSG:4326')
            int_tifs.append(int_tif)
        return int_tifs

    def get_granules(self, date, dates, sat):
        # TODO: This needs to become the source of data queries
        # set it up with caching of data to speed up
        # wrap with different paths.
        # eliminate all glob calls, and use the data that
        # comes direct from the sat query.
                # get the granules
        if sat == 'modis':
            dl_sat_config = dl_config.SatDownloadConfig(
                date_span=len(dates),
                name='daily',
                sat='modis',
                date_str=date
            )
        elif sat == 'viirs':
            dl_sat_config = dl_config.SatDownloadConfig(
                date_span=len(dates),
                name='daily',
                sat='viirs',
                date_str=date
            )

        start_date = dl_sat_config.get_start_date()
        end_date = dl_sat_config.get_end_date()

        earthdata_user=const.EARTHDATA_USER,
        earthdata_pass=const.EARTHDATA_PASS,

        cmr_client = dl_grans.CMRClientOStore(
            earthdata_user=earthdata_user,
            earthdata_pass=earthdata_pass
            )
        earthdata_user=const.EARTHDATA_USER,
        earthdata_pass=const.EARTHDATA_PASS,

        cmr_client = dl_grans.CMRClientOStore(
            earthdata_user=earthdata_user,
            earthdata_pass=earthdata_pass
            )
        grans = cmr_client.query(
            dl_config = dl_sat_config
        )
        LOGGER.debug("got grans")

        return grans
        return grans

    def get_aoi_shp(self, wat_or_bas):
        if wat_or_bas.lower() == 'watersheds':
            # TODO: search for Export_Output_SBIMap.shp and replace with this method call
            aoi = os.path.join(const.AOI, 'watersheds', 'Export_Output_SBIMap.shp')
        elif wat_or_bas.lower() == 'basins':
            aoi = os.path.join(const.AOI, 'basins','CLEVER_BASINS.shp')
        else:
            msg = (
                f'invalid parameter sent for "wat_or_bas".  value sent: {wat_or_bas}' +
                'valid values: watersheds|basins' )
            raise ValueError(msg)
        return aoi

    def get_watershed_basin_list(self, wat_bas):
        """returns a list of either the watershed names or the basin names depending
        on the value of the parameter `wat_bas`

        :param wat_bas: whether to retrieve watershed names or basin names
        :type wat_bas: str
        :return: a list of either watershed names or basin names
        :rtype: list[str]
        """
        if wat_bas == 'watersheds':
            column = 'basinName'
        elif wat_bas == 'basins':
            column = 'WSDG_NAME'

        watershed_names = []
        shp_file_path = self.get_aoi_shp(wat_bas)
        shapefile = osgeo.ogr.Open(shp_file_path)
        layer = shapefile.GetLayer()
        for feature in layer:
            # Get the attributes of the feature
            basinName = feature.GetField(column)
            basinName = basinName.translate({ord("("): None, ord(")"):None})
            basinName = "_".join(basinName.replace('.','').split(" "))
            watershed_names.append(basinName)
        # required to close the file
        del shapefile
        watershed_names = list(set(watershed_names))
        return watershed_names

    def get_watershed_or_basin_path(self, start_date, watershed_basin, watershed_name, sat, projection):
        """combines the args sent to the method to calculate the output path.

        :param start_date: The start date in the patterh YYY.MM.DD
        :type start_date: str
        :param watershed_basin: either 'watershed' or 'basin' indicating what the type
                                is
        :type watershed_basin: str
        :param watershed_name: name of the watershed or basin
        :type watershed_name: str
        :param sat: type of satellite the path is being generated for (modis|viirs)
        :type sat: str
        :param projection: Name of the projection EPSG:4326 or EPSG:3153
        :type projection: _type_
        """
        # data/watersheds/Stikine/modis/2023.03.23/Stikine_modis_2023.03.23_EPSG4326.tif

        if watershed_basin == 'watersheds':
            top_dir = const.WATERSHEDS
        elif watershed_basin == 'basins':
            top_dir = const.BASINS
        # TODO: assert that watershed_basin in const.TYPS
        projection_str = projection.replace(":", '')
        file_name = f'{watershed_name}_{sat}_{start_date}_{projection_str}.tif'
        full_path = os.path.join(
            top_dir,
            watershed_name,
            sat,
            start_date,
            file_name)
        return full_path

    def get_plot_dir(self, sat, watershed_basin, date_str=None):
        # TODO: Go through plot code and move path calculation to this and other methods
        out_pth = os.path.join(const.PLOT, sat, watershed_basin)
        if date_str:
            out_pth = os.path.join(out_pth, date_str)
        return out_pth
    def get_plot_dir(self, sat, watershed_basin, date_str=None):
        # TODO: Go through plot code and move path calculation to this and other methods
        out_pth = os.path.join(const.PLOT, sat, watershed_basin)
        if date_str:
            out_pth = os.path.join(out_pth, date_str)
        return out_pth

    # def get_modis_mosaic_composite(self, date):
    #     modis_dir = os.path.join(const.INTERMEDIATE_TIF_MODIS, date)
    #     modis_glob_pattern = os.path.join(modis_dir, "modis_composite*.tif")
    #     mosaic = glob.glob(modis_glob_pattern)
    #     # should only be one file, so grabbing the first one
    #     first_entry = mosaic[0]
    #     return first_entry
