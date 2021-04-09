import os
import yaml
import logging
import datetime
import shutil
import simplekml

import rasterio.plot

import rasterio as rio
import numpy as np
import matplotlib.pyplot as plt

from shapely.geometry import Point
from rasterio.warp import calculate_default_transform, reproject, Resampling
from sentinelsat import SentinelAPI
from glob import glob
from zipfile import ZipFile

from admin.db_handler import DBHandler
import admin.constants as const
from admin.color_ramp import s2_color_ramp

"""
S2 NDSI : https://sentinel.esa.int/web/sentinel/technical-guides/sentinel-2-msi/level-2a/algorithm

Long Term Archive (LTA) Notice
https://scihub.copernicus.eu/news/News00592 
- Data that is older than 18 months from the current date is transferred to 
LTA and may require aditional wait times for downlaoding as it is 
retrieved upon request.
"""

nodata_val = 254

logger = logging.getLogger(__name__)

def query(creds: str, udate: str, lat: float, lng: float, 
            max_allowable_cloud: int, day_tolerance: int = 50):
    """Query ESA Servers for Sentinel-2 L2A data

    Parameters
    ----------
    creds : str
        Path to credential YAML file
    udate : str
        Target date in format YYYY.MM.DD
    lat : float
        Target latitude
    lng : float
        Target longitude
    max_allowable_cloud : int
        Top percentage allowable cloud coverage for a tile
    day_tolerance : int, optional
        The numbers of days to query back from the target date, by default 50

    Returns
    -------
    ok : int
        If the query returned more than 0 products, return 1, else return 0 and 
        the rest of the pipeline will be skipped in favour of refining parameters
    product : str
        Product key to be passed to to download function
    api : API interface
        API interface that download() will use to get product
    date : str
        Date of selected tile as it may differ from target date
    """
    aoi = Point((lng, lat)) # WKT AOI

    # Get credentials
    envvars = open(creds ,'r')
    secrets = yaml.load(envvars, Loader=yaml.FullLoader)
    envvars.close()

    # Validate credentials for API access
    api = SentinelAPI(
        secrets['SENTINELSAT_USER'], 
        secrets['SENTINELSAT_PASS'], 
        'https://scihub.copernicus.eu/apihub', #'https://scihub.copernicus.eu/dhus',
        show_progressbars=True
    )

    # Query for products
    thisdate = udate.split('.')
    thisdate = datetime.date(int(thisdate[0]), int(thisdate[1]), int(thisdate[2]))
    products = []
    before = thisdate-datetime.timedelta(days=day_tolerance)
    products = api.query(
                    aoi,
                    date=(before, thisdate),
                    platformname='Sentinel-2',
                    cloudcoverpercentage=(0, max_allowable_cloud),
                    area_relation='intersects',
                    order_by='-beginposition',
                    limit=10,
                    producttype='S2MSI2A'
                    )
    logger.debug(f'PRODUCTS: {products}')
    logger.info(f'LEN PRODUCTS: {len(products)}')
    
    # User interface to select desired tile from date and cloud coverage
    if len(products) > 0:
        opts = []
        idx = 0
        for prod in products:
            opts.append(prod)
            dt = products[prod]['beginposition']
            d_truncated = datetime.date(dt.year, dt.month, dt.day)
            cloud = products[prod]['cloudcoverpercentage']
            print(f'{idx} : DATE: {d_truncated} || CLOUD%:  {cloud}')
            idx += 1
        try: # If user inputs anything but an integer, return ok=0 to end pipeline
            yn = int(input(f'Pick which product to download and process [0-{len(opts)-1}/n]: '))
        except ValueError as ve:
            return 0, None, None, udate
        if yn < 0 or yn > len(opts)-1: # Check user entered valid entry
            logger.error('[sentinel2.query] Invalid index entry')
            print(f'Invalid index selected, select an index between 0 and {len(opts)-1}')
            return 0, None, None, udate
        else: # Return user selected product to download
            dt = products[opts[yn]]['beginposition']
            d_truncated = datetime.date(dt.year, dt.month, dt.day)
            date = datetime.datetime.strftime(d_truncated, '%Y.%m.%d')
            return 1, opts[yn], api, date
    else: # If no products were found with given params
        print('Could not find any granules...')
        print('Try again with a higher cloud-tolerance')
        return 0, None, None, udate

