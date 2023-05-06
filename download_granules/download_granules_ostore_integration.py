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
from multiprocessing import Pool

import cmr

# from dateutil.parser import parse as dateparser
import dateutil.parser
import requests

import admin.constants as const

# from hatfieldcmr import CMRClient
from hatfieldcmr.ingest import LocalStorageWrapper

import NRUtil.NRObjStoreUtil
LOGGER = logging.getLogger(__name__)


class GranuleDownloader:
    def __init__(self, sat_config):
        self.sat_config = sat_config

    def download_granules(self):
        # TODO: once complete and tested this will be renamed to download_granules

        """ """
        date = self.sat_config.date_str.split(".")
        end_date = datetime.datetime(int(date[0]), int(date[1]), int(date[2]))
        ed_client = CMRClient(
            earthdata_user=const.EARTHDATA_USER,
            earthdata_pass=const.EARTHDATA_PASS,
        )
        start_date = end_date - datetime.timedelta(self.sat_config.date_span)
        granules = ed_client.query(
            str(start_date.date()),
            str(end_date.date()),
            self.sat_config,
            bbox=[*const.BBOX],
        )
        msg = (
            f"queried product {self.sat_config.products}, got {len(granules)} " +
            "granules, downloading"
        )
        LOGGER.info(msg)

        # debug - runs sync vs async to help debug
        # for gran in granules:
        #     ed_client.download_granule(gran)
        # LOGGER.debug("all granules downloaded...")

        try:
            with Pool(4) as p:
                p.map(ed_client.download_granule, granules)
        except KeyboardInterrupt:
            LOGGER.error('keyboard interupt... Exiting download pool')



class CMRClient:
    def __init__(self, earthdata_user="", earthdata_pass=""):
        self.earthdata_user = earthdata_user or os.getenv("EARTHDATA_USER")
        self.earthdata_pass = earthdata_pass or os.getenv("EARTHDATA_PASS")
        # methods that need a session will built it for themselves
        self.session = None

        self.chunk_size = 256 * 1024

    def query(
        self,
        start_date: str,
        end_date: str,
        dl_config,
        provider: str = "LPDAAC_ECS",
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
        provider: string
            Provider (default is 'LPDAAC_ECS')
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
        q = cmr.GranuleQuery()
        prod, ver = dl_config.get_product_version()[0]
        q.short_name(prod).version(ver)
        q.temporal(f"{start_date}T00:00:00Z", f"{end_date}T23:59:59Z")
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
            date = (
                dateutil.parser.parse(gran["time_start"].split("T")[0])
                + datetime.timedelta(days=day_offset)
            ).date()
            if (
                dateutil.parser.parse(start_date).date()
                <= date
                <= dateutil.parser.parse(end_date).date()
            ):
                granules.append(gran)
        LOGGER.info(
            "%s granules found within %s - %s" % (len(granules), start_date, end_date)
        )
        return granules

    def save_metadata(self, granule, output_file):
        if not os.path.exists(output_file):
            LOGGER.debug(f"output_file: {output_file}")
            # './data/MOD10A1.61/MOD10A1.061/2023.03.17/MOD10A1.A2023076.h11v03.061.2023078031324.hdf_meta.json'
            with open(output_file, "w") as fh:
                json.dump(granule, fh, sort_keys=True, indent=4, ensure_ascii=False)

    def get_file(self, granule_url, output_file, retries=0):
        if not os.path.exists(output_file):
            self.check_session()
            r1 = self.session.request("get", granule_url)

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
                self.get_file(granule_url, output_file, retries)
            else:
                # write straight to output file
                with open(output_file, "wb") as f:
                    for chunk in stream.iter_content(chunk_size=self.chunk_size):
                        # If you have chunk encoded response uncomment if
                        # and set chunk_size parameter to None.
                        # if chunk:
                        f.write(chunk)

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

    def get_ostore_file_list(self):
        pass

    def get_ostore_path(self, local_path):

        pass

    def get_file(self, granule_url, output_file, retries=0):
        # intercept the method call and determine if the files are in object storage, and
        # if they are pull them down, if now then call the super class.

        ostore_path = self.get_ostore_path()
        # exists, doesn't exist, need to figure out that logic
        if self.ostore.exists(ostore_path):
            # this doesn't exist yet
            self.get_from_ostore()

        else:
            # calling the super class method that was inherited, and then going to
            super(CMRClientOStore, self).get_file(granule_url, output_file, retries=0)

            # now after the super class method has been called push the files up to
            # ostore so they are there for the next time they are required



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
        self.title_pattern_string = r"\w+:([\w]+\.[\w]+):\w+"
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

        product_name = title_match.groups()[0]

        date_string = dateutil.parser.parse(self.granule.get("time_start")).strftime(
            "%Y.%m.%d"
        )
        path_prefix = os.path.join(const.MODIS_TERRA, product_name, date_string)
        LOGGER.debug(f"output local path: {path_prefix}")
        return path_prefix

    # moved to util class
    # def get_granule_local_path(self):
    #     """when downloading the granule, the path that it should be copied to
    #     locally.
    #     """
    #     output_path = self.get_local_path()

    #     title = self.granule.get("title", "")
    #     title_match = self.title_pattern.match(title)
    #     if title_match is None:
    #         raise ValueError(f"granule does not have well formated title: {title}")

    #     product_name = title_match.groups()[0]

    #     date_string = dateutil.parser.parse(self.granule.get("time_start")).strftime(
    #         "%Y.%m.%d"
    #     )

    #     #return folder_prefix

    def get_granule_ostore_path(self):
        pass

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
