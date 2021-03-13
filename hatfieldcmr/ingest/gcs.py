"""
Wrapper for pushing data to Google Cloud Storage
"""
import google.cloud
from google.cloud import storage
from io import BytesIO
from typing import Dict
from .push import AbstractStorageClientWrapper
from .ingest_exception import IngestException
class GCSClientWrapper(AbstractStorageClientWrapper):
    
    def __init__(self, client: storage.client, bucket: str):
        self._client = client
        self._bucket = bucket
        # check bucket exists
        self._client.get_bucket(self._bucket)

    def exists(self, blob_name: str) -> bool:
        bucket = self._client.get_bucket(self._bucket)
        blob = bucket.get_blob(blob_name)
        return blob is not None

    def upload(
        self, 
        blob_name: str, 
        buf: BytesIO, 
        metadata: Dict = None,
        content_type = None
        ):
    
        try:            
            bucket = self._client.get_bucket(self._bucket)
            blob = bucket.get_blob(blob_name)
            if blob is not None:
                # TODO raise more meaningful exception
                # raise IngestException("blob already exists")
                print(f"Blob already exists, why are you downloading it again? ?_? {blob_name}")
                return
            blob = bucket.blob(blob_name)
            # merge metadata dictionaries
            metadata = metadata or {}
            blob.metadata = blob.metadata or {}
            blob.metadata = { **metadata, **blob.metadata }
            blob.upload_from_file(buf, content_type=content_type)
        except google.cloud.exceptions.NotFound as e:
            raise e
        except google.cloud.exceptions.GoogleCloudError as e:
            raise e