def build_sentinel_dir_struture():
    """
    Build directory structure for Sentinel-2 processing
    """
    dirs= [
        const.TOP,
        const.LOG,
        const.KML,
        const.INTERMEDIATE_TIF,
        const.INTERMEDIATE_TIF_SENTINEL,
        const.PLOT,
        const.PLOT_SENTINEL,
        const.ANALYSIS,
        const.SENTINEL_OUTPUT
    ]

    for d in dirs:
        try:
            os.makedirs(d)
        except Exception as e:
            logger.warning(e)

def download(product: str, api: SentinelAPI, udate: str, lat: float, lng: float, force: str='false'):
    """Download Sentinel-2 tile user selected

    Parameters
    ----------
    product : str
        Product key of selceted tile
    api : SentinelAPI
        API interface to Sentinel-2 data hub
    udate : str
        Selected date in format YYYY.MM.DD
    lat : float
        Target latitude
    lng : float
        Target longitude
    force : str, optional
        Force download by removing existing downloaded zip files, by default 'false'

    Returns
    -------
    str
        Path to downloaded zip of tile
    """
    logger.info('DOWNLOADING SENTINEL-2 DATA')
    output_pth = os.path.join(const.MODIS_TERRA,'sentinel',udate, f'lat{lat}_lng{lng}')
    try:
        os.makedirs(output_pth)
    except Exception as e:
        logger.warning(e)
    if force == 'true': # if force then remove existing downloads
        files = glob(os.path.join(output_pth, '*'))
        for f in files:
            os.remove(f)
    try: # download target tile
        logger.info(f'Downloading {product}')
        info = api.download(product, directory_path=output_pth)
        return info
    except Exception as e:
        logger.error(e)
    
