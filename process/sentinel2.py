import os

from sentinelsat import SentinelAPI, geojson_to_wkt
from datetime import date, timedelta

def run_pipeline(user: str, pwd: str, long: float, lat: float, udate: str):
    
    point = {
        "type": "Feature",
        "geometry": {
        "type": "Point",
        "coordinates": [long, lat]
        }
    }

    api = SentinelAPI(
        user, 
        pwd, 
        'https://scihub.copernicus.eu/dhus',
        show_progressbars=True
    )

    day_tolerance = 2

    if type(udate) != date:
        udate = udate.split('.')
        udate = date(int(udate[0]), int(udate[1]), int(udate[2]))
    products = []
    while len(products) == 0:
    
        before = udate-timedelta(days=day_tolerance)
        products = api.query(
                        geojson_to_wkt(point),
                        date=(before, udate),
                        platformname='Sentinel-2',
                        cloudcoverpercentage=(0, 30),
                        limit=1,
                        )
        print(products)
        print(len(products))
        day_tolerance += 1
        print(f'DAY TOLERANCE: {day_tolerance}')

if __name__ == "__main__":
 run_pipeline(os.environ['SENTINELSAT_UNAME'], os.environ['SENTINELSAT_PWD'], 123.0, 49.0, date(2021, 2, 1))
    