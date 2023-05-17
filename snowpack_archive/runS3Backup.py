import archive2ObjectStore.archiveSnowpackData
import logging
import logging.config
import archive2ObjectStore.constants
import os
import sys
import click


# add a simple console logger
LOGGER = logging.getLogger()


def setup_logging():
    log_config_path = os.path.join(os.path.dirname(__file__), 'logging.config')
    logging.config.fileConfig(log_config_path)
    global LOGGER
    LOGGER = logging.getLogger(__name__)

def boost_recursion_limit():
    # boosting the recursion limit
    targetRecursionLimit = 15000
    recursionLimit = sys.getrecursionlimit()
    if recursionLimit < targetRecursionLimit:
        sys.setrecursionlimit(targetRecursionLimit)
        LOGGER.info(f"boosting the recursion limit to {targetRecursionLimit}")


@click.command()
@click.option(
    "--days_back",
    default=archive2ObjectStore.constants.DAYS_BACK,
    type=int,
    help="Number of days old a dataset should be to trigger an archive.",
)
@click.option(
    "--delete", default=False, type=bool, help="Whether to delete the original data"
)
def run_archive(days_back, delete=False):
    """Simple program that greets NAME for a total of COUNT times."""
    # days_back=archive2ObjectStore.constants.DAYS_BACK, delete=False
    LOGGER.info(f"days back for archive date threshold: {days_back}")
    LOGGER.debug(f"delete orginal data: {delete}")
    archive = archive2ObjectStore.archiveSnowpackData.ArchiveSnowData(
        backup_threshold=days_back, delete=delete
    )
    archive.archiveDirs()


if __name__ == "__main__":
    setup_logging()
    boost_recursion_limit()
    run_archive()
