import archive2ObjectStore.archiveSnowpackData
import logging
import archive2ObjectStore.constants

import sys
import click

# add a simple console logger
LOGGER = logging.getLogger()

def setup_logging():
    LOGGER.setLevel(logging.DEBUG)
    hndlr = logging.StreamHandler()
    fmtStr = '%(asctime)s - %(name)s - %(levelname)s - %(lineno)d - %(message)s'
    formatter = logging.Formatter(fmtStr)
    hndlr.setFormatter(formatter)
    LOGGER.addHandler(hndlr)
    LOGGER.debug("test")

def boost_recursion_limit():
    # boosting the recursion limit
    targetRecursionLimit = 15000
    recursionLimit = sys.getrecursionlimit()
    if recursionLimit < targetRecursionLimit:
        sys.setrecursionlimit(targetRecursionLimit)
        LOGGER.info(f"boosting the recursion limit to {targetRecursionLimit}")


@click.command()
@click.option('--days_back', default=None, type=int, help='Number of days old a dataset should be to trigger an archive.')
@click.option('--delete', default=True, type=bool, help='Whether to delete the original data')
def run_archive(days_back, delete):
    """Simple program that greets NAME for a total of COUNT times."""

    LOGGER.debug(f"days back: {days_back}")
    LOGGER.debug(f"delete orginal data: {delete}")
    archive = archive2ObjectStore.archiveSnowpackData.ArchiveSnowData(
        backup_threshold=days_back,
        delete=delete)
    archive.archiveDirs()


if __name__ == '__main__':
    setup_logging()
    boost_recursion_limit()
    run_archive()


# days_back = None
# if len(sys.argv) > 1:
#     days_back = sys.argv[1]
#     if not days_back.isnumeric():
#         msg = (
#             'the days back identifies the threshold number of day back a ' +
#             'directory needs to be to be archived to object storage.  Arg ' +
#             f'that was sent: {days_back}'
#         )
#         raise ValueError(msg)
#     days_back = int(days_back)

