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
import functools

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
notify = 0.01



def percentComplete(comp):
    global notify
    if notify >= 1.0:
        notify = 0.01

    if comp > notify:
        print(f"{int(comp*100)}% done with data")
        notify = notify + 0.01

    if notify >= 1.0:
        notify = 0.01


aura_dict = {}
mse = (-1.0, -1.0)
flag = False
previous_image = None
current_image = None


def auroraData(hdf_name, new_img, old_img):
    '''
    Update the frequency of photos capture by the station.
    Uses the threshold value set in \'.YooperConfig.toml.\'
    '''
    global aura_dict, notify
    notify = 0.01

    def auroraMasks(aura_img):
        '''
        Create masks for the aurora images used in comparison
        '''
        # Get statMasks
        blue_gt_img_mean = aura_img.statMask(channel=2, std_dev=0,
                                            image_stats=True)
        blue_gt_img_2std = aura_img.statMask(channel=2, std_dev=2,
                                            image_stats=True)
        # Mask 1: B>mean & ~B>mean+2std
        mask1 = blue_gt_img_mean & ~blue_gt_img_2std

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

    aura_dict['mse'] = aurora_mse
    aura_dict['mse_mask3'] = mse3
    aura_dict['flag'] = flag

    aura_dict['brightness'] = new_img.brightness.mean()

    aura_dict['red'] = new_img.r.sum()
    aura_dict['red mean'] = new_img.r.mean()
    aura_dict['ratio red'] = new_img.brightRatio(0, byPixel=True).mean()
    aura_dict['ratio red average brightness'] = new_img.brightRatio(0, byPixel=False).mean()

    aura_dict['green'] = new_img.g.sum()
    aura_dict['green mean'] = new_img.g.mean()
    aura_dict['ratio green'] = new_img.brightRatio(1, byPixel=True).mean()
    aura_dict['ratio green average brightness'] = new_img.brightRatio(1, byPixel=False).mean()

    aura_dict['blue'] = new_img.b.sum()
    aura_dict['blue mean'] = new_img.b.mean()
    aura_dict['ratio blue'] = new_img.brightRatio(2, byPixel=True).mean()
    aura_dict['ratio blue average brightness'] = new_img.brightRatio(2, byPixel=False).mean()

    # aura_dict
    # Return MSE and flag
    fman.hdf(hdf_name, aura_dict)



def fromPhotos(folder="Data/test_photos", filename=''):
    '''
    Test auroras from a series of photos given a directory.
    '''
    log.debug(f"starting the \'fromPhotos\' method with folder={folder}")
    global aura_dict, notify, previous_image, current_image
    notify = 0.01

    # Get a list of photos from the directory
    photos = dir2files(folder)
    photos.sort()
    num_photos = len(photos)
    total_num_photos = len(photos)
    log.info(f"there is {num_photos}")

    # Testing Dictionary
    aura_dict['photo'] = 'NA'

    # Analyze photos in a sequence
    for p in photos:

        log.log(DATA, f"This is photo {p} there are {num_photos} left.\n\n\n")
        num_photos = num_photos - 1
        aura_dict['photo'] = p.rpartition('/')[2]
        if "Identifier" in p:
            # photos.remove(p)
            log.warning("Was not photo, skipping\n\n")
            continue

        previous_image = copy(current_image)
        cur = cv.imread(p)
        current_image = AuroraImage(cur)

        # Put value in dict
        if (current_image is not None) & (previous_image is not None):
            mse, flag = auroraData(f'Data/hdf/{filename}_image.h5',
                                   current_image, previous_image)
        percentComplete((total_num_photos-num_photos)/total_num_photos)


def fromH5Photos(file="", filename=''):
    '''
    Test auroras from a series of photos given a directory.
    '''
    global aura_dict, notify, previous_image, current_image
    notify = 0.01
    # Get a list of photos from the directory
    with h5py.File(file, 'r') as f:

        # Testing Dictionary

        aura_dict['time'] = 'NA'
        total_num_photos = f['data']['images'].shape[3]
        # Analyze photos in a sequence
        for p in range(0, total_num_photos):

            cur = f['data']['images'][:, :, :, p]
            aura_dict['time'] =  f['data']['timestamp'][p]

            previous_image = copy(current_image)
            current_image = AuroraImage(cur)
            if (current_image is not None) & (previous_image is not None):
                auroraData(f'Data/hdf/{filename}_h5.h5',
                           current_image, previous_image)
            percentComplete((p)/total_num_photos)


def fromVideo(video_file, filename='', fps=0):
    '''
    Reads a video files to analyze frame-by-frame.

    '''
    # Read the video file
    cap = cv.VideoCapture(video_file)

    # init variables
    vf = 0
    global aura_dict, notify, previous_image, current_image
    notify = 0.01

    # Testing Dictionary
    aura_dict = {}
    aura_dict['mse'] = mse
    aura_dict['flag'] = flag
    aura_dict['time(ms)'] = 0
    aura_dict['frame'] = vf
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

        # Get video properties
        aura_dict['time(ms)'] = cap.get(vid_ms)
        vf = cap.get(vid_frame)
        aura_dict['frame'] = vf

        if (current_image is not None) & (previous_image is not None):
            auroraData(f'Data/hdf/{filename}_fps{fps}_video.h5',
                       current_image, previous_image)

        percentComplete((vf)/total_frames)
    # Stop video after loop

    cap.release()


def dir2files(direc):
    'Gives back a list of all the files in a directory'
    files = []
    for r, d, f in os.walk(direc):
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