import os
import simplekml
import zipfile
import logging

import rasterio as rio
import numpy as np

from glob import glob

from admin.color_ramp import color_ramp
from admin.db_handler import DBHandler

logger = logging.getLogger(__name__)

import admin.constants as const

def daily_kml(date: str, typ: str, sat: str, db_handler: DBHandler):
    """
    Apply color ramp and build KML's

    Parameters
    ----------
    date : str
        Target date to process
    typ : str
        Target type to process [watersheds | basins]
    sat : str
        Target satellite to process [modis | viirs]
    """
    sheds = glob(os.path.join(const.TOP, typ,'*'))
    for shed in sheds:
        for crs in ['EPSG4326', 'EPSG3153']:
            # Apply /data thresholding and balancing
            name = os.path.split(shed)[-1]
            shed_pth = os.path.join(const.TOP, typ, name, sat, date, f'{name}_{sat}_{date}_{crs}.tif')
            if not os.path.exists(shed_pth):
                logger.warning(f'Could not find {shed_pth}')
                continue            
            intermediate_pth = os.path.join(const.INTERMEDIATE_KML,f'{name}.tif')
            if os.path.exists(intermediate_pth):
                os.remove(intermediate_pth)
            with rio.open(shed_pth, 'r') as src:
                out_meta = src.meta.copy()
                with rio.open(intermediate_pth, 'w', **out_meta) as dst:
                    data = src.read(1, masked=True)
                    data[(data < 20)] = 0.0 # threshold
                    data[(data > 100) & (data < 255)] = 254 #dst.nodata
                    dst.write(data, indexes=1)

            color_ramp(intermediate_pth)

            output_pth = os.path.join(const.INTERMEDIATE_KML,f'{name}_{crs}_col.tif')
            
            try:
                os.remove(output_pth)
            except OSError as e:
                pass
            os.system(f'gdal_translate -q -expand rgb -of GTiff \
                {intermediate_pth} {output_pth}')
            # Process kmls on EPSG4326 ( EPSG3005 does not work )
            intermediate_fin_pth = os.path.join(const.INTERMEDIATE_TIF, sat, date,f'{name}_{crs}_fin.tif')
            shp_pth = os.path.join(const.TOP, typ, name, "shape", crs, f"{name}.shp")
            os.system(f'gdalwarp -overwrite -q --config GDALWARP_IGNORE_BAD_CUTLINE YES -dstalpha -cutline \
                {shp_pth} \
                -crop_to_cutline {output_pth} \
                {intermediate_fin_pth}')

            if crs == 'EPSG4326':
                kml_pth = os.path.join(const.KML,date,sat,typ,f'{name}_{date}')
                try:
                    os.makedirs(kml_pth)
                except:
                    pass
                os.system(f'gdal2tiles.py -q -p raster -t {name} --tilesize=128 -s \
                    EPSG:4326 -k -r near {intermediate_fin_pth} {kml_pth}')  

                with rio.open(intermediate_fin_pth) as src:
                    upperleft = src.transform * (0,0)
                    bottomright = src.transform * (src.width, src.height)
                coverage = [0,0,0]
                coverage[0] = db_handler.select(f'SELECT nodata FROM \
                    {sat} WHERE date_="{date}" and name="{os.path.split(shed)[-1]}"')
                coverage[1] = db_handler.select(f'SELECT below_threshold FROM \
                    {sat} WHERE date_="{date}" and name="{os.path.split(shed)[-1]}"')
                coverage[2] = db_handler.select(f'SELECT snow_coverage FROM \
                    {sat} WHERE date_="{date}" and name="{os.path.split(shed)[-1]}"')
                if None in coverage:
                    continue
                kml = simplekml.Kml(name=name)
                link = kml.newnetworklink(name=name)
                # Link low level kml
                link.link.href = os.path.join('doc.kml')
                link.link.viewrefreshmode = simplekml.ViewRefreshMode.onrequest
                fmt = lambda x: np.around(x, decimals=2)
                # Attach metadata
                pnt = kml.newpoint(name=name, description=f'NODATA: {fmt(coverage[0])}%,\
                    BELOW: {fmt(coverage[1])}%, SNOW: {fmt(coverage[2])}%', 
                     coords=[np.divide(np.add(upperleft, bottomright),2)])
                pnt.style.iconstyle.icon.href = 'http://maps.google.com/mapfiles/kml/shapes/snowflake_simple.png'
                #kml.document.description = f'NODATA: {fmt(coverage[0])}%,\
                #    BELOW: {fmt(coverage[1])}%, SNOW: {fmt(coverage[2])}%'
                # Save top level KML
                if typ == 'basins': # Turn off basins by default
                    pnt.visibility = 0
                    link.visibility = 0
                    kml.document.visibility = 0
                kml.save(os.path.join(kml_pth, f'{name}_{date}.kml'))

def composite_kml(date: str, sat: str):
    """
    Compose individual kmls into a heirarchal kml

    Parameters
    ----------
    date : str
        Target date to compose
    sat : str
        Target satellite to compose on [modis | viirs]
    """

    kml = simplekml.Kml(name=f'{sat}_{date}')

    location = glob(os.path.join(const.TOP, 'kml',date,sat,'*'))
    for shed in location:
        shed = os.path.split(shed)[-1]
        kmls = glob(os.path.join(const.TOP, 'kml',date,sat,shed,f'*_{date}*'))
        doc = kml.newfolder(name=shed)
        for k in kmls:
            name = os.path.split(k)[-1]
            link = doc.newnetworklink(name=name)
            link.link.href = os.path.join(date,sat,shed,name,f'{name}.kml')
            link.link.viewrefreshmode = simplekml.ViewRefreshMode.onrequest

    kml.save(os.path.join(const.TOP, 'kml',f'{sat}_{date}.kml'))
    #kml.savekmz(f'kml/{sat}_{date}.kmz')

    
def zipkmls():
    """
    Zip heirarchal kmls into a zipfile
    """
    with zipfile.ZipFile(os.path.join(const.TOP, 'kml.zip'), 'w') as zipf:
        for root, dirs, files in os.walk(os.path.join(const.TOP, 'kml')):
            for file in files:
                zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), os.path.join(const.TOP, 'kml', '..')))
    
    