def process(info: str, udate: str, lat: float, lng: float, rgb: str):
    """Process the Sentinel-2 tile calculating NDSI and saving GTiffs

    Parameters
    ----------
    info : str
        Path to downloaded zip tile
    udate : str
        Selected date in format YYYY.MM.DD
    lat : float
        Target latitude
    lng : float
        Target longitude
    rgb : str
        Indicator to create RGB GTiff

    Returns
    -------
    str
        Path to NDSI GTiff
    """
    
    logger.info('[sentinel2.process] PROCESSING S2 SCENE')
    gran = info['path']
    intermediate_tif = os.path.join(const.INTERMEDIATE_TIF_SENTINEL, udate,f'lat{lat}_lng{lng}')
    # Clean up residual files
    files = glob(os.path.join(intermediate_tif, '*'))
    for f in files:
        if os.path.isfile(f):
            os.remove(f)
        elif os.path.isdir(f):
            shutil.rmtree(f)
    try:
        os.makedirs(intermediate_tif)
    except OSError as e:
        logger.debug(f'[sentinel2.process] {e}')
    # Unzip downloaded tile
    logger.info('[sentinel2.process] EXTRACTING ZIPFILE...')
    with ZipFile(gran, 'r') as zipObj:
        zipObj.extractall(intermediate_tif)
    unzipped = os.path.join(intermediate_tif,os.path.split(gran)[-1].split('.')[0]+'.SAFE')
    base = os.path.join(intermediate_tif, glob(unzipped)[0], 'GRANULE', '**', 'IMG_DATA', 'R20m')

    # Gather band paths
    bands = [
        glob(os.path.join(base,'*B02*.jp2'))[0], #b2
        glob(os.path.join(base,'*B03*.jp2'))[0], #b3
        glob(os.path.join(base,'*B04*.jp2'))[0], #b4
        glob(os.path.join(base,'*B8A*.jp2'))[0], #b8
        glob(os.path.join(base,'*B11*.jp2'))[0], #b11
        glob(os.path.join(base,'*SCL*.jp2'))[0], #bCloud
    ]

    logger.info('[sentinel2.process] READING BANDS')
    with rio.Env():
        # Open bands and collect data for calculations
        with rio.open(bands[0], 'r', nodata=nodata_val) as src:
            b2 = src.read(1)
            profile = src.profile
        with rio.open(bands[1], 'r') as src:
            b3 = src.read(1)
        with rio.open(bands[2], 'r') as src:
            b4 = src.read(1)
        with rio.open(bands[3], 'r') as src:
            b8 = src.read(1)
        with rio.open(bands[4], 'r') as src:
            b11 = src.read(1)
        with rio.open(bands[5], 'r') as src:
            cloud_mask = src.read(1)

        # Create RGB version if selected
        if rgb == 'true':
            profile.update({
                "count": 3,
                "driver":"GTiff",
            })
            logger.info('[sentinel2.process] WRITING S2 RGB GTIFF')
            rgb_out = os.path.join(const.SENTINEL_OUTPUT, udate, f'lat{lat}_lng{lng}', f'{udate}.tif')
            try:
                os.makedirs(os.path.split(rgb_out)[0])
            except Exception as e:
                logger.debug(f'[sentinel2.process] {e}')
            with rio.open(rgb_out, 'w', **profile) as dst:
                dst.write(b2 ,1)
                dst.write(b3 ,2)
                dst.write(b4 ,3)
        
        # Create NDSI profile
        profile.update({
                "driver": 'GTiff',
                "count": 1,
                'dtype' : rio.float64,
                'nodata': nodata_val
            })
        inf_val = 0.0 #nodata_val
        dival = 10000
        nosnow = 0.0
        intermediate_ndsi = os.path.join(intermediate_tif, f'NDSI_{udate}.tif')
        logger.info('[sentinel2.process] WRITING NDSI GTIFF')
        with rio.open(intermediate_ndsi, 'w', **profile) as dst:
            np.seterr(divide='ignore', invalid='ignore')
            NDSI = np.divide((b3-b11), (b3+b11)) # NDSI Calculation
            NDSI[NDSI == np.inf] = inf_val # correct div by 0 and inf/nan
            NDSI = np.nan_to_num(NDSI, nan=inf_val, posinf=inf_val, neginf=inf_val) # correct div by 0 and inf/nan
            NDSI[(NDSI <= 0.0)] = nosnow # force no snow values to nosnow
            NDSI[(NDSI > 1.0)&(NDSI != nodata_val)] = nosnow  # force non-NDSI values to nosnow
            NDSI[(b8/dival < 0.35)] = nosnow # Step2.2 of NDSI calc
            NDSI[(b2/dival < 0.18)] = nosnow # Step2.3 of NDSI calc
            b2b4 = np.divide(b2/dival, b4/dival) # correct div by 0 and inf/nan
            b2b4 = np.nan_to_num(b2b4, nan=inf_val, posinf=inf_val, neginf=inf_val) # correct div by 0 and inf/nan
            NDSI[(b2b4 < 0.85)] = nosnow # Step2.4 of NDSI calc
            #nodata_msk = ((b2 == 0)&(b3==0)&(b4==0)&(b11==0))
            #NDSI[nodata_msk] = nodata_val
            NDSI[(cloud_mask==6)] = nodata_val # Water mask
            NDSI[(cloud_mask==8)] = nodata_val # Cloud_Medium_Probability mask
            NDSI[(cloud_mask==9)] = nodata_val # Cloud_High_Probabiliter mask
            NDSI = NDSI*100 # Scale to 0-100 range
            dst.write(NDSI, 1) # Write data to file
    return intermediate_ndsi

def reproject_s2(pth: str, date: str, lat: float, lng: float, dst_crs: str):
    """Reproject GTiff to target CRS
    EPSG:3005 - BC Albers - output tif and plot
    EPSG:4326 - KML generation

    Parameters
    ----------
    pth : str
        Path to source GTiff to be reprojected
    date : str
        Date selected in format YYYY.MM.DD
    lat : float
        Target latitude
    lng : float
        Target longitude
    dst_crs : str
        Desired CRS to reproject to

    Returns
    -------
    str
        Path to output GTiff
    """
    logger.info(f'[sentinel2.reproject_s2] REPROJECTING S2 TO {dst_crs}')
    base = os.path.split(pth)[0]
    if dst_crs == 'EPSG:4326':
        out_pth = os.path.join(base, f'{date}_EPSG4326.tif')
        res = 0.000285245221099300378 # Value from QGIS reprojection inspection
    elif dst_crs == 'EPSG:3153':
        out_pth = os.path.join(base, f'{date}_EPSG3153.tif')
        res = 20.00754121032614563 # Value from QGIS reprojection inspection
    else:
        logger.warning('[sentinel2.reproject_s2] Invalid CRS')
        return None
    try:
        os.remove(out_pth)
    except Exception as e:
        logger.debug(f'[sentinel2.reproject_s2] Removing residual file:  {e}')
    with rio.open(pth, 'r') as src:
        transform, width, height = calculate_default_transform(
                src.crs, dst_crs, src.width, src.height, *src.bounds, resolution=res) 
        kwargs = src.meta.copy()
        # Update meta information to desired CRS
        kwargs.update({
            'driver': 'GTiff',
            'crs': dst_crs,
            'transform': transform,
            'width': width,
            'height': height,
            'dtype': rio.uint16,
            'nodata': nodata_val
        })
        # Write reprojected granule into GTiff format
        with rio.open(out_pth, 'w', **kwargs) as dst:
            reproject(
            source=rio.band(src, 1),
            destination=rio.band(dst, 1),
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=transform,
            dst_crs=dst_crs,
            resampling=Resampling.nearest,
            dst_nodata=nodata_val)
    if dst_crs == 'EPSG:3153':
        mv_pth = os.path.join(const.SENTINEL_OUTPUT, date, f'lat{lat}_lng{lng}', os.path.split(out_pth)[-1])
        try:
            os.makedirs(os.path.split(mv_pth)[0])
        except:
            pass
        shutil.copy(out_pth, mv_pth)
    return out_pth


