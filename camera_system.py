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

# Camera Libraries
from camera.image_processing import Image
from camera.main import shot

# Variable initialization
T = 10  # When to take image
camera_period = 300  # a counter for camera's period
img = Image(np.zeros((512, 512, 3)))  # blank image
cur_day = datetime.datetime.now(datetime.timezone.utc)
cameraoff = False  # when True camera will not take picutre during the day

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


### THIS MAY BE VALUEABLE TO INTEGRATE ELSEWHERE
def get_sun(lati=42.279594, long=-83.732124):  # Get working file
    '''
    Calculates the next instance of Sunrise/Sunset using latitude and longitude
    Returns the next time as a datetime.datetime
    Returns the type of event as a string; "Sunrise" or "Sunset"
    time, sunXXX = get_sun(lat, lon)
    '''

    # Find Conditions (lat/lon of station)
    sun = Sun(lati, long)
    cur = datetime.datetime.now(datetime.timezone.utc)
    tmrw = cur + datetime.timedelta(1)
    yest = cur - datetime.timedelta(1)
  
    # Initialize Lists
    days = [yest, cur, tmrw]
    y = []; c = []; t = []
    dlist = [y, c, t]
    j = 0
    sun_events = []
    sr_or_ss = ["Sunset", "Sunrise", "Sunset", "Sunrise", "Sunset", "Sunrise"]
    # Get Sunrise/Sunset for 3 days
    for i in days:
        # Get days's sunrise and sunset then convert to UTC
        sr = sun.get_sunrise_time(i)
        ss = sun.get_sunset_time(i)
        
        dlist[j].append(ss)
        dlist[j].append(sr)
        sun_events.append(ss)
        sun_events.append(sr)

        j += 1
    

    # Find next instance of sun
    future_events = []
    for x in sun_events:
        
        if cur < x:
            future_events.append(x)
            # print(f"Event time: {x.strftime("%h %d %H:%M")}")
            
        else:
            pass
    
    next_event = min(future_events)
    idx_min = sun_events.index(next_event)
    sun_does_whaaat = sr_or_ss[idx_min]
    print("Next Sun Event: ", next_event.strftime("%h %d %H:%M"), " at ",
          sun_does_whaaat, ".\n")
    
    return next_event, sun_does_whaaat


def update_jobs():  # Turn off the cam
    '''
    Used to turn the camera on/off dependant on the time of day.
    Currently on between 12pm and 7 pm if the function is called.
    '''

    global cameraoff, camera_period
    # Cancel all jobs with the camera
    schedule.clear('camera')   

    # get sun event
    # todo use gps 
    a2_lat = 42.279594
    a2_lon = -83.732124
    next_job_update, set_or_rise = get_sun(a2_lat, a2_lon)

    if next_job_update is None:
        sys.exit('No scheduling time')
    else:
        upJob_time = next_job_update.strftime('%H:%M')  # String for next job update
        print(f"Next Job scheduled for {upJob_time} \n(From: {next_job_update})")
        schedule.every().day.at(upJob_time).do(update_jobs).tag('camera')  # Update Camera Status at next sunsrise/sunset

    # if curtime > today_sr and curtime < today_ss:
    #     pass
    # elif (curtime > today_ss and curtime < tmrw_sr) or curtime < today_sr:
    #     schedule.every(10).seconds.do(data_processing).tag('camera')
    # else:
    #     print(f"______________________________________________________________\n" 
    #           f"UNKNOWN ERROR WITH SCHEDULING HAS OCCURRED\n"
    #           f"Current time: {curtime} \n Todays sunrise: {today_sr} \n Todays"
    #           f"sunset: {today_ss} \n "
    #           f"Tommorows sunrise: {tmrw_sr} \n ")

    if set_or_rise == "Sunrise":
        cameraoff = False
        camera_period = 300
        print('CAMERA ON\n')
        schedule.every(10).seconds.do(data_processing).tag('camera')
    elif set_or_rise == "Sunset":
        cameraoff = True
        print('CAMERA OFF\n')
    else:
        print(f"Error with collecting next sun event type")


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
    Upload data to the University of Michigans "CRABYSS" server.
    '''
    global hdf_file, folder_id, old_file # ! add path on server
    # if glob.glob("*.hdf5"):
    print('uploading data to the ... google drive')
    upload_data(hdf_file, folder_id)
    os.remove(old_file)
    get_direcs()

    # * print("UPLOADING TO THE CRABYSS")
    # todo os.system(f'rsync -ahP {hdf_path} *USER*@crabyss.engin.umich.edu:{directory to save}')
    # ! ensure that the delete flag is here unless addressed seperately


def data_processing():  # Collects data, looks for Aurora, Makes HDF
    '''
    Processes data from all sensors and writes it to hdf5 file.
    Determines whether it is time to take a picture.
    Detects an Aurora and updates the camera period accordingly.
    '''
    global T, camera_period, cameraoff, hdf_file
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

    # take picture or use black image
    if cam_flag:  # takes an image if the camera period is complete
        try:
            img.img = shot()
        except RuntimeError:
            print(RuntimeError)
            print('No Image')
            img.img = np.zeros((512, 512, 3), dtype=np.uint8)
    else:
        img.img = np.zeros((512, 512, 3), dtype=np.uint8)

    img.resize()
    if cam_flag is True:
        is_aurora = check_aurora(img)
        img.pre = img.img
    else:
        is_aurora = False
    # ! hdf(mag, pres, temp, gps, img.img, hdf_file, cam_flag, is_aurora)  # save data to hdf
    cam_flag = False
    # * live_plot.plotting({'x': mag[0],'y': mag[1],'z': mag[2]}, {'in': temp[1], 'out': temp[0]}, pres, img.img, is_aurora)


get_direcs()

# initializes scheduling
schedule.every(5).seconds.do(data_processing).tag('camera')  # collect data every 5 seconds
schedule.every().day.at("08:00").do(update_jobs).tag('camera')  # turn camera off after 8am
schedule.every().day.at("20:00").do(update_jobs).tag('camera')  # turn camera on after 8pm
schedule.every().day.at("16:00").do(upload_data)  # upload hdf5 file at 4pm

while __name__ == '__main__':
    # runs any pending programs
    schedule.run_pending()
    time.sleep(1)
    
