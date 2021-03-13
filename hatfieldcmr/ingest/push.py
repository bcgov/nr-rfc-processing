"""
Wrapper for bucket store upload client
"""
from abc import ABC, abstractmethod
from typing import Dict, List
from io import BytesIO

class AbstractStorageClientWrapper(ABC):    
    @abstractmethod
    def exists(self, blob_name: str) -> bool:
        pass
    
    @abstractmethod
    def upload(
        self,
        blob_name: str, 
        buf: BytesIO, 
        metadata: Dict = None,
        content_type = None
        ):
        """
        Parameters
        ----------            
        blob_name: str
            name of blob to be uploaded
        buf: BytesIO
            buffer of file
        
        Raises
        ----------
        IngestionException
            if blob already exists
        """
        pass

    
