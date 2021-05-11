"""
expects the following environment variables be set:
  ROOT_DIR = the root directory for the snowpack data
  BACKUP_ROOT = the directory where snowpack data should get backed up

Script reads the config.json file that describes what exactly to backup:

config.json format:

    inputDirectoryList:
        list of objects with the following format:

        {directory_name: [list describing file paths]}

        where:
          * directory_name: is the name of the directory in the ROOT_DIR
                that needs to be backed up
          * list describing file paths: a list describing the path to a 
                directory containing a bunch of date delimited directories

        The file path list can contain:
        * name of a directory
        * a '*' meaning iterate through each directory evaluating the contents
        * a list describing a subset of the directories that are expected


The script:
* iterates through all of the dated directories
* parses the date directories into a date object
* if the directory is older than (default=2weeks) it archives the 
  directory into object store
* archive calculates md5 on source, copies, calculates again on destination
  then deletes.
"""

import minio
import os
import json


class BackupSnowData(object):
    def __init__(self):
        pwd = os.path.dirname(__file__)
        self.configFile = os.path.join(pwd, "config.json")
        self.backupConfig = self.getBackConfig()

    def getBackConfig(self):
        backupConfig = None
        with open(self.configFile, 'r') as fh:
            backupConfig = json.load(fh)
        return backupConfig

class BackupConfigIterator(object):

    def __init__(self, configObj):
        self.configRecord = configObj.backupConfig
        self.rootElement = 'inputDirectoryList'
        self.backupConfigList = None
        self.itercnt = 0

    def __iter__(self):
        self.backupConfigList = self.configRecord[self.rootElement]
        self.itercnt = 0
        return self

    def __next__(self):
        if self.itercnt >= len(self.backupConfigList):
            raise StopIteration
        backupConfig = self.backupConfigList[self.itercnt]
        self.itercnt += 1
        return backupConfig

class BackupDateDirectoryIterator(object):
    def __init__(self, configObj):
        self.configRecord = configObj.backupConfig

    def enumerateDirs(self):
        """
        reads the config record and
        """
        getDirs = GetDirectoryList(self.configRecord)
        
    def __iter__(self):
        return self

    def __next__(self):
        pass
        

class GetDirectoryList(object):
    def __init__(self, configRecord):
        self.configRecord = configRecord
        self.rootDir = self.configRecord.keys().pop()

    




if __name__ == "__main__":
    BackupSnowData()
