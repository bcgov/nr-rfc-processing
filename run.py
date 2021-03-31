import os
import click
import multiprocessing
import datetime
import pytz

import admin.constants as const

from download_granules import download_granules
from download_granules.download_granules import download_granules
from process import modis, viirs, sentinel2
from analysis import analysis
from admin import buildkml, plotter
from admin import buildup, teardown
from admin.check_date import check_date
from admin.logging import setup_logger
from admin.db_handler import DBHandler
from normal_gen.calculate_norm import _calculate_norms

if not os.path.exists(const.LOG):
    os.makedirs(const.LOG)

logger = setup_logger('snow_mapping', os.path.join(const.LOG, 'snow_mapping.log'))

@click.command()
def build():
    buildup.buildall()

@click.command()
@click.option('--target', required=True, 
        type=click.Choice(['intermediate','output','watersheds','basins','downloads','kml','all']),
        help="Target directory to clean up/remove"
        )
def clean(target):
    if target == 'all':
        teardown.cleanupall()
    if target == 'intermediate':
        teardown.clean_intermediate()
    if target == 'output':
        teardown.clean_output()
    if target == 'watersheds':
        teardown.clean_watersheds()
    if target == 'basins':
        teardown.clean_basins()
    if target == 'downloads':
        teardown.clean_downloads()
    if target == 'kml':
        teardown.clean_kmls()


@click.command()
@click.option('--envpth', type=str, required=True, help='Path to environment file.')
@click.option('--date', type=str, required=True, help='Date in format YYYY.MM.DD')
@click.option('--days', required=False, default='5', type=const.DAYS, help='Select 1, 5 or 8 day composite for MODIS')
@click.option('--sat', type=const.SATS, required=True, help='Which satellite source to process [ modis | viirs ]')
def download(envpth: str, sat: str, date: str, days: int = 5):
    if check_date(date):    
        print(f'download {sat}')
        if sat == 'viirs':
            days = 1
        download_granules(envpth, date, sat, int(days))
    else:
        print('ERROR: Date format YYYY.MM.DD')

@click.command()
@click.option('--date', required=True, type=str, help='Date in format YYYY.MM.DD')
@click.option('--days', required=False, default='5', type=const.DAYS, help='Select 1, 5 or 8 day composite for MODIS')
@click.option('--sat', type=const.SATS, required=True, help='Which satellite source to process [ modis | viirs ]')
def process(date: str, sat: str, days: int):
    if check_date(date):
        if sat == 'modis':
            modis.process_modis(date, int(days))
        elif sat == 'viirs':
            viirs.process_viirs(date)
        else: # Will never reach here due to click.Choice
            logger.error(f'ERR SAT {sat} NOT VALID INPUT')
    else:
        logger.error('ERROR: Date format YYYY.MM.DD')

@click.command()
@click.option('--creds', type=str, required=True, help='Path to credential file.')
@click.option('--date', type=str, required=True, help='Date in format YYYY.MM.DD')
@click.option('--lat', type=float, required=True, help='Latitude of point of interest')
@click.option('--lng', type=float, required=True, help='Longtitude of point of interest')
@click.option('--day-tolerance', type=int, required=False, default='50', help="How many days to look back for granules")
@click.option('--rgb', required=False, default='false', type=click.Choice(['true','false']), help='Save RGB GTiff')
@click.option('--max-allowable-cloud', required=False, default=50, help='Percentage of max allowable cloud to query with')
@click.option('--force-download', required=False, default='false', type=click.Choice(['true','false']), help='Force download by removing existing files for scene')
@click.option('--clean' ,required=False, default='false', type=click.Choice(['true', 'false']), help='Option to clean up intermediate files')
def process_sentinel(creds: str, date:str, lat: float, lng: float, rgb: str, 
                        max_allowable_cloud: int, force_download: str,
                        day_tolerance: int, clean: str):
    if check_date(date):
        db_handler = DBHandler()
        sentinel2.sentinel_pipeline(creds, date, float(lat), float(lng), rgb.lower(),
                             max_allowable_cloud, force_download, day_tolerance, db_handler)
        db_handler.db_to_csv()
        if clean == 'true':
            teardown.clean_intermediate()
    else:
        logger.error('ERROR: Date format YYYY.MM.DD')

@click.command()
@click.option('--date', type=str, required=True, help='Date in format YYYY.MM.DD')
@click.option('--typ', type=const.TYPS, required=True)
@click.option('--sat', type=const.SATS, required=True, help='Which satellite source to process [ modis | viirs ]')
def build_kml(date: str, typ: str, sat: str):
    if check_date(date):
        db_handler = DBHandler()
        buildkml.daily_kml(date, typ.lower(), sat.lower(), db_handler)
    else:
        logger.error('ERROR: Date format YYYY.MM.DD')

