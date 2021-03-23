import click
import datetime

from download_granules import download_granules
from admin import check_date

from constants import sats, days, typs

def download_(envpth: str, sat: str, date: str, days: int = 5):
    if check_date.check_date(date):    
        print(f'download {sat}')
        if sat == 'viirs':
            days = 1
        download_granules.download_granules(envpth, date, sat, int(days))
    else:
        print('ERROR: Date format YYYY.MM.DD')

@click.command()
@click.option('--envpth', type=str, required=True, help='Path to environment file.')
@click.option('--date', type=str, required=True, help='Date in format YYYY.MM.DD')
@click.option('--days', required=False, default='5', type=days, help='Select 1, 5 or 8 day composite for MODIS')
@click.option('--sat', type=sats, required=True, help='Which satellite source to process [ modis | viirs ]')
def download(envpth: str, sat: str, date: str, days: int = 5):
    download_(envpth, sat, date, days)

@click.command()
@click.option('--envpth', type=str, required=True, help='Path to environment file.')
@click.option('--month', type=click.Choice([str(month) for month in range(1,13)]), required=True, help='Month of interest in integer format MM; eg: 1 for Jan, 2 for Feb, etc')
@click.option('--year', type=click.Choice([str(year) for year in range(2000, int(datetime.datetime.today().year)+1)]), required=True, help='Year of interest in format YYYY')
@click.option('--sat', type=sats, required=True, help='Which satellite source to process [ modis | viirs ]')
def download_month(envpth: str, sat: str, month: str, year: str):
    download.month(envpth, sat, month, year)

@click.command()
@click.option('--envpth', type=str, required=True, help='Path to environment file.')
@click.option('--sat', type=sats, required=True, help='Which satellite source to process [ modis | viirs ]')
@click.option('--year', type=click.Choice([str(year) for year in range(2000, int(datetime.datetime.today().year)+1)]), required=True, help='Year of interest in format YYYY')
def download_year(envpth: str, sat: str, year: str):
    download.year(envpth, sat, year)

@click.command()
@click.option('--envpth', type=str, required=True, help='Path to environment file.')
@click.option('--sat', type=sats, required=True, help='Which satellite source to process [ modis | viirs ]')
def download_twenty_year(envpth: str, sat: str):
    download.twenty_year(envpth, sat)


@click.group()
def cli():
    pass

cli.add_command(download_month)
cli.add_command(download_year)
cli.add_command(download_twenty_year)

if __name__ == '__main__':
    cli()
    