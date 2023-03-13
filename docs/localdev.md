# Intro

describes getting a local development env up and running.

## WSL

All development moving forward will be completed on a linux based env.
[Install WSL](https://learn.microsoft.com/en-us/windows/wsl/install) if not
already installed.

## Miniconda

Run the following, then walk through the questions posed by the miniconda
installer

```
curl https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -o miniconda_install.sh
bash miniconda_install.sh
```

Then edit .bashrc adding the path to miniconda
```
export PATH=$PATH:~/miniconda3/bin
```

## Create the development conda env

the following may take a while... ~10 mins, however after the env is created it
can be re-used.

```
# initiallize the conda env
conda init bash
conda env create --prefix ldev --file environment.yaml
```

## Activate the environment

```
conda activate ./ldev
```

## Install the remaining dependencies

Not sure why these were not included in the conda environment.yaml??  However
this is what hatfield did to get the env built.  In a nutshell after the conda
env has been created and activated run pip on top of to install the final
list of dependencies.

```
pip install -r requirements.txt
pip install -e .
```

## Install dev dependencies (optional)

If you just need to run the code, you can skip these steps, however if you are
doing further development you should install these deps.

```
pip install -r requirements-dev.txt
```

## Update conda

After modifying the environment.yaml, update conda env
`conda env update --file environment.yaml --prune`

## Environment Variables

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

## Running the daily pipeline script:

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

## run the archive / s3 backup / save operation

### set the following env vars:
    * OBJ_STORE_BUCKET
    * OBJ_STORE_SECRET
    * OBJ_STORE_USER
    * OBJ_STORE_HOST
    * SRC_ROOT_DIR (optional) - defaults to 'data'
    * OBJ_STORE_ROOT_DIR(optional) - defaults to 'snowpack_archive'
    * ROOTDIRECTORIES_OMIT(optional) - defaults to None

run the archive script (assume the dependencies have been installed):
`python snowpack_archive\runS3Backup.py`