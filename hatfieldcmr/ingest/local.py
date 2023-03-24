import os
import logging

from io import BytesIO
from typing import Dict
from .push import AbstractStorageClientWrapper

LOGGER = logging.getLogger(__name__)

class LocalStorageWrapper(AbstractStorageClientWrapper):

    def __init__(self, out_dir: str):
        self._out_dir = out_dir
        #self.logger = logging.getLogger()

    def exists(self, blob_name: str) -> bool:
        path = self._make_path(blob_name)
        return os.path.exists(path)

    def upload(
        self,
        blob_name: str,
        buf: BytesIO,
        metadata: Dict = None,
        content_type = None
        ):
        path = self._make_path(blob_name)
        dir_path = os.path.dirname(path)
        if not os.path.exists(dir_path):
            try:
                os.makedirs(dir_path)
            except Exception as e:
                pass
        LOGGER.info(f'storing {path}')
        with open(path, 'wb') as f:
            f.write(buf.read())

    def _make_path(self, blob_name: str) -> str:
        return os.path.join(self._out_dir, blob_name)