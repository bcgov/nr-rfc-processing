import logging
from time import sleep

RETRY_NAP_DURATION = 60  # seconds
RETRY_NAP_DURATION_STR = "1 min"

RETRY_SLEEP_DURATION = 600  # seconds
RETRY_SLEEP_DURATION_STR = "10 min"

RETRY_HIBERNATE_DURATION = 3600  # seconds
RETRY_HIBERNATE_DURATION_STR = "1 hr"

# logging
logger = logging.getLogger()


def retry_func(func, retry_count: int = 0):
    try:
        return func()
    except Exception as e:
        logger.warn(f'exception in retry function, try {retry_count} {e}')
        if retry_count <= 0:
            dormir(retry_count, RETRY_NAP_DURATION, RETRY_NAP_DURATION_STR)
            return retry_func(func, retry_count=retry_count + 1)        
        elif retry_count == 1:
            dormir(retry_count, RETRY_SLEEP_DURATION, RETRY_SLEEP_DURATION_STR)
            return retry_func(func, retry_count=retry_count + 1)
        # elif retry_count == 2:
        #     dormir(retry_count, RETRY_HIBERNATE_DURATION,
        #            RETRY_HIBERNATE_DURATION_STR)
        #     return retry_func(func, retry_count=retry_count + 1)
        else:
            raise e


def dormir(count, duration_sec, text):
    logger.info(f"try {count}, sleep for {text}")
    sleep(duration_sec)