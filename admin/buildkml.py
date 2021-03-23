import os
import simplekml
import zipfile

import rasterio as rio
import numpy as np

from glob import glob

from .color_ramp import color_ramp

from admin.constants import Constants

const = Constants()

def daily_kml(date: str, typ: str, sat: str):
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

    sheds = glob(os.path.join(const.top, typ,'*'))
    for shed in sheds:
        for crs in ['EPSG4326', 'EPSG3153']:
            # Apply /data thresholding and balancing
            name = os.path.split(shed)[-1]
            shed_pth = os.path.join(const.top, typ, name, sat, date, f'{name}_{sat}_{date}_{crs}.tif')
            if not os.path.exists(shed_pth):
                print(f'Could not find {shed_pth}')
                continue            
            intermediate_pth = os.path.join(const.intermediate_kml,f'{name}.tif')
            if os.path.exists(intermediate_pth):
                os.remove(intermediate_pth)
            with rio.open(shed_pth, 'r') as src:
                out_meta = src.meta.copy()
                with rio.open(intermediate_pth, 'w', **out_meta) as dst:
                    data = src.read(1, masked=True)
                    #data[data == 237] = 0.0 # inland water
                    #data[data == 239] = 0.0 # ocean
                    data[(data < 20) & (data >= 0.0)] = 0.0 # threshold
                    #data[(data > 100) & (data < 255) & (data != 250)] = 254 #dst.nodata # Keep Clouds
                    data[(data > 100) & (data < 255)] = 254 #dst.nodata
                    dst.write(data, indexes=1)

            color_ramp(intermediate_pth)

            fname = f'{name}_{crs}_col.tif'
            output_pth = os.path.join(const.intermediate_kml,f'{name}_{crs}_col.tif')
            
            try:
                os.remove(output_pth)
            except OSError as e:
                pass
            os.system(f'gdal_translate -q -expand rgb -of GTiff \
                {intermediate_pth} {output_pth}')
            # Process kmls on EPSG4326 ( EPSG3005 does not work )
            intermediate_fin_pth = os.path.join(const.top, typ, name, sat, date,f'{name}_{crs}_fin.tif')
            shp_pth = os.path.join(const.top, typ, name, "shape", crs, f"{name}.shp")
            os.system(f'gdalwarp -overwrite -q --config GDALWARP_IGNORE_BAD_CUTLINE YES -dstalpha -cutline \
                {shp_pth} \
                -crop_to_cutline {output_pth} \
                {intermediate_fin_pth}')

            if crs == 'EPSG4326':
                kml_pth = os.path.join(const.kml,date,sat,typ,f'{name}_{date}')
                try:
                    os.makedirs(kml_pth)
                except:
                    pass
                os.system(f'gdal2tiles.py -q -p raster -t {name} --tilesize=128 -s \
                    EPSG:4326 -k -r near {intermediate_fin_pth} {kml_pth}')
    
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

    location = glob(os.path.join(const.top, 'kml',date,sat,'*'))
    for shed in location:
        shed = os.path.split(shed)[-1]
        kmls = glob(os.path.join(const.top, 'kml',date,sat,shed,f'*_{date}*'))
        doc = kml.newfolder(name=shed)
        for k in kmls:
            name = os.path.split(k)[-1]
            link = doc.newnetworklink(name=name)
            link.link.href = os.path.join(date,sat,shed,name,'doc.kml')
            link.link.viewrefreshmode = simplekml.ViewRefreshMode.onrequest

    kml.save(os.path.join(const.top, 'kml',f'{sat}_{date}.kml'))
    #kml.savekmz(f'kml/{sat}_{date}.kmz')

    
def zipkmls():
    """
    Zip heirarchal kmls into a zipfile
    """
    with zipfile.ZipFile(os.path.join(const.top, 'kml.zip'), 'w') as zipf:
        for root, dirs, files in os.walk(os.path.join(const.top, 'kml')):
            for file in files:
                zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), os.path.join(const.top, 'kml', '..')))
    
    