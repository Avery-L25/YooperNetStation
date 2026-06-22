#!/usr/bin/env python3

from pyzwoasi import ZWOCamera
import pyzwoasi as pza  # ! Camera Interfaceing Library CRUCIAL
# pyright: reportIncompatibleMethodOverride=false
# several base class functions are overwritten for convenience
import cv2 as cv
import numpy as np
import os
import csv
import toml
from time import sleep, time
from datetime import datetime as dt
import shutil

# import supporting libraries
import matplotlib.pyplot as plt
from pathlib import Path
import sys


class YooperCam(ZWOCamera):
    '''
    Interface with a ZWO ASI camera.

    TODO: File tracking as properties to be adjusted externally

    TODO Helper Functions:
        Configure from toml file.                                           #* Done!
        Configure given controllable/roi params, use defaults if not.       #* Done!
        Set individual controls.                                            #* Done!
        Set individual roi components.                                      #* Done!
        Print Control(s) and ROI.                                           #* Done!
        Return roi.                                                         #* Done!
        Return controllables.                                               #* Done I think...

    TODO image processing:
        Aurora Detection                                                    #  todo This is setup but not working
        Resize image                                                        #* What need be done
        Take single image.                                                  #* Done!
        Live feed of camera.                                                #* Done!
        Auto exposure.                                                      #  todo

    TODO [look over] Older Functions:
        #todo Look into integration with
            image                                                           #? Check if these make sense to integrate differently
            roi


    Index: defaults to 0, required if there are multiple connected camera.
    '''

    def __init__(self, *args, **kwargs):
        is_cam = pza.getNumOfConnectedCameras()  # Grabs Camera Locations
        if is_cam == 0:
            raise KeyError("No Camera Detected.")

        ZWOCamera.__init__(self, *args, **kwargs)

        # setup dictionaries
        self._dictControlVals = {}
        self._dictControlFacts = {}
        self._dictImgType = {'RAW8': 0, 'RGB24': 1, 'RAW16': 2, 'Y8': 3}
        
        # setup class locations
        self.img_folder = ''    
        self.img_info_file = ''

        # setup controls
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
        
        # Complete ROI attributes
        self.start_x, self.start_y = pza.getStartPos(self._cameraID)
        self.width, self.height, self.binning, self.imageType = self._roi[2:]
        # _, _, self.width, self.height, self.binning, self.imageType = self._roi
        self.configFromToml()

        # setup aurora detection params
        self._resetAuroraImages(self.width)
        self._imgName = None
        self._auroraFlag = False

        return None

    def __str__(self) -> str:
        print(f"YooperCam Camera Object Name: {self._name}\n"
              f"Intended to take all-sky images and flag potential auorora\n"
              f"in parallel with magnetometers and other sensors.\n\n"
              f"Saving images to {self.img_folder}\nSaving flags + other cam data"
              f"to {self.img_info_file}.\n")

        print(f"ROI")
        self.roi
        print(f"Controllables")
        self.controllables
        return str()

    def __getattr__(self, name):
        pass

    def liveShots(self):
        '''
        Captures and saves images to save locations.
        
        TODO: Everything
        refresh rate
        gui stuff
        update exposure
        csv as hdf file?? (saving all con/roi|toml file will have most)
        '''
    
        # Initialize Camera "Log File"
        file_date = dt.now().strftime("%y_%m_%d")
        camFileName = str(file_date + "_cam.csv")
        if os.path.exists(camFileName) is False:
            sys.exit()
        cFile = open(camFileName, 'a', newline='') 

        # Write data using dictionary
        cWriter = csv.DictWriter(cFile, fieldnames=self._dictControlID.keys())
        while True:
            
            # Config Settings
            expSec = 1  
            
            # Capture image
            print("Capturing Image")
            x = self.shot(exposure=expSec, return_img=True) # exp is in microsecs  
            

            # Save Image and move to folder
            curTime = dt.now()
            imageName = dt.strftime(curTime, f"m%md%d_%H_%M_%S_exp{expSec}.png")
            cv.imwrite(imageName, x)
            print(f"image saved as {imageName}")
            shutil.move(imageName, str(self.img_folder))
            

            sleep(5)  
        
        print("Ending live view \n")
        cv.destroyAllWindows()

    def shot(self, save=False, display=False, return_img=False,
             imgName='',exposure=1):
        '''
        Take an image view from the ASI Camera
        Takes kwargs save (bool), display (bool), imgName (string),
        and exposure in seconds (float).

        Parameters
        ----------
        save : bool, defaults to False
            Save the image in location set to YooperCam.
        display : bool, defaults to False
            Displays the full resolution image.        
        return_img : bool, defaults to False
            Returns image array.
        imgName : str, defaults to "shot_%H_%M_%S.png" 
            Name the saved image using the current time unless specified.
        exposure : float, defaults to 1
            Camera exposure in seconds, converted into microseconds for camera
            operation.
        
        Returns
        -------
        Image array if 'return_img' param is specified as true
        None if else

        Examples
        --------
        >>> ycam.shot(save=True)
        # image saved named using the time it was captured

        >>> ycam.shot(display=True, exposure=10)
        # image capture with 10 seconds of exposure is displayed to user screen

        >>> ycam.shot(save=True,imgName='test.png')
        # image saved with the specified name, 'test.png'
        '''
    
        # Config Settings
        expSec = exposure
        if imgName == '': imgName = dt.now().strftime(f"m%md%d_%H_%M_%S_exp{expSec}.png")
        self._imgName = imgName   
       
        # Capture Image
        print("Capturing Image")
        x = super().shot(exposureTime_us=int(expSec * 10**6), imageType=1) # exp is in microsecs type 1 is rgb24
       
        # Save Image
        if save is True:
            cv.imwrite(imgName, x)
            print(f"image saved as {imgName}")
            shutil.move(imgName, str(self.img_folder))

        # Display Image
        if display is True:
            y = cv.resize(x,[int(self.width/4),int(self.height/4)])
            cv.imshow('frame', y)
            cv.waitKey(0)
            cv.destroyAllWindows()
        
        # Return Image Array 
        if return_img is True:
            return x
        else:
            return None

    def writeData(self, imgName=False):
        '''
        Method to save data to hdf5 or csv file given.
        Writes the image name, time, exposure, gain, aurora flag, errors.

        TODO: Could add others such as resolution, file size, or other.
        '''
        pass
        
        # Get items to be written
        if imgName is False:
            imgName = self._imgName
        cur_time = dt.now().strftime("%Y/%m/%d, %H:%M:%S")                  #? Should it be a str or datetime
        exposure = self.exposure
        gain = self.gain
        aur_flag = self._auroraFlag
        error = None                                                     # todo add error handling
        
        dict_to_write = {'Image Name':imgName, 'Timestamp':cur_time,     # todo add error to dict
                         'Exposure':exposure, 'Gain':gain,
                         'Aurora Flag':aur_flag}

        # Initialize Camera "Log File"                                   # todo update file path management
        file_date = dt.now().strftime("%y_%m_%d")
        camFileName = str(file_date + "_cam.csv")
        
        if os.path.exists(camFileName) is False:
            write_header = True
        else:
            write_header = False
        
        # if 
        with open(camFileName, 'a', newline='') as cFile: 
            cWriter = csv.DictWriter(cFile, fieldnames=dict_to_write.keys())
            
            if write_header is True:                                        #! If we write config settings it could be here, otherwise a seperate log file?
                cWriter.writeheader()

            cWriter.writerow(dict_to_write)

    def writeConfig(self):
        'Write the camera configuration to a file'
        pass
        
    def auroraDetection(self,*args,**kwargs):
        'Checks for aurora and returns a true or false string. Run \"isAurora\" for a bool'
        isAuro = self.isAurora(*args,**kwargs)
        if isAuro is True:
            return "Aurora Present"
        else:
            return "No Aurora Detected"

    def _resetAuroraImages(self,size):
        '''
        Sets up default testing images for aurora detection, takes a size 
        assuming image is a square for an all-sky image
        '''
        for image_detecting_vars in ['img','pre','masked','premask']:
            setattr(self,image_detecting_vars,np.zeros((size, size, 3)))  # todo: fix property
        return None

    def isAurora(self,img=None):
        # Credit:
        # https://github.com/joncooper65/raspberry-aurora/blob/master/detect.py
        '''
        Check most images against previous for bright, green/blue areas and
        returns a flag (bool) if detected.

        Input an image.
        Return a boolean.

        NOTE: If instead of inputing an image, it is assigned directly the
        compared \'pre\' image will not be the last camera image.

        TODO: Fix pre-image assignment. We want to be able 
        '''
        # Ensure there is an image to work with
        if img is not None:
            pre_updated = True
            self.pre = self.img
            self.img = img
        else:
            pre_updated = False
            img = self.img
        
        pre = self.pre

        ### get rgb components as floats
        b, g, r = cv.split(img)
        r1 = r * 1.0
        g1 = g * 1.0
        b1 = b * 1.0

        ### Create masks from current image
        # Blue/Green ratio
        gbratio = cv.divide(b1, g1)  #? blue / green
        maskgbratio = cv.inRange(gbratio, 0.9, 1.3)  #? any cell with a b/g ratio between 0.9 and 1.3 is set to 255 

        # Red/Green ratio
        grratio = cv.divide(r1, g1)  #! red / green
        maskgrratio = cv.inRange(grratio, 0.9, 1.3)  #! any cell with a r/g ratio between 0.9 and 1.3 is set to 255

        # Masks for dominant green
        mask1 = cv.compare(0.95*g, 1.0*b, cv.CMP_GT)  #? If 95% of green is greater that 100% of blue set 1 otherwise 0
        mask2 = cv.compare(0.95*g, 1.0*r, cv.CMP_GT)  #! If 95% of green is greater that 100% of red set 1 otherwise 0
        maskgreendominant = cv.bitwise_and(mask1, mask2)  #* This sets each pixel to the minimum of the two masks. (0 anywhere green was is more present that red OR blue)

        # Create strong green mask
        neutralMask = cv.bitwise_and(maskgrratio, maskgbratio)  # mask for area that have similar values of rgb
        inverseNeutral = cv.bitwise_not(neutralMask)  # Mask for areas that do not have similar rgb values
        verygreen = cv.bitwise_and(maskgreendominant, inverseNeutral)  #* This shows only the areas where green is dominant over blue or red AND rgb is not similar

        # Apply masks and get images
        masked_img = cv.bitwise_and(img, img, mask=verygreen)  # Display the image only whre the verygreen mask values are
        masked_pre = cv.bitwise_and(pre, pre, mask=verygreen)

        # Update contained images
        self.masked = masked_img
        self.premask = masked_pre
        if pre_updated is False:
            self.pre = self.img
        
        # Use mse to determine the changes in time
        mask_img_diff = masked_img - masked_pre
        norm_of_diff = np.linalg.norm(mask_img_diff)  # Returns the normal vector
        mse = float(np.mean(mask_img_diff**2))  # Use a threshold instead?

        self._auroraFlag = bool(norm_of_diff)  # currently any difference in the 'very green' region will be marked as a potential aurora
        return bool(mse)

    def configFromToml(self):
        '''
        Configure Camera controls and ROI from toml file

        TODO: Assign Values so they are grabbed by the camera
        '''
        # Load Config Files
        config_file_path = os.getcwd() + "/.YooperConfig.toml"
        yoop_config = toml.load(config_file_path)

        # Setup Default Values
        controls = yoop_config['controllables']
        roi = yoop_config['roi']

        self.setROI(**roi)
        self.setControllables(**controls)

        # Write Storage Locations
        self.img_folder = yoop_config['paths']['Camera_Images_Folder']    
        self.img_info_file = yoop_config['paths']['Camera_Info_File'] 

    @ZWOCamera.roi.getter
    def roi(self):
        'Prints ROI info to terminal'
        print (f" {"start_x":<9}  {"|":<3}  {self.start_x:<3}{"\n"}"
                f" {"start_y":<9}  {"|":<3}  {self.start_y:<3}{"\n"}"
                f" {"width":<9}  {"|":<3}  {self.width:<3}{"\n"}"
                f" {"height":<9}  {"|":<3}  {self.height:<3}\n"
                f" {"binning":<9}  {"|":<3}  {self.binning:<3}\n"
                f" {"imageType":<7}  {"|":<3}  {self.imageType.name[8:]:<3}\n")
        return None

    @property
    def _roi(self):
        '''
        Returns Region of Interest Parameters as:
        (start_x, start_y, width, height, binning, imageType)
        '''
        return (self.start_x, self.start_y, self.width, self.height, self.binning, self.imageType)
        # (f" {"start_x":<5}  {"|":<5}  {self.start_x:<5}\n"
        #             f" {"start_y":<5}  {"|":<5}  {self.start_y:<5}\n"
        #             f" {"width":<5}  {"|":<5}  {self.width:<5}\n"
        #             f" {"height":<5}  {"|":<5}  {self.height:<5}\n"
        #             f" {"binning":<5}  {"|":<5}  {self.binning:<5}\n"
        #             f" {"imageType":<5}  {"|":<5}  {self.imageType.name[8:]:<5}\n"
        #         

    @property
    def bytesPerPixel(self):
        'property based on image type for array management'
        imgTypeIdx = self.imageType.value
        if   imgTypeIdx == 0 or imgTypeIdx == 3:
            bytesPerPixel = 1
        elif imgTypeIdx == 2:
            bytesPerPixel = 2
        elif imgTypeIdx == 1:
            bytesPerPixel = 3
        else:
            raise ValueError("Invalide Image Type")

        return bytesPerPixel

    ### Should this be changed to an 'roi getter'
    def setROI(self, width=None, height=None, binning=None, imageType=None,
               start_x=None, start_y=None):
        '''
        Set all portions of the ROI. Any unspecified params will remain the same.
        
        The height must be a multiple of 2
        The width must be a multiple of 8
        The total width or height must follow the following parameter:
        maxVal / binning  >=  start_val + val

        NOTE: When changing the binning, width, or height, the centered area may
        not align with the lens.
        '''
        # If no value specified, use original value
        if binning   is None:   binning     = self.softwareBinning
        if imageType is None:   imageType   = self.imageType
        if width     is None:   width       = self.width
        if height    is None:   height      = self.height
        if start_x   is None:   start_x     = self.start_x
        if start_y   is None:   start_y     = self.start_y
        
        if imageType is str:
            imageType = self._dictImgType[imageType.upper()]
        
        # Check for correct regional parameters
        width_check  = (self._maxWidth/binning >= start_x + width)
        height_check = (self._maxHeight/binning >= start_y + height)
        
        # if binning < 1 or binning > max(self._supportedBins):
        #     raise ValueError(f"Binning must fit in camera range: 1 - {max(self._supportedBins)}")
        if width  % 8 != 0:
            raise ValueError("Width must be a multiple of 8")
        if height % 2 != 0:
            raise ValueError("Height must be a multiple of 2")
        if height_check is not True:
            raise ValueError("The binned sensor combined sensor height must "
                             "respect the following rule:\n"
                             "maxHeight/binning >= start_y + height")
        if width_check is not True:
            raise ValueError("The binned sensor combined sensor width must "
                             "respect the following rule:\n"
                             "maxWidth/binning >= start_x + width")
        
        if type(imageType) is str:
            imageType = self._dictImgType[imageType.upper()]

        roi_params = {'width': width, 'height': height, 'start_x': start_x,
                      'start_y': start_y, 'binning': binning, 'imageType': imageType}

        for k, v in roi_params.items():
            setattr(self, k, v)

        
        pza.setStartPos(self._cameraIndex, start_x, start_y)
        pza.setROIFormat(self._cameraIndex, width, height, binning, imageType)

    @property
    def controllables(self):
        'print control information to terminal'
        for c,v in self._dictControlVals.items():
            print(f"{c:<25} {"|":<3} {v:<3}")
        return None

    def setControllables(self, Gain=None, Exposure=None, WB_R=None, WB_B=None,
                         Offset=None, BandWidth=None, Flip=None,
                         AutoExpMaxGain=None, AutoExpMaxExpMS=None,
                         AutoExpTargetBrightness=None, HardwareBin=None,
                         HighSpeedMode=None, MonoBin=None, Temperature=None):
        '''
        Assign controllable camera parameters
        '''
        
        all_args = locals()
        all_args.pop('self')
        pass_args = {k:v for k, v in all_args.items() if v is not None}

        for key, val in pass_args.items():
            if val is int or str:
                # If one arg is passed assign into list before config
                if str(val).lower() == "auto":
                    # If a controllable is set to auto, keep the assigned value 
                    # and update the auto portion to true [1]  
                    val = [getattr(self,key)[0], 1]
                else:
                    # If the controllable is not auto, use assigned value and 
                    # set auto to false [0]
                    val = [val, 0]
            elif val is not tuple or list:
                raise KeyError("Incorrect control type.")
            elif len(val) > 3:
                raise KeyError("Dataset should include 1 or 2 value (integer value, auto value)")
            
            self._setControllableValue(con=key, val=val[0], auto=val[1])

        return pass_args

    def _setControllableValue(self, con, val=None, auto=0):
        '''
        Sets/Prints control value. If no value is given will outprint the value 
        as (Value, is(Auto)). 
        Call using man_cam(self, control, value, auto)
        self is ZWOCamera class; Control is int or str type; value is int; auto is int
        
        TODO: ensure value/auto is allowed
        does auto even work
        '''

        # Make dictionary for access to controllable name and ID
        dicty = self._dictControlID
        key_dict = {v: k for k, v in dicty.items()}
        
        # Get both controllable name and ID
        if type(con) is str:
            # If the control is a string collect the name before getting ID
            con_name = con
            con = dicty[con]
        elif type(con) is int:
            # If control is an integer [ID#] get the controllable name
            con_name = key_dict[con]
        else:
            print("Check that value \"con\" is a controllable value")
            exit()

        if val is None:
            # If the method is called without a value, print information instead
            print(f"{con_name} is {pza.getControlValue(0,con)} [(Value, Auto)]"
                  f"\nValue was not changed.")
        else:
            # Set controllable value to camera
            try:
                pza.setControlValue(self._cameraID, con, val, auto)  # update setting
            except pza.ASIError as e_msg:
                # handle controls that cannot be set to camera directlly
                print(f"Unable to set controllable {con_name.upper()} directly.\n"
                      f"{e_msg}\nValue is assigned to YooperCam as attribute.")

            self._dictControlVals[con_name] = val  # update value in dictionary
            setattr(self, con_name, val) # update attribute value

            # Print output value, value is auto if the setting was set to auto
            if auto == True:
                value = "Auto"
            else:
                value = val
            print(f"{con_name} was set to {value}")

    def liveView(self, dim=480):
        """
        Live view with OpenCV interface. Press 'q' key to quit and space to pause.
        Allows live changing of gain and exposure while flagging for aurora.
        """
        # Main frame
        windowName = "Live Camera Capture"
        cv.namedWindow(windowName)
        cv.createTrackbar("Exposure" , windowName, 50  , 100, lambda x: None)
        cv.createTrackbar("Gain"     , windowName, 100  , 100, lambda x: None)

        # It is useless to go above 1 second exposure for live view testing
        maximumExposureLimit = np.minimum(self.exposureLimits[1], 1000)

        # Software binning does not change latence or FPS in live view
        self.softwareBinning = 1

        if "HardwareBin" in self._dictControlID:
            # Hardware binning, if available, may accelerate FPS
            self.hardwareBinning = self.hardwareBinningLimits[1]

        # High speed mode, if available, may accelerate FPS
        self.highSpeedMode = True

        # Reinitialize detection parameters live image size
        aur_size = 1200
        self._resetAuroraImages(aur_size)

        disp_size = dim
        small = np.zeros((disp_size, disp_size,3))

        state = True
        previousTime = time()
        self.configFromToml()
        self.startVideoCapture()
        while True:
            if state is True:  
                # Updating camera exposure
                exposureTime_percentage = cv.getTrackbarPos("Exposure", windowName)
                exposureTime_us = (self.exposureLimits[0] + (maximumExposureLimit - self.exposureLimits[0]) * exposureTime_percentage / 100)
                self.exposure = int(exposureTime_us)

                # Updating camera gain
                gain_percentage = cv.getTrackbarPos("Gain", windowName)
                cameraGainMin, cameraGainMax = self._dictControlMin["Gain"], self._dictControlMax["Gain"]
                gain = int(cameraGainMin + (cameraGainMax - cameraGainMin) * gain_percentage / 100)
                self.gain = gain

                # Getting image from camera
                try:
                    # As given by the manufacturer ZWO, the refresh rate should
                    # be at least twice the exposure time plus 500 microseconds
                    refreshRate = int(2 * exposureTime_us + 500)
                    frame = pza.getVideoData(self._cameraIndex, self.bufferSize, refreshRate)
                except pza.ASIError as e:
                    print(f"Error getting video data: {e}")
                    continue
                    
                img = np.frombuffer(frame, dtype=np.uint8).reshape(self.height, self.width, self.bytesPerPixel)

                # Resize image for display
                # target_height = 480
                # scale = target_height / img.shape[0]
                # target_width = int(img.shape[1] * scale)
                small = cv.resize(img, (disp_size, disp_size))

                # run aurora detection and display
                aur_img = cv.resize(img, (aur_size, aur_size))
                aur_txt = self.auroraDetection(aur_img)

                cv.putText(small, f"{aur_txt}", (10, disp_size-30), cv.FONT_HERSHEY_SIMPLEX, 1,(255, 255, 255), 2,)

                # Computing and displaying FPS
                currentTime = time()
                fps = 1 / (currentTime - previousTime)
                previousTime = currentTime
                cv.putText(small, f"FPS: {fps:.2f}", (10, 30), cv.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

            cv.imshow(windowName, small)

            # Let's close the window if 'q' is pressed
            key_press = cv.waitKey(1) & 0xFF
            if key_press == ord('q'): break  # q for quit
            if key_press == ord(' '): state = not state  # [space] for pause


        self.stopVideoCapture()
        cv.destroyAllWindows()

    def liveTestView(self):
        """
        Live view with visuals on all testing parameters.
        Built in operations to help with analysis.

        Press 'q' to quit.
        Press ' ' (space) to pause data acquisition.
        Precc 'c' to capture a single image.
        """
        # Main frame
        windowName = "Live Camera Capture"
        cv.namedWindow(windowName)
        cv.createTrackbar("Exposure" , windowName, 50  , 100, lambda x: None)
        cv.createTrackbar("Gain"     , windowName, 100  , 100, lambda x: None)

        # 1 second maximum instead
        maximumExposureLimit = np.minimum(self.exposureLimits[1], 1000)

        # Software binning does not change latence or FPS in live view
        self.softwareBinning = 1

        if "HardwareBin" in self._dictControlID:
            # Hardware binning, if available, may accelerate FPS
            self.hardwareBinning = self.hardwareBinningLimits[1]

        # High speed mode, if available, may accelerate FPS
        self.highSpeedMode = True

        # Reinitialize detection parameters live image size
        aur_size = 1200
        self._resetAuroraImages(aur_size)
        aur_disp = np.zeros([800,800,3])
        disp_size = 800
        ds = disp_size
        border_width = 40 
        pos1 = (border_width, border_width)
        pos2 = (2*border_width+disp_size, border_width)
        pos3 = (border_width, 2*border_width+disp_size)
        pos4 = (2*border_width+disp_size, 2*border_width+disp_size)
        canvas_size = 2*disp_size + 3*border_width
        
        # Initialize parameters
        small = np.full((canvas_size, canvas_size,3),100, dtype=np.uint8)
        state = True
        single_shot = False
        previousTime = time()
        self.configFromToml()
        self.startVideoCapture()
        while True:
            if state is True:  
                # Updating camera exposure
                exposureTime_percentage = cv.getTrackbarPos("Exposure", windowName)
                exposureTime_us = (self.exposureLimits[0] + (maximumExposureLimit - self.exposureLimits[0]) * exposureTime_percentage / 100)
                self.exposure = int(exposureTime_us)

                # Updating camera gain
                gain_percentage = cv.getTrackbarPos("Gain", windowName)
                cameraGainMin, cameraGainMax = self._dictControlMin["Gain"], self._dictControlMax["Gain"]
                gain = int(cameraGainMin + (cameraGainMax - cameraGainMin) * gain_percentage / 100)
                self.gain = gain

                # Getting image from camera
                try:
                    # As given by the manufacturer ZWO, the refresh rate should
                    # be at least twice the exposure time plus 500 microseconds
                    refreshRate = int(2 * exposureTime_us + 500)
                    frame = pza.getVideoData(self._cameraIndex, self.bufferSize, refreshRate)
                except pza.ASIError as e:
                    print(f"Error getting video data: {e}")
                    continue
                    
                img = np.frombuffer(frame, dtype=np.uint8).reshape(self.height, self.width, self.bytesPerPixel)

                # Resize image for display

                # run aurora detection and display
                
                
                aur_img = cv.resize(img, (aur_size, aur_size))
                # self.img = aur_img
                aur_txt = self.auroraDetection(aur_img)
                pre_disp = aur_disp
                aur_disp = cv.resize(img, (disp_size, disp_size))
                # Computing and displaying FPS
                rs_img = cv.resize(aur_disp, (disp_size,disp_size))
                rs_pre = cv.resize(pre_disp, (disp_size,disp_size))
                rs_preMask = cv.resize(self.premask, (disp_size,disp_size))
                rs_Mask = cv.resize(self.masked, (disp_size,disp_size))
                
                small[pos1[0]:pos1[0]+ds,pos1[1]:pos1[1]+ds] = rs_img
                cv.putText(small, f"Current Image", (pos1), cv.FONT_HERSHEY_SIMPLEX, 1,(255, 255, 255), 2,)

                small[pos3[0]:pos3[0]+ds,pos3[1]:pos3[1]+ds] = rs_pre
                cv.putText(small, f"Previous Image", (pos2), cv.FONT_HERSHEY_SIMPLEX, 1,(255, 255, 255), 2,)
                
                small[pos2[0]:pos2[0]+ds,pos2[1]:pos2[1]+ds] = rs_Mask
                cv.putText(small, f"Current Mask", (pos3), cv.FONT_HERSHEY_SIMPLEX, 1,(255, 255, 255), 2,)
                
                small[pos4[0]:pos4[0]+ds,pos4[1]:pos4[1]+ds] = rs_preMask
                cv.putText(small, f"Previous Mask", (pos4), cv.FONT_HERSHEY_SIMPLEX, 1,(255, 255, 255), 2,)

                # currentTime = time()
                # fps = 1 / (currentTime - previousTime)
                # previousTime = currentTime
                cv.putText(small, f"{aur_txt}", (int(disp_size*0.75), disp_size), cv.FONT_HERSHEY_SIMPLEX, 1,(255, 255, 255), 2,)
                # cv.putText(small, f"FPS: {fps:.2f}", (10, 30), cv.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)


            if single_shot is True:
                # Getting image from camera
                try:
                    # As given by the manufacturer ZWO, the refresh rate should
                    # be at least twice the exposure time plus 500 microseconds
                    refreshRate = int(2 * exposureTime_us + 500)
                    frame = pza.getVideoData(self._cameraIndex, self.bufferSize, refreshRate)
                except pza.ASIError as e:
                    print(f"Error getting video data: {e}")
                    continue
                    
                img = np.frombuffer(frame, dtype=np.uint8).reshape(self.height, self.width, self.bytesPerPixel)

                aur_img = cv.resize(img, (aur_size, aur_size))
                # self.img = aur_img
                aur_txt = self.auroraDetection(aur_img)
                pre_disp = aur_disp
                aur_disp = cv.resize(img, (disp_size, disp_size))
                # Computing and displaying FPS
                rs_img = cv.resize(aur_disp, (disp_size,disp_size))
                rs_pre = cv.resize(pre_disp, (disp_size,disp_size))
                rs_preMask = cv.resize(self.premask, (disp_size,disp_size))
                rs_Mask = cv.resize(self.masked, (disp_size,disp_size))
                
                small[pos1[0]:pos1[0]+ds,pos1[1]:pos1[1]+ds] = rs_img
                cv.putText(small, f"Current Image", (pos1), cv.FONT_HERSHEY_SIMPLEX, 1,(255, 255, 255), 2,)

                small[pos3[0]:pos3[0]+ds,pos3[1]:pos3[1]+ds] = rs_pre
                cv.putText(small, f"Previous Image", (pos2), cv.FONT_HERSHEY_SIMPLEX, 1,(255, 255, 255), 2,)
                
                small[pos2[0]:pos2[0]+ds,pos2[1]:pos2[1]+ds] = rs_Mask
                cv.putText(small, f"Current Mask", (pos3), cv.FONT_HERSHEY_SIMPLEX, 1,(255, 255, 255), 2,)
                
                small[pos4[0]:pos4[0]+ds,pos4[1]:pos4[1]+ds] = rs_preMask
                cv.putText(small, f"Previous Mask", (pos4), cv.FONT_HERSHEY_SIMPLEX, 1,(255, 255, 255), 2,)

                # currentTime = time()
                # fps = 1 / (currentTime - previousTime)
                # previousTime = currentTime
                cv.putText(small, f"{aur_txt}", (int(disp_size*0.75), disp_size), cv.FONT_HERSHEY_SIMPLEX, 1,(255, 255, 255), 2,)
                # cv.putText(small, f"FPS: {fps:.2f}", (10, 30), cv.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                 
                single_shot = False

            cv.imshow(windowName, small)

            # Let's close the window if 'q' is pressed
            key_press = cv.waitKey(1) & 0xFF
            if key_press == ord('q'): break  # q for quit
            if key_press == ord(' '): state = not state  # [space] for pause
            if key_press == ord('c'): 
                state = False
                single_shot = True


        self.stopVideoCapture()
        cv.destroyAllWindows()

