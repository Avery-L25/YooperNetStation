#!/usr/bin/env python3
'''
Interface with ZWO ASI Camera for all sky imagery
in a YooperNet Obervational Station
'''

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
import logging

# import supporting libraries
# import matplotlib.pyplot as plt # ? Replace displa
# from pathlib import Path # ? Make string into path
# import sys

# Setup logger
log = logging.getLogger("YooperCamera")


class YooperCam(ZWOCamera):
    '''
    Interface with a ZWO ASI camera for a YooperNet
    observational station. Provides some convenience
    functions and attributes to simplify management

    Helper Functions:
        Configure from toml file.
        Configure given controllable/roi params, use defaults if not.
        Set individual controls.
        Set individual roi components.
        Print Control(s) and ROI.
        Return roi.
        Return controllables.

    Image processing:
        TODO Aurora Detection  #  todo This is setup but not working
        Resize image
        Take single image.
        Live feed of camera.
        TODO Auto exposure.  #  todo

    Index: defaults to 0, required if there are multiple connected camera.
    '''

    def __init__(self, *args, **kwargs):

        # Query camera so it is ready to connect
        is_cam = pza.getNumOfConnectedCameras()  # Grabs Camera Locations
        if is_cam == 0:
            raise KeyError("No Camera Detected.")

        # Init camera from zwo library
        ZWOCamera.__init__(self, *args, **kwargs)

        # Dictionary to convert image type to ID number
        self._dictImgType = {'RAW8': 0, 'RGB24': 1, 'RAW16': 2, 'Y8': 3}

        # Dictionaries to help view info
        self._dictControlVals = {}
        self._dictControlFacts = {}
        # Assign controls to dictionary and attribute of object
        numOfControls = pza.getNumOfControls(self._cameraIndex)
        for controlIndex in range(numOfControls):
            # ? Get control info from ZWO SDK
            controlCaps = pza.getControlCaps(self._cameraIndex, controlIndex)
            controlName = controlCaps.Name.decode('utf-8')

            # Get the control value (value[int], auto[bool])
            ValAuto = pza.getControlValue(self._cameraID, controlIndex)
            setattr(self, controlName, ValAuto)  # assign attribute to object

            # ! May need to remove these
            # Fill dictionaries to see values of each control
            self._dictControlFacts[controlName] = ValAuto
            if ValAuto[1] is True:
                # todo make an auto feature
                self._dictControlVals[controlName] = 'Auto'
            else:
                self._dictControlVals[controlName] = ValAuto[0]

        # Initialize ROI attributes to object
        self.start_x, self.start_y = pza.getStartPos(self._cameraID)
        (self.width, self.height, self.binning, self.imageType
         ) = pza.getROIFormat(self._cameraID)
        # self._roi[2:]

        # Saving Informartion
        self._imgName = ''  # To track current name for logging purposes
        self.img_folder = ''  # Track saving location internally
        self._imgInfoFile = ''  # Track info file name
        self._CameraDirectory = os.path.dirname(os.path.realpath(__file__))
        # Configure object ROI and Controls from toml file
        self.tomlPath = os.path.join(self._CameraDirectory,
                                     '.YooperConfig.toml')
        self.tomlDefaultsPath = os.path.join(self._CameraDirectory,
                                             'Setup/Default.toml')
        # Assign default locations
        self.configFromToml()

        # Setup aurora detection params
        self.img = None  # Store most recent image captured
        self.pre = None  # Store previous image for comparison
        self.masked = None  # ? Mask to use in comparison
        self.premask = None  # ? Mask held for comparison
        self._resetAuroraImages(self.width)  # ! Make blank images
        self._auroraFlag = False

        return None

    def __str__(self):
        print(f"YooperCam Camera Object Name: {self._name}\n"
              f"Intended to take all-sky images and flag potential auorora\n"
              f"in parallel with magnetometers and other sensors.\n\n"
              f"Saving images to {self.img_folder}\nSaving flags + "
              f"other cam data to {self.imgInfoFile}.\n")

        # Print roi and controls to terminal
        print("ROI")
        self.roi
        print("Controllables")
        self.controllables
        return str()

    def shot(self, save=False, display=False, return_img=False, imgName='',
             path='', exposure=1):
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
        imgName : str, defaults to toml format
            Name the saved image using the current time unless specified.
            Default = "YYYY_MM_DD_exp{exposure in second}.png"
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
        # Get locations and foormats
        main_folder = self.img_folder

        # Config Settings
        expSec = exposure

        if imgName == '':
            # ?  {something with date }{exposure}{.png or other}
            # ? ---> "2026_05_24_exp10.png" or "26_06_12_shot12.jpg"
            imgName = dt.now().strftime(self.img_name_format + str(expSec) +
                                        self.img_extension)

        # todo Make directory OR use default path
        if (path == ''):
            # If path not given
            path = f"{main_folder}/{imgName}"
        self._imgName = imgName

        # Capture Image (exp is in microsecs, image type 1 is rgb24)
        print("Capturing Image")
        zwo_img = super().shot(exposureTime_us=int(expSec * 10**6),
                               imageType=1)

        # Save Image
        if save is True:
            # write image to image folder
            cv.imwrite(path, zwo_img)
            print(f"image saved as {imgName} to {main_folder}")

        # Display Image
        if display is True:
            # Resize image before displaying
            sm_im = cv.resize(zwo_img, [int(self.width/4), int(self.height/4)])
            cv.imshow('frame', sm_im)
            cv.waitKey(0)
            cv.destroyAllWindows()

        # Return Image Array
        if return_img is True:
            return zwo_img
        else:
            # return None array if not requested
            return np.asarray(None)

    def liveShots(self, exposure=1):
        '''
        Captures and saves images to images folder.
        A simple loop using the built in 'shot' method.

        TODO: Write data using dictionary
              Add exit condition

        Parameters
        ----------
        exposure : float, defaults to 1
            Camera exposure in seconds, converted into microseconds for camera
            operation.

        Returns
        -------
        None

        Examples
        --------
        >>> ycam.liveShots(exposure=10)
        # images saved with exposure time of 10 seconds
        '''
        # Loop images at a given exposure rate
        try:
            while True:
                # Capture image
                print("Capturing Image")
                x = self.shot(exposure=exposure, return_img=True)

                # Save Image and move to folder
                curTime = dt.now()
                imageName = dt.strftime(curTime, (self.img_name_format +
                                                  f"{exposure}_live.png"))
                img_success = cv.imwrite(imageName, x)
                if img_success:
                    print(f"image saved as {imageName}")
                shutil.move(imageName, str(self.img_folder))

                sleep(0.25)
        except KeyboardInterrupt:
            print("Ending live view \n")

        cv.destroyAllWindows()

    def writeData(self, imgName='', file='') -> None:
        '''
        Write information regarding the camera and image to CSV file.
        Writes the image name, time, exposure, gain, aurora flag, errors.

        TODO:Other info to write?
             resolution, file size, etc.
             hdf5
        '''
        # Get writing location.
        if file == '':
            file = self.imgInfoFile

        if os.path.exists(file):
            # Assumes that if the file exists, it already has a header.
            write_header = False
        else:
            # Seperate the path from the file
            write_header = True
            split_path = file.rpartition('/')
            if split_path.count('') == 2:
                # This is true if there is no folders
                pass
            else:
                # Make the path for the file if it doesn't exist
                os.mkdir(split_path[0])

        # Get items to be written
        if imgName == '':
            imgName = self._imgName
        cur_time = dt.now().strftime("%Y/%m/%d, %H:%M:%S")
        exposure = self.exposure
        gain = self.gain
        aur_flag = self._auroraFlag
        # error = None  # todo add error handling

        # todo add error to dict
        # ? should the dictionary be define here?
        dict_to_write = {'Image Name': imgName,
                         'Timestamp': cur_time,
                         'Exposure': exposure,
                         'Gain': gain,
                         'Aurora Flag': aur_flag
                         }

        # Write data from dictionary to file
        with open(file, 'a', newline='') as cFile:
            # open csv writer
            cWriter = csv.DictWriter(cFile, fieldnames=dict_to_write.keys())

            if write_header is True:
                # Write header if new file
                cWriter.writeheader()

                # ! If we write config settings it could be here
                # ! otherwise a seperate log file?

            # Write data to file
            cWriter.writerow(dict_to_write)

    def writeConfig(self):
        '''
        Write the camera configuration to a file

        TODO: To a log file?
        '''

        pass

    def auroraDetection(self, *args, **kwargs) -> str:
        '''
        Checks for aurora and returns a true or false string.
        Run \"isAurora\" for a bool
        '''
        isAuro = self.isAurora(*args, **kwargs)
        if isAuro is True:
            return "Aurora Present"
        else:
            return "No Aurora Detected"

    def _resetAuroraImages(self, size) -> None:
        '''
        Sets up default testing images for aurora detection, takes a size
        assuming image is a square for an all-sky image
        '''
        for image_detecting_vars in ['img', 'pre', 'masked', 'premask']:
            # todo: fix property
            setattr(self, image_detecting_vars, np.zeros((size, size, 3)))
        return None

    def isAurora(self, img: np.ndarray):  # ! Output TBD
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
        if img is None:
            log.warning("Image not provided, cannot check for aurora")

        # If there is no previous image, set current image as previous
        if self.pre is None:
            self.pre = img
            return

        self.pre = self.img
        pre = self.pre
        self.img = img

        # get rgb components as floats
        b, g, r = cv.split(img)
        r1 = r * 1.0
        g1 = g * 1.0
        b1 = b * 1.0

        b_p, g_p, r_p = cv.split(img)

        def maskCheck(img, pre):
            # Credit:
            # https://github.com/joncooper65/raspberry-aurora/blob/master/detect.py
            # ## Create masks from current image
            # Blue/Green ratio
            gbratio = cv.divide(b1, g1)
            maskgbratio = cv.inRange(gbratio, [0.9], [1.3])  # type: ignore
            # Red/Green ratio
            grratio = cv.divide(r1, g1)
            maskgrratio = cv.inRange(grratio, 0.9, 1.3)  # type: ignore

            # Masks for dominant green
            mask1 = cv.compare(0.95*g, 1.0*b, cv.CMP_GT)
            mask2 = cv.compare(0.95*g, 1.0*r, cv.CMP_GT)
            maskgreendominant = cv.bitwise_and(mask1, mask2)

            # Create strong green mask
            neutralMask = cv.bitwise_and(maskgrratio, maskgbratio)
            inverseNeutral = cv.bitwise_not(neutralMask)
            verygreen = cv.bitwise_and(maskgreendominant, inverseNeutral)

            # Apply masks and get images
            masked_img = cv.bitwise_and(img, img, mask=verygreen)
            masked_pre = cv.bitwise_and(pre, pre, mask=verygreen)

            # Update contained images
            self.masked = masked_img
            self.premask = masked_pre

            # Use mse to determine the changes in time
            mask_img_diff = masked_img - masked_pre
            norm_of_diff = np.linalg.norm(mask_img_diff)
            mse = float(np.mean(mask_img_diff**2))
            return norm_of_diff, mse

        def netColorCheck():
            '''
            Check total change in color between current and previous image
            '''
            # dr = (r - r_p).sum()
            # dg = (g - g_p).sum()
            # db = (b - b_p).sum()

            # Check mathematically

            pass

        mask_norm, mask_mse = maskCheck(img, pre)
        # Any 'very green' region be counted as a potential aurora
        self._auroraFlag = bool(mask_norm)
        return bool(mask_mse)

    def configFromToml(self, default=False) -> None:
        '''
        Configure Camera controls and ROI from toml file

        TODO: Assign Values so they are grabbed by the camera
        '''
        # Load Config Files
        if default is True:
            # Loads a default configuration
            config_file_path = self.tomlDefaultsPath
        else:
            config_file_path = self.tomlPath

        yoop_config = toml.load(config_file_path)

        # Setup Default Values
        controls = yoop_config['controllables']
        roi = yoop_config['roi']

        # Pass Values as kwargs to respect config functions
        self.setROI(**roi)
        self.setControllables(**controls)

        # Write Storage Locations
        self.img_folder = yoop_config['paths']['Images_Folder']
        self.imgInfoFile = yoop_config['paths']['HDF5_Folder']

        # Write Storage Locations
        self.img_name_format = yoop_config['formats']['Image_Name_Format']
        self.img_extension = yoop_config['formats']['Image_Extension']
        self.img_folder_format = yoop_config['formats']['Image_Folder_Format']
        self.img_file_format = yoop_config['formats']['Camera_Info_Format']

    @ZWOCamera.roi.getter
    def roi(self):
        # override ZWOCamera roi to output a clean display
        'Prints ROI info to terminal'
        print(f" {"start_x":<9}  {"|":<3}  {self.start_x:<3}{"\n"}"
              f" {"start_y":<9}  {"|":<3}  {self.start_y:<3}{"\n"}"
              f" {"width":<9}  {"|":<3}  {self.width:<3}{"\n"}"
              f" {"height":<9}  {"|":<3}  {self.height:<3}\n"
              f" {"binning":<9}  {"|":<3}  {self.binning:<3}\n"
              f" {"imageType":<7}  {"|":<3}  {self.imageType.name[8:]:<3}\n")
        return None

    @property
    def _roi(self):
        # Returns the values instead of a string
        '''
        Returns Region of Interest Parameters as:
        (start_x, start_y, width, height, binning, imageType)
        '''
        return (self.start_x, self.start_y, self.width, self.height,
                self.binning, self.imageType)
        # (f" {"start_x":<5}  {"|":<5}  {self.start_x:<5}\n"
        #  f" {"start_y":<5}  {"|":<5}  {self.start_y:<5}\n"
        #  f" {"width":<5}  {"|":<5}  {self.width:<5}\n"
        #  f" {"height":<5}  {"|":<5}  {self.height:<5}\n"
        #  f" {"binning":<5}  {"|":<5}  {self.binning:<5}\n"
        #  f" {"imageType":<5}  {"|":<5}  {self.imageType.name[8:]:<5}\n"
        #

    @property
    def bytesPerPixel(self):
        'property based on image type for array management'
        imgTypeIdx = self.imageType.value
        if imgTypeIdx == 0 or imgTypeIdx == 3:
            bytesPerPixel = 1
        elif imgTypeIdx == 2:
            bytesPerPixel = 2
        elif imgTypeIdx == 1:
            bytesPerPixel = 3
        else:
            raise ValueError("Invalide Image Type")

        return bytesPerPixel

    # ? Should this be changed to an 'roi getter'
    def setROI(self, width=None, height=None, binning=None, imageType=None,
               start_x=None, start_y=None) -> None:
        '''
        Set all portions of the ROI. Any unspecified params will
        remain the same.

        The height must be a multiple of 2
        The width must be a multiple of 8
        The total width or height must follow the following parameter:
        maxVal / binning  >=  start_val + val

        NOTE: When changing the binning, width, or height, the centered area
        may not align with the lens.
        '''
        # If no value specified, use original value
        if binning is None:
            binning = self.softwareBinning

        if imageType is None:
            imageType = self.imageType

        if width is None:
            width = self.width

        if height is None:
            height = self.height

        if start_x is None:
            start_x = self.start_x

        if start_y is None:
            start_y = self.start_y

        # Check for correct regional parameters
        width_check = (self._maxWidth/binning >= start_x + width)
        height_check = (self._maxHeight/binning >= start_y + height)

        # ## That parameters fit into camera requirements
        # if binning < 1 or binning > max(self._supportedBins):
        #     raise ValueError("Binning must fit in camera range: " +
        #                      f"1 - {max(self._supportedBins)}")

        if width % 8 != 0:
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

        # If imageType is a string (ie. "RGB24") use dict to find ID#
        if type(imageType) is str:
            imageType = self._dictImgType[imageType.upper()]

        # Update attributes for current roi values
        roi_params = {'width': width, 'height': height, 'start_x': start_x,
                      'start_y': start_y, 'binning': binning,
                      'imageType': imageType}

        for k, v in roi_params.items():
            setattr(self, k, v)

        # update values in camera
        pza.setStartPos(self._cameraIndex, start_x, start_y)
        pza.setROIFormat(self._cameraIndex, width, height, binning, imageType)

    @property
    def controllables(self):
        'Print control information to terminal'

        for c, v in self._dictControlVals.items():
            min = self._dictControlMin[c]
            max = self._dictControlMax[c]

            print(f"{c:<25} {"|":<3} {v:<10} | {min}  -  {max}")
        return None

    def setControllables(self, Gain=None, Exposure=None, WB_R=None, WB_B=None,
                         Offset=None, BandWidth=None, Flip=None,
                         AutoExpMaxGain=None, AutoExpMaxExpMS=None,
                         AutoExpTargetBrightness=None, HardwareBin=None,
                         HighSpeedMode=None, MonoBin=None, Temperature=None):
        '''
        Assign controllable camera parameters
        '''

        # Get all local variables and filter for controllables
        all_args = locals()
        all_args.pop('self')
        pass_args = {k: v for k, v in all_args.items() if v is not None}

        # for each controllable updated, update attribute and camera setting
        for key, val in pass_args.items():
            if val is int or str:
                # If one arg is passed assign into list before config
                if str(val).lower() == "auto":
                    # If a controllable is set to auto, keep the assigned value
                    # and update the auto portion to true [1]

                    val = [pza.getControlValue(self._cameraID,
                                               self._dictControlID[key])[0], 1]
                else:
                    # If the controllable is not auto, use assigned value and
                    # set auto to false [0]
                    val = [val, 0]
            elif val is not tuple or list:
                raise KeyError("Incorrect control type.")
            elif len(val) > 3:
                raise KeyError("Dataset should include 1 or 2 value (integer" +
                               "value, auto value)")
            self._setControllableValue(con=key, val=val[0], auto=val[1])

        return pass_args

    def _setControllableValue(self, con, val=None, auto=0):
        '''
        Sets/Prints control value. If no value is given will outprint the value
        as (Value, is(Auto)).
        Call using man_cam(self, control, value, auto)

        Parameters
        ----------
        con: int or str
            The control value that is getting updated.
        val: int; defaults to None
            The control value, if None the control will
            be printed instead.
        auto: int; defaults to 0 (not auto)
            Sets the camera setting to auto.
            Not supported on most controls.

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
            # If the method is called without a value, print to terminal
            print(f"{con_name} is {pza.getControlValue(0, con)}"
                  f" [(Value, Auto)]\nValue was not changed.")
        else:
            # Set controllable value to camera
            try:
                # Update control value
                pza.setControlValue(self._cameraID, con, val, auto)
            except pza.ASIError as zwo_error:
                # Grab error code
                error_code = zwo_error.args[1]
                # handle controls that cannot be set to camera directlly
                if error_code == 16:
                    log.info(f"Unable to set controllable {con_name.upper()} "
                             f"directly, Error Code: {error_code}\nValue is "
                             "assigned to YooperCam as attribute.")
                else:
                    log.warning("Unable to set controllable "
                                f"{con_name.upper()}.{zwo_error}")

            self._dictControlVals[con_name] = val  # update value in dictionary
            setattr(self, con_name, val)  # update attribute value

            # Print output value, value is auto if the setting was set to auto
            if auto is True:
                value = "Auto"
            else:
                value = val
            logging.debug(f"{con_name} was set to {value}")

    def liveView(self, dim=480) -> None:
        '''
        Live view with OpenCV interface.
        Press 'q' key to quit and space to pause.
        Allows live changing of gain and exposure while flagging for aurora.
        '''
        # ## SETUP ###
        # Main frame
        windowName = "Live Camera Capture"
        cv.namedWindow(windowName)
        cv.createTrackbar("Exposure", windowName, 50, 100, lambda x: None)
        cv.createTrackbar("Gain", windowName, 100, 100, lambda x: None)

        # It is useless to go above 1 second exposure for live view testing
        maximumExposureLimit = np.minimum(float(self.exposureLimits[1]), 1000)

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
        small = np.zeros((disp_size, disp_size, 3))

        state = True
        previousTime = time()
        self.configFromToml()
        self.startVideoCapture()
        error_counter = 0
        while True:
            if state is True:
                # Updating camera exposure
                exposureTime_percentage = cv.getTrackbarPos("Exposure",
                                                            windowName)
                exposureTime_us = (self.exposureLimits[0] +
                                   (maximumExposureLimit -
                                    self.exposureLimits[0]
                                    * exposureTime_percentage / 100))
                self.exposure = int(exposureTime_us)

                # Updating camera gain
                gain_percentage = cv.getTrackbarPos("Gain", windowName)
                cameraGainMin = self._dictControlMin["Gain"]
                cameraGainMax = self._dictControlMax["Gain"]
                gain = int(cameraGainMin + (cameraGainMax - cameraGainMin)
                           * gain_percentage / 100)
                self.gain = gain

                # Getting image from camera
                try:
                    # As given by the manufacturer ZWO, the refresh rate should
                    # be at least twice the exposure time plus 500 microseconds
                    refreshRate = int(2 * exposureTime_us + 500)
                    frame = pza.getVideoData(self._cameraIndex,
                                             self.bufferSize, refreshRate)
                    img = np.frombuffer(frame, dtype=np.uint8)
                    img = img.reshape(self.height, self.width,
                                      self.bytesPerPixel)

                except pza.ASIError as e:
                    print(f"Error getting video data: {e}")
                    img = np.zeros((self.width, self.width, 3))
                    error_counter = error_counter+1
                    print(error_counter)
                    continue

                # run aurora detection and display
                aur_img = cv.resize(img, (aur_size, aur_size))
                aur_txt = self.auroraDetection(aur_img)

                cv.putText(small, f"{aur_txt}", (10, disp_size-30),
                           cv.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2,)

                # Computing and displaying FPS
                currentTime = time()
                fps = 1 / (currentTime - previousTime)
                previousTime = currentTime
                cv.putText(small, f"FPS: {fps:.2f}", (10, 30),
                           cv.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

            cv.imshow(windowName, small)

            # Close the window if 'q' is pressed
            key_press = cv.waitKey(1) & 0xFF
            if key_press == ord('q') or error_counter == 10:
                break  # q for quit

            # Pause feed if space is pressed
            if key_press == ord(' '):
                state = not state  # [space] for pause

        self.stopVideoCapture()
        cv.destroyAllWindows()
