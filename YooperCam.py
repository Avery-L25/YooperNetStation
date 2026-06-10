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
from time import sleep, ctime, time
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
            configFromToml
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
        is_cam = pza.getNumOfConnectedCameras()  # Grabs Camera Locations
        if is_cam == 0:
            raise KeyError("No Camera Detected.")

        ZWOCamera.__init__(self, *args, **kwargs)

        # setup dictionaries
        self._dictControlVals = {}
        self._dictControlFacts = {}
        self._dictImgType = {'RAW8': 0, 'RGB24': 1, 'RAW16': 2, 'Y8': 3}
        
        # setup class locations
        self.img_folder = str()    
        self.img_info_file = str()

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
        _, _, self.width, self.height, self.binning, self.imageType = self._roi
        self.configFromToml()

        # setup aurora detection params
        self._resetAuroraImages(self.width)

        return None

    def __str__(self) -> str:
        return (f" {"VALUE":<5}  {"|":<5}  {"SELF":<5}  {"|":<5}  {"FUNCTION":<5}\n"
                f" {"start_x":<10}  {"|":<5}  {self.start_x:<9}  {"|":<5}  {pza.getStartPos(self._cameraID)[0]:<5}\n"
                f" {"image_type":<10}  {"|":<5}  {self.imageType:<9}  {"|":<5}  {self.roi[3]:<5}\n"
                f" {"wb_r":<10}  {"|":<5}  {self.WB_R:<9}  {"|":<5}  {pza.getControlValue(self._cameraID,self._dictControlID['WB_R']):<5}\n"
                )

    def __getattr__(self, name):
        pass

    def zwo_live(self, save=False):
        '''
        Live view from the ASI Camera
        
        TODO: Everything
        refresh rate
        gui stuff
        csv as hdf file?? (saving all con/roi|toml file will have most)
        '''
    
        # get initial camera settings
        first_data = self.getAllControls()

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
            expSec = 1  
            
            # Capture image
            print("Capturing Image")
            x = self.shot(exposureTime_us=expSec * 10**6, imageType=1) # exp is in microsecs type 1 is rgb24
            

            # Save Image and move to folder
            if save is True:
                curTime = dt.now()
                imageName = dt.strftime(curTime, f"m%md%d_%H_%M_%S_exp{expSec}.png")
                cv.imwrite(imageName, x)
                print(f"image saved as {imageName}")
                shutil.move(imageName, str(self.img_folder))
            
            # Pause/End
            y = cv.resize(x,[int(self._maxWidth/4),int(self._maxHeight/4)])
            cv.imshow('frame', y)

            if cv.waitKey == ord('q'):
                break

            sleep(5)  
        
        print("Ending live view \n")
        cv.destroyAllWindows()

    def zwo_shot(self,save=False, display=True, imgName=dt.now().strftime("shot_%H_%M_%S.png"),exposure=1):
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
            x = self.shot(exposureTime_us=int(expSec * 10**6), imageType=1) # exp is in microsecs type 1 is rgb24
            

            # Save Image
            if save is True:
                cv.imwrite(imgName, x)
                print(f"image saved as {imgName}")

            if display is True:
                y = cv.resize(x,[int(self._maxWidth/4),int(self._maxHeight/4)])
                cv.imshow('frame', y)
                cv.waitKey(0)
                cv.destroyAllWindows()

    def auroraDetection(self,*args,**kwargs):
        isAuro = self.isAurora(*args,**kwargs)
        if isAuro is True:
            return "Aurora Present"
        else:
            return "No Aurora Detected"

    def _resetAuroraImages(self,size):
        for image_detecting_vars in ['img','pre','masked','premasked']:
            setattr(self,image_detecting_vars,np.zeros((size, size, 3)))  # todo: fix property
        return None

    def isAurora(self,img=None):
        # Credit:
        # https://github.com/joncooper65/raspberry-aurora/blob/master/detect.py
        '''
        OpenCV Masking to detect BRIGHT, GREEN/BLUE areas and flag as
        potential aurora
        '''
        # Ensure there is an image to work with
        if img is None:
            img = self.img
        else:
            self.img = img

        # get rgb components as floats
        b, g, r = cv.split(self.img)
        r1 = r * 1.0
        g1 = g * 1.0
        b1 = b * 1.0

        # Mask "img" and "pre" to retrieve the green part, ignore white color
        gbratio = cv.divide(b1, g1)
        maskgbratio = cv.inRange(gbratio, 0.9, 1.3)
        grratio = cv.divide(r1, g1)
        maskgrratio = cv.inRange(grratio, 0.9, 1.3)

        # create masks
        mask1 = cv.compare(0.95*g, 1.0*b, cv.CMP_GT)
        mask2 = cv.compare(0.95*g, 1.0*r, cv.CMP_GT)
        maskgreendominant = cv.bitwise_and(mask1, mask2)
        verygreen = cv.bitwise_and(maskgreendominant, cv.bitwise_not( cv.bitwise_and(maskgrratio, maskgbratio)))

        # get masked images
        masked_img = cv.bitwise_and(self.img, self.img, mask=verygreen)
        masked_pre = cv.bitwise_and(self.pre, self.pre, mask=verygreen)

        # updated params
        self.masked = masked_img
        self.premask = masked_pre

        # Use mse to determine the changes in time
        mse = np.linalg.norm(masked_img-masked_pre)

        # !save image if we want
        # cv.imwrite('masked.jpg', masked_img)
        
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

        # Write Storage Locations
        self.img_folder = yoop_config['paths']['Camera_Images_Folder']    
        self.img_info_file = yoop_config['paths']['Camera_Info_File'] 

    @ZWOCamera.roi.getter
    def roi(self):
        print (f" {"start_x":<7}  {"|":<5}  {self.start_x:<5}{"\n"}"
                f" {"start_y":<7}  {"|":<5}  {self.start_y:<5}{"\n"}"
                f" {"width":<9}  {"|":<5}  {self.width:<5}{"\n"}"
                f" {"height":<8}  {"|":<5}  {self.height:<5}\n"
                f" {"binning":<7}  {"|":<5}  {self.binning:<5}\n"
                f" {"imageType":<5}  {"|":<5}  {self.imageType.name[8:]:<5}\n")
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
    def setROI(self, width=None, height=None, binning=None, imageType=None, start_x=None, start_y=None):
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
                    val = [getattr(self,key), 1]
                else:
                    val = [val, 0]
            elif val is not tuple or list:
                raise KeyError("Incorrect control type.")
            elif len(val) > 3:
                raise KeyError("Dataset should include 1 or 2 value (integer value, auto value)")
            setattr(self, key, val[0])
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

