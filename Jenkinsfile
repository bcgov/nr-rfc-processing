node('zavijava') {
    // ENVS to be set for this job
    //    * ENS_NETWORK_DRIVE
    //    * ENS_DRIVEMAPPING
    //    * ARTIFACTS
    //
    stage('checkout') {
        sh 'if [ ! -d "$TEMP" ]; then mkdir $TEMP; fi'
        checkout([$class: 'GitSCM', branches: [[name: "${env.TAGNAME}"]], doGenerateSubmoduleConfigurations: false, extensions: [[$class: 'SubmoduleOption', disableSubmodules: false, parentCredentials: true, recursiveSubmodules: true, reference: '', trackingSubmodules: false]], gitTool: 'Default', submoduleCfg: [], userRemoteConfigs: [[credentialsId: '607141bd-ef34-4e80-8e7e-1134b7c77176', url: 'https://github.com/bcgov/replication_health_check']]])
    }
    stage('configure drive mappings') {
    bat '''
        if NOT EXIST %ENS_DRIVEMAPPING%:\nul  (
            net use %ENS_DRIVEMAPPING%: %ENS_NETWORK_DRIVE% /PERSISTENT:YES /d
            @REM powershell -File ./mapdrives.ps1
        )

        IF NOT EXIST %RFC_ARTIFACTS_FOLDER% (
            echo creating the folder %RFC_ARTIFACTS_FOLDER% 
            mkdir %RFC_ARTIFACTS_FOLDER%
        )

        IF NOT EXIST %ENS_WEATHER_DATA% (
            echo creating the folder %ENS_WEATHER_DATA% 
            mkdir %ENS_WEATHER_DATA%
        )
        echo complete
        '''
    }
    stage('conda env setup') {
        // if check existence of a miniconda directory, if not then install
        // https://dev.to/waylonwalker/installing-miniconda-on-linux-from-the-command-line-4ad7

        // create a conda env directory on fileshare
        // install conda env
        //  conda env create --file environment.yaml --prefix $CONDAENVPATH
        bat '''
        SET PATH=%ARTIFACTS%\miniconda\condabin;%PATH%
        SET condaEnvPath=%ARTIFACTS%\rfc_conda_envs\nr-rfc-processing
        if NOT EXIST %condaEnvPath% (
            conda.bat env create --prefix %condaEnvPath% --file %condaEnvFilePath%
        )
        conda.bat activate %condaEnvPath%
        pip install -r requirements.txt
        pip install -e .
        conda.bat deactivate
        '''
    }
    stage('wgrib install') {
        // check if wgrib exe exists, if not then download source and install
        
    }
    stage('')

}
