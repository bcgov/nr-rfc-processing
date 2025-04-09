"""
Logic to allow:

a) get list of granules
b) for each granule - if exists in ostore get from there
                      otherwise get from source and then upload

All file retrievals should be async

Retrieves secrets from constants, do not use yaml file

"""

import datetime
import json
import logging
import os
import re
import multiprocessing

import cmr

import dateutil.parser
import requests

import admin.constants as const

import NRUtil.NRObjStoreUtil

LOGGER = logging.getLogger(__name__)

class GranuleDownloader:
    def __init__(self, sat_config):
        self.sat_config = sat_config

    def download_granules(self):
        # TODO: once complete and tested this will be renamed to download_granules

        """ """
        #end_date = datetime.datetime(int(date[0]), int(date[1]), int(date[2]))
        #start_date = end_date - datetime.timedelta(self.sat_config.date_span)

        #end_date = self.sat_config.get_end_date()
        #start_date = self.sat_config.get_start_date()
        ed_client = CMRClientOStore(
            earthdata_user=const.EARTHDATA_USER,
            earthdata_pass=const.EARTHDATA_PASS,
        )

        granules = ed_client.query(
            #str(start_date.date()),
            #str(end_date.date()),
            self.sat_config,
            bbox=[*const.BBOX],
        )
        msg = (
            f"queried product {self.sat_config.product}, got {len(granules)} "
            + "granules, downloading"
        )
        LOGGER.info(msg)

        # TODO: debug - runs sync vs async to help debug
        for gran in granules:
            ed_client.download_granule(gran)
        # LOGGER.debug("all granules downloaded...")

        # Adding the object storage upload renders the download_granule unpickleable
        # The operation doesn't have any serious cpu processing, but is mostly i/o,
        # converting to ThreadPool should provide the similar benefits
        # try:
        #     # with multiprocessing.Pool(4) as p:
        #     with multiprocessing.pool.ThreadPool(6) as p:
        #         p.map(ed_client.download_granule, granules)
        # except KeyboardInterrupt:
        #     LOGGER.error('keyboard interupt... Exiting download pool')

