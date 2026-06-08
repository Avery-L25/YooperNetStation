#!/usr/bin/env python3

from pyzwoasi import ZWOCamera
import pyzwoasi as pza  # ! Camera Interfaceing Library CRUCIAL
import cv2 as cv
import numpy as np

# import supporting libraries
import matplotlib.pyplot as plt
import sys
import os
import csv
import toml
from pathlib import Path
from time import sleep, ctime
from datetime import datetime as dt
import shutil


class YooperCam(ZWOCamera):
    '''
    Interface with a ZWO ASI camera.

    TODO Helper Functions:
        Configure from toml file.
        Configure given controllable/roi params, use defaults if not.
        Set individual controls.
        Set individual roi components.

        Output Control(s) and ROI.

    TODO image processing:
        Aurora Detection
        Resize image
        Take single image.
        Live feed of camera.
        Auto exposure.

    TODO [look over] Older Functions:
        #todo yoopercam [old]
            set_control
            get_controls
            config_from_toml
            to_dict
            to_toml #! NO
            get_roi
            _check_controllable
            configure
            capture
            __str__
        #todo main
            udev
            print_
            shot
            _shot
            dump
        #todo Look into integration with
            image
            roi


    Index: defaults to 0, required if there are multiple connected camera.
    '''

    def __init__(self, *args, **kwargs):
        ZWOCamera.__init__(self, *args, **kwargs)

        # Complete ROI attributes
        self.start_x, self.start_y = pza.getStartPos(self._cameraID)
        self.width, self.height, self.bins, self.imageType = self.roi

        self._dictControlVals = {}
        self._dictControlFacts = {}
        numOfControls = pza.getNumOfControls(self._cameraIndex)
        for controlIndex in range(numOfControls):
            controlCaps = pza.getControlCaps(self._cameraIndex, controlIndex)
            controlName = controlCaps.Name.decode('utf-8')

            ValAuto = pza.getControlValue(self._cameraID, controlIndex)
            setattr(self, controlName, ValAuto)


            #! May need to remove these  
            # Sets easy value managements
            self._dictControlFacts[controlName] = ValAuto
            if ValAuto[1] is True:
                # todo make an auto feature
                self._dictControlVals[controlName] = 'Auto'
            else:
                self._dictControlVals[controlName] = ValAuto[0]


            # pza.setControlValue(cameraID, controlType, value, auto)
            # self.__setattr__("WB_R", 9)
        return None

    def __str__(self) -> str:
        return (f" VALUE  |  SELF  |  FUNCTION"
                f"start_x  = {self.start_x}   |  {pza.getStartPos(self._cameraID)[0]}\n" +
                f"image_type= {self.imageType} | {self.roi}" +
                f"wb_r = {self.WB_R}    | {pza.getControlValue(self._cameraID,self._dictControlID['WB_R'])}
                )

    def zwo_live(self):
        '''
        Live view from the ASI Camera
        
        TODO: Everything
        refresh rate
        gui stuff
        csv as hdf file?? (saving all con/roi|toml file will have most)
        '''
    
        # get initial camera settings
        first_data = getAllControls(self)

        # Initialize Camera "Log File"
        file_date = dt.now().strftime("%y_%m_%d")
        camFileName = str(file_date + "_cam.csv")
        if os.path.exists(camFileName) is False:
            exit()
        cFile = open(camFileName, 'a', newline='') 

        # Write data using dictionary
        cWriter = csv.DictWriter(cFile, fieldnames=self._dictControlID.keys())
        while True:
            
            # Config Settings
            expSec = 30  
            
            # Capture and display image
            print("Capturing Image")
            x = self.shot(exposureTime_us=expSec * 10**6, imageType=1) # exp is in microsecs type 1 is rgb24
            cv.imshow('xframe', x)

            # Save Image
            curTime = dt.now()
            imageName = dt.strftime(curTime, f"m%md%d_%H_%M_%S_exp{expSec}.png")
            cv.imwrite(imageName, x)
            print(f"image saved as {imageName}")
            shutil.move(imageName, '/SPRL_Observatory/camera/ImagesJune4th')
            
            # Pause/End
            if cv.waitKey == ord('q'):
                break

            sleep(5)  
        
        print("Ending live view \n")
        cv.destroyAllWindows()


    def zwo_shot(self,imgName=dt.now().strftime("shot_%H_%M_%S_exp{expSec}.png"),exposure=1):
        '''
        Take an image view from the ASI Camera
        
        TODO: Everything
        refresh rate
        gui stuff
        csv as hdf file?? (saving all con/roi|toml file will have most)
        '''
        with pza.ZWOCamera(0) as self:
            # Config Settings
            expSec = exposure
            
            # Capture and display image
            print("Capturing Image")
            x = self.shot(exposureTime_us=expSec * 10**6, imageType=1) # exp is in microsecs type 1 is rgb24
            

            # Save Image
            cv.imwrite(imgName, x)
            print(f"image saved as {imgName}")

            cv.imshow('xframe', x)
            cv.waitKey(0)
            cv.destroyAllWindows()
            

    def config_from_toml(self):
        '''
        Configure Camera controls and ROI from toml file

        TODO: Assign Values so they are grabbed by the camera
        '''
        pass
        # Load Config Files
        config_file_path = os.getcwd() + "/.YooperConfig.toml"
        yoop_config = toml.load(config_file_path)

        # Setup Default Values
        controls = yoop_config['controllables']
        roi = yoop_config['roi']
        

        # Write Storage Locations
        self.img_folder = yoop_config['paths']['Camera_Images_Folder']    
        self.img_info_file = yoop_config['paths']['Camera_Info_File'] 


    def configROI(width, height, bin):
        '''Configure ROI Parameters
        
        start_x
        start_y
        width
        height
        bins
        image type
        '''
        pass

        imageType
        pza.setStartPos(camID,start_x,start_y)
        # self.setROI(width, height, bins, type)


    def man_con(self, con, val=None, auto=0):
        '''
        Sets/Prints control value. If no value is given will outprint the value 
        as (Value, is(Auto)). 
        Call using man_cam(self, control, value, auto)
        self is ZWOCamera class; Control is int or str type; value is int; auto is int
        
        TODO: ensure value/auto is allowed
        does auto even work
        '''
        # global self
        dicty = self._dictControlID
        key_dict = {v: k for k, v in dicty.items()}
        if type(con) is not int:
            con_name = con
            con = dicty[con]
        elif type(con) is int:
            con_name = key_dict[con]
        else:
            print("Check that value \"con\" is a controllable value")
            exit()

        if val is None:
            print(f"{con_name} is {pza.getControlValue(0,con)} [(Value, Auto)]")
        else:
            pza.setControlValue(0, con, val, auto)
            if auto == True:
                value = "Auto"
            else:
                value = val
            print(f"{con_name} was set to {value}")


    def getAllControls(self):
        '''
        Read and save all camera controls for the getters/setters. 
        
        TODO: Best way to update necessary values.

        Returns dictionary.
        '''
        
        # ROI Components
        start_x, start_y = pza.getStartPos(self._cameraID)
        w, h, bins, img_type = self.roi

        # Settings Components
        numOfControls = pza.getNumOfControls(self._cameraIndex)
        for controlIndex in range(numOfControls):
            controlCaps = pza.getControlCaps(self._cameraIndex, controlIndex)
            controlName = controlCaps.Name.decode('utf-8')

            ValAuto = pza.getControlValue(self._cameraID, controlIndex)


        return self._dictControlVals
    #############################
    ### The below functions need
    ### to be updated for pza
    #############################



    # Configure Camera From toml
    def config_cam(self):


        try:
            if use_file is True:
                self.configure_from_toml(CONFIG_FILE)  # configure camera from setting in zwo_asi.toml
                self.to_toml('zwo_asi.toml')
                print("\nConfiguring camera using " + '\033[94m' + f"{config_name}\n"
                    + '\033[0m')
            elif use_file is False:
                self.configure(conROI, conTroll)
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
        self.set_control("Gain",300)
        self.set_control("Exposure","auto")

        con = self.get_controls()
        # con.items()
        dict_keys = con.keys()  # the dictionary, not used for lookup
        keys = list(dict_keys)



        # ? changing the ROI (region of interest)
        print("setting ROI")
        roi = self.get_roi()
        roi.type = cza.ImageType.rgb24
        roi.start_x = 00
        roi.start_y = 00
        roi.bins = 2
        roi.width = 2744
        roi.height = 1836
        self.set_roi(roi)

        # saving this updated configuration to a file
        conf_path = Path(os.getcwd() + '/asi.toml')
        self.to_toml(conf_path)



    def take_photo(self):
        # ? Capture Image
        image = self.capture()       # take picture
        img_raw = image.get_image()     # save picture to (numpy array) for display
        # taking the picture
        filepath = Path(os.getcwd() + '/img_cza.png')
        
        # todo find a way to check for config.
        # filepath and show are optional, if you do not
        # want to save the image or display it
        image = self.capture(filepath=filepath,show=show)

        return img_raw


    # ! =============================================
    def make_cv_img(self, roi, frame):
        # Take image frame as list to array  of shape
        height = roi.get_y_size()
        width = self.get_x_size()
        shape = (width, height)
        small_shape = tuple(int(ti/4) for ti in shape)
        img_array = np.array(frame, dtype=np.uint16).reshape(shape)
        print("resizing image with opencv")


        # Create a black image, a window
        img = cv.resize(img_array, small_shape )
        cv.imwrite("img_cv.png", img)

        
