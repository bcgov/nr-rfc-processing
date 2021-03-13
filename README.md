# Process Pipeline

## Building Docker Image

To build the image from this directory:

```bash
docker build -t <tagname> .
```

## Running Docker Image

To run the Docker image use the following schema:

```bash
docker run --rm -v <local store>:/data <tagname> <extra_commands>
```

## Credential YAML

This YAML file will be passed to the ``--envpth`` argument to be able to download MODIS/VIIRS/Sentinel-2 data. This file needs to be located inside the mounted volume store in order for the internal processes to access the credentials. 

```bash
--envpth /data/<credential>.yml
```

<details>
<summary>YAML</summary>

```yaml
# register at https://urs.earthdata.nasa.gov/home
EARTHDATA_USER: username_without_quotes
EARTHDATA_PASS: password_without_quotes

# register at https://scihub.copernicus.eu/dhus/#/self-registration 
SENTINELSAT_USER: username_without_quotes
SENTINELSAT_PASS: password_without_quotes
```

</details>

## Input Formats

| ARG | VALUES | TYPE |
|---|---|---|
| envpth | Linux path | string |
| date | YYYY.MM.DD | string |
| sat  | modis / viirs / sentinel | string |
| typ | watersheds / basins | string |
| days | 1 / 5 / 8 | int |

## Docker Options

| OPTION | CAUSE | 
|---|---|
| --rm | Removes container once it finishes running |
| -v | Mount volume to Docker container |

## Help

To list out commands available:

The default CMD is "--help" to list out the available commands. 

```bash
docker run --rm -v <mount_point>:/data <tag_name>
```

## Daily-Pipeline

```bash
docker run --rm -v <mount_point>:/data <tag_name> daily-pipeline --envpth <path/to/creds.yml> --date <target_date: YYYY.MM.DD>
```

``daily-pipeline`` kicks off the entire process chain that will include performing the following per satellite (MODIS/VIIRS):

- Build up directory structure and supporting files
- Download raw granule files
- Process raw granules to GTiff formats
- Calculate snow coverage per watersheds/basin
- Build KML of watersheds/basins
- Clean up intermediate files

## Build Directory Structure

Builds necessary supporting files and directories in order for the process pipeline to properly manage file I/O. 

```bash
docker run --rm -v <mount_point>:/data <tag_name> build
```

High Level Directory Structure:
- /data
    - /analysis
    - /basins
    - /intermediate_kml
    - /intermediate_tif
    - /kml
    - /modis-terra
    - /output_tif
    - /plot
    - /watersheds

## Download

MODIS requires 5 or 8 days in order to build a composite of valid data. Option to download one day is possible.

```bash
docker run --rm -v <mount_point>:/data <tag_name> download --envpth <path/to/creds> --sat <modis/viirs> --date <YYYY.MM.DD> --days <1/5/8>
```

Output:
- Raw granules: ``modis-terra/<product>/<date>/.``
    - MODIS: MOD10A1.006
    - VIIRS: VNP10A1F.001

## Process

MODIS requires 5 or 8 days in order to build a composite of valid data. Default value is 5 days. 

```bash
docker run --rm -v <mount_point>:/data <tag_name> process --sat <modis/viirs> --date <YYYY.MM.DD> --days <1/5/8>
```

Output:
- Clipped watershed/basin GTiff: ``<watershed/basin>/<name>/<satellite>/<date>/.``
    - EPSG:4326 -> needed for KML
    - EPSG:3153 -> BC Albers projection GTiff


## Caclulate Snow Coverage

Analyze each watershed and basin to calculate the snow coverage based on the NDSI value. 

```bash
docker run --rm -v <mount_point>:/data <tag_name> run-analysis --typ <watersheds/basins> -sat <modis/viirs> --date <YYYY.MM.DD>
```

Output:
- SQLITE3 database: ``analysis/analysis.db``

## Database To CSV

Convert the SQLITE3 database into a CSV

```bash
docker run --rm -v <mount_point>:/data <tag_name> dbtocsv
```

Output: 
- CSV: ``analysis/analysis.csv``

## Build KMLs and Colour Ramped GTiffs

Build the colour-ramp GTiff and KML versions of the watersheds/basins.

```bash
docker run --rm -v <mount_point>:/data <tag_name> build-kml --date <YYYY.MM.DD> --typ <watersheds/basins> --sat <modis/viirs>
```

Output : 
- colourized GTiffs: ``<watersheds/basins>/<name>/<satellite>/<date>/.``
- KML : ``kml/<date>/``

## Compose KMLs

Compose built KML files into a heirarchal KML

```bash
docker run --rm -v <mount_point>:/data <tag_name> compose-kmls --date <YYYY.MM.DD> --sat <modis/viirs>
```

## Zip KMLs

ZIP KMLs into a ZIP file

```bash
docker run --rm -v <mount_point>:/data <tag_name> zip-kmls
```

KNOWN ISSUE: ZIP file is larger than original KMLs -- deprecated

## Plot

Plot all watersheds and basins into PNG plots with mapped colour bar.

```bash
docker run --rm -v <mount_point>:/data <tag_name> plot --date <YYYY.MM.DD> --sat <modis/viirs>
```

## Clean

Manually clean up files and directories.

| TARGET | CAUSE |
|---|---|
| all | All directories in ``/data`` AKA clean build |
| intermediate | Intermediate files in ``intermediate_\[tif/kml\]`` |
| output | Output files in ``output_tif`` |
| downloads | Raw granules in ``modis-terra/`` |
| watersheds | All files/dirs in ``watersheds/`` | 
| basins | All files/dirs in ``basins/`` |

```bash
docker run --rm -v <mount_point>:/data <tag_name> clean --target <target>
```