#     #############################
#     ### The below functions need
#     ### to be updated for pza
#     #############################
# #{ Configure Camera From toml
#     def config_cam(self):

    def liveView(self):
        """
        Live view with OpenCV interface. Press 'q' key to quit.
        Gives the ability to the user to change gain, exposure,
        and ROI on the fly.
        """
        # Main frame
        windowName = "Live Camera Capture"
        cv.namedWindow(windowName)
        cv.createTrackbar("Exposure" , windowName, 0  , 100, lambda x: None)
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
                disp_size = 480
                target_height = 480
                scale = target_height / img.shape[0]
                target_width = int(img.shape[1] * scale)
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
#         try:
#             if use_file is True:
#                 self.configure_from_toml(CONFIG_FILE)  # configure camera from setting in zwo_asi.toml
#                 self.to_toml('zwo_asi.toml')
#                 print("\nConfiguring camera using " + '\033[94m' + f"{config_name}\n"
#                     + '\033[0m')
#             elif use_file is False:
#                 self.configure(conROI, conTroll)
#                 print("THIS SHOULDN'T HAPPEN")
#             else:
#                 raise
#         except RuntimeError:
#             print("Camera was not configured")
#             pass  # This error will happen if camera was configured but had not taken an image



#         # ? changing some controllables
#         # (supported arguments: the one that are
#         # indicated as 'writable' in the information
#         # printed above)
#         print("setting controls")
#         self.set_control("Gain",300)
#         self.set_control("Exposure","auto")

#         con = self.get_controls()
#         # con.items()
#         dict_keys = con.keys()  # the dictionary, not used for lookup
#         keys = list(dict_keys)



#         # ? changing the ROI (region of interest)
#         print("setting ROI")
#         roi = self.get_roi()
#         roi.type = cza.ImageType.rgb24
#         roi.start_x = 00
#         roi.start_y = 00
#         roi.bins = 2
#         roi.width = 2744
#         roi.height = 1836
#         self.set_roi(roi)

#         # saving this updated configuration to a file
#         conf_path = Path(os.getcwd() + '/asi.toml')
#         self.to_toml(conf_path)

#     def take_photo(self):
#         # ? Capture Image
#         image = self.capture()       # take picture
#         img_raw = image.get_image()     # save picture to (numpy array) for display
#         # taking the picture
#         filepath = Path(os.getcwd() + '/img_cza.png')
        
#         # todo find a way to check for config.
#         # filepath and show are optional, if you do not
#         # want to save the image or display it
#         image = self.capture(filepath=filepath,show=show)

#         return img_raw

#     # ! =============================================
#     def make_cv_img(self, roi, frame):
#         # Take image frame as list to array  of shape
#         height = roi.get_y_size()
#         width = self.get_x_size()
#         shape = (width, height)
#         small_shape = tuple(int(ti/4) for ti in shape)
#         img_array = np.array(frame, dtype=np.uint16).reshape(shape)
#         print("resizing image with opencv")


#         # Create a black image, a window
#         img = cv.resize(img_array, small_shape )
#         cv.imwrite("img_cv.png", img)
# }#}
        
