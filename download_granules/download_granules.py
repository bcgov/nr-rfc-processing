import yaml
import logging

from datetime import datetime, timedelta
from multiprocessing import Pool

from hatfieldcmr.ingest import LocalStorageWrapper
from hatfieldcmr import CMRClient

from .download_config import set_product

import admin.constants as const

logger = logging.getLogger(__name__)
logger.debug("logger name: {__name__}")

# bundle these parameters into a download config
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

    # MODIS product is MOD10A1.61, (used to be just MOD10A1.6)
    # should be a single reference to this product comming from either
    # snow_path_lib function or from const.DEFAULT_PRODUCT, which should be
    # comming from MODIS Product parameter that doesn't exist.
    if sat == 'modis':
        product = {
                'name': 'daily',
                #'products': ['MOD10A1.61'],
                'products': [set_product(sat='modis', date=date)],
                'date_span': int(days)-1
            }
    elif sat == 'viirs':
        product = {
                    'name': 'daily',
                    'products': [set_product(sat='viirs', date=date)],
                    'date_span': int(days)-1
                }
    else:
        pass

    date = date.split('.')
    end_date = datetime(int(date[0]), int(date[1]), int(date[2]))
    storage_wrapper = LocalStorageWrapper(
        const.TOP
    )

    ed_client = CMRClient(storage_wrapper,
                          earthdata_user=secrets['EARTHDATA_USER'],
                          earthdata_pass=secrets['EARTHDATA_PASS'])
    start_date = end_date - timedelta(product['date_span'])
    granules = ed_client.query(
        str(start_date.date()),
        str(end_date.date()),
        product,
        bbox=[*const.BBOX]
    )
    msg = f"queried product {product}, got {len(granules)} granules, downloading"
    logger.info(msg)
    try:
        with Pool(4) as p:
            p.map(ed_client.download_granule, granules)
    except KeyboardInterrupt:
        logger.error('keyboard interupt... Exiting download pool')

# def download_granule(ed_client, granules, ostore_sync):
#     """_summary_

#     :param ed_client: _description_
#     :type ed_client: _type_
#     :param granules: _description_
#     :type granules: _type_
#     :param ostore_sync: object storage sync
#     :type ostore_sync: _type_
#     """

