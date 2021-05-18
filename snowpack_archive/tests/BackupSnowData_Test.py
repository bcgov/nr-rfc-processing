import unittest
import sys
import os
modulePath = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, modulePath)
import archive2ObjectStore.archiveSnowpackData as ArchiveSnowData

class Test_BackupConfig(unittest.TestCase):

    def test_getBackConfig(self):
        backup = ArchiveSnowData.ArchiveSnowData()
        dirStr = r'Z:\snowpack_data\basins\ADAMS_RIVER_NEAR_SQUILAX\modis\2021.04.24'
        dateFromDir = backup.getDirectoryDate(dirStr)
        isOlder = backup.isReadyForArchive(dirStr)
        self.assertTrue(isOlder)

        dirStr = r'Z:\snowpack_data\basins\ADAMS_RIVER_NEAR_SQUILAX\modis\2099.05.24'
        isOlder = backup.isReadyForArchive(dirStr)
        self.assertFalse(isOlder)

        print(f' is Older: {isOlder}')
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