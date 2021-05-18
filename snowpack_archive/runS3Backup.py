import archive2ObjectStore.archiveSnowpackData
import logging

# add a simple console logger
LOGGER = logging.getLogger()
LOGGER.setLevel(logging.DEBUG)
hndlr = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(lineno)d - %(message)s')
hndlr.setFormatter(formatter)
LOGGER.addHandler(hndlr)
LOGGER.debug("test")

archive = archive2ObjectStore.archiveSnowpackData.ArchiveSnowData()
archive.archiveDirs()
