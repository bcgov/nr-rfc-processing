import os
import descartes
import fiona
import rasterio.plot

import rasterio as rio
import matplotlib.pyplot as plt
import geopandas as gpd
import matplotlib as mpl

from rasterio.merge import merge
from glob import glob
from descartes import PolygonPatch
from typing import List

res = { 
        'modis': {
            'EPSG4326': 0.008259714517502726, 
            'EPSG3153': 500
        },
        'viirs': {
            'EPSG4326': 0.006659501656959246,
            'EPSG3153': 375
        }
    }

def plot_helper(sheds: List, typ: str, sat: str, date: str):
    """Create PNG plots of watersheds/basins
    + mosaic of all as well as individual

    Parameters
    ----------
    sheds : List
        List of sheds to turn into plots
    typ : str
        watersheds/basins/individual-name to determine
        mosaic or not
    sat : str
        Target satellite date to plot [modis | viirs]
    date : str
        Target date to plot in format YYYY.MM.DD
    """
    crs = os.path.split(sheds[0])[-1].split('_')[-2]
    # Create a mosaic plot
    if typ == 'watersheds' or typ == 'basins':
        fig, ax = plt.subplots(1,1,figsize=(10, 4), dpi=300)
        print(sheds)
        src_files_to_mosaic = []
        for shed in sheds:
            src = rio.open(shed, 'r')
            src_files_to_mosaic.append(src)
        mosaic, out_trans = merge(
            src_files_to_mosaic, 
            res=res[sat][crs]
            )
        out_meta = src.meta.copy()
        out_meta.update({
                "driver": "GTiff",
                "height": mosaic.shape[1],
                "width": mosaic.shape[2],
                "transform": out_trans,
                      })
        pth = os.path.join('/data','intermediate_tif','plot',f'{typ}_{crs}.tif')
        with rio.open(pth, 'w', **out_meta) as dst:
            dst.write(mosaic)
        for f in src_files_to_mosaic:
            f.close()
        r = rio.open(pth,'r')
        im = ax.imshow(r.read().transpose(1,2,0), cmap=plt.cm.RdYlBu, vmin=0, vmax=100, clim=[0,100])
        cbar = fig.colorbar(im)
        cbar.ax.set_ylabel('NDSI', rotation=270)
        rasterio.plot.show((r.read()), transform=r.transform, ax=ax, adjust=None)
        try:
            os.makedirs(os.path.join('/data','plot',sat,'mosaic',date))
        except:
            pass
        pth = os.path.join('aoi','provincial_boundary','FLNR10747_AOI_BC_boundary_20210106_AnS.shp')
        shapefile = gpd.read_file(os.path.join('aoi','provincial_boundary','FLNR10747_AOI_BC_boundary_20210106_AnS.shp'))
        shapefile.plot(ax=ax, alpha=0.2)
        ax.axis('off')
        fig.suptitle(f'{typ.upper()} - {sat.upper()} - {date}', x=0.6)
        plt.savefig(os.path.join('/data','plot',sat,'mosaic',date,f'{typ}_{crs}.png'), bbox_inches='tight')
    else: # Create individual plots
        fig, ax = plt.subplots(1,1, dpi=100)
        print(sheds[0])
        f = rio.open(sheds[0], 'r')
        mosaic = f.read()
        im = ax.imshow(mosaic.transpose(1,2,0), cmap=plt.cm.RdYlBu, vmin=0, vmax=100, clim=[0,100])
        cbar = fig.colorbar(im)
        cbar.ax.set_ylabel('NDSI', rotation=270)
        ax.axis('off')
        name = '_'.join(typ.split('_')[:-1])
        fig.suptitle(f'{name.upper()} - {sat.upper()} - {date}')
        if os.path.split(typ)[-1].split('_')[0].isupper():
            base = os.path.join('/data','plot',sat,'basins',date,crs)
        else:
            base = os.path.join('/data','plot',sat,'watersheds',date,crs)
        try:
            os.makedirs(base)
        except:
            pass
        plt.savefig(os.path.join(base,f'{typ}.png'))
    plt.close()

def plot_single_shed(shed_name: str, sat: str, date: str):
    """
    Helper function to plot individual watersheds or basins

    Parameters
    ----------
    shed_name : str
        name of shed to plot
    sat : str
        Target satellite date [modis | viirs]
    date : str
        Target date in format YYYY.MM.DD
    """
    typ = os.path.split(shed_name)[0]
    shed_name = os.path.split(shed_name)[-1]
    sheds = glob(os.path.join('/data',typ,shed_name,sat,date, '*EPSG3153_fin.tif'))
    for shed in sheds:
        plot_helper([shed], os.path.split(shed)[-1].replace('_fin',"").split('.')[0], sat, date)

def plot_(date: str, sat: str): 
    """Trigger point to plot all watersheds and basins

    Parameters
    ----------
    date : str
        Target date in format YYYY.MM.DD
    sat : str
        Target satellite data to plot [modis | viirs]
    """
    watersheds = glob(os.path.join('/data','watersheds','**',sat,date,'*EPSG3153_fin.tif'))
    if len(watersheds) != 0:
        plot_helper(watersheds, 'watersheds', sat, date)
    basins = glob(os.path.join('/data','basins','**',sat,date,'*EPSG3153_fin.tif'))
    if len(basins) != 0:
        plot_helper(basins, 'basins', sat, date)
    for task in ['watersheds', 'basins']:
        indiv_sheds = glob(os.path.join('/data',task,'*'))
        for shed in indiv_sheds:
            plot_single_shed(os.path.join(task,os.path.split(shed)[-1]), sat, date)
    