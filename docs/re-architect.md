# Overview

Current implementation does a LOT of different things.  With all the various
tasks that get completed by the dailyupdate process, failures are likely.

# Future Direction

Dissect daily pipeline into smaller steps processes.  Can piggy back on the
steps that have already been laid out in the run.py.  Some ideas around how
to break it down:

1. prepare directories (create the shape files)
2. download data - (specific provider: modis, viirs)
    * checks to see if data already exists in the object store
    * if not, checks to see if data is available for the range
    * error generated if no data available for all the date ranges provided
3. Process data
    * think this step breaks up the data into the various basins
    * load the object store data on an as needed basis

4. Upload data
    * What results from the processing should be uploaded back to object store

5. Reporting
    * generation of the various images (maps/charts)
    * Haven't dug in too deep, but suspect this step might require all the
      data to be processed.  Either way want to be able define each of these
      steps individually into gha.

6. upload reports
    * essentially persistence for the reports generated.

Other considerations:
* think about what data needs to be persisted... raw downloaded imagery, mosaics
  processed data, etc.


* Long term, can we pull together a report using obj store and ghp that
  publishes the information.

...


* potentially break up the pipelines to satellite type
    * modis download
    * process
    * reporting (creation of charts etc)

# Running specific steps

The following is some of the code that can be used to run specific steps /
chunks described above.


download modis:
`python run.py download --sat modis --envpth=$SNOWPACK_ENVS_PTH --date 2023.02.16`

process modis:
`python run.py process --sat modis --date 2023.02.16`

download viirs:
`python run.py download --sat modis --envpth=$SNOWPACK_ENVS_PTH --date 2023.02.16`
