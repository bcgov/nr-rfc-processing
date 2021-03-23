# Setup / Install

## Environment Variables

PATH                - Add the path to the miniconda condabin folder
condaEnvPath        - path to where the conda environment will be created
condaEnvFilePath    - path to the environment.yaml file
SNOWPACK-DATA       - Where the snowpack data will be located



## Create Conda Environment

Extracted the install instructions from the docker file so that the 
processing scripts can be run on bare metal windows box with mimimal of 
pre installed software.  Setup borrows heavily from the artifacts used in 
the [ensemble weather project](https://github.com/bcgov/nr-rfc-ensweather)

Run the cicd/setupConda.bat
requires the following environmen









Notes on steps required to get this code deployed on jenkins

a) figure out steps to build the conda env
   - potentially translate to conda env.yaml
   - simply install to:
     `conda env create --prefix <conda env location> --file <conda env file> `

b) get running locally

c) translate to remote


Questions:
  * why not create a 