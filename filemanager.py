#!/usr/bin/env python3

'''
Methods for writing, uploading, and managing files for the YooperNet Stations.
This includes when to start new files, name said files, and handling
authentication necessary in the uploading process.
'''

import numpy as np
import time
import datetime
import schedule
from suntime import Sun
import logging
import h5py
import toml
import shutil
import sys
import os
from os import path  # , listdir
from os.path import join  # isfile,  getsize, isdir
import subprocess


# Load Config Files
wkdir = path.dirname(path.realpath(__file__))
config_file_path = join(wkdir, ".YooperConfig.toml")
yoop_config = toml.load(config_file_path)

# Write Storage Locations
yoop_paths = yoop_config['paths']
img_folder_path = join(wkdir, yoop_paths['Images_Folder'])
img_info_path = join(wkdir, yoop_paths['HDF5_Folder'])
sensor_file_path = join(wkdir, yoop_paths['Log_Folder'])


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
rclone_remote = yoop_paths['RClone_Remote']

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
log.setLevel(level=10)


# todo check rclone setup for installer
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
        log.critical("CRITICAL ERROR: UNKNOWN UPLOADING OPERATION")
        uploadMethod = 'copy'  # Copy incase
        # ! Upload a flag or file to alert handler?

    # Create remote path for upload
    remote_path = join(rclone_remote, folder)

    # create command to upload folder using rclone
    str_cmd = f"rclone {uploadMethod} {path} {remote_path}"

    runStr(str_cmd)


# Do full uploading process. Upload -> Delete -> Update Locations
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
    # 1st: Upload files
    # rclone -> upload current working folder to remote with same name
    rclone(path=data_folder_full, folder=current_data_folder)

    # 2nd: Update working directory
    # ! Need to assign when file changes
    current_time = datetime.datetime.now()
    next_day = current_time + datetime.timedelta(hours=12)
    dataLoc(date=next_day)  # todo verify MAYBE read previous file name

    # 3rd: Delete uploaded files
    # ! implement once operable
    # shutil(path_to_delete)


# Delete certain files only.
def deleteFiles(path):
    '''
    Deletes files after upload verification.
    TODO: Add file types to mark
    '''
    # option 1: methodically, seperately delete each file.
    # Can look for flags or unique filetype
    for root, dirs, files in os.walk('projects', topdown=False):
        # skip any roots or directories we want to blacklist
        if any(item in root for item in safe_dirs):
            continue

        # If there are files in the directory delete based on
        # # ! extension or flag
        if files == []:
            pass
        elif type(files) is list:
            for file in files:
                if file.rpartition('.')[2] in file_ext_del:
                    log.error(f"deleting {join(root, file)}")
                    # os.remove(join(root,file))

        # Delete the directory if emptied
        # ? force delete if there is something else?
        if dirs == []:
            pass
        else:
            for d in dirs:
                if d in safe_dirs:
                    continue
                d_len = len(os.listdir(join(root, d)))
                if d_len == 0:
                    log.error(f"deleting empty dir {join(root, d)}")
                    # os.rmdir(join(root,d))
                else:
                    log.info(f"{d_len} files in {d}")
                    pass
        log.info(f"roots are {root}")
        log.info(f"Directories ares{dirs}")
        log.info(f"Files are {files}\n\n")
    # os.remove to delete a file
    # os.rmdir to delete an empty directory

    # option 2: fast with shutil
    # shutil.rmtree to delete a whole tree


# Find storage used on drive.
def dataSize(path):
    'Get the size data in path, the total disk usage.'
    total, used, free = shutil.disk_usage('/')

    file_size = 0
    for root, dirs, files in os.walk('projects', topdown=False):
        # skip any roots or directories we want to
        # if any(item in root for item in safe_dirs):
        #     continue

        # If there are files in the directory delete based on
        # # ! extension or flag
        if files == []:
            pass
        elif type(files) is list:
            for file in files:
                # get each filesize and add it to the total
                fs = path.getsize(join(root, file))
                file_size = file_size + fs

        log.info(f"Total file size is now {file_size}")
        log.info(f"roots are {root}")
        log.info(f"Directories ares{dirs}")
        log.info(f"Files are {files}\n\n")

    def b2gb(val):
        'Turn bytes value into gigabytes'
        return (val / (1024**3))

    # If upload at a certaint file size
    file_size_gb = b2gb(file_size)

    # If upload based on disk storage
    total_percent_used = used/total
    # total_percent_free = free/total

    # If upload based on how much the system storage is using
    total_percent_by_station = file_size/total

    return file_size_gb, total_percent_used, total_percent_by_station


