#!/usr/bin/env python3

# sensor interfacing functions
from YooperCam import YooperCam
from Sensors.barom_therm_data_collection import temp_n_pres
from Sensors.mag_data import mag_data

# support functions
import pyzwoasi as pza
import os
import sys
import toml
import datetime
import time
import numpy as np
# import schedule
from ischedule import schedule, run_pending
from multiprocessing import Process


### Load Config Files
wkdir = os.getcwd()
config_file_path = wkdir + "/.YooperConfig.toml"
yoop_config = toml.load(config_file_path)

# ### Write Storage Locations
img_folder_path = wkdir + yoop_config['paths']['Camera_Images_Collection']    
# img_info_path = yoop_config['paths']['Camera_Info_File'] 
sensor_file_path = wkdir + yoop_config['paths']['Sensor_Data_Folder']
# google_folder_id = yoop_config['paths']['GDrive_Folder_ID']               #? If using hdf5 or uploading using python instead of RCLONE


# ### initializes scheduling
# schedule.every(5).seconds.do(data_processing)  # collect data every 5 seconds
# schedule.every().day.at("16:00").do(upload_data)  # upload hdf5 file at 4pm
# schedule.every().day.at("08:00").do(cam_off)  # turn camera off after 8am
# schedule.every().day.at("20:00").do(cam_off)  # turn camera on after 8pm

### Define Camera functions
def startCam():
    'Handles opening camera returnng the YooperCam object'

    # initialize camera
    YCamera = YooperCam(0)
    cam_working = False
    
    while cam_working is False:
        try:
            # take a test photo to ensure camera opened properly
            take_photo = YCamera.shot(exposure=1,return_img=True)
            if take_photo is not None:
                # This should not happen
                #! Log error/critical or other
                cam_working = True

        except pza.ASIError as zwo_error:
            # Grab error code
            error_code = zwo_error.args[1]

            if error_code == 4:
                # Camera did not open, try again
                YCamera = YooperCam(0)

            elif error_code == 16:
                # General error, liekly not problematic here
                #! log with warning
                cam_working = True

            elif error_code == 11:
                # Error grabbing exposure, likely image is too dark
                #! warning/error
                print(error_code)
                cam_working = True

            else:
                # Other errors needing additional diagnosis
                print(zwo_error)
                print("="*35 + "\n")
                sys.exit()
    
    #! Temporary fixes!!!
    YCamera.img_folder = img_folder_path

    # Return working camera
    return YCamera

def captureImage(expSec=30):
    '''
    Takes all sky images and save them. Writes data about the camera.
    '''

    global ycam
    
    print("Start Image capturing loop")
    
    try:
        ycam.shot(save=True, exposure=expSec)
        time.sleep(1)
    except pza.pyzwoasi.ASIError:
        print("Failed to get image, trying again.")
        # ycam.writeData()
        # add a wait, #? Should this be here or a class? Hand in hand with changing exposure.
    
    print('Capturing Finished')

def getSensorData():
    '''
    Get sensor data and write to appropriate file.
    TODO: Secondary MAG data
    '''
    

    while True:
        mag, pres, temp, gps = _readSensors()
        sensor_dict = {'Mag X':mag[0],'Mag Y':mag[1],'Mag Z':mag[2],
                    'Pressure':pres,'Temperature':temp,'GPS':gps}
        print(sensor_dict)
        time.sleep(5)

def _readSensors():
    '''
    Reads data from magnetometers, thermometer, barometer and returns their output.
    TODO: GPS
    '''

    mag = mag_data()
    temp, pres = temp_n_pres()
    gps = None  # todo complete gps code

    return mag, pres, temp, gps

def startStation():
    'Start data collection'
    ### Initialize Camera Object
    global ycam
    ycam = startCam()

    # Start sensor data collection
    sensors_proc = Process(target=getSensorData)
    sensors_proc.start()

    # Loop image capturing until stop condition is met
    #todo determine and implement a stop condition
    try:
        while True:
            captureImage(expSec=1)
            time.sleep(1)    
    except KeyboardInterrupt:
        sensors_proc.kill()
        print("Closing program")
    
    sensors_proc.join()
    # todo Log start time

    # Once processes end
    print("System operatation stopped.\nWaiting...")

### Start Camera, Sensors functions
# try:
if __name__ == '__main__':

    print("Starting YooperNet Station")
    print("==========================")
    print("\n"*3)

    # start the station for operation
    startStation()

    # run the program with period = 10 sec
    # schedule(timer, interval=2)
    # schedule(data_processing, interval=2)
    # run_loop(return_after=3)