@click.command()
@click.option('--sat', type=const.SATS, required=True, help='Which satellite source to process [ modis | viirs ]')
@click.option('--date', type=str, required=True, help='Date in format YYYY.MM.DD')
def compose_kmls(date: str, sat: str):
    if check_date(date):
        buildkml.composite_kml(date, sat.lower())
    else:
        logger.error('ERROR: Date format YYYY.MM.DD')

@click.command()
@click.option('--typ', type=const.TYPS, required=True)
@click.option('--sat', type=const.SATS, required=True, help='Which satellite source to process [ modis | viirs ]')
@click.option('--date', type=str, required=True, help='Date in format YYYY.MM.DD')
def run_analysis(typ: str, sat: str, date: str):
    if check_date(date):
        db_handler = DBHandler()
        analysis.calculate_stats(typ, sat, date, db_handler)
    else:
        logger.error('ERROR: Date format YYYY.MM.DD')

@click.command()
def dbtocsv():
    db_handler = DBHandler()
    db_handler.db_to_csv()


@click.command()
@click.option('--date', type=str, required=True, help='Date in format YYYY.MM.DD')
@click.option('--sat', type=const.SATS, required=True, help='Which satellite source to process [ modis | viirs ]')
def plot(date: str, sat: str):
    if check_date(date):
        plotter.plot_handler(date, sat)
    else:
        logger.error('ERROR: Date format YYYY.MM.DD')


@click.command()
@click.option('--date', type=str, required=True, help='Date in format YYYY.MM.DD')
@click.option('--envpth', type=str, required=True, help='Path to environment file.')
@click.option('--days', required=False, default='5', type=const.DAYS, help='Select 5 or 8 day composite for MODIS')
@click.option('--clean' ,required=False, default='false', type=click.Choice(['true', 'false']), help='Option to clean up intermediate files')
def daily_pipeline(envpth: str, date: str, clean: str, days: int = 5):
    if check_date(date):
        # MODIS/VIIRS NASA server products are about 2 days behind current date
        logger.info('Daily Pipeline Started')
        buildup.buildall()
        db_handler = DBHandler()
        pst = pytz.timezone('US/Pacific')
        date_l = date.split('.')
        target_date = datetime.datetime(int(date_l[0]), int(date_l[1]), int(date_l[2]))
        if target_date.date() == datetime.datetime.now(pst).date():
            date = datetime.datetime.strftime(target_date - datetime.timedelta(days=2), '%Y.%m.%d')
        for sat in ['modis','viirs']:
            logger.info(f'Daily Pipeline running {sat} process')
            dailypipeline(envpth, date, sat, int(days), db_handler)
        if clean == 'true':
            teardown.clean_intermediate()
    else:
        logger.error('ERROR: Date format YYYY.MM.DD')

def dailypipeline(envpth: str, date: str, sat: str, days: int, db_handler: DBHandler):
    if check_date(date):
        if sat == 'viirs':
            days = 1
        download_granules(envpth, date, sat, int(days))
        if sat == 'modis':
            modis.process_modis(date, int(days))
        elif sat == 'viirs':
            viirs.process_viirs(date)
        for typ in ['watersheds', 'basins']:
            analysis.calculate_stats(typ, sat, date, db_handler)
            buildkml.daily_kml(date, typ.lower(), sat.lower(), db_handler)
        db_handler.db_to_csv()
        plotter.plot_handler(date, sat)
        buildkml.composite_kml(date, sat.lower())
    else:
        logger.error('ERROR: Date format YYYY.MM.DD')

@click.command()
@click.option('--envpth', type=str, required=True, help='Path to environment file.')
@click.option('--rng', type=click.Choice(['10','20']), help='Range of years to calculate normal for.')
@click.option('--sat', type=const.SATS, required=True, help='Which satellite source to process [ modis | viirs ]')
def calculate_norms(envpth: str, rng: int, sat: str):
    _calculate_norms(envpth, rng, sat)

@click.group()
def cli():
    pass

# ADMIN COMMANDS
cli.add_command(build)
cli.add_command(clean)

# DOWNLOAD
cli.add_command(download)

# PROCESS
cli.add_command(process)

# ANALYSIS
cli.add_command(run_analysis)
cli.add_command(dbtocsv)

# BUILD KML FILES
cli.add_command(build_kml)
cli.add_command(compose_kmls)

# PLOTTING
cli.add_command(plot)

# DAILY PIPELINE KICKER
cli.add_command(daily_pipeline)

# SENTINEL-2
cli.add_command(process_sentinel)

# NORMALS
cli.add_command(calculate_norms)


if __name__ == '__main__':
    multiprocessing.freeze_support()
    cli()
    