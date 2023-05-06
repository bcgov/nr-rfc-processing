
import pytest
import logging

import download_granules.download_granules_ostore_integration


LOGGER = logging.getLogger(__name__)

class TestDownloadGranulesOStoreIntegration:

    def test_validate(self, granules_fixture):
        for gran in granules_fixture:
            LOGGER.debug(f"title: {gran['title']}")
            gran_util = download_granules.download_granules_ostore_integration.GranuleUtil(gran)
            gran_util.validate()

    def test_get_granule_local_path(self, granules_fixture):
        for gran in granules_fixture:
            gran_util = download_granules.download_granules_ostore_integration.GranuleUtil(gran)
            local_file = gran_util.get_granule_local_path()
            LOGGER.info(local_file)

