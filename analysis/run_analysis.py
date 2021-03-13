import click
import datetime

from analysis import custom_day_range
from analysis import monthly
from analysis import yearly


sats = click.Choice(['modis', 'viirs'], case_sensitive=False)

def check_date(date: str):
    format = '%Y.%m.%d'
    try:
        datetime.datetime.strptime(date, format)
        return True
    except:
        return False


@click.command()
@click.option('--envpth', type=str, required=True, help='Path to environment file.')
@click.option('--days', type=int, required=True, help='Number of days for historical analysis')
@click.option('--date', type=str, required=True, help='Date in format YYYY.MM.DD')
@click.option('--sat', type=sats, required=True, help='Which satellite source to process [ modis | viirs ]')
def custom_day_range_analysis(envpth: str, date: int, sat: str, days: int):
    if check_date(date):
        custom_day_range.run(envpth, sat, date, days)
    else:
        print('ERROR: Date format YYYY.MM.DD')

@click.command()
@click.option('--envpth', type=str, required=True, help='Path to environment file.')
@click.option('--days', type=int, required=True, help='Number of days for historical analysis')
@click.option('--date', type=str, required=True, help='Date in format YYYY.MM.DD')
@click.option('--sat', type=sats, required=True, help='Which satellite source to process [ modis | viirs ]')
def day_analysis(envpth: str, date: int, sat: str, days: int):
    if check_date(date):
        custom_day_range.run(envpth, sat, date, 1)
    else:
        print('ERROR: Date format YYYY.MM.DD')

@click.command()
@click.option('--envpth', type=str, required=True, help='Path to environment file.')
@click.option('--year', type=click.Choice([str(year) for year in range(2000, int(datetime.datetime.today().year)+1)]), required=True, help='Year of interest in format YYYY')
@click.option('--month', type=click.Choice([str(month) for month in range(1,13)]), required=True, help='Month of interest in integer format MM; eg: 1 for Jan, 2 for Feb, etc')
@click.option('--sat', type=sats, required=True, help='Which satellite source to process [ modis | viirs ]')
def month_analysis(envpth: str, sat: str, year: int, month: int):
    monthly.run(envpth, sat, year, month)

@click.command()
@click.option('--envpth', type=str, required=True, help='Path to environment file.')
@click.option('--year', type=click.Choice([str(year) for year in range(2000, int(datetime.datetime.today().year)+1)]), required=True, help='Year of interest in format YYYY')
@click.option('--sat', type=sats, required=True, help='Which satellite source to process [ modis | viirs ]')
def year_analysis(envpth: str, year: int, sat: str):
    yearly.run(envpth, sat, year)


@click.group()
def cli():
    pass

cli.add_command(custom_day_range_analysis)
cli.add_command(day_analysis)
cli.add_command(month_analysis)
cli.add_command(year_analysis)

if __name__ == '__main__':
    cli()
    