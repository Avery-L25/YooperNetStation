#!/usr/bin/env python3

import time
from suntime import Sun
import schedule
import datetime
import numpy as np
import subprocess

import shutil
import os
import os.path
from os.path import isfile, join
import h5py
import toml

# Upload file using google API
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaUpload

### Load Config Files
wkdir = os.getcwd()
config_file_path = wkdir + "/.YooperConfig.toml"
yoop_config = toml.load(config_file_path)

# 

# Write Storage Locations
yoop_paths = yoop_config['paths']
img_folder_path     = wkdir + yoop_paths['Camera_Images_Collection']    
img_info_path       = wkdir + yoop_paths['Camera_Info_Folder'] 
sensor_file_path    = wkdir + yoop_paths['Sensor_Data_Folder']
# Google folder ID for individual file uploads
google_folder_id = yoop_paths['GDrive_Folder_ID']               #? If using hdf5 or uploading using python instead of RCLONE

# Get formats for storage locations/files
yoop_form = yoop_config['formats']
data_folder_format = yoop_form['Data_Folder']
img_folder_format = yoop_form['Image_Folder_Format']
cam_info_format = yoop_form['Camera_Info_Format']
sensor_data_format = yoop_form['Sensor_Data_Format']

# Define constants
SCOPES = ["https://www.googleapis.com/auth/drive.file"]

# Define functions # todo check rclone setup for installer
def rclone(path='', folder=''):
    '''
    Given a folder (and path???) uploads the folder and its contents to 
    the set "remote" path in rclone.

    Parameters
    ----------
    path : str
        the location of the file or folder to be upload to remote

    folder : str
        the name of the folder to hold the uploaded data, if not present
        at remote a new folder will be made.
    '''
    print(folder)
    
    # create command to upload folder using rclone
    command = ["rclone", "copy", "/home/amland/Documents/txt_duds", "remote:"]
    str_cmd = f"rclone copy {path} remote:{folder}"
    
    # update a list to use directly
    print(command)
    command[-1] = command[-1] + folder

    # output the two would-be commands
    print(f"list based command: {command}")
    print(f"string based command: {str_cmd}")


def dataLoc(date, format=''):
    '''
    Returns the data collection locations (file/directory) when called.

    Parameters
    ----------
    date: datetime
        Date of the new files using UTC.
    format: str, strftime
        Format for the file or directory, will use strftime to write.

    Returns
    -------
    str : Path to working file/folder

    '''
    global data_folder_full
    global current_data_folder
    # Make new days data folder if doesn't exist
    #! Add naming convention addition incase multiple folder per day [hour?]
    current_data_folder = date.strftime(data_folder_format)
    data_folder_full = f"{wkdir}/Data/{current_data_folder}"

    if os.path.exists(data_folder_full) is False:
        os.mkdir(data_folder_full)
        os.mkdir(f"{data_folder_full}/{img_folder_format}")
        # start sensor csv
        # start camera csv
        #? open( {file}, 'a').clos()
        #? Start new log?

    

    if format != '': 
        return time.strftime(f"{data_folder_full}/{format}")
    return None


# todo Integrate this into file creation
def getSun(lati=42.279594, long=-83.732124):  # Get working file
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


# ? Use this as format to update??
def updateJobs():  # Turn off the cam
    '''
    Used to turn the camera on/off dependant on the time of day.
    Currently on between 12pm and 7 pm if the function is called.
    '''
    return None
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

# delete files #? mark with flags for deletion?
def deleteFiles(path):
    '''
    Deletes files after upload verification.
    '''
    return None
    # option 1: methodically, seperately delete each file. Can look for flags or unique filetype
    # os.remove to delete a file
    # os.rmdir to delete an empty directory

    # option 2: fast with shutil
    # shutil.rmtree to delete a whole tree 


# todo will hdf5 be used
def createHDF5(file_name):
    '''
    Creates an empty hdf5 files
    '''
    pass


# todo will this function be valueable
def uploadFileToDrive(folder_id: str,file_name: str):  # Upload data to Google Drive
    '''
    Upload data to the google drive.
    '''
    creds = None
    token_path = '/home/USER/SPRL_Observatory/Token_management/token_2.json'
    creds_path = '/home/USER/SPRL_Observatory/Token_management/credentials.json'

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                creds_path, SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open(token_path, "w") as token:
            token.write(creds.to_json())

    try:
        service = build("drive", "v3", credentials=creds)

        file_metadata = {"name": file_name, "parents": [folder_id]}
        media = MediaFileUpload(
            file_name, mimetype="application/x-hdf5", resumable=True
        )
        
        file = (
            service.files()
            .create(body=file_metadata, media_body=media, fields="id",
                    supportsAllDrives=True)
            .execute()
        )
        print(f"File ID: {file['id']} uploaded successfully to folder"
              f"{folder_id}.")
    except HttpError as error:
        print(f"An error occurred: {error}")


def uploadFiles():
    '''
    Uploads data files from the YooperNet station. Creates and/or updates 
    working directories for data collection. Logs the procedure.

    TODO
        Upload all files
        Update Directories
        Write log

    Parameters
    ----------
    '''
    # Save extra variables before they are written
    path_to_delete = data_folder_full
    # 1st: Upload files
    # rclone -> upload current working folder to remote with same name
    rclone(path=data_folder_full,folder=current_data_folder)

    # 2nd: Update working directory
    #! Need to assign when file changes
    dataLoc(date=filler)

    # 3rd: Delete uploaded files
    # ! implement once operable
    # shutil(path_to_delete)

# Run commands from strings
def runStr(cmd: str):
    'run a string command as though it is in the terminal'
    command = cmd.split(' ')
    subprocess.run(command, check=True)

#? Is this going to be a script to run, an object, or a method holder [?]
while __name__ == '__main__':
    # runs any pending programs every hour to account for variable size thresholds                                                                                                                                                                 
    schedule.run_pending()
    time.sleep(60*60)
