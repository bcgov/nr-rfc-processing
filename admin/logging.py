import logging
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s {%(module)s:%(lineno)d} : %(message)s')

def setup_logger(name, log_file, level=logging.INFO):
    """To setup as many loggers as you want"""

    handler = logging.FileHandler(log_file)
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    return logger

def setup_stream_logger(name, level=logging.DEBUG):
    """To setup as many loggers as you want"""

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    # configure the root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)

    # hatfield module log level
    hatfieldLogLevel = logging.DEBUG
    logger = logging.getLogger('admin.buildkml')
    logger.setLevel(hatfieldLogLevel)

    logger = logging.getLogger('admin.buildup')
    logger.setLevel(hatfieldLogLevel)

    logger = logging.getLogger('admin.check_date')
    logger.setLevel(hatfieldLogLevel)

    logger = logging.getLogger('admin.db_handler')
    logger.setLevel(hatfieldLogLevel)

    logger = logging.getLogger('admin.plotter')
    logger.setLevel(hatfieldLogLevel)

    logger = logging.getLogger('admin.teardown')
    logger.setLevel(hatfieldLogLevel)

    logger = logging.getLogger('analysis.analysis')
    logger.setLevel(hatfieldLogLevel)

    logger = logging.getLogger('analysis.support')
    logger.setLevel(hatfieldLogLevel)

    logger = logging.getLogger('download_granules.download_granules')
    logger.setLevel(hatfieldLogLevel)

    logger = logging.getLogger('download_granules.download')
    logger.setLevel(hatfieldLogLevel)

    logger = logging.getLogger('download_granules.run_download')
    logger.setLevel(hatfieldLogLevel)

    logger = logging.getLogger('process.modis')
    logger.setLevel(hatfieldLogLevel)

    logger = logging.getLogger('process.sentinel2')
    logger.setLevel(hatfieldLogLevel)

    logger = logging.getLogger('process.support')
    logger.setLevel(hatfieldLogLevel)

    logger = logging.getLogger('process.viirs')
    logger.setLevel(hatfieldLogLevel)

    logger = logging.getLogger('caluculate_norm')
    logger.setLevel(hatfieldLogLevel)

    logger = logging.getLogger('caluculate_norm')
    logger.setLevel(hatfieldLogLevel)

    logger = logging.getLogger('__main__')
    logger.setLevel(hatfieldLogLevel)

    return logger