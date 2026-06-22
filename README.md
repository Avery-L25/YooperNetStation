# SPRL_Observatory
Software module for operating a YooperNet Station. Intended for use with the following operations.
An all-sky imager checking for visibile aurora.
Data collection from a magnetometer, thermometer, and barometer.
Automatic file uploads.

## Requirements
_Ongoing decisions_
RaspberryPi with Rasbian installed
ZWO ASI Camera
Chip based magnetometer
Python >=3.12


## Installation/Setup
Installation Script in progress.

1. Clones the Github repository to the system (typically /home/[USER]/)
2. Run Setup/installer.py to update the system, download and install
   necessary packages/libraries, and setup the yoopernet service.
3. Configure toml file to customize camera settings, file locations, 
   and user data.
4. 

**Will need to put in google folder id**

## Usage
Intended to automatically run after setup. Will collect data to an **hdf5 file**. 
The YooperNet repository (link) offers operations to interpret data collected by the YooperNet station.