class CMRClient:
    def __init__(self, earthdata_user="", earthdata_pass=""):
        self.earthdata_user = earthdata_user or os.getenv("EARTHDATA_USER")
        self.earthdata_pass = earthdata_pass or os.getenv("EARTHDATA_PASS")
        # methods that need a session will built it for themselves
        self.session = None

        self.chunk_size = 256 * 1024
        self.max_retries = 5

    def query(
        self,
        dl_config,
        bbox: list = [],
    ) -> list[dict]:
        # TODO: add type for dl_config
        """
        Search CMR database for spectral MODIS tiles matching a temporal range,
        defined by a start date and end date. Returns metadata containing the URL of
        each image.

        Parameters
        ----------
        start_date: string
            Start date yyyy-mm-dd
        end_date: string
            End date yyyy-mm-dd
        product: download_granules.download_config.SatDownloadConfig
            Product name
        bbox: List[float]
            Bounding box [lower_left_lon,
                          lower_left_lat,
                          upper_right_lon,
                          upper_right_lat]

        Returns
        ----------
        List[Dict]
            List of granules

        """
        LOGGER.info("querying for granules...")
        q = cmr.GranuleQuery()

        end_date = dl_config.get_end_date()
        end_date_str = end_date.strftime('%Y-%m-%d')
        start_date = dl_config.get_start_date()
        start_date_str = start_date.strftime('%Y-%m-%d')

        prod, ver = dl_config.get_product_version()
        q.short_name(prod).version(ver)
        q.temporal(f"{start_date_str}T00:00:00Z", f"{end_date_str}T23:59:59Z")
        if len(bbox) >= 4:
            q.bounding_box(*bbox[:4])
        _granules = q.get_all()

        # filter dates
        if dl_config.day_offset:
            day_offset = dl_config.day_offset
        else:
            day_offset = 0
        granules = []
        for gran in _granules:
            # CMR uses day 1 of window - correct this to be middle of window
            d1 = dateutil.parser.parse(gran["time_start"].split("T")[0])
            d2 = d1 + datetime.timedelta(days=day_offset)
            date = (
                dateutil.parser.parse(gran["time_start"].split("T")[0])
                + datetime.timedelta(days=day_offset)
            ).date()

            # if (
            #     dateutil.parser.parse(start_date_str).date()
            #     <= date
            #     <= dateutil.parser.parse(end_date_str).date()
            # ):
            start_date_date = start_date.date()
            end_date_date = end_date.date()

            if ( start_date_date <= date and date <= end_date_date):
                granules.append(gran)
            else:
                LOGGER.debug(f"date that fails: {date}")
        LOGGER.info(
            "%s granules found within %s - %s" % (len(granules), start_date, end_date_str)
        )
        return granules

    def save_metadata(self, granule, output_file):
        if not os.path.exists(output_file):
            LOGGER.debug(f"output_file: {output_file}")
            # './data/MOD10A1.61/MOD10A1.061/2023.03.17/MOD10A1.A2023076.h11v03.061.2023078031324.hdf_meta.json'
            with open(output_file, "w") as fh:
                json.dump(granule, fh, sort_keys=True, indent=4, ensure_ascii=False)

        # now persist to object storage

    def get_file(self, granule_url, output_file, retries=0):
        if not os.path.exists(output_file):
            self.get_file_from_earth_data(granule_url, output_file, retries=retries)

    def get_file_from_earth_data(self, granule_url, output_file, retries=0):
        try:
            self.check_session()
            r1 = self.session.request("get", granule_url)
            # TODO: add a try except to this entire flow

            # TODO: make sure this is using the auth credentials defined in the session
            stream = self.session.get(
                r1.url,
                auth=(self.earthdata_user, self.earthdata_pass),
                allow_redirects=True,
                stream=True,
            )
            LOGGER.debug(f"status_code: {stream.status_code}")
            if stream.status_code == 302:
                retries += 1
                LOGGER.warning(
                    f"{stream.status_code} retries: {retries} get: {granule_url}"
                )
                self.get_file_from_earth_data(granule_url, output_file, retries)
            else:
                # write straight to output file
                with open(output_file, "wb") as f:
                    for chunk in stream.iter_content(chunk_size=self.chunk_size):
                        # If you have chunk encoded response uncomment if
                        # and set chunk_size parameter to None.
                        # if chunk:
                        f.write(chunk)
        except requests.exceptions.ConnectionError as e:
            if retries > self.max_retries:
                LOGGER.exception(
                    f"maximum number of retries: {self.max_retries} exceeded"
                )
                raise
            else:
                LOGGER.warning(
                    f"connection error raised, trying again... (retries: {retries})"
                )
                retries += 1
                self.get_file_from_earth_data(granule_url, output_file, retries=retries)

    def check_session(self):
        """makes sure a session object exists"""
        if self.session is None:
            self.session = requests.Session()
            self.session.auth = (self.earthdata_user, self.earthdata_pass)

    # TODO: define a typed dict for granule type
    def download_granule(self, granule):
        # helper for output path names
        gran_util = GranuleUtil(granule)

        # check output directory exists
        gran_dir = gran_util.get_local_path()
        if not os.path.exists(gran_dir):
            LOGGER.info(f"creating output directory: {gran_dir}")
            os.makedirs(gran_dir)

        # save metadata
        granule_metadata_local_file_name = gran_util.get_granule_meta_file_name()
        LOGGER.info(f"saving granule metadata: {granule_metadata_local_file_name}")
        self.save_metadata(granule, granule_metadata_local_file_name)

        # get the hdf file
        hdf_url = gran_util.get_hdf_url()
        hdf_local_file_name = gran_util.get_hdf_local_file_name(full_path=True)
        LOGGER.info(f"saving the hdf file: {hdf_local_file_name}")
        self.get_file(hdf_url, hdf_local_file_name)

        # get the xml metadata
        xml_url = gran_util.get_xml_url()
        if xml_url:
            xml_local_file_name = gran_util.get_xml_local_file_name(full_path=True)
            LOGGER.debug(f"saving xml metadata {xml_local_file_name}")
            self.get_file(xml_url, xml_local_file_name)

        # get the browse image
        browseimage_url = gran_util.get_browseimage_url()
        if browseimage_url:
            browseimage_local_file_name = gran_util.get_browseimage_local_file_name(
                full_path=True
            )
            LOGGER.debug(f"saving browse image {browseimage_local_file_name}")
            self.get_file(browseimage_url, browseimage_local_file_name)


