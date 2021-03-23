import os

class Constants(object):
    def __init__(self):
        self.top = os.environ['SNOWPACK-DATA']
        self.basins = os.path.join(self.top,'basins')
        self.watersheds = os.path.join(self.top,'watersheds')
        self.kml = os.path.join(self.top,'kml')
        self.intermediate_kml = os.path.join(self.top,'intermediate_kml')
        self.intermediate_tif = os.path.join(self.top,'intermediate_tif')
        self.intermediate_tif_modis = os.path.join(self.intermediate_tif,'modis')
        self.intermediate_tif_viirs = os.path.join(self.intermediate_tif,'viirs')
        self.intermediate_tif_sentinel = os.path.join(self.intermediate_tif,'sentinel')
        self.intermediate_tif_plot = os.path.join(self.intermediate_tif,'plot')
        self.output_tif = os.path.join(self.top,'output_tif')
        self.output_tif_modis = os.path.join(self.output_tif,'modis')
        self.output_tif_viirs = os.path.join(self.output_tif,'viirs')
        self.output_tif_sentinel = os.path.join(self.output_tif,'sentinel')
        self.plot = os.path.join(self.top,'plot')
        self.plot_modis = os.path.join(self.plot,'modis')
        self.plot_modis_mosaic = os.path.join(self.plot,'modis','mosaic')
        self.plot_modis_watersheds = os.path.join(self.plot_modis,'watersheds')
        self.plot_modis_basins = os.path.join(self.plot_modis,'basins')
        self.plot_viirs = os.path.join(self.plot,'viirs')
        self.plot_viirs_mosaic = os.path.join(self.plot_viirs,'mosaic')
        self.plot_viirs_watersheds = os.path.join(self.plot_viirs,'watersheds')
        self.plot_viirs_basins = os.path.join(self.plot_viirs,'basins')
        self.plot_sentinel = os.path.join(self.plot,'sentinel')
        self.analysis = os.path.join(self.top,'analysis')
        self.modis_terra = os.path.join(self.top,'modis-terra')

        self.aoi = os.path.join(os.path.dirname(__file__), '..', 'aoi')