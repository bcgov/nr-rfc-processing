from enum import Enum


class MODISBlobType(Enum):
    THUMBNAIL = 1
    METADATA_XML = 2
    METADATA_JSON = 3
    DATA_HDF = 4
    GEOTIFF = 5
    GEOTIFF_XML = 6
