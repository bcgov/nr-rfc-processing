import logging
import minio
import NRUtil.NRObjStoreUtil
import os.path

LOGGER = logging.getLogger(__name__)


class OStore:
    def __init__(self):
        self.ostore = NRUtil.NRObjStoreUtil.ObjectStoreUtil()
        self.historical_norms_path = "norm/{sat}/daily/{period}/{month}.{day}.tif"

    def get_10yr_tif(self, sat, month, day, out_path):
        if not os.path.exists(out_path):
            ostore_path = self.historical_norms_path.format(
                period="10yr", month=month, day=day, sat=sat
            )
            LOGGER.debug(f"pulling the 10yr file: {ostore_path} down from obj store")
            self.ostore.get_object(file_path=ostore_path, local_path=out_path)

    def get_20yr_tif(self, sat, month, day, out_path):
        if not os.path.exists(out_path):

            ostore_path = self.historical_norms_path.format(
                period="20yr", month=month, day=day, sat=sat
            )
            LOGGER.debug(f"pulling the 20yr file: {ostore_path} down from obj store")
            self.ostore.get_object(file_path=ostore_path, local_path=out_path)
