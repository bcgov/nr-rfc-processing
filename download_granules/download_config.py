"""
standardizes the configuration used for a satellite download
"""

import admin.constants as const

class SatDownloadConfig:
    def __init__(self, date_span: int, name: str, products: list[str],
                 date_str: str, day_offset=None):
        self.name = name
        # TODO: modify and make the product a singular value
        self.products = products  # VNP10A1F.1 MOD10A1.61
        self.day_offset = day_offset

        # TODO: add a date string validation
        self.date_str = date_str

        # if the product is modis these are the possible values for the date
        # span, the date span identifies what dates of modis data will be
        # downloaded in order to create a composite
        self.modis_valid_date_spans = [1, 5, 8]
        if self.is_product_modis() and date_span not in self.modis_valid_date_spans:
            msg = f"specified an invalid modis config of: {date_span}. " + \
                f"valid values are: {self.modis_valid_date_spans}"
            raise ValueError(msg)

        self.date_span = date_span - 1

    def is_product_modis(self):
        """returns true if the propery 'product' contains a modis related
        product

        :return: is there a modis product in the 'product' property
        :rtype: bool
        """
        is_modis = False
        products = [pv[0] for pv in self.get_product_version()]
        modis_prod_ver = self._get_product_version(const.MODIS_PRODUCT)
        modis_prod = modis_prod_ver[0]
        if modis_prod in products:
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
        for product in self.products:
            prod_version = self._get_product_version(product)
            prod_version_list.append(prod_version)
        return prod_version_list

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

