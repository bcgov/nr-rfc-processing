
# MODIS SPECIFIC STEPS
---------------------------------------------------------

## PROCESS DATA FLOW:

### Reproject step:

#### inputs
all the files in that directory with similar file name pattern

* `/data/modis-terra/MOD10A1.061/2023.03.23/MOD10A1.A2023082.h12v02.061.2023084034450.hdf`

#### outputs:
just one example, one to one relationship with inputs

* `/data/intermediate_tif/modis/2023.03.23/MOD10A1.A2023082.h12v02.061.2023084034450_EPSG4326.tif`



### Create Modis Mosaic Step:

#### inputs:

all the granule files... following is a single file example

* `data/intermediate_tif/modis/2023.03.23/MOD10A1.A2023082.h12v03.061.2023084034310_EPSG4326.tif`

#### outputs:

`data/norm/mosaics/modis/2023/2023.03.22.tif`

### Create Composite Mosaic Step:
#### inputs:
usually the 5 mosaics corresponding to the days in run.py... single example...

* `data/norm/mosaics/modis/2023/2023.03.23.tif`
* `data/norm/mosaics/modis/2023/2023.03.22.tif`
* `data/norm/mosaics/modis/2023/2023.03.21.tif`
*  etc...

#### outputs:
file name is calculated from the input dates MODIS (days paramater in run.py)

* `data/intermediate_tif/modis/2023.03.23/modis_composite_2023.03.23_2023.03.22_2023.03.21_2023.03.20_2023.03.19.tif`

### process by watershed - A

#### inputs:

* `data/intermediate_tif/modis/2023.03.23/modis_composite_2023.03.23_2023.03.22_2023.03.21_2023.03.20_2023.03.19.tif`

#### outputs:
clipped versions of the composite above to watersheds / basins directories, creates 4326 and 3153 versions

* `data/watersheds/Stikine/modis/2023.03.23/Stikine_modis_2023.03.23_EPSG4326.tif`
* `data/watersheds/Stikine/modis/2023.03.23/Stikine_modis_2023.03.23_EPSG3153.tif`

### process by watershed - B

calculates % change against normals for 10yr and 20yr normals
examples are for 10yr

#### inputs:
* norm: `data/norm/modis/daily/10yr/03.03.tif`
* clipped: `data/intermediate_tif/modis/2023.03.23/modis_composite_2023.03.23_2023.03.22_2023.03.21_2023.03.20_2023.03.19.tif`

#### outputs:
(copies norm to this file)
* `data/watersheds/Upper_Columbia/modis/2023.03.23/orig_Upper_Columbia_10yrNorm.tif`

(then manipulates norm)
* `data/watersheds/Lower_Fraser/modis/2023.03.23/Upper_Columbia_10yrNorm.tif`

---------------------------------------------------------

## PLOT

### Generate Plots by Watershed/Basin

simple but convoluted step that generates the final output plot

#### input:

* `data/watersheds/Stikine/modis/2023.03.23/Stikine_modis_2023.03.23_EPSG3153.tif`
* `data/watersheds/Stikine/modis/2023.03.23/Stikine_10yrNorm.tif`
* `data/watersheds/Stikine/modis/2023.03.23/Stikine_20yrNorm.tif`

#### output:

example of watersheds output... also creates similar pattern for basins

* `data/plot/modis/watersheds/2023.03.23/Stikine.png`

### Generate - Mosaic

#### input:
the 10yr and 20yr tifs are pulled from object storage if they don't exist locally

* `data/intermediate_tif/modis/2023.03.23/modis_composite_2023.03.23_2023.03.22_2023.03.21_2023.03.20_2023.03.19.tif`
* `data/norm/modis/daily/10yr/03.21.tif`
* `data/norm/modis/daily/20yr/03.21.tif`

#### output:

* `./data/plot/modis/mosaic/2023.03.21/2023.03.21.png`