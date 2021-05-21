import unittest
import sys
import logging
import os
modulePath = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, modulePath)
import archive2ObjectStore.archiveSnowpackData as ArchiveSnowData
import archive2ObjectStore.constants

# config simple logger for debugging tests
# add a simple console logger
LOGGER = logging.getLogger()
LOGGER.setLevel(logging.DEBUG)
hndlr = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(lineno)d - %(message)s')
hndlr.setFormatter(formatter)
LOGGER.addHandler(hndlr)
LOGGER.debug("test")


class Test_BackupConfig(unittest.TestCase):

    def setUp(self):
        self.backup = ArchiveSnowData.ArchiveSnowData()
        os.environ['ROOTDIRECTORIES_OMIT'] = os.environ['ROOTDIRECTORIES_OMIT'] + ',basins/ADAMS_RIVER_NEAR_SQUILAX'
        const = archive2ObjectStore.constants
        self.backup.getOmitDirs()


    def test_getBackConfig(self):
        dirStr = r'Z:\snowpack_data\basins\ADAMS_RIVER_NEAR_SQUILAX\modis\2021.04.24'
        dateFromDir = self.backup.getDirectoryDate(dirStr)
        isOlder = self.backup.isReadyForArchive(dirStr)
        self.assertTrue(isOlder)

        dirStr = r'Z:\snowpack_data\basins\ADAMS_RIVER_NEAR_SQUILAX\modis\2099.05.24'
        isOlder = self.backup.isReadyForArchive(dirStr)
        self.assertFalse(isOlder)

        print(f' is Older: {isOlder}')

    def test_iterator(self):
        cnt = 0
        for newDir in self.backup.dirIterator:
            print(f'newDir: {newDir}')
            if cnt > 30:
                break
            cnt += 1


        #self.assert

        #self.assertIsNotNone(conf)
        #self.assertIsInstance(conf, dict)

# class Test_BackupConfigIterator(unittest.TestCase):
#     def test_backupiterator(self):
#         backupConfig = backup.BackupSnowData()
#         backupIter = backup.BackupConfigIterator(backupConfig)
#         print(f'backupIter: {backupIter}')
#         self.assertTrue(hasattr(backupIter, '__iter__'))
#         self.assertTrue(hasattr(backupIter, '__next__'))

#         for obj in backupIter:
#             print(obj)

# class BackupDateDirectoryIterator(unittest.TestCase):
#     def test_GetDirectoryList(self):
#         record = {'basins': ['*', ['modis', 'viirs']]}
#         backup.GetDirectoryList(record)




if __name__ == '__main__':
    unittest.main()