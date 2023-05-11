import os
import rasterio.plot
import logging

import numpy as np
import rioxarray as rioxr
import rasterio as rio
import matplotlib.pyplot as plt
import geopandas as gpd

import admin.constants as const

from admin.color_ramp import color_ramp

from collections import defaultdict
from matplotlib.patches import Patch
from glob import glob
from collections import defaultdict

import admin.object_store_util

logger = logging.getLogger(__name__)
ostore = admin.object_store_util.OStore()

def plot_sheds(sheds: list, typ: str, sat: str, date: str):
    """Plot individual watersheds/basins

    Parameters
    ----------
    sheds : list
        List of watersheds or basins names
    typ : str
        Watersheds or Basins [watersheds | basins]
    sat : str
        Source satellite [modis | viirs]
    date : str
        Target date in format YYYY.MM.DD
    """
    chunk = 512 # Chunk size to read in as not to overwhelm memory
    org = defaultdict(list) # Organizer for all open sheds to be plot
    for shed in sheds:
        logger.debug(f'PLOTTING {os.path.split(shed)[-1]}')
        # shed will be just the name of the watershed
        name = os.path.split(shed)[-1]
        base = os.path.join(shed, sat, date)

        out_pth = os.path.join(const.PLOT, sat, typ, date, f'{name}.png')
        out_dir = os.path.dirname(out_pth)
        if not os.path.exists(out_pth):


            # prepare
            try: # If the shed is not accessible, skip to next
                daily = glob(os.path.join(base, '*EPSG3153.tif'))[0]
            except Exception as e:
                logger.warning(e)
                continue
            d = rioxr.open_rasterio(daily, chunks={'band': 1, 'x': chunk, 'y': chunk})
            # replace values that are = to _FillValue to non number
            #d.data[(d.data == d._FillValue)] = np.nan
            # raster = raster.where(raster != raster.rio.nodata, np.nan)

            d = d.where(d != d._FillValue, np.nan)
            d.data[(d.data > 100)] = np.nan
            org['daily'].append(d)
            try: # If generated normal file is missing, skip to next
                norm10yr = glob(os.path.join(base, f'{name}_10yrNorm.tif'))[0]
            except Exception as e:
                logger.warning(e)
                continue
            d = rioxr.open_rasterio(norm10yr, chunks={'band': 1, 'x': chunk, 'y': chunk})
            d.data[(d.data == d._FillValue)] = np.nan
            org['10yrnorm'].append(d)
            try: # If generated normal file is missing, skip to next
                norm20yr = glob(os.path.join(base, f'{name}_20yrNorm.tif'))[0]
            except Exception as e:
                logger.warning(e)
                continue
            d = rioxr.open_rasterio(norm20yr, chunks={'band': 1, 'x': chunk, 'y': chunk})
            d.data[(d.data == d._FillValue)] = np.nan
            org['20yrnorm'].append(d)
            ######################
            # Plot individual shed
            ######################
            fig, ax = plt.subplots(1,3, figsize=(15,5))
            fig.suptitle(f'{name.upper()} - {sat.upper()} - {date}')
            # Plot date generated raster
            ax[0].set_title(date)
            ax[0].axis('off')
            im1 = ax[0].imshow(org['daily'][-1].data.transpose(1,2,0), cmap=plt.cm.RdYlBu,
                                    vmin=0, vmax=100, clim=[0,100], interpolation='none')
            fig.colorbar(im1, ax=ax[0])
            # Plot % difference to 10 year normal
            ax[1].set_title('% Difference to 10 Year Normal')
            ax[1].axis('off')
            im2 = ax[1].imshow(org['10yrnorm'][-1].data.transpose(1,2,0), cmap=plt.cm.RdYlBu,
                                    vmin=-100, vmax=100, clim=[-100,100], interpolation='none')
            fig.colorbar(im2, ax=ax[1])
            # Plot % different to 20 year normal
            ax[2].set_title('% Difference to 20 Year Normal')
            ax[2].axis('off')
            im3 = ax[2].imshow(org['20yrnorm'][-1].data.transpose(1,2,0), cmap=plt.cm.RdYlBu,
                                    vmin=-100, vmax=100, clim=[-100,100], interpolation='none')
            fig.colorbar(im3, ax=ax[2])

            # Make sure the output dir is accessible and replace with
            # most up to date version
            out_pth = os.path.join(const.PLOT, sat, typ, date, f'{name}.png')
            out_dir = os.path.dirname(out_pth)
            if not os.path.exists(out_dir):
                logger.debug(f"creating directory: {out_dir}")
                os.makedirs(out_dir)
            # why overwrite!!!!!?????
            # if os.path.exists(out_pth):
            #     logger.debug(f"removing the path: {out_pth}")
            #     os.remove(out_pth)
            # could multiprocess this
            try:
                logger.debug(f"creating the plot: {out_pth}")
                plt.savefig(out_pth)
                plt.close()
            except Exception as e:
                logger.debug(e)
                continue