# Get/Set data storage locations
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
    # ! Add naming convention addition incase multiple folder per day [hour?]
    current_data_folder = date.strftime(data_folder_format)
    data_folder_full = f"{wkdir}/Data/{current_data_folder}"

    if path.exists(data_folder_full) is False:
        os.mkdir(data_folder_full)
        os.mkdir(f"{data_folder_full}/{img_folder_format}")
        # start sensor csv
        # start camera csv
        # ? open( {file}, 'a').clos()
        # ? Start new log?

    if format != '':
        return time.strftime(f"{data_folder_full}/{format}")
    return None


# todo Integrate this into file creation
# Get relative sun location to take images at night
def getSun(lati=42.279594, long=-83.732124):
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
    y = []
    c = []
    t = []
    dlist = [y, c, t]
    j = 0
    sun_events = []
    sr_or_ss = ["Sunset", "Sunrise"] * 3

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
            log.info(f"Event time: {x.strftime("%h %d %H:%M")}")

        else:
            pass

    next_event = min(future_events)
    idx_min = sun_events.index(next_event)
    sun_does_whaaat = sr_or_ss[idx_min]
    log.info("Next Sun Event: ", next_event.strftime("%h %d %H:%M"), " at ",
             sun_does_whaaat, ".\n")

    return next_event, sun_does_whaaat


# ? Use this as format to update??
# Update camera status using sun location
def updateJobs():  # Turn off the cam
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
    next_job_update, set_or_rise = getSun(a2_lat, a2_lon)

    if next_job_update is None:
        sys.exit('No scheduling time')
    else:
        # String for next job update
        upJob_time = next_job_update.strftime('%H:%M')
        log.info(f"Next Job scheduled for {upJob_time} \n"
              f"(From: {next_job_update})")

        # Update Camera Status at next sunsrise/sunset
        schedule.every().day.at(upJob_time).do(updateJobs).tag('camera')

    # if curtime > today_sr and curtime < today_ss:
    #     pass
    # elif (curtime > today_ss and curtime < tmrw_sr) or curtime < today_sr:
    #     schedule.every(10).seconds.do(data_processing).tag('camera')
    # else:
    #     log.info("_"*62 + "\n"
    #           f"UNKNOWN ERROR WITH SCHEDULING HAS OCCURRED\n"
    #           f"Current time: {curtime} \n"
    #           f"Todays sunrise: {today_sr} \n Todays"
    #           f"sunset: {today_ss} \n "
    #           f"Tommorows sunrise: {tmrw_sr} \n ")

    if set_or_rise == "Sunrise":
        cameraoff = False
        camera_period = 300
        log.info('CAMERA ON\n')
    elif set_or_rise == "Sunset":
        cameraoff = True
        log.info('CAMERA OFF\n')
    else:
        log.error("Error with collecting next sun event type")


# Create/Write to hdf file
def hdf(file, data_dict):
    '''
    Creates an empty hdf5 file. Create directories if necessary.

    Cannot handle datetime datatype, must be a string.

    Parameters
    ----------
    file: str
        File and path to file.
    data_dict: dict
        Dictionary with data to write to hdf5 file.
        Key is used as the dataset name and the value
        is the written data.
    '''
    if path.exists(file) & path.isfile(file):
        # If the file exist append information
        with h5py.File(file, "a") as f:
            for k, v in data_dict.items():
                k = str(k)

                # resize dataset and add new value
                f[k].resize((f[k].shape[0] + 1), axis=0)  # type: ignore
                f[k][-1] = v  # type: ignore
    elif file.rpartition('.')[-1] == 'hdf5':
        # If a file is passed and does not exist, check that directory exists
        hdf_direc = file.rpartition('/')[0]
        if path.exists(hdf_direc) is False:
            # Make directory to the file location
            os.makedirs(hdf_direc)

        # Start new hdf5 file
        with h5py.File(file, "w") as f:
            for k, v in data_dict.items():
                # Create a dataset and store data
                f.create_dataset(str(k), maxshape=((None,)+np.shape(v)),
                                 data=[v], chunks=True)
    else:
        log.warning(f'File is not hdf5: {file}')


# Run commands from strings
def runStr(cmd: str):
    'run a string command as though it is in the terminal'
    # Turn a string command into a list
    command = cmd.split(' ')

    # Run the command
    subprocess.run(command, check=True)
