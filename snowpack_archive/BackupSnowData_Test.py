import unittest
import backup

class Test_BackupConfig(unittest.TestCase):

    def test_getBackConfig(self):
        bkup = backup.BackupSnowData()
        conf = bkup.getBackConfig()
        print(f'conf {conf}')
        self.assertIsNotNone(conf)
        self.assertIsInstance(conf, dict)

class Test_BackupConfigIterator(unittest.TestCase):
    def test_backupiterator(self):
        backupConfig = backup.BackupSnowData()
        backupIter = backup.BackupConfigIterator(backupConfig)
        print(f'backupIter: {backupIter}')
        self.assertTrue(hasattr(backupIter, '__iter__'))
        self.assertTrue(hasattr(backupIter, '__next__'))

        for obj in backupIter:
            print(obj)

class BackupDateDirectoryIterator(unittest.TestCase):
    def test_GetDirectoryList(self):
        record = {'basins': ['*', ['modis', 'viirs']]}
        backup.GetDirectoryList(record)
        



if __name__ == '__main__':
    unittest.main()