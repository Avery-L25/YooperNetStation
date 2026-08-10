# !/usr/bin/env python3

'''
Script to run the prototype YooperNet Observational Station.
Will use configurations set in the \'.YooperConfig.toml\' file.

Primary Functions
-----------------
Taking All-Sky Images
    Methods are primarily held in \'YooperCam.py,\' this script manages the
    frequency of the image capturing.
Magnetometer Data
    Collects data from a chip-based moldwin magnetometer an several other
    sensors including a thermometer and barometer.
Writing to CSVs
    Data is written to two files; a camera file and a sensor file.
    These files are used to account for the different frequencies of
    data collection.
Uploading Files
    Uploads data using to google drive using \'rclone.\' rclone should be
    configured before running the station.


Can be called using startStation() if using a seperate script.
'''

import os
from os import path
import sys
import toml
import logging
import time
import datetime as dt
from copy import copy
from multiprocessing import Process
import cv2 as cv  # Image management
import pyzwoasi as pza  # Camera Library
from YooperCam import YooperCam  # Camera Interface for YooperNet
from auroral_image_check import AuroraImage  # Image masking
import filemanager as fman
import h5py

# region Initialize Variables
# Get working directory and repository directory
wkdir = path.dirname(path.realpath(__file__))

# Load Config Files
yoop_config = toml.load(path.join(wkdir, ".YooperConfig.toml"))

# Get Storage Locations
yoop_paths = yoop_config['paths']
general_img_folder = path.join(wkdir, yoop_paths['Images_Folder'])
hdf_folder = path.join(wkdir, yoop_paths['HDF5_Folder'])
log_folder = path.join(wkdir, yoop_paths['Log_Folder'])
# ? If using hdf5 or uploading using python instead of RCLONE
# google_folder_id = yoop_config['paths']['GDrive_Folder_ID']
img_folder = general_img_folder
sensor_file = 'test.h5'

# Get Storage Formats
yoop_form = yoop_config['formats']
image_folder_format = path.join(general_img_folder,
                                yoop_form['Image_Folder_Format'])
image_file_format = (yoop_form['Image_Name_Format'] +
                     yoop_form['Image_Extension'])
camera_file_format = path.join(hdf_folder, yoop_form['Camera_Info_Format'])
sensor_file_format = path.join(hdf_folder, yoop_form['Sensor_Data_Format'])
log_file_format = path.join(log_folder, yoop_form['Log_File_Format'])

# Initialize System Variables
yoop_aurora = yoop_config['aurora']
HIGH_IMG_RATE = yoop_aurora['Aurora_CapRate']
LOW_IMG_RATE = yoop_aurora['No_Aurora_CapRate']
AURORA_THRESHOLD = yoop_aurora['Aurora_MSE_Threshold']
AFTER_FLAG_TIME = yoop_aurora['Detection_After_Time']
exposure_time = 30
image_rate = HIGH_IMG_RATE
sensor_feed_rate = yoop_config['sensors']['Data_Rate']


# initializes scheduling # ! Implement for Uploading
# import schedule
# schedule.every(5).seconds.do(data_processing)  # collect data every 5 seconds
# schedule.every().day.at("16:00").do(upload_data)  # upload hdf5 file at 4pm
# schedule.every().day.at("08:00").do(cam_off)  # turn camera off after 8am
# schedule.every().day.at("20:00").do(cam_off)  # turn camera on after 8pm

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
log.setLevel(level=30)
# endregion

# from PyQt5.QtCore import QLibraryInfo
# # from PySide2.QtCore import QLibraryInfo


# os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = QLibraryInfo.location(
#     QLibraryInfo.PluginsPath
# )
mask_name = 'maskTuple'
percent_complete = 0.00
notify = 0.05
def percentComplete(comp):
    global notify
    if notify >= 1.0:
        notify = 0.05

    if comp > notify:
        print(f"{comp*100}% done with data")
        notify = notify + 0.05

    if notify >= 1.0:
        notify = 0.05


mse = (-1.0, -1.0)
flag = False
previous_image = None
current_image = None


def updateCaptureRate(new_img, old_img):
    '''
    Update the frequency of photos capture by the station.
    Uses the threshold value set in \'.YooperConfig.toml.\'
    '''
    global image_rate

    def auroraMasks(aura_img):
        '''
        Create masks for the aurora images used in comparison
        '''
        # Get statMasks
        blue_g_img_mean = aura_img.statMask(channel=2, std_dev=0,
                                            image_stats=True)
        blue_g_img_2std = aura_img.statMask(channel=2, std_dev=2,
                                            image_stats=True)
        # Mask 1: B>mean & ~B>mean+2std
        mask1 = blue_g_img_mean & ~blue_g_img_2std

        # Get neutralMasks
        neurtal_r_g = aura_img.neutralMask(num=0, den=1)
        neutral_b_g = aura_img.neutralMask(num=2, den=1)
        # Mask 2: Mask1 and Neutral Green bottom
        mask2 = mask1 & neutral_b_g & neurtal_r_g

        # Get normMaks
        norm_mean_green = aura_img.normMask(channel=1)
        norm_mean_blue = aura_img.normMask(channel=2)
        # Mask 3: Norm G>mean and Norm B<mean
        mask3 = norm_mean_green & ~norm_mean_blue

        aura_img.maskDict['mask2'] = mask2
        aura_img.maskDict['mask3'] = mask3

    # Mask images
    auroraMasks(new_img)
    auroraMasks(old_img)

    # Compare Images
    aurora_mse = new_img.compare(old_img, 'mask2')
    mse3 = new_img.compare(old_img, 'mask3')

    # Check MSE against threshold and determine capture rate
    if aurora_mse > AURORA_THRESHOLD:
        image_rate = HIGH_IMG_RATE
        flag = True
    else:
        image_rate = LOW_IMG_RATE
        flag = False


    # Return MSE and flag
    return (aurora_mse, mse3), flag


