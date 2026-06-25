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
