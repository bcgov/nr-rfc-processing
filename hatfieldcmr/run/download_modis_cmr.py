import sys
import time
import os
import datetime
import logging
import logging.handlers
import argparse
import subprocess
from time import sleep
from typing import List, Dict

from dateutil.parser import parse
from google.cloud import storage

from hatfieldcmr import CMRClient
from hatfieldcmr.ingest import AbstractStorageClientWrapper, LocalStorageWrapper, GCSClientWrapper
from hatfieldcmr.version import __version__
import admin.constants as const

# quiet these loggers
logging.getLogger('nose').setLevel(logging.CRITICAL)
logging.getLogger('requests').setLevel(logging.CRITICAL)

fmt = '%(asctime)s %(name)-12s %(levelname)-8s %(message)s'

SLEEP_DURATION = 3 # seconds

# default values
#DEFAULT_LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs', 'hatfieldcmr.log')
DEFAULT_LOG_PATH = "/logs/hatfieldcmr.log"

# default product
DEFAULT_PRODUCT = const.MODIS_PRODUCT #'MOD10A1.61'#'MOD10A1.6'

# bounding box is of british columbia
DEFAULT_BOUNDING_BOX = [-139.06, 48.30, -114.03, 60]

# environment variables
EARTHDATA_USER = os.getenv('EARTHDATA_USER')
EARTHDATA_PASS = os.getenv('EARTHDATA_PASS')

#

bucket = os.getenv('EO_GCS_MTL_BUCKET')
secret_path = os.getenv('EO_INGEST_SECRET')

def download(args):
    """
    Sub-command function to query and download granules
    """
    logger = logging.getLogger()
    storage = configure_storage_wrapper(secret_path, bucket)
    cmrclient = CMRClient(storage, earthdata_user=EARTHDATA_USER, earthdata_pass=EARTHDATA_PASS)
    granules = cmrclient.query(
        args.start_date,
        args.end_date,
        args.product,
        bbox=args.bounding_box
    )
    space_needed = calc_space_needed(granules)
    if args.dry_run:
        logger.info(f'Dry run: {args.product} between {args.start_date} to\
             {args.end_date} bbox: {args.bounding_box}. Queried {len(granules)}\
                  granules amounting to {space_needed} MB')
        return granules

    logger.info(f'Beginning download: {args.product} between {args.start_date}\
         to {args.end_date} bbox: {args.bounding_box}. Queried {len(granules)}\
              granules amounting to {space_needed} MB')
    for g in granules:
        _, is_skip = cmrclient.download_granule(g)
        if not is_skip:
            sleep(SLEEP_DURATION)
    return granules

def calc_space_needed(granules: List[Dict]) -> float:
    res = 0.0
    for g in granules:
        res += float(g.get('granule_size', 0))
    return res

def parse_args(args):
    """ Parse arguments for the NDWI algorithm """
    desc = 'NASA CMR Dataset Retrieval Utility (v%s)' % __version__
    dhf = argparse.ArgumentDefaultsHelpFormatter
    parser = argparse.ArgumentParser(description=desc, formatter_class=dhf)
    parser.add_argument('--version',
                        help='Print version and exit',
                        action='version',
                        version=__version__)
    parser.add_argument('--log-path', default=DEFAULT_LOG_PATH, type=str)
    parser.add_argument('--log-level', default=2, type=int)
    parser.set_defaults(func=lambda x: parser.print_help())
    subparsers = parser.add_subparsers(
        title='subcommands',
        description='valid subcommands',
        help='sub-command help')

    download_sp = subparsers.add_parser('download')
    configure_granule_query_parser_parameters(download_sp)
    download_sp.set_defaults(func=download)
    return parser.parse_args(args)

def configure_granule_query_parser_parameters(sp):
    sp.add_argument('start_date', help='First date')
    sp.add_argument('end_date', help='End date')
    sp.add_argument('-p', '--product', default=DEFAULT_PRODUCT)
    sp.add_argument('--bounding-box',
                        nargs=4,
                        type=float,
                        default=DEFAULT_BOUNDING_BOX,
                        help='Bounding box',
                        metavar=('[lower left lon]', '[lower left lat]',
                                 '[upper left lon]', '[upper left lat]'))
    sp.add_argument('-n', '--dry-run', action="store_true")
    sp.add_argument('--log-path', default=DEFAULT_LOG_PATH, type=str)
    sp.add_argument('--log-level', default=2, type=int)

def configure_listener(log_path: str = DEFAULT_LOG_PATH):
    logging.basicConfig(level=logging.INFO, format=fmt, datefmt='%m-%d-%Y %H:%M')
    logger = logging.getLogger()

    log_dir = os.path.dirname(log_path)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    h = logging.handlers.RotatingFileHandler(log_path, 'a', 3e6, 5)
    f = logging.Formatter(fmt)
    h.setFormatter(f)
    logger.addHandler(h)
    return logger

def get_date(gid):
    """ Get date from granule ID """
    d = gid.split('.')[1].replace('A', '')
    return datetime.datetime.strptime(d, '%Y%j')

def configure_storage_wrapper(secret_path, bucket):
    gcs_client = storage.Client.from_service_account_json(secret_path)
    storage_wrapper = GCSClientWrapper(gcs_client, bucket)
    return storage_wrapper

def main(input_args):
    args = parse_args(input_args)
    logger = configure_listener(args.log_path)
    try:
        args.func(args)
    except Exception as e:
        logger.error(f"Uncaught exception: {e}")
        raise e

if __name__ == "__main__":
    main(sys.argv[1:])
