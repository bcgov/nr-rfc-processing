
from osgeo import gdal

def color_ramp(pth):
    """
    Apply colour ramp to GTiff

    Parameters
    ----------
    pth : str
        Path to file that the colour ramp will be applied to
    """
     # Apply color ramp
    ds = gdal.Open(pth, 1)
    band = ds.GetRasterBand(1)
    colours = gdal.ColorTable()
    colours.CreateColorRamp(0, (255, 255,191), 50, (214, 47,39))
    colours.CreateColorRamp(50, (69,117,182), 100, (255, 255,191) ) 
    #colours.SetColorEntry(250, (255,255,255)) # Clouds
    colours.SetColorEntry(254, (0,0,0))
    band.SetRasterColorTable(colours)
    band.SetRasterColorInterpretation(gdal.GCI_PaletteIndex)
    del band, ds