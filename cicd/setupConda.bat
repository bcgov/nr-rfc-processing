
if NOT EXIST %condaEnvPath% (
    conda.bat env create --prefix %condaEnvPath% --file %condaEnvFilePath%
)
conda.bat activate %condaEnvPath%
pip install -r requirements.txt
pip install -e .
conda.bat deactivate
