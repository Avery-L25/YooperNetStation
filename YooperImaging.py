#!/usr/bin/env python3

# sensor interfacing functions
from YooperCam import YooperCam

# support functions
import pyzwoasi as pza
import os
import sys
import toml
import datetime
import time
import numpy as np
# import schedule


### Load Config Files
wkdir = os.getcwd()
config_file_path = wkdir + "/.YooperConfig.toml"
yoop_config = toml.load(config_file_path)

# ### Write Storage Locations
# img_folder_path = yoop_config['paths']['Camera_Images_Folder']    
# img_info_path = yoop_config['paths']['Camera_Info_File'] 
# sensor_file_path = yoop_config['paths']['Sensor_Data_File']
# google_folder_id = yoop_config['paths']['GDrive_Folder_ID']               #? If using hdf5 or uploading using python instead of RCLONE


# ### initializes scheduling
# schedule.every(5).seconds.do(data_processing)  # collect data every 5 seconds
# schedule.every().day.at("16:00").do(upload_data)  # upload hdf5 file at 4pm
# schedule.every().day.at("08:00").do(cam_off)  # turn camera off after 8am
# schedule.every().day.at("20:00").do(cam_off)  # turn camera on after 8pm

### Define Camera functions
def captureImage(expSec=30):
    '''
    Takes all sky images and save them. Writes data about the camera.
    '''
    global ycam
    print("Start Image captureing loop")
    while True:
        try:
            ycam.shot(save=True, exposure=expSec)
            time.sleep(1)
        except pza.pyzwoasi.ASIError:
            print("Failed to get image, trying again.")
        # ycam.writeData()
        # add a wait, #? Should this be here or a class? Hand in hand with changing exposure.
    
    print('Capturing stopped')


### Start Camera, Sensors functions
# try:
if __name__ == '__main__':

    ### Initialize Camera Object
    print("Starting YooperCam")
    ycam = YooperCam(0)                                                         #! This likely will need to incorporate error handling/pza lib

    try:
        while True:
            time.sleep(1)
            pass
    except KeyboardInterrupt:
        print("Closing program")
    # todo Log start time

    # Once processes end
    print("Camera Stopped.\nWaiting...")
