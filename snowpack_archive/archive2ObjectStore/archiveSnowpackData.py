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
import VerifyETag

LOGGER = logging.getLogger(__name__)

# pylint: disable=anomalous-backslash-in-string
#


class ArchiveSnowData(object):
    """High level functionality for archiving snowpack data."""

    def __init__(self):
        LOGGER.debug("init object")
        omitDirs = self.getOmitDirs()
        self.dirIterator = DirectoryList(constants.SRC_ROOT_DIR,
                                         omitDirectoryList=omitDirs)

    def archiveDirs(self):
        objStore = ObjectStore()
        cnt = 0
        for currentDirectory in self.dirIterator:
            LOGGER.debug(f"currentdir: {currentDirectory}")
            if self.isReadyForArchive(currentDirectory,
                                      daysBack=constants.DAYS_BACK):
                LOGGER.debug(f"directory for archive: {currentDirectory}")
                objStore.copy(currentDirectory)
                self.deleteDir(currentDirectory)
                # used when testing to run on limited number of directories
                cnt += 1

    def deleteDir(self, inDir):
        """Deletes empty directoires.

        Tests to make sure the directory is empty, if it is it gets deleted.

        :param inDir: directory to delete
        :type inDir: str
        """
        contents = os.listdir(inDir)
        if not contents:
            LOGGER.info(f"removing the directory: {inDir}")
            os.rmdir(inDir)
        else:
            LOGGER.info(f"cannot remove the directory as its not empty: {inDir}")  # noqa: E501

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
        if (hasattr(constants, 'ROOTDIRECTORIES_OMIT')) and \
                constants.ROOTDIRECTORIES_OMIT:
            dirStringList = constants.ROOTDIRECTORIES_OMIT.split(',')
            LOGGER.debug(f"dirStringList: {dirStringList}")
            for omitDir in dirStringList:
                omitDirFullPath = os.path.join(constants.SRC_ROOT_DIR, omitDir)
                omitDirFullPath = os.path.normcase(
                    os.path.normpath(omitDirFullPath))
                if os.path.exists(omitDirFullPath):
                    omitDirList.append(omitDirFullPath)
                    LOGGER.info(f"adding {omitDirFullPath} to omit list")
                else:
                    LOGGER.warning(f"the omit directory: {omitDirFullPath} " +
                                   "could not be found")
        LOGGER.debug(f"omitDirList: {omitDirList}")
        return omitDirList

    def isReadyForArchive(self, inPath, daysBack=20):
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
        if daysBack > 0:
            daysBack = 0 - daysBack
        dateObj = self.getDirectoryDate(inPath)
        daysBack = datetime.timedelta(days=daysBack)
        currentDate = datetime.datetime.now()
        Threshold = currentDate + daysBack
        isOlderThanThreshold = False
        if dateObj < Threshold:
            # date of directory is older than 2 weeks
            isOlderThanThreshold = True
        return isOlderThanThreshold

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
                dateObj = datetime.datetime.strptime(dirPart, '%Y.%m.%d')
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
                    if not self.isDirInOmitList(fullpath) and \
                            self.inputDirRegex.match(iterdir):
                        dirs.append(fullpath)
                        LOGGER.debug('datedir being added to iterator: ' +
                                     f'{fullpath}')
                if dirs:
                    break
            self.dirList = dirs
            self.dirIndex = 0
            return dirs
        except StopIteration:
            self.dirWalkingComplete = True

    def getNextDirList_old(self):
        try:
            rootdir, tmpDirs, files = self.dirWalker.__next__()
            dirs = []
            for iterdir in tmpDirs:
                fullpath = os.path.join(rootdir, iterdir)
                if not self.isDirInOmitList(fullpath) and \
                        self.inputDirRegex.match(iterdir):
                    dirs.append(fullpath)
                    LOGGER.debug('datedir being added to iterator: ' +
                                 f'{fullpath}')
            if not dirs:
                dirs = self.getNextDirList()
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


