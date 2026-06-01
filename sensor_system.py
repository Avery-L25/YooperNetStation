#!/usr/bin/env python3

# import necessary libraries
import os
import datetime
import time
import numpy as np
import schedule
from Data_processing.image_processing import Image
from Data_processing.hdf import hdf
from Data_processing.transmission.file_transmission_2 import upload_file_to_drive
from Data_processing.visualizer import Live_plotting

from Sensors.barom_therm_data_collection import temp_n_pres
from Sensors.mag_data import mag_data
from Sensors.camera.main import shot

# Variable initialization
T = 10  # When to take image
camera_period = 300  # a counter for camera's period
img = Image(np.zeros((512, 512, 3)))  # blank image
cur_day = datetime.datetime.now(datetime.timezone.utc)
cameraoff = False  # when True camera will not take picutre during the day
# ! live_plot = Live_plotting()

# Working directory and file
wdir = os.getcwd()
folder = cur_day.strftime('%y%B')
if cur_day.hour >= 20:
    hdf_file = cur_day.strftime('%d_%m_%y.hdf5')
else:
    cur_day = cur_day - datetime.timedelta(1)
    hdf_file = cur_day.strftime('%d_%m_%y.hdf5')

# GOOGLE AUTHORIZATION
folder_id = "1vgaHd2zrHlnLKV55_ARNKjABrqwS_hxM"


# todo 2 paths? the raspi and the one on 


def get_direcs():  # Get working file
    '''
    Calculates the working file name based on UTC time.
    If it is after 4pm UTC a new file name is created for the current day.
    If it is before 4pm UTC the file is the prior day.
    '''
    global folder, hdf_file, cur_day, old_file
    now = datetime.datetime.now(datetime.timezone.utc)
    cur_day = now - datetime.timedelta(1)
    old_day = now - datetime.timedelta(2)
    
    folder = now.strftime('%y%B')
    if now.hour >= 20:
        hdf_file = now.strftime('%d_%m_%y.hdf5')
        old_file = old_day.strftime('%d_%m_%y.hdf5')
    else:
        cur_day = now - datetime.timedelta(1)
        older_day = cur_day - datetime.timedelta(2)
        hdf_file = cur_day.strftime('%d_%m_%y.hdf5')
        old_file = older_day.strftime('%d_%m_%y.hdf5')


def cam_off():  # Turn off the cam
    '''
    Used to turn the camera on/off dependant on the time of day.
    Currently on between 12pm and 7 pm if the function is called.
    '''

    global cameraoff, camera_period
    curtime = datetime.now()
    if curtime.hour > 7 and curtime.hour < 12:
        cameraoff = True
        print('CAMERA OFF')
    else:
        cameraoff = False
        camera_period = 300
        print('CAMERA ON')


def read_data(cam_flag):  # Read data from sensors and camera
    '''
    Runs all the sensors functions to collect data.
    Tales pictures if the cam_flag is true.
    '''

    mag = mag_data()
    temp, pres = temp_n_pres()
    gps = None  # todo complete gps code

    if cam_flag:  # takes an image if the camera period is complete
        img = shot()
    else:
        img = np.zeros((512, 512, 3), dtype=np.uint8)
    return mag, pres, temp, gps, img


def check_aurora(img):

    global T
    # Check if there us an aurora present
    is_aurora = img.aurora_detection()  # is there an aurora present
    if is_aurora is True:  # if yes, camera takes a photo every 10 seconds
        T = 10
        print('aurora present')
    elif is_aurora is False:  # if no, camera takes a photo every 5 minutes
        T = 300
        print('no aurora')

    return is_aurora


def upload_data():  # Upload data to Google Drive
    '''
    Upload data to the 
    '''
    global hdf_file, folder_id, old_file # ! add path on server
    # if glob.glob("*.hdf5"):
    print('uploading data to the ... google drive')
    upload_file_to_drive(hdf_file, folder_id)
    os.remove(old_file)
    get_direcs()


    # ! ensure that the delete flag is here unless addressed seperately


def data_processing():  # Collects data, looks for Aurora, Makes HDF
    '''
    Processes data from all sensors and writes it to hdf5 file.
    Determines whether it is time to take a picture.
    Detects an Aurora and updates the camera period accordingly.
    '''
    global T, camera_period, cameraoff, hdf_file # ! live_plot
    if cameraoff is True:
        cam_flag = False
    elif camera_period >= T:  # it the time to take picture
        camera_period = 0
        cam_flag = True
    else:
        camera_period += 5  # update counter by the run period
        cam_flag = False

    # for testing
    print(f"T = {T}\ncamera period = {camera_period}\ncamflag = {cam_flag}")

    mag, pres, temp, gps, img.img = read_data(bool(cam_flag))
    img.resize()
    if cam_flag is True:
        is_aurora = check_aurora(img)
        img.pre = img.img
    else:
        is_aurora = False
    hdf(mag, pres, temp, gps, img.img, hdf_file, cam_flag, is_aurora)  # save data to hdf
    cam_flag = False
    # ! live_plot.plotting({'x': mag[0],'y': mag[1],'z': mag[2]}, {'in': temp[1], 'out': temp[0]}, pres, img.img, is_aurora)

get_direcs()

# initializes scheduling
schedule.every(5).seconds.do(data_processing)  # collect data every 5 seconds
schedule.every().day.at("16:00").do(upload_data)  # upload hdf5 file at 4pm
schedule.every().day.at("08:00").do(cam_off)  # turn camera off after 8am
schedule.every().day.at("20:00").do(cam_off)  # turn camera on after 8pm

while __name__ == '__main__':
    # runs any pending programs
    schedule.run_pending()
    time.sleep(1)