class DirCache:
    """simple utility created to cache the directory queries that have already
    been made to object storage so they don't get made a second time.

    """

    def __init__(self):
        self.cache_dict = {}

    def exists(self, path, struct=None):
        """returns true if the path exists in the data structure.  The data structure
        stores paths like:

        struct[directory name] = [list of files in directory]

        assumption is made that the input path is the path to a file

        :param path: the input path
        :type path: str(path)
        :return: boolean that indicates if the directory exists or not
        :rtype: bool
        """
        path_exists = False
        path_dir, path_file = os.path.split(path)
        if (path_dir in self.cache_dict) and path_file in self.cache_dict[path_dir]:
            path_exists = True
        return path_exists

    def set_path(self, path):
        path_dir, path_file = os.path.split(path)
        if path_dir not in self.cache_dict:
            self.cache_dict[path_dir] = []
        if path_file not in self.cache_dict[path_dir]:
            self.cache_dict[path_dir].append(path_file)

    def set_paths(self, path_list):
        for path in path_list:
            self.set_path(path)

    def add_dir(self, directory_path):
        """used to keep track of directories that have been checked but don't
        contain any file"""
        if directory_path not in self.cache_dict:
            self.cache_dict[directory_path] = []


class CMRClientOStore(CMRClient):
    """extends the basic CMRClient functionality.

    Purpose is to get the data from object storage it it exists there vs from the
    official sources.

    :param CMRClient: _description_
    :type CMRClient: _type_
    """

    def __init__(self, earthdata_user, earthdata_pass):
        CMRClient.__init__(self, earthdata_user="", earthdata_pass="")
        self.ostore = NRUtil.NRObjStoreUtil.ObjectStoreUtil()
        self.ostore_cache = DirCache()

    def get_ostore_file_list(self, ostore_directory):
        # get the data in the directory in the object storage bucket
        file_list = self.ostore.list_objects(
            objstore_dir=ostore_directory, return_file_names_only=True
        )
        if file_list:
            # add the files to the cache to reduce the number or queries that need to
            # be made to object storage
            self.ostore_cache.set_paths(file_list)

        # add the directory that was checked.  won't do anything if the previous step
        # already added it.
        self.ostore_cache.add_dir(ostore_directory)
        return file_list

    def exists_ostore(self, ostore_file_path):
        # ostore_path = self.get_ostore_path(local_path)
        path_exists = False
        if self.ostore_cache.exists(ostore_file_path):
            # the path is in the cache, and therefor the path exists and has already
            # been queried
            path_exists = True
        else:
            # the path is not in the cache so we will add it to the cache and then
            # query again.
            LOGGER.debug(f"polling ostore for existance of {ostore_file_path}")
            ostore_dir, ostore_file = os.path.split(ostore_file_path)
            ostore_file_list = self.get_ostore_file_list(ostore_directory=ostore_dir)

            ostore_objs = self.ostore.list_objects(
                objstore_dir=ostore_dir, return_file_names_only=True
            )
            LOGGER.debug(f"ostore_objs: {ostore_objs}")
            path_exists = self.ostore_cache.exists(ostore_file_path)
        return path_exists

    def get_ostore_path(self, local_path):
        """
        input is a local_path, returns the equivalent path for the same data in
        object storage.
        """
        # take a path like './data/modis-terra/MOD10A1.061/2023.03.17/MOD10A1.A2023076.h11v03.061.2023078031324.hdf'
        # and convert to snowpack_archive/modis-terra/MOD10A1.061/2023.03.17/MOD10A1.A2023076.h11v03.061.2023078031324.hdf
        # local_dir = self.get_local_path()
        local_dir, local_file = os.path.split(local_path)
        remove_local_dir = NRUtil.NRObjStoreUtil.ObjectStoragePathLib()
        # same path but strip off the TOP part, in example would be:
        # modis-terra/MOD10A1.061/2023.03.17/MOD10A1.A2023076.h11v03.061.2023078031324.hdf # noqa
        no_local = remove_local_dir.remove_sr_root_dir(local_dir, const.TOP)
        ostore_dir = os.path.join(const.OBJ_STORE_TOP, no_local, local_file)
        return ostore_dir

    def get_from_ostore(self, ostore_file, local_file):
        """retrieve the file from object storage that is described by the path
        `ostore_file` to the local path describe by `local_file`

        :param ostore_file: the path to the file in object storage
        :type ostore_file: str(path)
        :param local_file: the local path that the object storage path will be downloaded
            to.
        :type local_file: str(path)
        """
        self.ostore.get_object(file_path=ostore_file, local_path=local_file)

    def get_file(self, granule_url, output_file, retries=0):
        # intercept the method call and determine if the files are in object storage, and
        # if they are pull them down, if now then call the super class.

        ostore_path = self.get_ostore_path(output_file)
        ostore_exists = self.exists_ostore(ostore_path)

        # exists, doesn't exist, need to figure out that logic
        if ostore_exists:
            # this doesn't exist yet
            self.get_from_ostore(ostore_path, output_file)
            ostore_exists = True
        else:
            LOGGER.debug(f"Data not in object store, getting it from snow guys")

            # calling the super class method that was inherited, and then going to
            super(CMRClientOStore, self).get_file(
                granule_url, output_file, retries=retries
            )

            # now after the super class method has been called push the files up to
            # ostore so they are there for the next time they are required

        # finnally if the file was downloaded from the National Snow and Ice Data Centre
        # then upload it now to object storage.
        if not ostore_exists:
            LOGGER.info(f'persisting the file {output_file} to object storage')
            self.ostore.put_object(local_path=output_file, ostore_path=ostore_path)


