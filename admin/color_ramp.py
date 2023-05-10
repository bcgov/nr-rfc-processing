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
    existing_color_table = band.GetColorTable()
    # only apply color ramp if there isn't one already
    if not existing_color_table:
        colours = gdal.ColorTable()
        colours.CreateColorRamp(20, (255, 38, 56), 50, (255, 254, 189))
        colours.CreateColorRamp(50, (255, 254, 189), 100, (25, 147, 255) )
        colours.SetColorEntry(254, (0,0,0))
        band.SetRasterColorTable(colours)
        band.SetRasterColorInterpretation(gdal.GCI_PaletteIndex)
    del band, ds

def s2_color_ramp(pth):
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
    colours.CreateColorRamp(0, (255, 38, 56), 50, (255, 254, 189))
    colours.CreateColorRamp(50, (255, 254, 189), 100, (25, 147, 255) )
    colours.SetColorEntry(254, (0,0,0))
    band.SetRasterColorTable(colours)
    band.SetRasterColorInterpretation(gdal.GCI_PaletteIndex)
    del band, ds

def color_ramp_norm(pth):
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
    colours.CreateColorRamp(-100, (255, 38, 56), 0, (255, 254, 189))
    colours.CreateColorRamp(0, (255, 254, 189), 100, (25, 147, 255))
    band.SetRasterColorTable(colours)
    band.SetRasterColorInterpretation(gdal.GCI_PaletteIndex)
    del band, ds