def fromPhotos(folder="Data/test_photos", filename=''):
    '''
    Test auroras from a series of photos given a directory.
    '''
    log.debug(f"starting the \'fromPhotos\' method with folder={folder}")
    global mse, flag, previous_image, current_image

    # Get a list of photos from the directory
    photos = dir2files(folder)
    photos.sort()
    num_photos = len(photos)
    total_num_photos = len(photos)
    log.info(f"there is {num_photos}")

    # Testing Dictionary
    auraDict = {}
    auraDict['mse'] = mse
    auraDict['flag'] = flag
    auraDict['photo'] = 'NA'

    # Analyze photos in a sequence
    for p in photos:

        log.log(DATA, f"This is photo {p} there are {num_photos} left.\n\n\n")
        num_photos = num_photos - 1
        auraDict['photo'] = p.rpartition('/')[2]
        if "Identifier" in p:
            # photos.remove(p)
            log.warning("Was not photo, skipping\n\n")
            continue

        previous_image = copy(current_image)
        cur = cv.imread(p)
        current_image = AuroraImage(cur)
        if (current_image is not None) & (previous_image is not None):
            mse, flag = updateCaptureRate(current_image, previous_image)

        # Put value in dict
        auraDict['mse'] = mse
        auraDict['flag'] = flag
        fman.hdf(f'Data/hdf/{mask_name}_{filename}_image.h5', auraDict)
        percentComplete((total_num_photos-num_photos)/total_num_photos)


def fromH5Photos(file="", filename=''):
    '''
    Test auroras from a series of photos given a directory.
    '''
    global mse, flag, previous_image, current_image
    # Get a list of photos from the directory
    with h5py.File(file, 'r') as f:

        # Testing Dictionary
        auraDict = {}
        auraDict['mse'] = mse
        auraDict['flag'] = flag
        auraDict['time'] = 'NA'
        total_num_photos = f['data']['images'].shape[3]
        # Analyze photos in a sequence
        for p in range(0, total_num_photos):

            cur = f['data']['images'][:,:,:,p]
            auraDict['time'] =  f['data']['timestamp'][p]

            previous_image = copy(current_image)
            current_image = AuroraImage(cur)
            if (current_image is not None) & (previous_image is not None):
                mse, flag = updateCaptureRate(current_image, previous_image)

            # Put value in dict
            auraDict['mse'] = mse
            auraDict['flag'] = flag
            fman.hdf(f'Data/hdf/{mask_name}_{filename}_h5.h5', auraDict)
            percentComplete((p)/total_num_photos)


def fromVideo(video_file, filename='', fps=0):
    '''
    Reads a video files to analyze frame-by-frame.

    '''
    # Read the video file
    cap = cv.VideoCapture(video_file)

    # init variables
    vf = 0
    global mse, flag, previous_image, current_image

    # Testing Dictionary
    auraDict = {}
    auraDict['mse'] = mse
    auraDict['flag'] = flag
    auraDict['time(ms)'] = 0
    auraDict['frame'] = vf
    vid_ms = cv.CAP_PROP_POS_MSEC
    vid_frame = cv.CAP_PROP_POS_FRAMES
    total_frames = cap.get(cv.CAP_PROP_FRAME_COUNT)

    if fps != 0:
        skip_count = int(cap.get(cv.CAP_PROP_FPS)/fps)
    else:
        skip_count = 1

    if filename == '':
        print(filename)
        filename = (video_file.rpartition('/')[-1]).partition('.')[0]
        print(filename)

    print(filename)
    previous_image = None
    current_image = None
    log.log(HIGH_DEBUG, f"Video Capture status before: {cap.isOpened()}")
    while cap.isOpened():

        # Get next frame

        ret, frame = cap.read()

        # if frame is read correctly ret is True
        if not ret:
            print("Can't receive frame (stream end?). Exiting ...")
            break
        else:
            cur_frame = cap.get(cv.CAP_PROP_POS_FRAMES)
            vf += skip_count
            cap.set(vid_frame, vf)
            log.log(DATA, f"On frame {cur_frame} of {total_frames}")

        # frame to aura img
        previous_image = copy(current_image)
        current_image = AuroraImage(frame)
        if (current_image is not None) & (previous_image is not None):
            mse, flag = updateCaptureRate(current_image, previous_image)

        # Put value in dict
        auraDict['mse'] = mse
        auraDict['flag'] = flag

        # Get video properties
        auraDict['time(ms)'] = cap.get(vid_ms)
        vf = cap.get(vid_frame)
        auraDict['frame'] = vf

        fman.hdf(f'Data/hdf/{mask_name}_{filename}_fps{fps}_video.h5', auraDict)
        percentComplete((vf)/total_frames)
    # Stop video after loop

    cap.release()


def dir2files(direc):
    'Gives back a list of all the files in a directory'
    files = []
    for r,d,f in os.walk(direc):
        log.debug(f"\nr = {r}\nd = {d} \n\n\n f = {f}")
        if d == []:
            d = ''

        if f == []:
            pass
        elif type(f) is list:
            for i in f:
                file = os.path.join(r,d,i)
                log.debug(file)
                files.append(file)
        else:
            file = os.path.join(r,d,f)
            log.debug(file)
            files.append(f)
    return files