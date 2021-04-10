import yaml
import logging

from datetime import datetime, timedelta
from multiprocessing import Pool

from hatfieldcmr.ingest import LocalStorageWrapper
from hatfieldcmr import CMRClient

import admin.constants as const

logger = logging.getLogger(__name__)

def download_granules(envpath: str, date: str, sat: str, days: int = 5):
    """Download MODIS/VIIRS granules for a given day

    Parameters
    ----------
    envpath : str
        [description]
    sat : str
        [description]
    """
    #load_dotenv(envpath)
    envvars = open(envpath ,'r')
    secrets = yaml.load(envvars, Loader=yaml.FullLoader)
    envvars.close()
    
    if sat == 'modis':
        product = {
                'name': 'daily',
                'products': ['MOD10A1.6'],
                'date_span': int(days)-1
            }
    elif sat == 'viirs':
        product = {
                    'name': 'daily',
                    'products': ['VNP10A1F.1'],
                    'date_span': int(days)-1
                }
    else:
        pass

    date = date.split('.')
    end_date = datetime(int(date[0]), int(date[1]), int(date[2]))
    storage_wrapper = LocalStorageWrapper(
        const.TOP
    )

    ed_client = CMRClient(storage_wrapper, earthdata_user=secrets['EARTHDATA_USER'], earthdata_pass=secrets['EARTHDATA_PASS'])
    start_date = end_date - timedelta(product['date_span'])
    granules = ed_client.query(
        str(start_date.date()),
        str(end_date.date()),
        product,
        bbox=[*const.BBOX]
    )
    print(f"queried product {product}, got {len(granules)} granules, downloading")
    try:
        with Pool(4) as p:
            p.map(ed_client.download_granule, granules)
    except KeyboardInterrupt:
        print('Exiting download pool')
