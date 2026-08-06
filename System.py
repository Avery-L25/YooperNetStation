# !/usr/bin/env python3

'''
Script to run the prototype YooperNet Observational Station.
Will use configurations set in the \'.YooperConfig.toml\' file.

Primary Functions
-----------------
Taking All-Sky Images
    Methods are primarily held in \'YooperCam.py,\' this script manages the
    frequency of the image capturing.
Magnetometer Data
    Collects data from a chip-based moldwin magnetometer an several other
    sensors including a thermometer and barometer.
Writing to CSVs
    Data is written to two files; a camera file and a sensor file.
    These files are used to account for the different frequencies of
    data collection.
Uploading Files
    Uploads data using to google drive using \'rclone.\' rclone should be
    configured before running the station.


Can be called using startStation() if using a seperate script.
'''

import os
from os import path
import sys
import toml
import logging
import time
import datetime as dt
from copy import copy
from multiprocessing import Process
import cv2 as cv  # Image management
import pyzwoasi as pza  # Camera Library
from YooperCam import YooperCam  # Camera Interface for YooperNet
from auroral_image_check import AuroraImage  # Image masking
from Sensors.barom_therm_data_collection import temp_n_pres
from Sensors.mag_data import mag_data
import filemanager as fman

# region Initialize Variables
# Get working directory and repository directory
wkdir = path.dirname(path.realpath(__file__))

# Load Config Files
yoop_config = toml.load(path.join(wkdir, ".YooperConfig.toml"))

# Get Storage Locations
yoop_paths = yoop_config['paths']
general_img_folder = path.join(wkdir, yoop_paths['Images_Folder'])
hdf_folder = path.join(wkdir, yoop_paths['HDF5_Folder'])
log_folder = path.join(wkdir, yoop_paths['Log_Folder'])
# ? If using hdf5 or uploading using python instead of RCLONE
# google_folder_id = yoop_config['paths']['GDrive_Folder_ID']
img_folder = general_img_folder
sensor_file = 'test.hdf5'

# Get Storage Formats
yoop_form = yoop_config['formats']
image_folder_format = path.join(general_img_folder,
                                yoop_form['Image_Folder_Format'])
image_file_format = (yoop_form['Image_Name_Format'] +
                     yoop_form['Image_Extension'])
camera_file_format = path.join(hdf_folder, yoop_form['Camera_Info_Format'])
sensor_file_format = path.join(hdf_folder, yoop_form['Sensor_Data_Format'])
log_file_format = path.join(log_folder, yoop_form['Log_File_Format'])

# Initialize System Variables
yoop_aurora = yoop_config['aurora']
HIGH_IMG_RATE = yoop_aurora['Aurora_CapRate']
LOW_IMG_RATE = yoop_aurora['No_Aurora_CapRate']
AURORA_THRESHOLD = yoop_aurora['Aurora_MSE_Threshold']
AFTER_FLAG_TIME = yoop_aurora['Detection_After_Time']
exposure_time = 30
image_rate = HIGH_IMG_RATE
sensor_feed_rate = yoop_config['sensors']['Data_Rate']


# initializes scheduling # ! Implement for Uploading
# import schedule
# schedule.every(5).seconds.do(data_processing)  # collect data every 5 seconds
# schedule.every().day.at("16:00").do(upload_data)  # upload hdf5 file at 4pm
# schedule.every().day.at("08:00").do(cam_off)  # turn camera off after 8am
# schedule.every().day.at("20:00").do(cam_off)  # turn camera on after 8pm

# Log
logging.basicConfig()
DEBUG2 = 11
HIGH_DEBUG = 24
DATA = 28

# Add logging levels
logging.addLevelName(DEBUG2, "DEBUG2")
logging.addLevelName(HIGH_DEBUG, "HIGH_DEBUG")
logging.addLevelName(DATA, "DATA")

log = logging.getLogger("auraCheck")
log.setLevel(level=30)
# endregion


