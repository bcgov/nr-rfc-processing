"""
Client library for using NASAs CMR API for searching and downloading from NASA data holdings
"""

import os
import requests
import datetime
import io
from dateutil.parser import parse as dateparser
from functools import partial
from json import dumps
from time import sleep
from typing import Dict, List, Tuple
import logging
from requests.packages.urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from html.parser import HTMLParser
#from dotenv import load_dotenv, find_dotenv
from cmr import GranuleQuery
from .products import products
from hatfieldcmr.common.retrytools import retry_func
from hatfieldcmr.session import SessionWithHeaderRedirection

from .ingest import AbstractStorageClientWrapper, format_object_name, IngestException
# get environment variables
# load_dotenv(find_dotenv())

# logging
logger = logging.getLogger(__name__)

CHUNK_SIZE = 256 * 1024


class CMRClient():
    def __init__(self,
                 storage_client: AbstractStorageClientWrapper,
                 earthdata_user='',
                 earthdata_pass=''):
        self._storage_client = storage_client
        self.earthdata_user = earthdata_user or os.getenv('EARTHDATA_USER')
        self.earthdata_pass = earthdata_pass or os.getenv('EARTHDATA_PASS')

    def query(self,
              start_date: str,
              end_date: str,
              product: str,
              provider: str = 'LPDAAC_ECS',
              bbox: List = []) -> List[Dict]:
        """
        Search CMR database for spectral MODIS tiles matching a temporal range,
        defined by a start date and end date. Returns metadata containing the URL of
        each image.

        Parameters
        ----------
        start_date: string
            Start date yyyy-mm-dd
        end_date: string
            End date yyyy-mm-dd
        product: string
            Product name
        provider: string
            Provider (default is 'LPDAAC_ECS')
        bbox: List[float]
            Bounding box [lower_left_lon, lower_left_lat, upper_right_lon, upper_right_lat]

        Returns
        ----------
        List[Dict]
            List of granules
        """
        q = GranuleQuery()
        prod, ver = product['products'][0].split('.')
        q.short_name(prod).version(ver)
        q.temporal(f"{start_date}T00:00:00Z", f"{end_date}T23:59:59Z")
        if (len(bbox) >= 4):
            q.bounding_box(*bbox[:4])
        _granules = q.get_all()

        # filter dates
        if 'day_offset' in product.keys():
            day_offset = products[product]['day_offset']
        else:
            day_offset = 0
        granules = []
        for gran in _granules:
            # CMR uses day 1 of window - correct this to be middle of window
            date = (dateparser(gran['time_start'].split('T')[0]) +
                    datetime.timedelta(days=day_offset)).date()
            if (dateparser(start_date).date() <= date <=
                    dateparser(end_date).date()):
                granules.append(gran)
        logger.info("%s granules found within %s - %s" %
                    (len(granules), start_date, end_date))
        return granules

    def siesta(self):
        sleep(0.2)

    def download_granule(self, meta):
        """ Download granule files from metadata instance """
        # get basename
        url = str(meta['links'][0]['href'])
        is_skip = False
        # save metadata
        fn_meta, sk = self.persist_metadata(meta, os.path.basename(url))

        # download hdf
        fn_hdf, sk = self.download_file(url,
                                        meta,
                                        content_type="application/x-hdfeos")
        is_skip = is_skip or sk
        if not sk:
            self.siesta()

        links = {
            m['type']: m['href']
            for m in meta['links'][1:] if 'type' in m
        }
        # download xml metadata
        fn_metaxml = None
        if links.get('text/xml'):
            fn_metaxml, sk = self.download_file(links['text/xml'],
                                                meta,
                                                content_type="text/xml")
            is_skip = is_skip or sk
            if not sk:
                self.siesta()

        # download browse image
        fn_browse = None
        if links.get('text/jpeg'):
            fn_browse, sk = self.download_file(links['image/jpeg'],
                                            meta,
                                            noauth=True,
                                            content_type="image/jpeg")
            is_skip = is_skip or sk
            if not sk:
                self.siesta()

        return [fn_hdf, fn_browse, fn_meta, fn_metaxml], is_skip

    def persist_metadata(self, meta: Dict, bname: str,
                         encoding: str = 'utf-8'):
        fout = format_object_name(meta, f"{bname}_meta.json")
        if self._storage_client.exists(fout):
            logger.info(f"file {fout} already exists in store, skipping")
            return fout, True
        buf = io.BytesIO(
            bytes(dumps(meta, sort_keys=True, indent=4, ensure_ascii=False),
                  encoding))
        try:
            self._storage_client.upload(fout,
                                        buf,
                                        content_type="application/json")
        except IngestException:
            pass
        except Exception as e:
            raise RuntimeError(f"Problem saving {fout}, {e}")
        return fout, False

    def download_file(self,
                      url: str,
                      meta: Dict,
                      noauth: bool = False,
                      download_retry_count: int = 0,
                      upload_retry_count: int = 0,
                      content_type: str = None) -> Tuple[str, bool]:
        """ Get URL and save with some name """
        fout = format_object_name(meta, os.path.basename(url))
        auth = () if noauth else (self.earthdata_user, self.earthdata_pass)
        logger.info(f"downloading file {url}")

        check_exist_func = partial(self._storage_client.exists, fout)
        if (retry_func(check_exist_func)):
            logger.info(f"file {fout} already exists in store, skipping")
            return fout, True

        # download as stream
        download_func = partial(self.download_earthdata_file,
                                url,
                                auth,
                                noauth=noauth)
        buf = retry_func(download_func)

        logger.info(f"saving granule {fout}")
        upload_func = partial(self._storage_client.upload,
                              fout,
                              buf,
                              content_type=content_type)
        retry_func(upload_func)
        logger.info(f"fetched and uploaded file {fout} from {url}")
        return fout, False

    def download_earthdata_file(self,
                                url: str,
                                auth: Tuple,
                                noauth: bool = False) -> io.BytesIO:
        session = self.get_session(auth, retries=5)
        if noauth:
            stream = session.get(url, stream=True)
        else:
            stream = self.get_stream(session, url, auth, [])
        buf = io.BytesIO()
        for chunk in stream.iter_content(CHUNK_SIZE):
            buf.write(chunk)
        buf.seek(0, 0)
        return buf

    def get_session(self, auth, retries=5):
        # s = requests.Session()
        s = SessionWithHeaderRedirection(auth)
        # r = Retry(total=retries, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
        # s.mount('http://', HTTPAdapter(max_retries=r))
        # s.mount('https://', HTTPAdapter(max_retries=r))
        return s

    def get_stream(self, session, url, auth, previous_tries):
        """ Traverse redirects to get the final url """

        # stream = session.get(url, auth=auth, stream=True)
        stream = session.get(url,
                             auth=auth,
                             allow_redirects=True,
                             stream=True)

        # if we get back to the same url, it's time to download
        if url in previous_tries or stream.status_code == 200:
            return stream

        if stream.status_code == 302:
            # if stream.status_code != 200:
            #     print(f"Error getting response {stream.status_code} {stream.text}")
            previous_tries.append(url)
            link = LinkFinder()
            link.feed(stream.text)
            return self.get_stream(session, link.download_link, auth,
                                   previous_tries)
        else:
            raise RuntimeError(
                f"Earthdata Authentication Error {stream.status_code} {stream.text}"
            )
        # return stream


class LinkFinder(HTMLParser):
    def __init__(self):
        super().__init__()
        self.download_link = None

    def handle_starttag(self, tag, attrs):
        if attrs and attrs[0][0] == 'href':
            self.download_link = attrs[0][1]
