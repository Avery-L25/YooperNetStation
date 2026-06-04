#!/usr/bin/env python3

import pyzwoasi as pza  # ! Camera Interfaceing Library CRUCIAL
import numpy as np
import cv2 as cv
import sys
from time import sleep
# import supporting libraries
import os
from pathlib import Path
import matplotlib.pyplot as plt

# Check for camera
if pza.getNumOfConnectedCameras() == 0:
    KeyError("No camera detected, please connect camera before continueing.")
    exit()

# todo Initialization


def zwo_live():
    'Live view from the ASI Camera'
    with pza.ZWOCamera(0) as zcam:
        while True:
            print("Capturing Image")
            x = zcam.shot(exposureTime_us=100000, imageType=1) # exp is in microsecs type 1 is rgb24

            cv.imwrite('image.png', x)

            sleep(5)  
    print("Ending live view \n")

def controller_check():
    for controlIndex in range(numOfControls):
                controlCaps = pyzwoasi.getControlCaps(self._cameraIndex, controlIndex)
                controlName = controlCaps.Name.decode('utf-8')
                self._dictControlID [controlName]  = controlIndex
                self._dictControlMin[controlName]  = controlCaps.MinValue
                self._dictControlMax[controlName]  = controlCaps.MaxValue
                self._dictControlType[controlName] = controlCaps.ControlType

                # Initialize both the exposure time and image type with default values
                if controlName == "Exposure"  : self.exposure  = controlCaps.DefaultValue
                if controlName == "Image Type": self.imageType = controlCaps.DefaultValue

                # Initialize the gain to minimum value, for better safety.
                if controlName == "Gain": self.gain = controlCaps.MinValue

                # If the cooler can be controlled, it will always be set on
                if (controlName == "CoolerOn") and controlCaps.IsWritable:
                    pyzwoasi.setControlValue(self._cameraIndex, self._dictControlType["CoolerOn"], True, auto=False)

#############################
### The below functions need
### to be updated for pza
#############################



# Configure Camera From toml
def config_cam(zcam):


    try:
        if use_file is True:
            zcam.configure_from_toml(CONFIG_FILE)  # configure camera from setting in zwo_asi.toml
            zcam.to_toml('zwo_asi.toml')
            print("\nConfiguring camera using " + '\033[94m' + f"{config_name}\n"
                + '\033[0m')
        elif use_file is False:
            zcam.configure(conROI, conTroll)
            print("THIS SHOULDN'T HAPPEN")
        else:
            raise
    except RuntimeError:
        print("Camera was not configured")
        pass  # This error will happen if camera was configured but had not taken an image



    # ? changing some controllables
    # (supported arguments: the one that are
    # indicated as 'writable' in the information
    # printed above)
    print("setting controls")
    zcam.set_control("Gain",300)
    zcam.set_control("Exposure","auto")

    con = zcam.get_controls()
    # con.items()
    dict_keys = con.keys()  # the dictionary, not used for lookup
    keys = list(dict_keys)



    # ? changing the ROI (region of interest)
    print("setting ROI")
    roi = zcam.get_roi()
    roi.type = cza.ImageType.rgb24
    roi.start_x = 00
    roi.start_y = 00
    roi.bins = 2
    roi.width = 2744
    roi.height = 1836
    zcam.set_roi(roi)

    # saving this updated configuration to a file
    conf_path = Path(os.getcwd() + '/asi.toml')
    zcam.to_toml(conf_path)



def take_photo(zcam):
    # ? Capture Image
    image = zcam.capture()       # take picture
    img_raw = image.get_image()     # save picture to (numpy array) for display
    # taking the picture
    filepath = Path(os.getcwd() + '/img_cza.png')
    
    # todo find a way to check for config.
    # filepath and show are optional, if you do not
    # want to save the image or display it
    image = zcam.capture(filepath=filepath,show=show)

    return img_raw


# ! =============================================
def make_cv_img(zcam, roi, frame):
    # Take image frame as list to array  of shape
    height = roi.get_y_size()
    width = zcam.get_x_size()
    shape = (width, height)
    small_shape = tuple(int(ti/4) for ti in shape)
    img_array = np.array(frame, dtype=np.uint16).reshape(shape)
    print("resizing image with opencv")


    # Create a black image, a window
    img = cv.resize(img_array, small_shape )
    cv.imwrite("img_cv.png", img)

    