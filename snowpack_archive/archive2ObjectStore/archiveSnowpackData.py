"""

Archives snowpack data to object store that exceeds a specified time period.

Script iterates through data defined on the path $SRC_ROOT_DIR.  Looks for
directories that match the expression defined in the
constant.DIRECTORY_DATE_REGEX (example of default pattern: 2021.05.15).  If the
date folder is older than constants.DAYS_BACK.  The archive process first
uploads the file to boject

Environment Variables Used by Script:
* ROOT_DIR = the root directory for the snowpack data
* BACKUP_ROOT = the directory where snowpack data should get backed up

Constants used:
* DAYS_BACK - How many days old a directories name describes when compared with
              the current date, to determine if it should be archived or not
* ROOTDIRECTORIES_OMIT - a list of sub directories off of the root directory
              that should be ignored from the archive process

"""

import datetime
import glob
import hashlib
import logging
import os
import pathlib
import posixpath
import re
import sys

import minio
import scandir

from archive2ObjectStore import constants as constants
import NRUtil.NRObjStoreUtil

LOGGER = logging.getLogger(__name__)

# pylint: disable=anomalous-backslash-in-string


class ArchiveSnowData(object):
    """High level functionality for archiving snowpack data."""

    def __init__(self, backup_threshold: int = None, delete: bool = True):
        """_summary_

        :param backup_threshold: This parameter determines how old a directory
            needs to be in order to trigger a backup of the data to object
            storage.  The default value is set in the constants.py file in the
            property DAYS_BACK.  This property allows that property to be
            overridden, defaults to None
        :type backup_threshold: int, optional
        :param delete: identifies if the original data should be deleted after
            it has been copied to object storage, if this arg is not supplied
            it is assumed that it is True, ie the data SHOULD be deleted
        :type delete: bool, optional
        """
        LOGGER.debug("init object")
        if backup_threshold is not None:
            constants.DAYS_BACK = backup_threshold
        self.delete = delete
        omitDirs = self.getOmitDirs()
        self.dirIterator = DirectoryList(
            constants.SRC_ROOT_DIR, omitDirectoryList=omitDirs
        )

    def is_dir_candidate_backup(self, in_dir):
        """identifies if the directory should be backed up or not.  Looks at the exclusion
        list identified in the constants directory, and if the directory is in that list
        then it should be skipped, and thus the method will return false.

        :param in_dir: input directory to be tested
        :type in_dir: _type_
        """
        should_backup = True
        omit_dir_list = constants.ROOTDIRECTORIES_OMIT.split(',')
        indir_norm = os.path.normpath(in_dir)
        # does the in_dir start the same way that in_dir does?
        for omit_dir in omit_dir_list:
            omit_dir_norm = os.path.normpath(omit_dir)
            if indir_norm.startswith(omit_dir_norm):
                should_backup = False
                break
        return should_backup



    def archiveDirs(self):
        """initiates the actual backup of the directories defined in
        constants.SRC_ROOT_DIR, where any exception are defined in
        the environment variable ROOTDIRECTORIES_OMIT
        """
        # sync = NRUtil.NRObjStoreUtil.ObjectStoreDirectorySync()
        pathUtil = NRUtil.NRObjStoreUtil.ObjectStoragePathLib()
        for currentDirectory in self.dirIterator:
            LOGGER.debug(f"currentdir: {currentDirectory}")
            # does the directory date match the date restrictions
            if ( self.isReadyForArchive(currentDirectory, days_back_int=constants.DAYS_BACK) and
                self.is_dir_candidate_backup(currentDirectory)):
            # does the directory date match the date restrictions:
                LOGGER.debug(f"directory for archive: {currentDirectory}")
                dest_path = pathUtil.get_obj_store_path(
                    src_path=currentDirectory,
                    ostore_path=constants.OBJ_STORE_ROOT_DIR,
                    src_root_dir=constants.SRC_ROOT_DIR,
                    prepend_bucket=False,
                )
                LOGGER.info(
                    f"syncing: {currentDirectory} to the ostore dir: {dest_path}"
                )
                sync = NRUtil.NRObjStoreUtil.ObjectStoreDirectorySync(
                    src_dir=currentDirectory, dest_dir=dest_path
                )
                sync.update_ostore_dir(public=True)
                if self.delete:
                    #LOGGER.info(f"removing the original directory: {currentDirectory}")
                    #self.deleteDir(currentDirectory)
                    pass


    def deleteDir(self, inDir):
        """Deletes empty directoires.

        Tests to make sure the directory is empty, if it is it gets deleted.

        :param inDir: directory to delete
        :type inDir: str
        """
        contents = os.listdir(inDir)

        if not contents:
            LOGGER.info(f"removing the directory: {inDir} ... disabled!")
            #os.rmdir(inDir)
        else:
            LOGGER.info(
                f"cannot remove the directory as its not empty: {inDir}"
            )  # noqa: E501

    def getOmitDirs(self):
        """Retrieves the list of directories to omit.

        Determines if a constants ROOTDIRECTORIES_OMIT parameter has been
        defined.  If it has, then looks at the directories defined there, makes
        sure that they exist, if they do the full paths for those directories
        are added to a list and returned

        :return: full paths to any directories that should be ommitted
        :rtype: list
        """
        omitDirList = []
        if (
            hasattr(constants, "ROOTDIRECTORIES_OMIT")
        ) and constants.ROOTDIRECTORIES_OMIT:
            dirStringList = constants.ROOTDIRECTORIES_OMIT.split(",")
            LOGGER.debug(f"dirStringList: {dirStringList}")
            for omitDir in dirStringList:
                omitDirFullPath = os.path.join(constants.SRC_ROOT_DIR, omitDir)
                omitDirFullPath = os.path.normcase(os.path.normpath(omitDirFullPath))
                if os.path.exists(omitDirFullPath):
                    omitDirList.append(omitDirFullPath)
                    LOGGER.info(f"adding {omitDirFullPath} to omit list")
                else:
                    LOGGER.warning(
                        f"the omit directory: {omitDirFullPath} " + "could not be found"
                    )
        LOGGER.debug(f"omitDirList: {omitDirList}")
        return omitDirList

    def isReadyForArchive(self, inPath: str, days_back_int: int = 20):
        """Should the input directory be archived.

        River forecast snowpack data has directories with the string
        YYYY.MM.DD to identify what dates the data is for.  This method will
        recieve a path, extract the date portion of the path, convert it into
        a date object and return true if the date is older than the defined
        number of days in the constant DAYS_BACK.

        Note: longer term, thinking that this could be moved to the directory
              iterator.  Iterator could get passed a method definition that
              gets executed per directory?  mixin kind of pattern idea

        :param inPath: input path string
        :type inPath: str
        :return: does the date string found in the directory path exceed the
            date threhold (default is 15 days)
        :rtype: boolean
        """
        if days_back_int > 0:
            days_back_int = 0 - days_back_int
        # expecting a directory with a directory date string in its path,
        # extracts the first date string found and returns a datetime object
        current_directory_date = self.getDirectoryDate(inPath)
        daysBack = datetime.timedelta(days=days_back_int)
        currentDate = datetime.datetime.now()
        Threshold = currentDate + daysBack
        isOlderThanThreshold = False
        if current_directory_date < Threshold:
            # date of directory is older than the threshold for backing up.
            isOlderThanThreshold = True
        # swap the boolean as if the file / directory is older than the threshold then
        # it should not be backed up.
        return not isOlderThanThreshold

    def getDirectoryDate(self, inPath):
        """Get directory as a date.

        Gets a path, Iterates through it starting at the end
        of the tree and working back towards the root for a directory
        name that matches the

        :param inPath: input relative path
        :type inPath: str
        :return: datetime object calculated from the direcotory path
        :rtype: datetime
        """
        dateRegex = re.compile(constants.DIRECTORY_DATE_REGEX)
        pathObj = pathlib.PurePath(inPath)
        LOGGER.debug(f"pathObj : {len(pathObj.parts)}, {pathObj.parts}")
        # iterate from end to start
        iterCnt = len(pathObj.parts) - 1
        dateObj = None
        while iterCnt > 0:
            dirPart = pathObj.parts[iterCnt]
            if dateRegex.match(dirPart):
                LOGGER.debug(f"date part of directory: {dirPart}")
                dateObj = datetime.datetime.strptime(dirPart, "%Y.%m.%d")
                break
            iterCnt -= 1
        return dateObj


