import logging
import os
import sys

newPath = os.path.realpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, newPath)

LOGGER = logging.getLogger(__name__)

pytest_plugins = [
    "fixtures.granules_fixtures"
]
