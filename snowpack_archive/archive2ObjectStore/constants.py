""" Declaring constants used by the archive script. """

import os
import dotenv

envPath = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(envPath):
    print("loading dot env...")
    dotenv.load_dotenv()

#
SRC_ROOT_DIR = os.getenv('SRC_ROOT_DIR', 'data')
OBJ_STORE_ROOT_DIR = os.getenv('OBJ_STORE_ROOT_DIR', 'snowpack_archive')

# get required environments:
required_envs = ['OBJ_STORE_BUCKET', 'OBJ_STORE_SECRET', 'OBJ_STORE_USER', 'OBJ_STORE_HOST']
for req_env_name in required_envs:
    env = os.getenv(req_env_name)
    if not env:
        msg = (
                'These are the environment varialbes that must be set in ' +
                'order for the script to function: ' +
                f'{", ".join(required_envs)} Cannot find the env var: ' +
                f"{req_env_name}"
            )
        raise ValueError(msg)

OBJ_STORE_BUCKET = os.environ['OBJ_STORE_BUCKET']
OBJ_STORE_SECRET = os.environ['OBJ_STORE_SECRET']
OBJ_STORE_USER = os.environ['OBJ_STORE_USER']
OBJ_STORE_HOST = os.environ['OBJ_STORE_HOST']

# used to identify directories that contain dates in them
DIRECTORY_DATE_REGEX = '^[0-9]{4}\.{1}[0-9]{2}\.{1}[0-9]{2}$'  # noqa: W605

#  identifies the root directories (sub dirs in SRC_ROOT_DIR) that should
#  be ommitted (a comma delimited list) for example:
#  ROOTDIRECTORIES_OMIT=dir1,dir2\\someotherdir,dir3
ROOTDIRECTORIES_OMIT = os.getenv('ROOTDIRECTORIES_OMIT', '')

# if a direcotory's naming (YYYY.mm-dd) is older
# than this number of days it will be archived
DAYS_BACK = 20
