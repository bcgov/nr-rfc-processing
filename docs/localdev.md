# Intro

describes getting a local development env up and running.

## WSL

All development moving forward will be completed on a linux based env.

## miniconda

run the following, then walk through the questions posed by the
miniconda installer

```
curl https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -o miniconda_install.sh
bash miniconda_install.sh
```

Then edit .bashrc adding the path to miniconda
```
export PATH=$PATH:~/miniconda3/bin
```

## Create the development conda env

the following may take a while... ~10 mins,
however after the env is created it can be re-used.

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

assume these cannot be installed using conda and that is why hatfield kept them
as separate installs.

```
pip install -r requirements.txt
pip install -e .
```

