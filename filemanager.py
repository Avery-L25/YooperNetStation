#!/usr/bin/env python3

'''
Methods for writing, uploading, and managing files for the YooperNet Stations.
This includes when to start new files, name said files, and handling
authentication necessary in the uploading process.
'''

import time
from suntime import Sun
import schedule
import datetime
import numpy as np
import subprocess

import shutil
import os
from os import path # , listdir
from os.path import  join # isfile,  getsize, isdir
import h5py
import glob
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
file_ext_del = ['png', 'csv']
safe_dirs = ['Sensors']
rclone_remote = yoop_paths['REMOTE_CONFIG']

# region Upload
# Define functions # todo check rclone setup for installer
def rclone(move=True, path='', folder=''):
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
    # log(folder)

    # Get type of command for upload
    if move is True:
        uploadMethod = 'move'
    elif move is False:
        uploadMethod = 'copy'
    else:
        print("CRITICAL ERROR: UNKNOWN UPLOADING OPERATION")
        #! Upload a flag or file to alert handler?
    
    # Create remote path for upload
    remote_path = join(rclone_remote,folder)
    # create command to upload folder using rclone
    str_cmd = f"rclone copy {path} {remote_path}"
    
    # output the two would-be commands
    # print(f"string based command: {str_cmd}")
    runStr(str_cmd)


# todo will this function be valueable
def uploadFileToDrive(folder_id: str,file_name: str):  # Upload data to Google Drive
    '''
    Upload data to the google drive.
    '''
    creds = None
    token_path = '/home/USER/SPRL_Observatory/Token_management/token_2.json'
    creds_path = '/home/USER/SPRL_Observatory/Token_management/credentials.json'

    if path.exists(token_path):
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

# endregion

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

    if path.exists(data_folder_full) is False:
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
    global file_ext_del, safe_dirs
    # option 1: methodically, seperately delete each file. Can look for flags or unique filetype
    for root,dirs,files in os.walk('projects',topdown=False):
        # skip any roots or directories we want to blacklist
        if any(item in root for item in safe_dirs):
            continue

        # If there are files in the directory delete based on #! extension or flag
        if files == []:
            pass
        elif type(files) is list:
            for file in files:
                if file.rpartition('.')[2] in file_ext_del:
                    error(f"deleting {file}")
                    # os.remove(join(root,file))
        
        # Delete the directory if emptied  #? force delete if there is something else?
        if dirs == []:
            pass
        else:
            for d in dirs:
                if d in safe_dirs:
                    continue
                d_len = len(os.listdir(join(root,d)))
                if d_len == 0:
                    error(f"deleting empty dir {d}")
                    # os.rmdir(join(root,d))
                else:
                    log(f"{d_len} files in {d}")
        print(f"roots are {root}")
        print(f"Directories ares{dirs}")
        print(f"Files are {files}\n\n")
    # os.remove to delete a file
    # os.rmdir to delete an empty directory

    # option 2: fast with shutil
    # shutil.rmtree to delete a whole tree 

def dataSize(path):
    'Get the size data in path, the total disk usage.'
    total, used, free = shutil.disk_usage('/')
    
    file_size = 0
    for root,dirs,files in os.walk('projects',topdown=False):
        # skip any roots or directories we want to 
        # if any(item in root for item in safe_dirs):
        #     continue

        # If there are files in the directory delete based on #! extension or flag
        if files == []:
            pass
        elif type(files) is list:
            for file in files:
                # get each filesize and add it to the total
                fs = path.getsize(join(root,file))
                file_size = file_size + fs

        print(f"Total file size is now {file_size}")
        print(f"roots are {root}")
        print(f"Directories ares{dirs}")
        print(f"Files are {files}\n\n")

    def b2gb(val): 
        'Turn bytes value into gigabytes'
        return (val / (1024**3))
    
    # If upload at a certaint file size
    file_size_gb = b2gb(file_size)
    
    # If upload based on disk storage
    total_percent_used = used/total
    total_percent_free = free/total

    # If upload based on how much the system storage is using
    total_percent_by_station = file_size/total


# region hdf5 functions
def createHDF5(file_name):
    '''
    Creates an empty hdf5 files
    '''
    pass

def build_hdf(date, gps, temp, pres, mag, img, file):
    '''
    Builds hdf5 file with XXX \'groups\' to write data too.
    '''
    print('build hdf')
    with h5py.File(file, "w") as f:
        f.create_dataset("date", maxshape=(None,), dtype=h5py.string_dtype(),
                         data=[date])
        f.create_dataset("gps", maxshape=(None,), dtype='f', data=[gps])
        f.create_dataset("temperature", maxshape=(None, 2), dtype='f',
                         data=[temp])
        f.create_dataset("pressure", maxshape=(None,), dtype='f', data=[pres])
        f.create_dataset("magnetic field", maxshape=(None, 3), dtype='f',
                         data=[mag])

        # create group for images and their own timestamps
        i = f.require_group("images")
        i.create_dataset("date", maxshape=(None,), dtype=h5py.string_dtype(),
                         data=[date])
        i.create_dataset("aurora img", maxshape=(None, 512, 512, 3),
                         dtype='uint8', data=[img])
        i.create_dataset("aurora flag", maxshape=(None,), dtype=h5py.string_dtype(),
                         data=['Start of file'])


def add_data(date, gps, temp, pres, mag, img, file, camflag, aurflag):
    print('add data')
    with h5py.File(file, "a") as f:
        f["date"].resize((f["date"].shape[0] + 1), axis=0)
        f['date'][-1] = date
        f["gps"].resize((f["gps"].shape[0] + 1), axis=0)
        f["gps"][-1:] = gps
        f["temperature"].resize((f["temperature"].shape[0] + 1), axis=0)
        f['temperature'][-1] = temp
        f["pressure"].resize((f["pressure"].shape[0] + 1), axis=0)
        f['pressure'][-1] = pres
        f["magnetic field"].resize((f["magnetic field"].shape[0] + 1), axis=0)
        f['magnetic field'][-1] = mag

        # adds photos and their appropriate timestamp
        if camflag is True:  # if image was taken upload image
            i = f.require_group("images")
            i["date"].resize((i["date"].shape[0] + 1), axis=0)
            i['date'][-1] = date
            i['aurora img'][-1] = img
            i["aurora img"].resize((i["aurora img"].shape[0] + 1), axis=0)
            i['aurora flag'].resize((i["aurora flag"].shape[0] + 1), axis=0)
            if aurflag is True:
                i['aurora flag'][-1] = "True"
            else:
                i['aurora flag'][-1] = "False"


def hdf(mag, pres, temp, gps, img, file, camflag, aurflag):
    global utc_now

    d_t = np.datetime64('now').item().strftime('%Y_%m_%d_%H_%M_%S')

    utc_now = datetime.datetime.now(datetime.timezone.utc)
    if glob.glob(file):
        add_data(d_t, gps, temp, pres, mag, img, file, camflag, aurflag)
    else:
        build_hdf(d_t, gps, temp, pres, mag, img, file)

# endregion


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
