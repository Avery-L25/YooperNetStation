#!/usr/bin/env python3

# import necessary libraries
import datetime
import numpy as np
# from Data_processing.image_processing import Image
from SPRL_Observatory.camera.main import shot

# force reload (remove later pl0x)
from SPRL_Observatory.camera import image_processing
from importlib import reload

reload(image_processing)
Image = image_processing.Image

# Variable initialization
img = Image(np.zeros((512, 512, 3)))  # blank image
cur_day = datetime.datetime.now(datetime.timezone.utc)
x = 0  # will use x as variable for taking picture or not


def read_data(cam_flag):  # Read data from sensors and camera
    '''
    Runs all the sensors functions to collect data.
    Tales pictures if the cam_flag is true.
    '''
    if cam_flag:  # takes an image if the camera period is complete
        img = shot()
    else:
        img = np.zeros((512, 512, 3), dtype=np.uint8)
    return img


def check_aurora(img):

    # Check if there us an aurora present
    is_aurora = img.aurora_detection()  # is there an aurora present
    if is_aurora is True:  # if yes, camera takes a photo every 10 seconds
        print('aurora present')
    elif is_aurora is False:  # if no, camera takes a photo every 5 minutes
        print('no aurora')


def data_processing():  # Collects data, looks for Aurora, Makes HDF
    '''
    Processes data from all sensors and writes it to hdf5 file.
    Determines whether it is time to take a picture.
    Detects an Aurora and updates the camera period accordingly.
    '''
    global x
    cam_flag = True
    print(f"camera period = {x}\ncamflag = {cam_flag}")
    x += 1
    img.img = read_data(bool(cam_flag))
    img.resize()
    check_aurora(img)
    display_grid(img)
    


def display_grid(img):
    '''
    Create a 2x2 image and show to screen.
    '''

    import matplotlib.pyplot as plt

    plt.close()
    # cv2.imshow('image', array)
    # cv2.waitKey(10000)
    fig, ax = plt.subplots(2, 2)
    ax[0, 0].imshow(img.img)
    ax[0, 0].set_title('current image')

    ax[0, 1].imshow(img.pre)
    ax[0, 1].set_title('previous image')
    ax[1, 0].imshow(img.masked)
    ax[1, 0].set_title('current mask')
    ax[1, 1].imshow(img.premask)
    ax[1, 1].set_title('previous mask')
    fig.show()
    img.pre = img.img
