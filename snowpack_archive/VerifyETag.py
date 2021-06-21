"""
copied from https://teppen.io/2018/10/23/aws_s3_verify_etags/

Used to determine if the etag can be verified, for multipart file uploads.
"""

import os
import sys
from hashlib import md5
import minio

import logging

LOGGER = logging.getLogger(__name__)

class CalcETags(object):
    def __init__(self):
        self.defaultPartSize = 1048576

    def factor_of_1MB(self, filesize, num_parts):
        x = filesize / int(num_parts)
        y = x % self.defaultPartSize
        return int(x + self.defaultPartSize - y)

    def calc_etag(self, inputfile, partsize):
        md5_digests = []
        with open(inputfile, 'rb') as f:
            for chunk in iter(lambda: f.read(partsize), b''):
                md5_digests.append(md5(chunk).digest())
        return md5(b''.join(md5_digests)).hexdigest() + '-' + str(len(md5_digests))

    def possible_partsizes(self, filesize, num_parts):
        return lambda partsize: partsize < filesize and (float(filesize) / float(partsize)) <= num_parts

    def etagIsValid(self, inFilePath, s3eTag):
        LOGGER.debug(f'inFilePath: {inFilePath}, s3eTag: {s3eTag}')
        filesize  = os.path.getsize(inFilePath)
        num_parts = int(s3eTag.split('-')[1])
        etagIsValid = False
        # Default Partsizes Map: aws_cli/boto3, s3cmd
        partsizes = [
            8388608,
            15728640,
            self.factor_of_1MB(filesize, num_parts) # Used by many clients to upload large files
        ]

        for partsize in filter(self.possible_partsizes(filesize, num_parts), partsizes):
            calcETag = self.calc_etag(inFilePath, partsize)
            LOGGER.debug(f'etags froms3: {s3eTag}, calced: {calcETag}, {partsize}')

            if s3eTag == calcETag:
                LOGGER.debug("paths match")
                etagIsValid = True
                break
        return etagIsValid

if __name__ == '__main__':

    LOGGER = logging.getLogger()
    LOGGER.setLevel(logging.DEBUG)
    hndlr = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(lineno)d - %(message)s')
    hndlr.setFormatter(formatter)
    LOGGER.addHandler(hndlr)
    LOGGER.debug("test")

    src = r'Z:\snowpack_data\intermediate_tif\modis\2021.04.25\MOD10A1.A2021115.h12v02.006.2021117210232_EPSG4326.tif'
    destEtag = '4147381cf3b9d6d4b1b7f0da691af8a6-3'
    calcETag = CalcETags()
    retVal = calcETag.etagIsValid(src, destEtag)
    LOGGER.debug(f"retVal: {retVal}")
