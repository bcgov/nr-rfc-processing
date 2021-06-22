import archive2ObjectStore.archiveSnowpackData
import logging

import sys

# add a simple console logger
LOGGER = logging.getLogger()
LOGGER.setLevel(logging.DEBUG)
hndlr = logging.StreamHandler()
fmtStr = '%(asctime)s - %(name)s - %(levelname)s - %(lineno)d - %(message)s'
formatter = logging.Formatter(fmtStr)
hndlr.setFormatter(formatter)
LOGGER.addHandler(hndlr)
LOGGER.debug("test")

# boosting the recursion limit
targetRecursionLimit = 15000
recursionLimit = sys.getrecursionlimit()
if recursionLimit < targetRecursionLimit:
    sys.setrecursionlimit(targetRecursionLimit)
    LOGGER.info(f"boosting the recursion limit to {targetRecursionLimit}")


archive = archive2ObjectStore.archiveSnowpackData.ArchiveSnowData()
archive.archiveDirs()