def analysis(pth: str, date: str, name: str, db_handler: DBHandler):
    """Calculate the snow coverage, nodata, and below threshold
    values for the selected tile

    Parameters
    ----------
    pth : str
        Path of tile to be analyzed
    date : str
        Date selected in format YYYY.MM.DD
    name : str
        Name for output
    db_handler : DBHandler()
        Handler class for database connection

    Returns
    -------
    tuple
        calculated values of (nodata, belowthreshold, snowcoverage)
    """    
    logger.info('[sentinel2.analysis] RUNNING ANALYSIS ON S2 SCENE')
    with rio.Env():
        # Calculate values
        with rio.open(pth, 'r') as src:
            data = src.read(1)
            land = data.shape[0]*data.shape[1]
            nodata = np.around(((data > 100).sum()/land)*100, 6)
            below_threshold =  np.around(((data <= 20).sum()/land)*100, 6)
            cover = (((data > 20) & (data <= 100)).sum())
            coverage = np.around((cover/land)*100, decimals=6)

    logger.info(f'S2 SNOW COVERAGE FOR {name}')
    logger.info(f'NODATA: {nodata}')
    logger.info(f'BELOW {below_threshold}')
    logger.info(f'COVERAGE {coverage}')

    prepare = {
        'sat': 'sentinel2',
        'name': name,
        'date_': date,
        'coverage': coverage,
        'nodata': nodata,
        'below_threshold': below_threshold
    }
    db_handler.insert(**prepare)
    return (nodata, below_threshold, coverage)


def attach_colour_ramp(pth: str):
    """Attaches the colour ramp to tile GTiff

    Parameters
    ----------
    pth : str
        Path of GTiff to attach colour ramp to
    """    
    logger.info('[sentinel2.attach_colour_ramp] ATTACHING COLOUR RAMP TO GTIFF')
    s2_color_ramp(pth)

def expand(pth: str, date: str):
    """Expand single band with colour ramp into RGB GTiff

    Parameters
    ----------
    pth : str
        Path to single band GTiff
    date : str
        Date selected in format YYYY.MM.DD

    Returns
    -------
    str
        Path to expanded RB GTiff
    """    
    logger.info('[sentinel2.expand] EXPANDING SINGLE BAND TO RGB OF COLOUR RAMP')
    output_pth = os.path.join(os.path.split(pth)[0], f'{date}_col.tif')
    if os.path.exists(output_pth):
        os.remove(output_pth) # Clean residual file
    os.system(f'gdal_translate -q -ot Byte -expand rgb -of GTiff \
                {pth} {output_pth}')
    return output_pth