def startCam():
    '''
    Handle opening the camera, returning the YooperCam object.
    Designed to handle common errors such as a closed camera.
    '''

    # initialize camera
    YCamera = YooperCam(0)
    cam_working = False

    while cam_working is False:
        try:
            # take a test photo to ensure camera opened properly
            take_photo = YCamera.shot(exposure=1, return_img=True)
            if take_photo is not None:
                # This should not happen
                # ! Log error/critical or other
                cam_working = True

        except pza.ASIError as zwo_error:
            # Grab error code
            error_code = zwo_error.args[1]

            if error_code == 4:
                # Camera did not open, try again
                YCamera = YooperCam(0)

            elif error_code == 16:
                # General error, liekly not problematic here
                # ! log with warning
                cam_working = True

            elif error_code == 11:
                # Error grabbing exposure
                # Usually occurs if the image was too dark
                # To be expected with the short exposure
                # ! warning/error
                print(error_code)
                cam_working = True

            else:
                # Other errors needing additional diagnosis
                # ! error/critical
                print(zwo_error)
                print("="*35 + "\n")
                sys.exit()

    # ! Temporary fixes!!!
    YCamera.img_folder = img_folder

    # Return working camera
    return YCamera


def captureImage(expSec=30):
    '''
    Capture an all sky image, write to storage location,
    write data about camera, and runs a check for aurora.

    Parameters
    ----------
    expSec: int
        The camera exposure time in seconds. This is for adjustment within
        this script
    '''
    log.debug("Start Image capturing")
    global current_image, previous_image, aurora_flag

    # Get previous image for comparison
    try:
        previous_image = copy(current_image)  # type: ignore
    except NameError:
        log.debug('No current image to copy')
        pass

    # Take photo
    try:
        sky_img = ycam.shot(return_img=True, exposure=expSec)
    except pza.pyzwoasi.ASIError:
        # todo add error handling
        log.error("Failed to get image, trying again.")

        return None

    current_image = AuroraImage(sky_img)
    cv.imwrite(path.join(img_folder,
                         dt.datetime.now(dt.UTC).strftime(image_file_format)),
               sky_img)

    # Run aurora check/screen
    try:
        aurora_flag = current_image - previous_image
        updateCaptureRate(aurora_flag)
    except NameError as ne_args:
        log.debug(ne_args)
    except KeyError as ke:
        log.error(f'Key for image comparison mask \'{ke}\' not found.')

    log.debug('Capturing Finished')


def getSensorData():
    '''
    Get sensor data and collection time.
    Write data to HDF5 file.
    Wait at appropriate rate.

    TODO: Second magnetometer data collection
          GPS data collection
    '''
    while True:
        # Read data into dictionary
        mag, pres, temp, gps = _readSensors()

        # HDF5 needs time as string
        sens_time = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
        sensor_dict = {'Time': sens_time, 'Mag': mag, 'Pressure': pres,
                       'Temperature': temp}
        # add {'GPS': gps} after code functions

        log.debug(f"Sensor data written at {sens_time}")

        # Write dictionary to file
        fman.hdf(sensor_file, sensor_dict)

        # Collect data at configured rate
        time.sleep(sensor_feed_rate)


def _readSensors():
    '''
    Reads data from magnetometers, thermometer, and barometer
    then returns their output.

    TODO: GPS
    '''

    # Moldwin Magnetometer Data
    mag = mag_data()

    # Adafruit Thermometer and Barometer
    temp, pres = temp_n_pres()

    # GPS code is not complete
    gps = None  # todo complete gps code

    return mag, pres, temp, gps