class DirectoryList(object):
    """Iterator class for directories.

    Provides an iterable, with each iteration gets the path to a new directory
    that needs to be backed up
    """

    def __init__(self, srcRootDir, inputDirRegex=None, omitDirectoryList=[]):
        self.srcRootDir = srcRootDir
        self.omitDirectoryList = omitDirectoryList
        if not inputDirRegex:
            self.inputDirRegex = re.compile(constants.DIRECTORY_DATE_REGEX)
        self.dirList = []
        self.dirIndex = 0
        self.dirWalker = None
        self.dirWalkingComplete = False

    def __iter__(self):
        self.dirWalker = scandir.walk(self.srcRootDir)
        return self

    def __next__(self):
        if self.dirIndex >= len(self.dirList):
            self.getNextDirList()
            if self.dirWalkingComplete:
                raise StopIteration
        dir2Return = self.dirList[self.dirIndex]
        self.dirIndex += 1
        return dir2Return

    def getNextDirList(self):
        r"""Gets a directory list.

        recursion approach reached maximum stack size, couldn't get
        past:
        Z:\snowpack_data\basins\HORSESHOE_RIVER_ABOVE_LOIS_LAKE\viirs\2021.05.31  # noqa: E501

        so restructing how to populate directories to be iterated
        """
        try:
            while True:
                rootdir, tmpDirs, files = self.dirWalker.__next__()
                dirs = []
                for iterdir in tmpDirs:
                    fullpath = os.path.join(rootdir, iterdir)
                    if not self.isDirInOmitList(fullpath) and self.inputDirRegex.match(
                        iterdir
                    ):
                        dirs.append(fullpath)
                        LOGGER.debug(
                            "datedir being added to iterator: " + f"{fullpath}"
                        )
                if dirs:
                    break
            self.dirList = dirs
            self.dirIndex = 0
            return dirs
        except StopIteration:
            self.dirWalkingComplete = True

    def isDirInOmitList(self, inDir):
        """Should input directory be omitted.

        Checks to see if the input directory is a subdirectory
        of the omit list

        :param inDir: [description]
        :type inDir: [type]
        """
        isInOmitList = False
        if self.omitDirectoryList:
            for omitDir in self.omitDirectoryList:
                if self.isSubDir(inDir, omitDir):
                    isInOmitList = True
                    break
        return isInOmitList

    def isSubDir(self, pth1, pth2):
        """Is a subdirectory.

        Gets two paths, and return true if either of them are subpaths
        of the other.

        :param pth1: [description]
        :type pth1: [type]
        :param pth2: [description]
        :type pth2: [type]
        :return: [description]
        :rtype: [type]
        """
        areEqual = True
        pth1Corrected = os.path.normcase(os.path.normpath(pth1))
        pth2Corrected = os.path.normcase(os.path.normpath(pth2))

        pth1List = list(pathlib.PurePath(pth1Corrected).parts)
        pth2List = list(pathlib.PurePath(pth2Corrected).parts)
        if pth1List != pth2List:
            for x, y in zip(pth1List, pth2List):
                if x != y:
                    areEqual = False
        return areEqual
