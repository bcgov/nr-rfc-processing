import numpy
import os
import multiprocessing
import warnings
import rasterio
import h5py
import datetime
import sqlite3
import csv
import click
import time
import calendar
import yaml

# Only this file uses sys
import sys

import geopandas as gpd
import rasterio as rio
import datetime
import fiona
import rasterio.mask

from osgeo import gdal, gdal_array
from multiprocessing import Pool
from glob import glob
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.merge import merge
from typing import List


# Custom CMR
import io
from dateutil.parser import parse as dateparser
from functools import partial
from json import dumps
from time import sleep
from typing import Dict, List, Tuple
import logging
from requests.packages.urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from html.parser import HTMLParser
#from dotenv import load_dotenv, find_dotenv

if __name__ == '__main__':
    print('Python')
    print(sys.version)
    print(sys.version_info)
    os.system('gdalinfo --version')
    #os.system('gdalinfo --formats')