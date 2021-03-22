import os
import shutil

from glob import glob

from admin.constants import Constants

const = Constants()

dirs = [
    const.modis_terra,
    const.basins,
    const.watersheds,
    const.intermediate_tif,
    const.output_tif,
    const.intermediate_kml,
    const.kml
]

def cleanupall():
    for dir in dirs:
        try:
            shutil.rmtree(dir)
        except Exception as e:
            print(e)

def clean_downloads():
    try:
        shutil.rmtree(const.modis_terra)
    except Exception as e:
        print(e)

def clean_intermediate():
    try:
        for dr in [const.intermediate_tif, const.intermediate_kml]:
            shutil.rmtree(dr)
    except Exception as e:
        print(e)

def cleanup_output():
    try:
        shutil.rmtree(const.output_tif)
    except Exception as e:
        print(e)

def cleanup_basins():
    try:
        shutil.rmtree(const.basins)
    except Exception as e:
        print(e)

def cleanup_watersheds():
    try:
        shutil.rmtree(const.watersheds)
    except Exception as e:
        print(e)
