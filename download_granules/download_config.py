"""
standardizes the configuration used for a satellite download
"""

import admin.constants as const
import datetime
import logging

LOGGER = logging.getLogger(__name__)

product_lut = {
    'modis': const.MODIS_PRODUCT,
    'viirs': const.VIIRS_PRODUCT
}


def set_product(sat: str, datestr: str) -> str:
    """
    over time different versions become available for the same product.  This results
    in the query for the product being a combination of the product and the version
    resulting in no granules.  This method is intended to allow the script to adapt
    to what product to download depending on the date.

    :param product: the name of the product to download, example VNP10A1F.001, VNP10A1F.002
    :type product: str
    """
    product = product_lut[sat]
    if sat == 'viirs':
        cur_date = datetime.datetime.strptime(datestr, "%Y.%m.%d")
        # and datestr != '2024.07.11' - can add logic if required to temporarily revert
        # to V1 of the VNP product.  There is a data hole between the dates 2024.07.10
        # and 2024.07.15
        if cur_date > datetime.datetime(2024, 6, 15):
            # setting to version 2 if after the date above
            product = const.VIIRS_PRODUCT.split('.')[0] + '.2'
    LOGGER.debug(f"set the satellite {sat} product to {product}")
    return product

class SatDownloadConfig:
    def __init__(self,
                 date_span: int,
                 name: str,
                 sat: str,
                 #products: list[str],
                 date_str: str,
                 day_offset=0):
        self.name = name
        # TODO: modify and make the product a singular value
        self.product = set_product(sat, date_str)
        self.day_offset = day_offset
        if sat == 'viirs':
            # force the date_span to 1 for viirs
            date_span = 1

        # TODO: add a date string validation
        self.date_str = date_str

        # if the product is modis these are the possible values for the date
        # span, the date span identifies what dates of modis data will be
        # downloaded in order to create a composite
        self.modis_valid_date_spans = [1, 5, 8]
        if self.is_product_modis() and int(date_span) not in self.modis_valid_date_spans:
            msg = f"specified an invalid modis config of: {date_span}. " + \
                f"valid values are: {self.modis_valid_date_spans}"
            raise ValueError(msg)

        self.date_span = int(date_span) - 1
        LOGGER.debug(f"date_span: {self.date_span}")

    def get_end_date(self):
        """returns the end date
        """
        date = self.date_str.split(".")
        end_date = datetime.datetime(int(date[0]), int(date[1]), int(date[2]))
        return end_date

    def get_start_date(self):
        # date = self.sat_config.date_str.split(".")
        # end_date = datetime.datetime(int(date[0]), int(date[1]), int(date[2]))
        end_date = self.get_end_date()
        start_date = end_date - datetime.timedelta(self.date_span)
        return start_date

    def is_product_modis(self):
        """returns true if the propery 'product' contains a modis related
        product

        :return: is there a modis product in the 'product' property
        :rtype: bool
        """
        is_modis = False
        #products = [pv[0] for pv in self.get_product_version()]
        product_version = self.get_product_version()
        product = product_version[0]
        modis_prod_ver = self._get_product_version(const.MODIS_PRODUCT)
        modis_prod = modis_prod_ver[0]
        if modis_prod == product:
            is_modis = True
        return is_modis

    def get_product_version(self):
        """
        iterates over each product in the products list and
        separates out into product and version

        so  product list like this:
        ['VNP10A1F.1', 'MOD10A1.61']

        turns into:
        [['VNP10A1F', 1], ['MOD10A1', 61]]
        """

        prod_version_list = []
        #for product in self.products:
        prod_version = self._get_product_version(self.product)
        #prod_version_list.append(prod_version)
        return prod_version

    def _get_product_version(self, product_version_str: str) -> list[str, int]:
        """takes a product string and returns it as a product string and the
        associated version assuming the product has the syntax:
        'product.version'


        :param product_version_str: input version string
        :type product_version_str: str
        :return: a list with the the first element being the product string and
            the second the verson number as an int
        :rtype: list[str, int]
        """
        prod_version = product_version_str.split('.')
        prod_version[1] = int(prod_version[1])
        return prod_version

