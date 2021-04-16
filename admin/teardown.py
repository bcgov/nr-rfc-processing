import os
import shutil

from glob import glob

import admin.constants as const

dirs = [
    const.MODIS_TERRA,
    const.BASINS,
    const.WATERSHEDS,
    const.INTERMEDIATE_TIF,
    const.KML,
    const.SENTINEL_OUTPUT,
    const.PLOT
]

def cleanupall():
    """
    Clean up all folders
    USE WITH CAUTION
    """
    for dir in dirs:
        try:
            shutil.rmtree(dir)
        except Exception as e:
            print(e)

def clean_downloads():
    try:
        shutil.rmtree(const.MODIS_TERRA)
    except Exception as e:
        print(e)

def clean_intermediate():
    try:
        shutil.rmtree(const.INTERMEDIATE_TIF)
    except Exception as e:
        print(e)

def clean_basins():
    try:
        shutil.rmtree(const.BASINS)
    except Exception as e:
        print(e)

def clean_watersheds():
    try:
        shutil.rmtree(const.WATERSHEDS)
    except Exception as e:
        print(e)

def clean_kmls():
    try:
        shutil.rmtree(const.KML)
    except Exception as e:
        print(e)