def kml(pth: str, date: str, name: str, coverage: float):
    """Create KML of selected tile

    Parameters
    ----------
    pth : str
        Path of GTiff to generate KML from
    date : str
        Date selected in format YYYY.MM.DD
    name : str
        Name for output KML
    coverage : float
        Tuple of meta information to attach to KML
    """
    logger.info('[sentinel2.kml] BUILDING KML FILES')
    name = "_".join(name.split(" "))
    kml_pth = os.path.join(const.KML, 'sentinel', name)
    if os.path.exists(kml_pth):
        shutil.rmtree(kml_pth)
    try:
        os.makedirs(kml_pth)
    except Exception as e:
        logger.warning(e)
    # Get location for metadata label
    with rio.open(pth) as src:
        upperleft = src.transform * (0,0)
        bottomright = src.transform * (src.width, src.height)
    # Create KML version of expanded EPSG:4326 GTiff
    gdal_str = f'gdal2tiles.py -q --processes=4 -p raster -t {name} --tilesize=128 -s \
                    EPSG:4326 -k -r near {pth} {kml_pth}'
    os.system(gdal_str)
    # Build top level KML to attach metadata to
    kml = simplekml.Kml(name=name)
    link = kml.newnetworklink(name=name)
    # Link low level kml
    link.link.href = os.path.join('sentinel', name, 'doc.kml')
    link.link.viewrefreshmode = simplekml.ViewRefreshMode.onrequest
    fmt = lambda x: np.around(x, decimals=2)
    # Attach metadata
    #kml.document.description = f'NODATA: {fmt(coverage[0])}%,\
    #     BELOW: {fmt(coverage[1])}%, SNOW: {fmt(coverage[2])}%'
    pnt = kml.newpoint(name=name, description=f'NODATA: {fmt(coverage[0])}%,\
                    BELOW: {fmt(coverage[1])}%, SNOW: {fmt(coverage[2])}%', 
                     coords=[np.divide(np.add(upperleft, bottomright),2)])
    pnt.style.iconstyle.icon.href = 'http://maps.google.com/mapfiles/kml/shapes/snowflake_simple.png'
    # Save top level KML
    kml.save(os.path.join(const.KML, 'sentinel_'+name+'.kml'))

def plot(pth: str, name: str):
    """Plot EPSG:3005 GTiff

    Parameters
    ----------
    pth : str
        Path of GTiff to be plot
    name : str
        Output name for plot
    """
    logger.info('[sentinel2.plt] PLOTTING S2 SCENE')
    fig, ax = plt.subplots(1,1, dpi=100)
    out_pth = os.path.join(const.PLOT_SENTINEL, f'{name}.png')
    if os.path.exists(out_pth):
        os.remove(out_pth)
    with rio.Env():
        with rio.open(pth, 'r') as src:
            data = src.read()
            # underlying image to generate colourbar from
            im = ax.imshow(data.transpose(1,2,0), cmap=plt.cm.RdYlBu, vmin=0, vmax=100, clim=[0,100])
            cbar = fig.colorbar(im)
            cbar.ax.set_ylabel('NDSI', rotation=270)
            # Plot GTiff
            rasterio.plot.show((src.read()), transform=src.transform, ax=ax, adjust=None)
            ax.axis('off')
            ax.set_title(name)
        plt.savefig(out_pth)

def sentinel_pipeline(creds: str, date: str, 
                        lat: float, lng: float, rgb: str,
                        max_allowable_cloud: int, force_download: str,
                        day_tolerance: int, db_handler: DBHandler
                    ):
    """Pipeline Kicker

    Parameters
    ----------
    creds : str
        Path to credential YAML file
    date : str
        Target date in format YYYY.MM.DD
    lat : float
        Target latitude
    lng : float
        Target longitude
    rgb : str
        Indicator to generate RGB version
    max_allowable_cloud : int
        Max allowable cloud percentage when querying tiles
    force_download : str
        Force download by removing previous downloaded zip files
    day_tolerance : int
        Number of days to look back from target date
    db_handler : DBHandler()
        Handler class for database connection
    """
    logger.info('[sentinel2.sentinel_pipeline] SENTINEL2 PIPELINE STARTING')
    build_sentinel_dir_struture()
    ok, prod, api, date = query(creds, date, lat, lng, max_allowable_cloud, day_tolerance)
    if ok:
        out_name = f'S2 - {date} - {lat}, {lng}'
        info = download(prod, api, date, lat, lng, force_download)
        orig_pth = process(info, date, lat, lng, rgb)
        
        # BC Albers build
        bc_pth = reproject_s2(orig_pth, date, lat, lng, 'EPSG:3153')
        attach_colour_ramp(bc_pth)
        bc_col = expand(bc_pth, date)
        plot(bc_col, out_name)
        coverage = analysis(bc_pth, date, out_name, db_handler)

        # KML build
        pth = reproject_s2(orig_pth, date, lat, lng, 'EPSG:4326')
        attach_colour_ramp(pth)
        col_pth = expand(pth, date)
        kml(col_pth, date, out_name, coverage)