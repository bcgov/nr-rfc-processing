import os
import click

# Click options for satellites
SATS = click.Choice(['modis', 'viirs'], case_sensitive=False)

# Click options for watersheds or basins
TYPS = click.Choice(['watersheds', 'basins'], case_sensitive=False)

# Click options for number of days to process
DAYS = click.Choice(['1', '5', '8'])

# Resolution
RES = {'modis':(500,500), 'viirs': (375,375)}
RES = {'modis':(500,500), 'viirs': (375,375)}
MODIS_EPSG4326_RES = 0.008259714517502726
VIIRS_EPSG4326_RES= 0.006659501656959246

# Bounding box to clip mosaics to
BBOX = [-140.977, 46.559, -112.3242, 63.134]

# MODIS PRODUCT
MODIS_PRODUCT = 'MOD10A1.61' # 'MOD10A1.6', good up to feb 15 2023
VIIRS_PRODUCT = 'VNP10A1F.1'

TOP = os.environ['SNOWPACK_DATA']
LOG = os.path.join(TOP, 'log')
BASINS = os.path.join(TOP,'basins')
WATERSHEDS = os.path.join(TOP,'watersheds')
KML = os.path.join(TOP,'kml')
INTERMEDIATE_KML = os.path.join(TOP,'intermediate_tif','kml')
INTERMEDIATE_TIF = os.path.join(TOP,'intermediate_tif')
INTERMEDIATE_TIF_MODIS = os.path.join(INTERMEDIATE_TIF,'modis')
INTERMEDIATE_TIF_VIIRS = os.path.join(INTERMEDIATE_TIF,'viirs')
INTERMEDIATE_TIF_SENTINEL = os.path.join(INTERMEDIATE_TIF,'sentinel')
INTERMEDIATE_TIF_PLOT = os.path.join(INTERMEDIATE_TIF,'plot')
PLOT = os.path.join(TOP,'plot')
PLOT_MODIS = os.path.join(PLOT,'modis')
PLOT_MODIS_MOSAIC = os.path.join(PLOT,'modis','mosaic')
PLOT_MODIS_WATERSHEDS = os.path.join(PLOT_MODIS,'watersheds')
PLOT_MODIS_BASINS = os.path.join(PLOT_MODIS,'basins')
PLOT_VIIRS = os.path.join(PLOT,'viirs')
PLOT_VIIRS_MOSAIC = os.path.join(PLOT_VIIRS,'mosaic')
PLOT_VIIRS_WATERSHEDS = os.path.join(PLOT_VIIRS,'watersheds')
PLOT_VIIRS_BASINS = os.path.join(PLOT_VIIRS,'basins')
PLOT_SENTINEL = os.path.join(PLOT,'sentinel')
ANALYSIS = os.path.join(TOP,'analysis')
MODIS_TERRA = os.path.join(TOP,'modis-terra')
SENTINEL_OUTPUT = os.path.join(TOP, 'sentinel_output')

NORM_ROOT = os.getenv('NORM_ROOT', TOP)

NORM = os.path.join(NORM_ROOT,'norm')
MOSAICS = os.path.join(NORM, 'mosaics')
OUTPUT_TIF_MODIS = os.path.join(MOSAICS,'modis')
OUTPUT_TIF_VIIRS = os.path.join(MOSAICS,'viirs')
MODIS_NORM = os.path.join(NORM, 'modis')
MODIS_DAILY_NORM = os.path.join(MODIS_NORM, 'daily')
MODIS_DAILY_10YR = os.path.join(MODIS_DAILY_NORM, '10yr')
MODIS_DAILY_20YR = os.path.join(MODIS_DAILY_NORM, '20yr')
VIIRS_NORM = os.path.join(NORM, 'viirs')
VIIRS_DAILY_NORM = os.path.join(VIIRS_NORM, 'daily')
VIIRS_DAILY_10YR = os.path.join(VIIRS_DAILY_NORM, '10yr')
VIIRS_DAILY_20YR = os.path.join(VIIRS_DAILY_NORM, '20yr')

AOI = os.path.join(os.path.dirname(__file__), '..', 'aoi')

# set default values and then override with what is in the
# env vars if populated with a valid value
VIIRS_OFFSET = 1
if ('VIIRS_OFFSET' in os.environ ) and os.environ['VIIRS_OFFSET']:
    VIIRS_OFFSET=int(os.environ['VIIRS_OFFSET'])

MODIS_OFFSET = 5
if ('MODIS_OFFSET' in os.environ) and os.environ['MODIS_OFFSET']:
    MODIS_OFFSET=int(os.environ['MODIS_OFFSET'])


EARTHDATA_USER = os.getenv("EARTHDATA_USER")
EARTHDATA_PASS = os.getenv("EARTHDATA_PASS")
SENTINELSAT_USER = os.getenv("SENTINELSAT_USER")
SENTINELSAT_PASS = os.getenv("SENTINELSAT_PASS")

# this is the directory that all the data in TOP will get copied
# to
OBJ_STORE_TOP = 'snowpack_archive'
