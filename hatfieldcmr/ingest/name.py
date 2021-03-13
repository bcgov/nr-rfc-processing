"""
Contains data ingest related functions
"""
import re
import os.path
from dateutil.parser import parse as dateparser

import typing
from typing import Dict

import cmr
from hatfieldcmr.ingest.file_type import MODISBlobType

MODIS_NAME = "modis-terra"
TITLE_PATTERN_STRING = r"\w+:([\w]+\.[\w]+):\w+"
TITLE_PATTERN = re.compile(TITLE_PATTERN_STRING)

GRANULE_TITLE_KEY = 'title'
GRANULE_TIME_KEY = 'time_start'
GRANULE_NAME_KEY = 'producer_granule_id'


def format_object_name(meta: Dict, object_name: str) -> str:
    """
    Parameters
    ----------
    metas: Dict
        Single Granule metadata JSON response from CMR
    object_name: str
        Name of object (ex. hdf file, xml file)
    Returns
    ----------
    str
        Object name for granule. 
        If insufficient information is available, empty string is returned.
    """
    default_value = ""
    if meta is None:
        return default_value

    folder_prefix = ""
    try:
        folder_prefix = format_object_prefix(meta)
    except ValueError:
        return ''
    os.makedirs(folder_prefix, exist_ok=True)
    return f"{folder_prefix}/{object_name}"


def format_object_prefix(meta: Dict):
    """Helper function to generate 'folder prefix' of the bucket object
    """
    if not ((GRANULE_TITLE_KEY in meta) and (GRANULE_TIME_KEY in meta) and
            (GRANULE_NAME_KEY in meta)):
        raise ValueError('granule does not have required keys', meta)

    title = meta.get(GRANULE_TITLE_KEY, "")
    m = TITLE_PATTERN.match(title)
    if m is None:
        raise ValueError('granule does not have well formated title', title)

    product_name = m.groups()[0]

    date_string = dateparser(meta.get("time_start")).strftime('%Y.%m.%d')

    folder_prefix = format_object_prefix_helper(product_name, date_string)
    # f"{MODIS_NAME}/{product_name}/{date_string}"

    return folder_prefix


def format_object_prefix_helper(product_name: str, date_string: str):
    return f"{MODIS_NAME}/{product_name}/{date_string}"

class BlobPathMetadata:
    def __init__(self, product_name: str, date_string: str):
        self.product_name = product_name
        self.product_name_without_version = product_name[:7].lower()
        self.date_string = date_string
        self.date = dateparser(date_string)

    @staticmethod
    def parse(prefix_or_full_name: str):
        parts = prefix_or_full_name.split(r'/')
        if (len(parts) >= 3):
            product_name = parts[1]
            date_string = parts[2]
            return BlobPathMetadata(product_name, date_string)
        return None


class MODISFileNameParser:
    THUMBNAIL_RE = re.compile(r"BROWSE\.([\w\.]+)\.\d+\.jpg")

    @classmethod
    def identify_file_type(cls, name: str):
        basename = os.path.basename(name)
        if ('BROWSE' in basename):
            return MODISBlobType.THUMBNAIL
        elif ('.hdf.xml' in basename):
            return MODISBlobType.METADATA_XML
        elif ('.hdf_meta.json' in basename):
            return MODISBlobType.METADATA_JSON
        elif ('.hdf' in basename):
            return MODISBlobType.DATA_HDF
        elif ('.tif.aux.xml' in basename):
            return MODISBlobType.GEOTIFF_XML
        elif ('.tif' in basename):
            return MODISBlobType.GEOTIFF
        else:
            print(f'unknown file name {name}')
        return ''

    @classmethod
    def extract_blob_id(cls, name: str, file_type: MODISBlobType = None):
        if file_type is None:
            file_type = cls.identify_file_type(name)

        if file_type == MODISBlobType.THUMBNAIL:
            return cls._extract_blob_id_thumbnail(name)
        elif file_type == MODISBlobType.METADATA_XML:
            return cls._extract_basename_from_file(name, '.hdf.xml')
        elif file_type == MODISBlobType.METADATA_JSON:
            return cls._extract_basename_from_file(name, '.hdf_meta.json')
        elif file_type == MODISBlobType.DATA_HDF:
            return cls._extract_basename_from_file(name, '.hdf')
        elif file_type == MODISBlobType.GEOTIFF:
            return cls._extract_basename_from_file(name, '.tif')
        elif file_type == MODISBlobType.GEOTIFF_XML:
            return cls._extract_basename_from_file(name, '.tif.aux.xml')
        return ''

    @classmethod
    def _extract_blob_id_thumbnail(cls, name: str) -> str:
        basename = os.path.basename(name)
        m = cls.THUMBNAIL_RE.match(basename)
        if m is None:
            return ''
        blob_id = m.groups()[0]

        name_includes_dir = len(name.split(r'/')) >= 4
        if (name_includes_dir):
            product_name_doesnt_match_blob_prefix = cls._check_thumbnail_product_inconsistency(
                name, blob_id)
            if (product_name_doesnt_match_blob_prefix):
                blob_id = cls._fix_thumbnail_product_name_inconsistency(
                    name, blob_id)
        return blob_id

    @classmethod
    def _check_thumbnail_product_inconsistency(cls, name: str, blob_id: str):
        full_name_product_name, blob_id_product_name = cls._extract_product_names(
            name, blob_id)
        return full_name_product_name != blob_id_product_name

    @classmethod
    def _fix_thumbnail_product_name_inconsistency(cls, name: str,
                                                  blob_id: str):
        full_name_product_name, blob_id_product_name = cls._extract_product_names(
            name, blob_id)
        return blob_id.replace(blob_id_product_name, full_name_product_name)

    @classmethod
    def _extract_product_names(cls, name: str, blob_id: str):
        product_name_with_version = name.split(r'/')[1]
        full_name_product_name = product_name_with_version[:7]
        blob_id_product_name = blob_id[:7]
        return full_name_product_name, blob_id_product_name

    @classmethod
    def _extract_basename_from_file(cls, name: str, extension: str) -> str:
        basename = os.path.basename(name).strip()
        extension_len = len(extension)
        if (len(basename) > extension_len
                and basename[-extension_len:] == extension):
            return basename[:-extension_len]
        return ''
