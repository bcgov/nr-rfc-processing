# one off script to iterate over all the files in the snowpack_archive
# folder and convert them all to public/read permissions if they
# aren't already.


import NRUtil.NRObjStoreUtil
import logging

LOGGER = logging.getLogger()

class MakePublic:
    def __init__(self, obj_store_dir):
        self.obj_store_dir = obj_store_dir
        self.os_util = NRUtil.NRObjStoreUtil.ObjectStoreUtil()

    def set_public(self):
        LOGGER.info(f"getting the list of files for: {self.obj_store_dir}")
        ostr_files = self.os_util.list_objects(objstore_dir=self.obj_store_dir)

        for cur_file in ostr_files:
            #LOGGER.debug(f"cur_file: {cur_file.object_name}")
            if not cur_file.is_dir:
                self.os_util.set_public_permissions(object_name=cur_file.object_name)

if __name__ == '__main__':

    # logging config
    LOGGER.setLevel(logging.INFO)
    hndlr = logging.StreamHandler()
    fmtStr = '%(asctime)s - %(name)s - %(levelname)s - %(lineno)d - %(message)s'
    formatter = logging.Formatter(fmtStr)
    hndlr.setFormatter(formatter)
    LOGGER.addHandler(hndlr)
    LOGGER.debug("test")

    obj_store_dir = 'snowpack_archive/plot/viirs/'
    pub = MakePublic(obj_store_dir)

    pub.set_public()