def norm_math(orig: np.array, norm: np.array):
    """Perform math against normal to calculate
    percent change

    Parameters
    ----------
    orig : np.array
        User generated array
    norm : np.array
        10 or 20 year normal data array

    Returns
    -------
    np.array
        Percent change w.r.t normal data array
    """
    cp = norm.copy()
    set_val = np.nan
    np.seterr(divide='ignore', invalid='ignore')
    norm = np.divide((orig-norm), norm, out=np.zeros(norm.shape))*100
    norm[norm == np.inf] = set_val # correct div by 0 and inf/nan
    norm = np.nan_to_num(norm, nan=set_val, posinf=set_val, neginf=set_val) # correct div by 0 and inf/nan
    norm[((norm > 100)&(norm != np.nan))] = 100
    norm[((norm < -100)&(norm != np.nan))] = -100
    norm[((orig > 100)|(cp > 100))] = 0
    return norm

def plot_mosaics(sat: str, date: str):
    """Plot mosaics and clip to prov boundary

    Parameters
    ----------
    sat : str
        Source satllite [modis | viirs]
    date : str
        Target date in format YYYY.MM.DD
    """
    out_pth = os.path.join(const.PLOT, sat, 'mosaic', date, f'{date}.png')
    out_dir = os.path.dirname(out_pth)
    if not os.path.exists(out_pth):


        shp_pth = os.path.join(const.AOI, 'provincial_boundary',
                        'FLNR10747_AOI_BC_boundary_20210106_AnS.shp')
        shapefile = gpd.read_file(shp_pth)
        for _, row in shapefile.iterrows(): # Grab geometry
            geom = row.geometry
        fig, ax = plt.subplots(1,3, figsize=(25,5))
        fig.suptitle(f'{sat.upper()} - {date}')
        date_split = date.split('.')
        d_year = date_split[0]
        d_month = date_split[1]
        d_day = date_split[2]

        # Gather satellite respective data and prepare path bases
        if sat == 'modis':
            orig = glob(os.path.join(const.INTERMEDIATE_TIF_MODIS, date, '*modis_composite*.tif'))[0]
            base10yr_dir = const.MODIS_DAILY_10YR
            base20yr_dir = const.MODIS_DAILY_20YR
        elif sat == 'viirs':
            orig = glob(os.path.join(const.OUTPUT_TIF_VIIRS, d_year, f'{date}.tif'))[0]
            base10yr_dir = const.VIIRS_DAILY_10YR
            base20yr_dir = const.VIIRS_DAILY_20YR
        else: # @click should not let this else ever be reached
            return

        # pull any 10 year data required
        norm10yr = os.path.join(base10yr_dir, f'{date_split[1]}.{date_split[2]}.tif')
        ostore.get_10yr_tif(sat=sat, month=d_month, day=d_day, out_path=norm10yr)
        logger.debug(f"norm10yr: {norm10yr}")
        #norm10yr_glob = glob(norm10yr_tif[2:])
        #norm10yr = norm10yr_glob.pop()

        norm20yr = os.path.join(base20yr_dir, f'{date_split[1]}.{date_split[2]}.tif')
        ostore.get_20yr_tif(sat=sat, month=d_month, day=d_day, out_path=norm20yr)
        logger.debug(f"norm20yr: {norm10yr}")

        # norm20yr_glob = glob(norm20yr_tif)
        # norm20yr = norm20yr_glob.pop()

        #norm20yr = glob(os.path.join(base20yr, f'{date_split[1]}.{date_split[2]}.tif'))[0]

        # Plot user generated mosaic and clip to prov boundary
        ax[0].set_title(f'{date}')
        ax[0].axis('off')
        daily_pth = os.path.join(const.INTERMEDIATE_TIF, 'plot', 'merged_daily.tif')
        with rioxr.open_rasterio(orig) as orig:
            fill_val = orig._FillValue
            orig = orig.rio.reproject('EPSG:3153', resolution=const.RES[sat])
            d_cp = orig.data.copy()
            orig.rio.to_raster(daily_pth, recalc_transform=True)
        color_ramp(daily_pth)
        # implement gdal cutting to remove most nodata in plot
        gdal_pth = os.path.join(os.path.split(daily_pth)[0], 'out_d.tif')
        os.system(f'gdal_translate -q -expand rgb -of GTiff \
                    {daily_pth} {gdal_pth}')
        os.system(f'gdalwarp -overwrite -q --config GDALWARP_IGNORE_BAD_CUTLINE YES -dstalpha -cutline \
                    {shp_pth} \
                    -crop_to_cutline {gdal_pth} \
                {daily_pth}')
        with rio.open(daily_pth, 'r') as src:
            im1 = ax[0].imshow(src.read().transpose(1,2,0), cmap=plt.cm.RdYlBu,
                                vmin=0, vmax=100, clim=[0,100], interpolation='none')
            rasterio.plot.show((src.read()), transform=src.transform, ax=ax[0], cmap=plt.cm.RdYlBu,
                                vmin=0, vmax=100, clim=[0,100], interpolation='none')
            fig.colorbar(im1, ax=ax[0])

        # Alter user generated data to prepare for norm math
        d_cp[(d_cp > 100)&(d_cp != fill_val)] = 0

        # Plot % change to 10 year norm
        ax[1].set_title('% Difference to 10 Year Normal')
        ax[1].axis('off')
        norm10yr_pth = os.path.join(const.INTERMEDIATE_TIF, 'plot', '10yr.tif')
        with rioxr.open_rasterio(norm10yr) as norm10yr:
            norm10yr = norm10yr.rio.reproject('EPSG:3153', resolution=const.RES[sat])
            norm10yr.data = norm_math(d_cp, norm10yr.data)
            norm10yr = norm10yr.rio.clip([geom], drop=True, all_touched=True)
            norm10yr.rio.to_raster(norm10yr_pth, recalc_transform=True)
        gdal_pth = os.path.join(os.path.split(daily_pth)[0], 'out_.tif')
        # Cut to prov boundary
        os.system(f'gdalwarp -overwrite -q --config GDALWARP_IGNORE_BAD_CUTLINE YES -dstalpha -cutline \
                    {shp_pth} \
                    -crop_to_cutline {norm10yr_pth} \
                {gdal_pth}')
        with rio.open(gdal_pth) as src:
            d = src.read(1)
            msk = src.read(2)
            d[(msk == False)] = np.nan
            im2 = ax[1].imshow(d, cmap=plt.cm.RdYlBu,
                                vmin=-100, vmax=100, clim=[-100,100], interpolation='none')
            fig.colorbar(im2, ax=ax[1])
            rasterio.plot.show((d), ax=ax[1], cmap=plt.cm.RdYlBu,
                                vmin=-100, vmax=100, clim=[-100,100], interpolation='none')

        #  Plot % change to 20 year norm
        ax[2].set_title('% Difference to 20 Year Normal')
        ax[2].axis('off')
        norm20yr_pth = os.path.join(const.INTERMEDIATE_TIF, 'plot', '20yr.tif')
        with rioxr.open_rasterio(norm20yr) as norm20yr:
            norm20yr = norm20yr.rio.reproject('EPSG:3153', resolution=const.RES[sat])
            norm20yr.data = norm_math(d_cp, norm20yr.data)
            norm20yr = norm20yr.rio.clip([geom], drop=True, all_touched=True)
            norm20yr.rio.to_raster(norm20yr_pth, recalc_transform=True)
        # gdal_pth = os.path.join(os.path.split(daily_pth)[0], 'out_.tif')
        # Clip to provincial boundary
        os.system(f'gdalwarp -overwrite -q --config GDALWARP_IGNORE_BAD_CUTLINE YES -dstalpha -cutline \
                    {shp_pth} \
                    -crop_to_cutline {norm20yr_pth} \
                {gdal_pth}')
        with rio.open(gdal_pth) as src:
            d = src.read(1)
            msk = src.read(2)
            d[(msk == False)] = np.nan
            im3 = ax[2].imshow(d, cmap=plt.cm.RdYlBu,
                                vmin=-100, vmax=100, clim=[-100,100], interpolation='none')
            fig.colorbar(im3, ax=ax[2])
            rasterio.plot.show((d), ax=ax[2], cmap=plt.cm.RdYlBu,
                                vmin=-100, vmax=100, clim=[-100,100], interpolation='none')

        # Add legend for nodata
        legend_elements = [Patch(facecolor='black', edgecolor='k',
                                label='NoData')]
        fig.legend(handles=legend_elements, loc='lower center')
        # Make sure output path is accessible and
        # replace with most up to date version
        if not os.path.exists(out_dir):
            logger.debug(f"creating the directory: {out_dir}")
            os.makedirs(out_dir)
        if os.path.exists(out_pth):
            logger.debug(f"deleting the file: {out_pth}")
            os.remove(out_pth)
        try:
            logger.debug(f"creating the file: {out_pth}")
            plt.savefig(out_pth)
            plt.close()
        except Exception as e:
            logger.debug(e)


def plot_handler(date: str, sat: str):
    """Handler for plotting all watersheds, basins
    and mosaics

    Parameters
    ----------
    date : str
        Target date in format YYYY.MM.DD
    sat : str
        Source satellite [modis | viirs]
    """
    watersheds = glob(os.path.join(const.TOP, 'watersheds', '*'))
    plot_sheds(watersheds, 'watersheds', sat, date)
    basins = glob(os.path.join(const.TOP, 'basins', '*'))
    plot_sheds(basins, 'basins', sat, date)
    plot_mosaics(sat, date)

