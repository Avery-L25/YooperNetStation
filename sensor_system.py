#!/usr/bin/env python3

# Supporting Libraries
import os
import sys
import datetime
from suntime import Sun
import time
import schedule
import numpy as np

# File Management Libraries
from dotenv import load_dotenv
from Data_processing.hdf import hdf
from Data_processing.file_transmission_2 import upload_file_to_drive as upload_data
from Data_processing.visualizer import Live_plotting

# Sensor Functions
from Sensors.barom_therm_data_collection import temp_n_pres
from Sensors.mag_data import mag_data

# Variable initialization
cur_day = datetime.datetime.now(datetime.timezone.utc)
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
load_dotenv()
folder_id = os.getenv('FOLDER_ID')  # Dan Wellings Server


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


### GPS, MAG, THERM, BARO...
def read_data():  # Read data from sensors and camera
    '''
    Runs all the sensors functions to collect data.
    Tales pictures if the cam_flag is true.
    '''

    mag = mag_data()
    temp, pres = temp_n_pres()
    gps = None  # todo complete gps code

    return mag, pres, temp, gps



def upload_data():  # Upload data to Google Drive
    '''
    Upload data to the 
    '''
    global hdf_file, folder_id, old_file # ! add path on server
    # if glob.glob("*.hdf5"):
    print('uploading data to the ... google drive')
    upload_data(hdf_file, folder_id)
    os.remove(old_file)
    get_direcs()


    # ! ensure that the delete flag is here unless addressed seperately


def data_processing():  # Collects data, looks for Aurora, Makes HDF
    '''
    Processes data from all sensors and writes it to hdf5 file.
    Determines whether it is time to take a picture.
    Detects an Aurora and updates the camera period accordingly.
    '''
    global hdf_file  # ! live_plot

    mag, pres, temp, gps = read_data()

    # todo   hdf(mag, pres, temp, gps, img.img, hdf_file, cam_flag, is_aurora)  # save data to hdf

    # ! live_plot.plotting({'x': mag[0],'y': mag[1],'z': mag[2]}, {'in': temp[1], 'out': temp[0]}, pres, img.img, is_aurora)


get_direcs()

# initializes scheduling
schedule.every(5).seconds.do(data_processing)  # collect data every 5 seconds
schedule.every().day.at("16:00").do(upload_data)  # upload hdf5 file at 4pm


while __name__ == '__main__':
    # runs any pending programs
    schedule.run_pending()
    time.sleep(1)
