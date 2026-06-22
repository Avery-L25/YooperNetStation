#!/usr/bin/env python3

# sensor interfacing functions
from Sensors.barom_therm_data_collection import temp_n_pres
from Sensors.mag_data import mag_data
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
from multiprocessing import Process

### Initialize Camera Object
ycam = YooperCam(0)                                                         #! This likely will need to incorporate error handling/pza lib

### Load Config Files
wkdir = os.getcwd()
config_file_path = wkdir + "/.YooperConfig.toml"
yoop_config = toml.load(config_file_path)

### Write Storage Locations
img_folder_path = yoop_config['paths']['Camera_Images_Folder']    
img_info_path = yoop_config['paths']['Camera_Info_File'] 
sensor_file_path = yoop_config['paths']['Sensor_Data_File']
# google_folder_id = yoop_config['paths']['GDrive_Folder_ID']               #? If using hdf5 or uploading using python instead of RCLONE


# ### initializes scheduling
# schedule.every(5).seconds.do(data_processing)  # collect data every 5 seconds
# schedule.every().day.at("16:00").do(upload_data)  # upload hdf5 file at 4pm
# schedule.every().day.at("08:00").do(cam_off)  # turn camera off after 8am
# schedule.every().day.at("20:00").do(cam_off)  # turn camera on after 8pm

### Define Station functions
def captureImage():
    '''
    Takes all sky images and save them. Writes data about the camera.
    '''
    global ycam
    print("Start Image captureing loop")
    while True:
        try:
            ycam.shot(save=True)
        except pza.pyzwoasi.ASIError:
            print("Failed to get image, trying again.")
        # ycam.writeData()
        # add a wait, #? Should this be here or a class? Hand in hand with changing exposure.
    
    print('Capturing stopped')

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

### Start Camera, Sensors functions
try:
    if __name__ == '__main__':
        print("Starting YooperNet Station")
        Process(target=captureImage).start()                                #* Set the target to be whichever method needs to be run
        Process(target=getSensorData).start()                            #todo Can add a stop condition controlled by the file manager
        # Process(target=).start()                                       #todo stopping to reset file names or something else   
        # todo Log start time
except KeyboardInterrupt:
    print('\nUser quit\n')
    # todo Add log entry
