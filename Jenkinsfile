node('zavijava_rfc') {
    // ENVS to be set for this job
    //    * ENS_NETWORK_DRIVE
    //    * ENS_DRIVEMAPPING
    //    * RFC_ARTIFACTS_FOLDER
    //
    stage('checkout') {
        //sh 'if [ ! -d "$TEMP" ]; then mkdir $TEMP; fi'
        checkout([$class: 'GitSCM', branches: [[name: '$TAGNAME']], extensions: [], userRemoteConfigs: [[url: 'https://github.com/bcgov/nr-rfc-processing']]])    
    }
    stage('configure drive mappings') {
    bat '''
        if NOT EXIST %RFC_DRIVEMAPPING%:\\nul  (
            net use %RFC_DRIVEMAPPING%: %RFC_NETWORK_DRIVE% /PERSISTENT:NO /d
            @REM powershell -File ./mapdrives.ps1
        )

        IF NOT EXIST %RFC_ARTIFACTS_FOLDER% (
            echo creating the folder %RFC_ARTIFACTS_FOLDER% 
            mkdir %RFC_ARTIFACTS_FOLDER%
        )

        echo complete

        :: print the network mappings
        net use
        '''
    }
    stage('conda env setup') {
        // if check existence of a miniconda directory, if not then install
        // https://dev.to/waylonwalker/installing-miniconda-on-linux-from-the-command-line-4ad7

        // create a conda env directory on fileshare
        // install conda env
        //  conda env create --file environment.yaml --prefix $CONDAENVPATH
        bat '''
        SET PATH=%RFC_ARTIFACTS_FOLDER%\\miniconda\\condabin;%PATH%
        SET condaEnvPath=%RFC_ARTIFACTS_FOLDER%\\rfc_conda_envs\\nr-rfc-processing
        SET condaEnvFilePath=%WORKSPACE%\\environment.yaml

        echo RFC_ARTIFACTS_FOLDER %RFC_ARTIFACTS_FOLDER%
        echo condaEnvPath %condaEnvPath%
        echo condaEnvFilePath %condaEnvFilePath%

        if NOT EXIST %condaEnvPath% (

            conda.bat env create --prefix %condaEnvPath% --file %condaEnvFilePath%
        )
        conda.bat activate %condaEnvPath%
        pip install -r requirements.txt
        pip install -e .
        conda.bat deactivate
        '''
    }
    stage('run snowpack analysis') {
        // 
        bat '''
            SET CONDABIN=%RFC_ARTIFACTS_FOLDER%\\miniconda\\condabin
            SET condaEnvPath=%RFC_ARTIFACTS_FOLDER%\\rfc_conda_envs\\nr-rfc-processing
            SET PATH=%CONDABIN%;%PATH%

            call conda.bat activate %condaEnvPath%

            cd nr-rfc-processing
            pip install -r .\\requirements.txt

            # ----------------------------------------------
            echo env var param is: %SNOWPACK_ENVS_PTH%
            echo SNOWPACK_SECRETS: %SNOWPACK_SECRETS%

            %condaEnvPath%\\python run.py daily-pipeline --envpth=%SNOWPACK_SECRETS% --date 2021.03.15
        '''
    }
}
