"""
Client to interact with STAC API
"""
import json
from functools import reduce
from typing import List, Dict

from dateutil.parser import parse as dateparser
from pystac import Item
import requests
from urllib.parse import urljoin

STAC = 'stac'
ITEM = 'item'
ITEMS = 'items'
COLLECTIONS = 'collections'

DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'


class StacClient:
    def __init__(self,
                 api_url: str,
                 session: requests.Session = None,
                 cookies=None):
        if not session:
            session = requests.Session()
        if '://' not in api_url:
            raise Exception(
                f'Api URL needs to begin with URI scheme [scheme]://, {api_url}'
            )
        self.api_url = api_url
        self.session = session
        self.cookies = cookies

    def find_collection(self, collection_id: str) -> Dict:
        url = self._create_find_collection_endpoint(collection_id)
        r = self.session.get(url)
        return r.json()

    def find_collection_items(self, collection_id: str) -> Dict:
        url = self._create_find_collection_items_endpoint(collection_id)
        r = self.session.get(url)
        return r.json()

    def find_item(self, collection_id: str, item_id: str) -> Dict:
        url = self._create_find_item_endpoint(collection_id, item_id)
        r = self.session.get(url)
        return r.json()

    def add_item(self, collection_id: str, item: Dict):
        if type(item) == Item:
            item = item.to_dict()
        item = self._normalize_datetime_field(item)
        url = self._create_add_item_endpoint(collection_id)
        headers = {'Content-Type': 'application/json'}
        #r = self.session.post(url, item, headers=headers)
        data = json.dumps(item)
        r = self.session.post(url,
                              data=data,
                              headers=headers,
                              cookies=self.cookies)
        if not r.ok:
            print(f'!!error occurred {url} {r.status_code}')
        #print(f"adding to {url} {r.status_code} {r.text}")
        return r, data

    def _create_find_collection_endpoint(self, collection_id: str):
        """/stac/[collection_id]
        """
        return join_url(self.api_url, STAC, collection_id)

    def _create_find_collection_items_endpoint(self, collection_id: str):
        """/stac/[collection_id]/items
        """
        return join_url(self.api_url, STAC, collection_id, ITEMS)

    def _create_find_item_endpoint(self, collection_id: str, item_id: str):
        """/stac/[collection_id]/item/[item_id]
        """
        return join_url(self.api_url, STAC, collection_id, ITEMS, item_id)

    def _create_add_item_endpoint(self, collection_id: str):
        """/collections/[collection_id]/items
        """
        return join_url(self.api_url, COLLECTIONS, collection_id, ITEMS)

    def _normalize_datetime_field(self, item: Dict) -> Dict:
        datetime_field = item['properties']['datetime']
        item['properties']['datetime'] = dateparser(datetime_field).strftime(
            DATETIME_FORMAT)
        return item


def join_url(*args):
    return reduce(lambda a, b: urljoin(a + '/', b), args)
