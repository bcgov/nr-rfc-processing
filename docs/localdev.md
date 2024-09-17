# Intro

describes getting a local development env up and running.

# Install WSL

All development moving forward will be completed on a linux based env.
[Install WSL](https://learn.microsoft.com/en-us/windows/wsl/install) if not
already installed.

# Configure Environment Variables

The scripts retrieve the following secrets from the environment:
* object store - username, password, host etc
* sentinal data - username password
* earth data - username password

Before you can run the scripts you must populate these environment variables:
* OBJ_STORE_BUCKET
* OBJ_STORE_SECRET
* OBJ_STORE_USER
* OBJ_STORE_HOST
* SRC_ROOT_DIR (optional) - defaults to 'data'
* OBJ_STORE_ROOT_DIR(optional) - defaults to 'snowpack_archive'
* ROOTDIRECTORIES_OMIT(optional) - defaults to None, these are directories to not include
    when syncing data to object storage.  They are sub directories in the SRC_ROOT_DIR.
    see the github action run_pipeline_auto_fill_data.yaml for an example.

For quick access you can populate these parameters into a .env file.  The gitignore
is already configured to ignore this file.  Then to populate the secrets from that
file you can run:

`set -a; source .env; set +a`

# Configure / Install Dependencies using Micromamba

This step is mostly for the situation where you want to add new features to the scripts.
If you just want to run them locally, its likely a lot easier to build and run the images
defined in the `Dockerfile`

Builds of the env in GHA were taking 2+ hours... then cancelled.  Mostly due to
slowness of conda, and that was rebuilding the env in GHA vs creating a lock
file and installing from lock.  The process out lined below does the build /
package conflict resolution using micromamba.  This speeds up the time required
to generate an env by several factors.

For local development the mm process creates an env called `ldev`
The gha creates an env called `snowpack_env`

All subsequent examples are for local development and use the env name `ldev`

## Create Micromamba Environment, and install dependencies

Create mamba env from the environment.yaml definition.  This step only needs
to be run when either setting up a new computer, or if the dependency
declarations have changed.  Once created you should be able to just activate the
environment, and re-use.

`micromamba create -y --prefix ./ldev --file environment.yaml`

Having created an environment the next step is to activate it, before you add the
additional dependencies.

Activate the environment
`micromamba activate ./ldev`

Install other deps to conda env
```
pip install -r requirements.txt

# dev deps install
pip install -r requirements-dev.txt

# local hatfieldcmr package
pip install -e .
```

At this stage you should be done, and able to run the scripts in this repo.  Subsquent
sections add additional information about the micromamba environment.

## Create Environment Lock File

The lock file persists the outcome of the package resolution that would have
taken place in the previous step.  Creating an env from the lock file is
significantly faster as it just installs packages vs calculating version
compatibility of packages and sub packages.

before executing make sure that the environment is activated
`micromamba activate ./ldev`

`micromamba env export --prefix ./ldev -e > explicit.lock`

## Create Environment from the Lock file

Previous examples that created an environment from environment.yaml, will figure out
the version compatibility.  If you have already done this, and have created a lock file
you can recreate the environment much more quickly with the following command which
installs the versions defined in the lock.

`micromamba create --prefix ./ldev -f explicit.lock -y`

## Upgrade a package and any dependencies

After this step has been completed and verified that it creates a stable env
that supports the snowpack processing code, then go back and [regenerate the
lock file](#create-environment-from-the-lock-file)

`mm install click=8.1.2 --prefix ./ldev -c conda-forge`

## Delete environment

Sometimes its easier to start from scratch

`mm env remove --prefix ./ldev`

# Running Scripts

Having [created and activated an micromamba environment](#configure--install-dependencies-using-micromamba), and
[setting the various environment variables](#define-object-store-environment-variables),
you should now be in a position to run the various scripts that make up the snowpack
analysis.

In a nutshell the scripts do the following things:
1. build the required directory and data structures
1. download the data from the various earth data sources
1. process / analyze / coallate the data
1. archive the data to S3 Storage.

## Run build process

This creates the basin / watershed directories, and boundaries that are used to clip the
various data sets that get created by the scripts.  This must be run at least once
before any of the subsequent processes are run.

`python run.py build`

## Run download process

This will reach out to the earthdata portal, and download the data for the specified
date and satellite if it is available.

prerequisite: build

`python run.py download --date 2024.06.17 --sat viirs`

# Run data processing

This step will process the data that was downloaded in the previous step.

prerequisite: download

`python run.py process --date 2024.06.17 --sat viirs`

# Run the plot creation

This step will generate plots for the data that was analyzed by the process step.

prerequisite: download

`python run.py plot --date 2024.06.17 --sat viirs`

# Archive the data from to object storage

This step will compare the data in object store with the data that has been downloaded,
processed, and plotted, updating the object store where holes are found.  The days
back is usually ok to omit and leave with defaults (20 days), however when recovering
from a deactivation of the script and big data holes, you may want to increase this
parameter.

This step is usually run after any local data processing is complete

`python snowpack_archive/runS3Backup.py --days_back 120`

# Identify satellite and date combinations to run

This script is run in the github action.  Its not required if you are only manually running
a single date, unless you are trouble shooting issues with it.

The script will start by looking at the most recent data that exists in object storage,
Once it determines the most recent day of data in object storage it starts to query days
after that in the earthdata portal, until it either gets to the current date, or finds
a day with no data.

When data holes occur (days with no data, but subsequent data after), you will need to
run the download/process/plot/sync processes on the day that the data population resumes.

Taking the most recent example, where a hole in the data was found for 2024.07.10 through
to 2024.07.15.  Running manually on my local machine the data for 2024.07.16 and pushing
the data up to object store, will then allow the scheduled job to pick up the remainder
of the processing time from that date forward.

`python get_available_data.py`

# Docker

These steps demonstrate how to run the exact same processes as above only using the docker
images.  This can be useful for debugging the gha processes that use the docker images.

### Mapping data drives:

In the processes below that include the following clause
`... /home/kjnether/rfc_proj/snowpack/data_tmp:/data` this is telling docker to map the
folder /home/kjnether/rfc_proj/snowpack/data_tmp to /data inside the docker image.  When
any processes are run the contents of that local folder will be visible through the path
/data.

### Environment Variables

You will also notice the lines: `--env-file=.env`, this is telling docker to read that
.env file and populate the variables that are described in it, inside the docker
container.

You will also see after the `--env-file=.env` the clauses `-e "SNOWPACK_DATA=/data"`. If these
lines are included after the --env-file clause they will overwrite any values that were
defined in the file.

### Running commands in Docker

#### create the docker image.

`docker build -t snow:snow .`

#### Log into the image.

If there are problems with the docker image this will produce a shell
inside of the docker image that allows you to navigate through the directory structure and
run processes, in that image to try to identify what the problem might be.

`docker run -v /home/kjnether/rfc_proj/snowpack/data_tmp:/data --env-file=.env -e "SNOWPACK_DATA=/data" -e "NORM_ROOT=/data" -it --entrypoint /bin/bash  snow:snow`

#### Get the available dates for processing

`docker run -v /home/kjnether/rfc_proj/snowpack/data_tmp:/data --env-file=.env -e "SNOWPACK_DATA=/data" -e "NORM_ROOT=/data"  snow:snow python get_available_data.py get-days-to-process --sat viirs`

#### Run the download script

`docker run -v /home/kjnether/rfc_proj/snowpack/data_tmp:/data --env-file=.env -e "SNOWPACK_DATA=/data" -e "NORM_ROOT=/data"  snow:snow python run.py download --date 2024.06.10 --sat viirs`

#### Process the data

`docker run -v /home/kjnether/rfc_proj/snowpack/data_tmp:/data --env-file=.env -e "SNOWPACK_DATA=/data" -e "NORM_ROOT=/data"  snow:snow python run.py process --date 2023.05.01 --sat viirs`

#### Plot the data

`docker run -v /home/kjnether/rfc_proj/snowpack/data_tmp:/data --env-file=.env -e "SNOWPACK_DATA=/data" -e "NORM_ROOT=/data"  snow:snow python run.py plot --date 2023.05.01 --sat viirs`

#### backup data to object storage

`docker run -v /home/kjnether/rfc_proj/snowpack/data_tmp:/data --env-file=.env -e "SRC_ROOT_DIR=/data" -e "ROOTDIRECTORIES_OMIT=/data/kml,/data/norm"  snow:snow python snowpack_archive/runS3Backup.py --days_back 120`

# Trouble shooting the image built in github

The following command demonstrates how you can run the image stored in the github
container registry that is used by the github actions, on a local machine.

`docker run --rm -v /home/kjnether/rfc_proj/snowpack/data_tmp:/data --env-file=.env -e "SNOWPACK_DATA=/data" -e "NORM_ROOT=/data"  ghcr.io/bcgov/snow_analysis:latest python run.py download --date 2023.06.11 --sat viirs`