class GranuleUtil:
    """
    This class represents a first attempt to centralize where granule related
    paths and other data will be calculated.

    Currently paths for granules rely on two separate locations for their
    configuration which is obviously problematic.

    `hatfieldcmr/ingest/name.py` defined the parameter `MODIS_NAME` as modis-terra
    which is then used to calculate the output path by the hatfieldcmr package

    conversly the `admin/constants.py` defines the `MODIS_TERRA` parameter which
    also defines the same path.

    LONG TERM: migrate away from hatfieldcmr as it adds a lot of unused functionality
    and the functionality that is being used could be expressed in an easier to
    understand and maintain way.  Also provides the opportunity to replace the
    dual path definitions.

    example of an output path calculated for a granule object:
    modis-terra/MOD10A1.061/2023.03.17/MOD10A1.A2023076.h11v03.061.2023078031324.hdf
    """

    def __init__(self, granule):
        self.granule = granule

        self.expected_keys = ["title", "time_start", "producer_granule_id"]
        #self.title_pattern_string = r"\w+:([\w]+\.[\w]+):\w+"
        self.title_pattern_string = r"(\w+).\w+.\w+(.\w+)"
        self.title_pattern = re.compile(self.title_pattern_string)

        self.validate()

    def validate(self):
        for expected_key in self.expected_keys:
            if expected_key not in self.granule:
                raise ValueError(
                    "granule does not have the required key: " + f"{expected_key}"
                )

    def get_local_path(self):
        title = self.granule.get("title", "")
        title_match = self.title_pattern.match(title)
        if title_match is None:
            raise ValueError(f"granule does not have well formated title: {title}")

        #product_name = title_match.groups()[0]
        product_name = ''.join(title_match.groups())

        date_string = dateutil.parser.parse(self.granule.get("time_start")).strftime(
            "%Y.%m.%d"
        )
        path_prefix = os.path.join(const.MODIS_TERRA, product_name, date_string)
        LOGGER.debug(f"output local path: {path_prefix}")
        return path_prefix

    def get_xml_url(self):
        xml_url = None
        for link_dict in self.granule["links"]:
            if ("type" in link_dict) and link_dict["type"] == "text/xml":
                xml_url = link_dict["href"]
        return xml_url

    def get_xml_local_file_name(self, full_path=False):
        xml_url = self.get_xml_url()
        file_name = os.path.basename(xml_url)
        if full_path:
            base_path = self.get_local_path()
            file_name = os.path.join(base_path, file_name)
        return file_name

    def get_hdf_url(self):
        hdf_url = self.granule["links"][0]["href"]
        return hdf_url

    def get_hdf_local_file_name(self, full_path=False):
        """gets the hdf file name from the granule"""
        hdf_url = self.get_hdf_url()
        file_name = os.path.basename(hdf_url)
        if full_path:
            base_path = self.get_local_path()
            file_name = os.path.join(base_path, file_name)
        return file_name

    def get_browseimage_url(self):
        browseimage_url = None
        for link_dict in self.granule["links"]:
            if ("type" in link_dict) and link_dict["type"] == "image/jpeg":
                browseimage_url = link_dict["href"]
        return browseimage_url

    def get_browseimage_local_file_name(self, full_path=False):
        """gets the browseimage file name from the granule"""
        browseimage_url = self.get_browseimage_url()
        file_name = os.path.basename(browseimage_url)
        if full_path:
            base_path = self.get_local_path()
            file_name = os.path.join(base_path, file_name)
        return file_name

    def get_granule_meta_file_name(self):
        """returns the name of the json file containing all the metadata about
        the granule.  The json file is a dump of the granule object to json.
        """
        meta_suffix = "_meta.json"
        directory_path = self.get_local_path()
        source_file_name = self.get_hdf_local_file_name()
        meta_data_file_name = f"{source_file_name}{meta_suffix}"
        full_path = os.path.join(directory_path, meta_data_file_name)
        LOGGER.debug(f"metdata full path: {full_path}")
        return full_path

    # def get_granule_ostore_path(self, granule):
    #     """
    #     gets a granule object, and returns the path for that granule in the object
    #     storage repository.

    #     :param path: _description_
    #     :type path: _type_
    #     """
    # granule.
    # when downloading the format_object_name method will return
    # modis-terra/<file-name>, the storage wrapper then adds on
    # the path config.TOP in this case would be data/ so full path would
    # be data/modis-terra/<file-name>
    # example fout path

    # 'modis-terra/MOD10A1.061/2023.03.17/MOD10A1.A2023076.h11v03.061.2023078031324.hdf'
    # TODO: there are duplicate path definitions.  Example hatfieldcmr/ingest/name.py defines
    #     MODIS_NAME parameter which defines 'modis-terra' as the folder
    #     name for the various granule related files.  That parameter is also in
    #     admin/constants.py.  Feel like the hatfieldcmr is more complex then it
    #     needs to be and is awkward to extend. Documentation is also pretty sparse which
    #     makes it difficult to extend.

    # gran = list of dicts
    #        property: links list with 8 elements - all dicts
    #        0 - link to hdf
    #        1 -
    #

    # the json data comes from dumping the meta / granule object using
    # the json.dump() method.
    #
    # THIS WILL GO TO THE UTIL  CLASS