class ObjectStore(object):
    '''
    methods to support easy copying of data from filesystem to object
    store.

    Gets the object store connection information from environment variables:
        * OBJ_STORE_HOST
        * OBJ_STORE_USER
        * OBJ_STORE_SECRET

    Gets the directory to copy to from:
        OBJ_STORE_ROOT_DIR

    Gets the source dir that needs to be copied from:
        SRC_ROOT_DIR

    So given the following hypothetical values:
       SRC_ROOT_DIR = C:\Lafleur\WinningNumbers
       OBJ_STORE_ROOT_DIR = lafleursData\Winnings

    the script will copy the contents of C:\Lafleur\WinningNumbers into the
    directory lafleursData\Winnings in the object store
    '''

    def __init__(self):
        """contructor, sets up object store client, and inits obj store obj.
        """
        self.minIoClient = minio.Minio(os.environ['OBJ_STORE_HOST'],
                                       os.environ['OBJ_STORE_USER'],
                                       os.environ['OBJ_STORE_SECRET'])

        self.objIndex = {}
        self.curDir = None
        self.copyDateDirCnt = 0

    def getObjStorePath(self, srcPath, prependBucket=True,
                        includeLeadingSlash=False):
        """ Gets the source file path, calculates the destination path for
        use when referring to the destination location using the minio api.

        :param srcPath: the source path referring to the file that is to be
            copied to object storage
        :type srcPath: str
        :param prependBucket: default is true, identifies if the name of the
            bucket should be the leading part of the destination path
        :type prependBucket: bool
        :param includeLeadingSlash: if the path should include a leading path
            delimiter character.  Example if true /guyLafleur/somedir
            would be the path, if set to false it would be guyLafleur/somedir
        :type includeLeadingSlash: bool
        """
        relativePath = self.removeSrcRootDir(srcPath)
        if prependBucket:
            objStoreAbsPath = os.path.join(
                constants.OBJ_STORE_BUCKET,
                constants.OBJ_STORE_ROOT_DIR,
                relativePath)
        else:
            objStoreAbsPath = os.path.join(
                constants.OBJ_STORE_ROOT_DIR,
                relativePath)
        if os.path.isdir(srcPath):
            if objStoreAbsPath[-1] != os.path.sep:
                objStoreAbsPath = objStoreAbsPath + os.path.sep
        if includeLeadingSlash:
            if objStoreAbsPath[0] != os.path.sep:
                objStoreAbsPath = os.path.sep + objStoreAbsPath
        # object storage always uses posix / unix path delimiters
        if sys.platform == 'win32':
            objStoreAbsPath = objStoreAbsPath.replace(os.path.sep,
                                                      posixpath.sep)
        LOGGER.debug(f"object store absolute path: {objStoreAbsPath}")
        return objStoreAbsPath

    def copy(self, srcDir):
        """Copies the contents of a source directory recursively to object
        storage.

        :param srcDir: name of the source directory to be copied
        :type srcDir: str
        """
        objStorePath = self.getObjStorePath(srcDir, prependBucket=False)
        LOGGER.debug(f'objStorePath: {objStorePath}')
        LOGGER.info(f'copying: {srcDir}...')
        self.copyDirectoryRecurive(srcDir)
        LOGGER.info(f"copied the path: {srcDir}, to object storage")
        # if self.copyDateDirCnt > 17:
        #     LOGGER.debug("stopping here")
        #     sys.exit()
        self.copyDateDirCnt += 1

    def removeSrcRootDir(self, inPath):
        """
        a utility method that will recieve a path, and remove a leading portion
        of that path.  For example if the input path was
        /habs/guy/lafleur/points

        and the source root directory defined in the environment variable
        SRC_ROOT_DIR was /habs/guy

        The output path would be lafleur/points

        :param inPath: the input path that is to have the root directory
            removed
        :type inPath: str
        :raises ValueError: raise if the the inPath is found to not be a
            subdirectory of the SRC_ROOT_DIR (env var)
        :return: modified src directory with the root potion removed
        :rtype: str
        """
        LOGGER.debug(f"inPath: {inPath}")
        rootPathObj = pathlib.PurePath(constants.SRC_ROOT_DIR)
        inPathObj = pathlib.PurePath(inPath)
        if rootPathObj not in inPathObj.parents:
            msg = f'expecting the root path {constants.SRC_ROOT_DIR} to ' + \
                  f'be part of the input path {inPath}'
            LOGGER.error(msg)
            raise ValueError(msg)

        newPath = os.path.join(*inPathObj.parts[len(rootPathObj.parts):])
        LOGGER.debug(f"newpath: {newPath}")
        return newPath

    def copyDirectoryRecurive(self, srcDir):
        """Recursive copy of directory contents to object store.

        Iterates over all the files and directoris in the 'srcDir' parameter,
        when the iteration finds a directory it calls itself with that
        directory

        If the iteration finds a file, it copies the file to object store then
        compares the object stores md5 with the md5 of the version on file, if
        they match then the src file is deleted.  If a mismatch is found then
        the ValueError is raised.

        :param srcDir: input directory that is to be copied
        :type srcDir: str
        :raises ValueError: if the file has been copied by the md5's do not
            align between source and destination this error will be raised.
        """
        part_size = 15728640
        for local_file in glob.glob(srcDir + '/**'):
            LOGGER.debug(f"local_file: {local_file}")
            objStorePath = self.getObjStorePath(local_file,
                                                prependBucket=False)
            LOGGER.debug(f"objStorePath: {objStorePath}")
            if not os.path.isfile(local_file):
                self.copyDirectoryRecurive(local_file)
            else:
                if not self.objExists(objStorePath):
                    LOGGER.debug(f"uploading: {local_file} to {objStorePath}")
                    copyObj = self.minIoClient.fput_object(
                        constants.OBJ_STORE_BUCKET,
                        objStorePath,
                        local_file,
                        part_size=part_size)
                    LOGGER.debug(f'copyObj: {copyObj}')
                    etagDest = copyObj[0]
                else:
                    etagDest = self.objIndex[objStorePath]
                md5Src = \
                    hashlib.md5(open(local_file, 'rb').read()).hexdigest()
                LOGGER.debug(f"etagDest: {etagDest}")
                if etagDest == md5Src:
                    # delete the source
                    LOGGER.info("md5's of source / dest match deleting the " +
                                f"src: {srcDir}")
                    os.remove(local_file)
                elif (len(etagDest.split('-')) == 2) and \
                        self.checkMultipartEtag(local_file, etagDest):
                    # etag format suggests the file was uploaded as a multipart
                    # which impacts how the etags are calculated
                    LOGGER.info("md5's of source / dest match as multipart " +
                                f"deleting the src: {srcDir}")
                    os.remove(local_file)
                else:
                    # if the md5 doesn't match either file isn't valid on the
                    # s3 side in which case we won't delete the source and we
                    # will throw and error in the log.
                    #    OR
                    # the etag doesn't match because the file was uploaded as a
                    # multipart object

                    msg = f'source: {local_file} and {objStorePath} both ' + \
                          'exists, but md5s don\'t align'
                    LOGGER.error(msg)

    def checkMultipartEtag(self, localFile, etagFromDest):
        """checks to see if the etag from S3 can be validated locally

        :param localFile: path to the local file
        :type localFile: str
        :param etagFromDest: the etag that was returned from s3
        :type etagFromDest: str
        :return: a boolean that tells us if the etag can be validated
        :rtype: bool
        """
        verifyEtag = VerifyETag.CalcETags()
        return verifyEtag.etagIsValid(localFile, etagFromDest)

    def objExists(self, inFile):
        """Identifies if the path 'inFile' exists in object storage

        :param inFile: path to who's existence in object storage is to be
            tested
        :type inFile: str
        :return: boolean indicating if the file exists or not
        :rtype: bool
        """
        objDoesExist = False
        self.refreshObjList(inFile)
        if inFile in self.objIndex:
            objDoesExist = True
        return objDoesExist

    def refreshObjList(self, inFile):
        """
        Going to be iterating of a lot of files, don't want to make api call
        for individual file, instead want to grab them in directory bundles as
        the script works on a directory by directory level.  Also don't want to
        keep all the directories in memory as each directory is processed at a
        time

        This method keeps track of what the current directory is, and when it
        changes it refreshes the contents of that direcotry.

        :param inFile: [description]
        :type inFile: [type]

        """
        inDir = os.path.dirname(inFile)
        if self.curDir != inDir:
            self.curDir = inDir
            LOGGER.debug("refreshing the directory contents cache")
            self.objIndex = {}
            objects = self.minIoClient.list_objects(
                os.environ['OBJ_STORE_BUCKET'], recursive=True, prefix=inDir)
            for obj in objects:
                LOGGER.debug(f"{obj.object_name}")
                objName = obj.object_name
                self.objIndex[objName] = obj.etag
