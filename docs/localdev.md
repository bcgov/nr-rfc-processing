# Intro

describes getting a local development env up and running.

# Install WSL

All development moving forward will be completed on a linux based env.
[Install WSL](https://learn.microsoft.com/en-us/windows/wsl/install) if not
already installed.


# Install Deps Using Mamba

More detailed docs on mamba exist [further down](#mamba---details), this is
focused on just getting a local dev env built and running

## Create environment

Create mamba env from the environment.yaml definition.  This step only needs
to be run when either setting up a new computer, or if the dependency
declarations have changed.

### Create mamba env

`micromamba create -y -n ldev --file environment.yaml`

### Install other dependencies

These are other misc dependencies that are not installable through conda
like tools

```
pip install -r requirements.txt

# dev deps install
pip install -r requirements-dev.txt

# local hatfieldcmr package
pip install -e .
```

# Define Required Environment Variables

The script currently looks for an environments.yaml file for the username and
passwords for communicating with the various data providers.

Create a file called `env.yaml`

yaml file has the following structure *example only*:

```
EARTHDATA_USER: GuyLafleur
EARTHDATA_PASS: MontrealNumber10
SENTINELSAT_USER: YvonneC
SENTINELSAT_PASS: sc0resLots0fGoals
```

# Running the daily pipeline script:

* activate conda env path:
    `conda activate ./ldev`

* run the daily update
    ``` bash
    export SNOWPACK_DATA=./data
    mkdir -p $SNOWPACK_DATA
    export SNOW_PIPELINE_DATE=$(python getDate.py)
    export SNOWPACK_ENVS_PTH=./env.yaml
    export NORM_ROOT=data
    python run.py daily-pipeline --envpth=$SNOWPACK_ENVS_PTH --date $SNOW_PIPELINE_DATE
    ```

See the re-architect.md doc for bullets to dissect up the tasks that are part
of the daily update into smaller chunks.

# Run the Archive / S3 backup / Save Operation

### Define Object Store Environment Variables:

The following env vars must be defined for the s3 archive operation to communicate
with object storage:
    * OBJ_STORE_BUCKET
    * OBJ_STORE_SECRET
    * OBJ_STORE_USER
    * OBJ_STORE_HOST
    * SRC_ROOT_DIR (optional) - defaults to 'data'
    * OBJ_STORE_ROOT_DIR(optional) - defaults to 'snowpack_archive'
    * ROOTDIRECTORIES_OMIT(optional) - defaults to None

run the archive script (assume the dependencies have been installed):
`python snowpack_archive/runS3Backup.py`

# Mamba - Extra Info Details

Builds of the env in GHA were taking 2+ hours... then cancelled.  Mostly due to
slowness of conda, and that was rebuilding the env in GHA vs creating a lock
file and installing from lock.  The process out lined below does the build /
package conflict resolution using micromamba.  This speeds up the time required
to generate an env by several factors.

For local development the mm process creates an env called `ldev`
The gha creates an env called `snowpack_env`

All subsequent examples are for local development and use the env name `ldev`

## Build env using micromamba - fresh install
Build from environment.yaml
`micromamba create -y -n ldev --file environment.yaml`

Install other deps to conda env
```
pip install -r requirements.txt

# dev deps install
pip install -r requirements-dev.txt

# local hatfieldcmr package
pip install -e .
```

## Create Environment Lock File

The lock file persists the outcome of the package resolution that would have
taken place in the previous step.  Creating an env from the lock file is
significantly faster as it just installs packages vs calculating version
compatibility of packages and sub packages.

`micromamba env export -n ldev -e > explicit.lock`

## Create Environment from the Lock file

`micromamba create -n ldev -f explicit.lock -y`

## Activate and micromamba environment

`micromamba activate ldev`

## Upgrade a package and any dependencies

After this step has been completed and verified that it creates a stable env
that supports the snowpack processing code, then go back and [regenerate the
lock file](#create-environment-from-the-lock-file)

`mm install click=8.1.2 -n ldev -c conda-forge`


## Delete environment

Sometimes its easier to start from scratch

`mm env remove -n ldev`


# Misc Notes
# Docker

log into the image:
`docker run -v /home/kjnether/rfc_proj/snowpack/data_tmp:/data --env-file=.env -e "SNOWPACK_DATA=/data" -e "NORM_ROOT=/data" -it --entrypoint /bin/bash  snow:snow`

run the download script
`docker run -v /home/kjnether/rfc_proj/snowpack/data_tmp:/data --env-file=.env -e "SNOWPACK_DATA=/data" -e "NORM_ROOT=/data"  snow:snow python run.py download --date 2023.05.01 --sat viirs`

process the data
`docker run -v /home/kjnether/rfc_proj/snowpack/data_tmp:/data --env-file=.env -e "SNOWPACK_DATA=/data" -e "NORM_ROOT=/data"  snow:snow python run.py process --date 2023.05.01 --sat viirs`


get the available dates for processing
`docker run -v /home/kjnether/rfc_proj/snowpack/data_tmp:/data --env-file=.env -e "SNOWPACK_DATA=/data" -e "NORM_ROOT=/data"  snow:snow python get_available_data.py get-days-to-process --sat viirs`

backup data to object storage
`docker run -v /home/kjnether/rfc_proj/snowpack/data_tmp:/data --env-file=.env -e "SRC_ROOT_DIR=/data" -e "ROOTDIRECTORIES_OMIT=/data/kml,/data/norm"  snow:snow python snowpack_archive/runS3Backup.py`


docker run -it --entrypoint /bin/bash ghcr.io/bcgov/snow_analysis:latest
docker run -it --entrypoint /bin/bash  snow:snow


docker run -v /home/kjnether/rfc_proj/snowpack/data_tmp:/data --env-file=.env -e "SNOWPACK_DATA=/data" -e "NORM_ROOT=/data"  ghcr.io/bcgov/snow_analysis:latest python run.py 