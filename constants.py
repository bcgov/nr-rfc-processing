import click

# Click options for satellites
def sats():
    return click.Choice(['modis', 'viirs'], case_sensitive=False)

# Click options for watersheds or basins
def typs():
    return click.Choice(['watersheds', 'basins'], case_sensitive=False)

# Click options for number of days to process
def days():
    return click.Choice(['1', '5', '8'])