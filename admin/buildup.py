import os
import logging

import geopandas as gpd

import admin.constants as const

logger = logging.getLogger(__name__)

def build_dir_structure():
    dirs= [
        const.TOP,
        const.LOG,
        const.BASINS,
        const.WATERSHEDS,
        const.KML,
        const.INTERMEDIATE_KML,
        const.INTERMEDIATE_TIF,
        const.INTERMEDIATE_TIF_MODIS,
        const.INTERMEDIATE_TIF_VIIRS,
        const.INTERMEDIATE_TIF_SENTINEL,
        const.INTERMEDIATE_TIF_PLOT,
        const.NORM,
        const.MOSAICS,
        const.MODIS_DAILY_10YR,
        const.MODIS_DAILY_20YR,
        const.VIIRS_DAILY_10YR,
        const.VIIRS_DAILY_20YR,
        const.MOSAICS,
        const.OUTPUT_TIF_MODIS,
        const.OUTPUT_TIF_VIIRS,
        const.PLOT,
        const.PLOT_MODIS,
        const.PLOT_MODIS_MOSAIC,
        const.PLOT_MODIS_WATERSHEDS,
        const.PLOT_MODIS_BASINS,
        const.PLOT_VIIRS,
        const.PLOT_VIIRS_MOSAIC,
        const.PLOT_VIIRS_WATERSHEDS,
        const.PLOT_VIIRS_BASINS,
        const.PLOT_SENTINEL,
        const.ANALYSIS,
        const.SENTINEL_OUTPUT
    ]

    for d in dirs:
        if not os.path.exists(d):
            os.makedirs(d)

def build_shapefiles(typ, dataset):
    gdf = gpd.read_file(dataset)
    for crs in ['EPSG:4326', 'EPSG:3153']:
        gdf = gdf.to_crs(crs)
        if typ == 'basins':
            objs = gdf.WSDG_NAME.unique()
            col = 'WSDG_NAME'
            base = const.BASINS
        elif typ == 'watersheds':
            objs = gdf.basinName.unique()
            col = 'basinName'
            base = const.WATERSHEDS
        for name in objs:
            logger.info(f'Creating supporting files for {name}')
            tmp = gdf[gdf[col] == name]
            name = name.translate({ord("("): None, ord(")"):None})
            name = "_".join(name.replace('.','').split(" "))

            out_dir = os.path.join(base, name)
            if not os.path.exists(out_dir):
                os.makedirs(os.path.join(base, name))

            pths = ['shape', os.path.join('shape', crs.replace(':', '')), 'modis', 'viirs']
            for pth in pths:
                tmp_path = os.path.join(base, name, pth)
                if not os.path.exists(tmp_path):
                    os.makedirs()

            output_file_name = os.path.join(base, name, 'shape', crs.replace(':', ''), f'{name}.shp')
            if not os.path.exists(output_file_name):
                tmp.to_file()

def buildall():
    logger.info('Building up directory structure')
    build_dir_structure()
    clever_basins_dir = os.path.join(const.AOI, 'clever_basins')
    if not os.path.exists(clever_basins_dir):
        os.makedirs(clever_basins_dir)

    build_shapefiles('basins', os.path.join(clever_basins_dir, 'CLEVER_BASINS.shp'))

    watersheds_dir = os.path.join(const.AOI, 'watersheds')
    if not os.path.exists(watersheds_dir):
        os.makedirs(watersheds_dir)

    #build_shapefiles('watersheds', os.path.join(watersheds_dir, 'Export_Output_SBIMap.shp'))

    logger.info('Building supporting files')
    build_shapefiles('basins', os.path.join(const.AOI, 'basins','CLEVER_BASINS.shp'))
    build_shapefiles('watersheds', os.path.join(const.AOI, 'watersheds','Export_Output_SBIMap.shp'))