def uploadData(folder='', path=path.join(wkdir, 'Data'), move=True,
               doUpload=True, flag=''):
    '''
    Upload from the station to a setup remote drive using rclone.
    TODO: Support uploading when storage is getting full.

    Parameters
    ----------
    folder: str, defaults to \'\'
        Name of folder to be uploaded, retains name when uploaded.
    path: str, defaults to \'YooperNet/Data\'
        Path to the files that need to be updated. Uploads everything in
        the 'Data' directory by default.
    move: bool, defaults to True
        If true, rclone will copy the files to drive and delete
        them automatically after a succesful upload. Otherwise, it will
        only copy files.
    doUpload: bool, defaults to True
        If true, upload without checking for any flags/parameters.
        This is intended for end-of-day uploads.

    Examples
    --------
    Upload Data in YooperNet/Data/Images to remote.
    This includes files and subdirectories
    YooperNet/Data/Images/ |- 12-05-26_images/morning
                            |- 12-06-26_images/*
                            |- 12-06-26_23-59-00.png
    >>> uploadData(folder='Images')
    YooperNet/Data/Images/

    '''

    # Get storage information
    station_Gb, total_used, station_used = fman.dataSize(wkdir)

    if doUpload is True:
        fman.rclone(move=move, path=path, folder=folder)

    # Check if a flag is met # todo Figure out if this is necessary
    if doUpload is False:
        # ! log that a flag was checked
        if flag == '':
            print(f"GB used: {station_Gb}\nStorage used: {station_used}%\n"
                  f"Total storage used: {total_used}%")
        elif flag.lower() in ['gb', 'station gb', 'data size', 'size']:
            pass

    # todo Function


def updateCaptureRate(aurora_mse):
    '''
    Update the frequency of photos capture by the station.
    '''
    global image_rate

    if aurora_mse > AURORA_THRESHOLD:
        image_rate = HIGH_IMG_RATE
    else:
        image_rate = LOW_IMG_RATE

    pass


def getStorageLocations():
    '''
    Set the storage locations for images, hdf5 files, and log file.
    '''
    global sensor_file, img_folder, camera_file, log_file

    def makePath(format):
        # Get path for the correct data
        fpath = dt.datetime.now(dt.UTC).strftime(format)

        if os.path.exists(fpath) is False:
            # Create path if it doesn't exists
            if fpath.partition('.')[-1] == '':
                # if directory passed, make full directory
                os.makedirs(fpath)
            else:
                # if a file is passed, make path to file
                os.makedirs(fpath.rpartition('/')[0])

        # return formatted path
        return path.realpath(fpath)

    # Get working paths
    img_folder = makePath(image_folder_format)
    camera_file = makePath(camera_file_format)
    sensor_file = makePath(sensor_file_format)
    log_file = makePath(log_file_format)


def startStation():
    '''
    Run the station starting the process of collecting sensors data and
    capturing all sky images.

    TODO: Is it necessary to stop collection to upload? This is a serious issue
        if necessary at night. Data should not get too large in a single night.
    '''
    # Initialize Camera Object
    global ycam
    ycam = startCam()

    # Start sensor data collection
    sensors_proc = Process(target=getSensorData)
    sensors_proc.start()

    # Loop image capturing until stop condition is met
    # todo determine and implement a stop condition
    try:
        while True:
            # ! This should encapsulate taking the photo, logging, and analysis
            before = time.time()
            captureImage(expSec=1)
            after = time.time()

            # sleep however long is needed before
            sleep_for = image_rate - (after - before)
            if sleep_for > 0:
                time.sleep(sleep_for)
    except KeyboardInterrupt:
        # Stop the sensors if manually killed
        sensors_proc.kill()
        print("Closing program")

    # wait for the sensors to finish their loop before finishing
    sensors_proc.join()
    # todo Log start time

    # Once processes end
    print("System operatation stopped.\nWaiting...")


# ## Start Camera, Sensors functions
if __name__ == '__main__':

    print("Starting YooperNet Station")
    print("==========================")
    print("\n"*3)

    # start the station for operation
    getStorageLocations()
    startStation()

    # run the program with period = 10 sec
    # from ischedule import schedule, run_pending
    # schedule(timer, interval=2)
    # schedule(data_processing, interval=2)
    # run_loop(return_after=3)
