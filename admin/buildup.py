import os

import geopandas as gpd

from admin.constants import Constants

const = Constants()

def build_dir_structure():
    dirs= [
        const.top,
        const.basins,
        const.watersheds,
        const.kml,
        const.intermediate_kml,
        const.intermediate_tif,
        const.intermediate_tif_modis,
        const.intermediate_tif_viirs,
        const.intermediate_tif_sentinel,
        const.intermediate_tif_plot,
        const.output_tif,
        const.output_tif_modis,
        const.output_tif_viirs,
        const.output_tif_sentinel,
        const.plot,
        const.plot_modis,
        const.plot_modis_mosaic,
        const.plot_modis_watersheds,
        const.plot_modis_basins,
        const.plot_viirs,
        const.plot_viirs_mosaic,
        const.plot_modis_watersheds,
        const.plot_viirs_basins,
        const.plot_sentinel,
        const.analysis
    ]

    for d in dirs:
        try:
            os.makedirs(d)
        except Exception as e:
            print(e)

def build_shapefiles(typ, dataset):
    gdf = gpd.read_file(dataset)
    for crs in ['EPSG:4326', 'EPSG:3153']:
        gdf = gdf.to_crs(crs)
        if typ == 'basins':
            objs = gdf.WSDG_NAME.unique()
            col = 'WSDG_NAME'
            base = const.basins
        elif typ == 'watersheds':
            objs = gdf.basinName.unique()
            col = 'basinName'
            base = const.watersheds
        for name in objs:
            print(f'Creating supporting files for {name}')
            tmp = gdf[gdf[col] == name]
            name = name.translate({ord("("): None, ord(")"):None})
            name = "_".join(name.replace('.','').split(" "))
            try:
                os.makedirs(os.path.join(base, name))
            except Exception as e:
                pass
            pths = ['shape', os.path.join('shape', crs.replace(':', '')), 'modis', 'viirs']
            for pth in pths:
                try:
                    os.makedirs(os.path.join(base, name, pth))
                except:
                    continue
            tmp.to_file(os.path.join(base, name, 'shape', crs.replace(':', ''), f'{name}.shp'))

def buildall():
    build_dir_structure()
    build_shapefiles('basins', os.path.join('aoi','clever_basins','CLEVER_BASINS.shp'))
    build_shapefiles('watersheds', os.path.join('aoi','watersheds','Export_Output_SBIMap.shp'))