from datetime import datetime, timedelta
from dateutil.parser import parse as dateparser
from typing import Tuple, List, Dict

from google.cloud import storage
from hatfieldcmr.ingest.name import format_object_prefix_helper, MODISFileNameParser

DATE_FORMAT = '%Y.%m.%d'


def form_prefixes(product: str, start_date: str, end_date: str = ''):
    start_date = dateparser(start_date)
    end_date = dateparser(end_date) if end_date != '' else datetime.now()

    if (start_date > end_date):
        #TODO
        raise Exception('invalid date range')

    ndays = (end_date - start_date).days + 1
    prefixes = []
    for i in range(ndays):
        date = start_date + timedelta(i)
        date_string = date.strftime(DATE_FORMAT)
        prefixes.append(format_object_prefix_helper(product, date_string))
    return prefixes


def group_blobs(blobs: List) -> Dict:
    blob_dict = {}
    for b in blobs:
        if type(b) == storage.blob.Blob and not b.content_type is None:
            blob_type, granule_id = group_blobs_helper(b)
            if not (granule_id in blob_dict):
                blob_dict[granule_id] = {}
            blob_dict[granule_id][blob_type.name] = b
    return blob_dict


def group_blobs_helper(blob: storage.Blob) -> Tuple[str, str]:
    name = blob.name
    file_type = MODISFileNameParser.identify_file_type(name)
    blob_id = MODISFileNameParser.extract_blob_id(name)
    return file_type, blob_id
