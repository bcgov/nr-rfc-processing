from dateutil.parser import parse as dateparser
from typing import Dict, List

import pystac


class CMR2STACItemParser:
    POLYGONS_KEY = 'polygons'
    TIME_START_KEY = 'time_start'
    TIME_END_KEY = 'time_end'
    DAY_NIGHT_FLAG_KEY = 'day_night_flag'

    STAC_DAY_NIGHT_FLAG_KEY = 'modis:day_night_flag'
    STAC_YEAR_KEY = 'modis:year'
    STAC_MONTH_KEY = 'modis:month'
    STAC_DAY_KEY = 'modis:day'
    STAC_TIME_START_KEY = 'modis:start_date'
    STAC_TIME_END_KEY = 'modis:end_date'

    @classmethod
    def parse(cls, id: str, product_name_without_version: str,
              cmr_item: Dict) -> pystac.Item:
        geom = cls.parse_polygons(cmr_item)
        bbox = cls.geojson_polygon_to_bbox(geom['coordinates'])
        datetime = cls.parse_start_date(cmr_item)
        properties = cls.parse_properties(cmr_item)
        return pystac.Item(id,
                           geom,
                           bbox,
                           datetime,
                           properties,
                           collection=cls.form_stac_collection_id(
                               product_name_without_version.lower()))

    @classmethod
    def parse_polygons(cls, cmr_item: Dict) -> Dict:
        if (not (cls.POLYGONS_KEY in cmr_item)):
            raise Exception(f'required key {cls.POLYGONS_KEY} not found')
        polygons_raw = cmr_item[cls.POLYGONS_KEY]
        polygons = []
        for outer in polygons_raw:
            for lat_lon_str_array in outer:
                coord_array = cls._parse_lat_lon_str_array(lat_lon_str_array)
                polygons.append(coord_array)
        geom = {'type': 'Polygon', 'coordinates': polygons}
        return geom

    @classmethod
    def _parse_lat_lon_str_array(cls, str_array: List) -> List:
        lat_lon_alt_str = str_array.split(' ')
        if (len(lat_lon_alt_str) % 2 != 0):
            raise Exception(
                f'polygon lat lon pairs need to be even in length {str_array}')
        lat_lon_alt_values = [float(x) for x in lat_lon_alt_str]
        result = []
        for j in range(int(len(lat_lon_alt_values) / 2)):
            # GeoJSON spec requires Lon, Lat coordinates
            # https://tools.ietf.org/html/rfc7946#section-3.1
            lat = lat_lon_alt_values[2 * j]
            lon = lat_lon_alt_values[2 * j + 1]
            result.append([lon, lat])
        return result

    @classmethod
    def geojson_polygon_to_bbox(cls, polygons: List) -> List:
        if (len(polygons) == 0):
            raise Exception('empty polygon')
        nonempty_polygons = list(filter(lambda x: len(x) > 0, polygons))
        first_coord = nonempty_polygons[0][0]
        min_lat = first_coord[1]
        max_lat = first_coord[1]
        min_lon = first_coord[0]
        max_lon = first_coord[0]

        for polygon in nonempty_polygons:
            for coord in polygon:
                lat = coord[1]
                lon = coord[0]
                if lat < min_lat:
                    min_lat = lat
                if lat > max_lat:
                    max_lat = lat
                if lon < min_lon:
                    min_lon = lon
                if lon > max_lon:
                    max_lon = lon
        return [min_lon, min_lat, max_lon, max_lat]

    @classmethod
    def parse_start_date(cls, cmr_item: Dict):
        if (not (cls.TIME_START_KEY in cmr_item)):
            raise Exception('no start key in cmr_item')
        return dateparser(cmr_item[cls.TIME_START_KEY])

    @classmethod
    def parse_properties(cls, cmr_item: Dict):
        properties = {}

        if cls.DAY_NIGHT_FLAG_KEY in cmr_item:
            properties[cls.STAC_DAY_NIGHT_FLAG_KEY] = cmr_item[
                cls.DAY_NIGHT_FLAG_KEY]

        if cls.TIME_START_KEY in cmr_item:
            date = cls.parse_start_date(cmr_item)
            properties[cls.STAC_YEAR_KEY] = date.year
            properties[cls.STAC_MONTH_KEY] = date.month
            properties[cls.STAC_DAY_KEY] = date.day
            # properties[cls.STAC_TIME_START_KEY] = cmr_item[cls.TIME_START_KEY]

        # if cls.STAC_TIME_END_KEY in cmr_item:
        #     properties[cls.STAC_TIME_END_KEY] = cmr_item[cls.TIME_END_KEY]
        return properties

    @classmethod
    def form_stac_collection_id(cls, product_name_without_version: str) -> str:
        return f'modis.{product_name_without_version}'