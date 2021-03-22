import click
import multiprocessing
import datetime

from constants import days, sats, typs

from download_granules import download_granules
from download_granules.run_download import download_
from process import modis, viirs
from analysis import calculate_snow_coverage
from admin import buildkml, plotter
from admin import buildup, teardown
from admin.check_date import check_date

SATS = sats()
TYPS = typs()
DAYS = days()

@click.command()
def build():
    buildup.buildall()

@click.command()
@click.option('--target', required=True, 
        type=click.Choice(['intermediate','output','watersheds','basins','downloads','all']),
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


@click.command()
@click.option('--envpth', type=str, required=True, help='Path to environment file.')
@click.option('--date', type=str, required=True, help='Date in format YYYY.MM.DD')
@click.option('--days', required=False, default='5', type=DAYS, help='Select 1, 5 or 8 day composite for MODIS')
@click.option('--sat', type=SATS, required=True, help='Which satellite source to process [ modis | viirs ]')
def download(envpth: str, sat: str, date: str, days: int = 5):
    download_(envpth, sat, date, days)

@click.command()
@click.option('--date', required=True, type=str, help='Date in format YYYY.MM.DD')
@click.option('--days', required=False, default='5', type=DAYS, help='Select 1, 5 or 8 day composite for MODIS')
@click.option('--sat', type=SATS, required=True, help='Which satellite source to process [ modis | viirs ]')
def process(date: str, sat: str, days: int):
    if check_date(date):
        if sat == 'modis':
            modis.process_modis(date, int(days))
        elif sat == 'viirs':
            viirs.process_viirs(date)
        else: # Will never reach here due to click.Choice
            print(f'ERR SAT {sat} NOT VALID INPUT')
    else:
        print('ERROR: Date format YYYY.MM.DD')

@click.command()
@click.option('--date', type=str, required=True, help='Date in format YYYY.MM.DD')
@click.option('--typ', type=TYPS, required=True)
@click.option('--sat', type=SATS, required=True, help='Which satellite source to process [ modis | viirs ]')
def build_kml(date: str, typ: str, sat: str):
    if check_date(date):
        buildkml.daily_kml(date, typ.lower(), sat.lower())
    else:
        print('ERROR: Date format YYYY.MM.DD')

@click.command()
@click.option('--sat', type=SATS, required=True, help='Which satellite source to process [ modis | viirs ]')
@click.option('--date', type=str, required=True, help='Date in format YYYY.MM.DD')
def compose_kmls(date: str, sat: str):
    if check_date(date):
        buildkml.composite_kml(date, sat.lower())
    else:
        print('ERROR: Date format YYYY.MM.DD')

@click.command()
def zip_kmls():
    buildkml.zipkmls()

@click.command()
@click.option('--typ', type=TYPS, required=True)
@click.option('--sat', type=SATS, required=True, help='Which satellite source to process [ modis | viirs ]')
@click.option('--date', type=str, required=True, help='Date in format YYYY.MM.DD')
def run_analysis(typ: str, sat: str, date: str):
    if check_date(date):
        conn = calculate_snow_coverage.init_db()
        calculate_snow_coverage.calc(typ.lower(), sat.lower(), date)
    else:
        print('ERROR: Date format YYYY.MM.DD')

@click.command()
def dbtocsv():
    calculate_snow_coverage.db_to_csv()


@click.command()
@click.option('--date', type=str, required=True, help='Date in format YYYY.MM.DD')
@click.option('--sat', type=SATS, required=True, help='Which satellite source to process [ modis | viirs ]')
def plot(date: str, sat: str):
    if check_date(date):
        plotter.plot_(date, sat)
    else:
        print('ERROR: Date format YYYY.MM.DD')


@click.command()
@click.option('--date', type=str, required=True, help='Date in format YYYY.MM.DD')
@click.option('--envpth', type=str, required=True, help='Path to environment file.')
@click.option('--days', required=False, default='5', type=DAYS, help='Select 5 or 8 day composite for MODIS')
@click.option('--clean' ,required=False, default='false', type=str, help='Option to clean up intermediate files')
def daily_pipeline(envpth: str, date: str, clean: str, days: int = 5):
    if check_date(date):
        buildup.buildall()
        for sat in ['modis','viirs']:
            dailypipeline(envpth, date, sat, int(days), clean.lower())
    else:
        print('ERROR: Date format YYYY.MM.DD')

def dailypipeline(envpth: str, date: str, sat: str, days: int, clean: str):
    if check_date(date):
        if sat == 'viirs':
            days = 1
        download_granules.download_granules(envpth, date, sat, int(days))
        if sat == 'modis':
            modis.process_modis(date, int(days))
        elif sat == 'viirs':
            viirs.process_viirs(date)
        calculate_snow_coverage.init_db()
        for typ in ['watersheds', 'basins']:
            calculate_snow_coverage.calc(typ, sat, date)
            buildkml.daily_kml(date, typ.lower(), sat.lower())
        plotter.plot_(date, sat)
        calculate_snow_coverage.db_to_csv()
        buildkml.composite_kml(date, sat.lower())
        if clean == 'true':
            teardown.clean_intermediate()
            teardown.clean_output()
    else:
        print('ERROR: Date format YYYY.MM.DD')

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
cli.add_command(zip_kmls)

# PLOTTING
cli.add_command(plot)

# DAILY PIPELINE KICKER
cli.add_command(daily_pipeline)


if __name__ == '__main__':
    multiprocessing.freeze_support()
    cli()
    