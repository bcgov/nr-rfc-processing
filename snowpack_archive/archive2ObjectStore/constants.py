import os
import dotenv

envPath = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(envPath):
    print("loading dot env...")
    dotenv.load_dotenv()

SRC_ROOT_DIR = os.environ['SRC_ROOT_DIR']
OBJ_STORE_ROOT_DIR = os.environ['OBJ_STORE_ROOT_DIR']
OBJ_STORE_BUCKET = os.environ['OBJ_STORE_BUCKET']
OBJ_STORE_SECRET = os.environ['OBJ_STORE_SECRET']
OBJ_STORE_USER = os.environ['OBJ_STORE_USER']
OBJ_STORE_HOST = os.environ['OBJ_STORE_HOST']

# used to identify directories that contain dates in them
DIRECTORY_DATE_REGEX = '^[0-9]{4}\.{1}[0-9]{2}\.{1}[0-9]{2}$'  # noqa: W605

#  identifies the root directories (sub dirs in SRC_ROOT_DIR) that should
#  be ommitted (a comma delimited list) for example:
#  ROOTDIRECTORIES_OMIT=dir1,dir2\\someotherdir,dir3
ROOTDIRECTORIES_OMIT = os.environ['ROOTDIRECTORIES_OMIT']
