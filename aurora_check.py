#!/usr/bin/env python3

import cv2 as cv
import numpy as np
import os
import csv
import toml
from time import sleep, time
from datetime import datetime as dt
import shutil
import logging
from multiprocessing import Process, Pool

import matplotlib.pyplot as plt; plt.ion()
import pandas as pd

from YooperCam import YooperCam

logging.basicConfig()
DEBUG2 = 11
DATA = 28
logging.addLevelName(DEBUG2,"DEBUG2")
logging.addLevelName(DATA,"DATA")

log = logging.getLogger("auraCheck")
log.setLevel(level=10)

data_log = logging.getLogger("writeData")
data_1 = logging.FileHandler("data.log")
data_formatter = logging.Formatter('%(asctime)s - %(message)s')
data_1.setFormatter(data_formatter)
data_log.addHandler(data_1)
def data(msg): data_log.log(DATA, msg)

class auraCheck():
    def __init__(self, *args, **kwargs) -> None:
        self.img    = None
        self.pre    = None
        self._testingPre = {}
        self.masked = None
        self.premask= None
        self.file = None # dt.now().strftime("Data/test_files/check_data_%Y-%m-%d_%H-%M-%S.csv")
        self.auraDict = {}
        self._fileHasHeader = False
        
        # K clustering do
        self.doKCluster = False
        self._kValue = 4
        self._kSmall = 0  # 0==Reg, 1==Reg->Shrink, 2==Small
        
        self.tests = {'No Clustering':{'doKCluster':False,'_kValue':0}}
        self.auraDict['Test Name'] = 'No Clustering'
        self._doMultiProc = True
        pass


    def _resetAuroraImages(self,size) -> None:
        '''
        Sets up default testing images for aurora detection, takes a size 
        assuming image is a square for an all-sky image
        '''
        for image_detecting_vars in ['img','pre','masked','premask']:
            setattr(self,image_detecting_vars,np.zeros((size, size, 3)))  # todo: fix property
        return None

    def runTest(self, img, k, v):
        '''
        Test a k value for clustering of an image using aurora detection.
        Will test at original image size, shrinking after clustering, and small.

        Parameters
        ----------
        img : numpy array
            The working image/frame to be checked against.
        k : str
            The key from the testing dictionary, should be the name of the
            current test.        
        v : str
            The values from the testing dictionary, should contain any testing
            parameters.
        '''    
        
        curTestDict = self.auraDict.copy()
        curTestDict['Test Name'] = k
        curTestDict['K Vakue'] = v['_kValue']
        self._kValue = v['_kValue']
        
        
        # Attempt to get previous images, otherwise write as empty
        try:
            preDict = self._testingPre[k]
        except KeyError:
            preDict = {'img0':None,'img1':None,'img2':None}

        if v['doKCluster'] is True:
            self._kSmall = 0

            # Full size klustered image
            img0 = self.kClust(img)
            log.debug(f"isAurora on img0 test {k} with params {v} \n\n\n")
            x = self.isAurora(img0, curTestDict.copy(), preDict['img0'])

            # Shrunk klustered images
            img1 = cv.resize(img0,[int(img0.shape[0]/4),int(img0.shape[1]/4)])
            log.debug(f"isAurora on img1 test {k} with params {v} \n\n\n")           
            x = self.isAurora(img1, curTestDict.copy(), preDict['img1'])

            # Small klustered image
            self._kSmall = 2
            img2 = self.kClust(img)
            log.debug(f"isAurora on img2 test {k} with params {v} \n\n\n")
            x = self.isAurora(img2, curTestDict.copy(), preDict['img2'])

            # Update previous images
            preDict = {'img0':img0,'img1':img1,'img2':img2}
            self._testingPre[k] = preDict
        else:
            # Do a standard test
            log.debug(f"isAurora on default image test {k} with params {v} \n\n\n")
            x = self.isAurora(img)

    def doTests(self, image):
        '''
        Method to efficiently perform multiple analysis on the same data.
        Works through the tests defined by aura.tests.
        
        The tests are held in a dictionary with the format
        aura.tests['No Clustering']  = {'doKCluster':False,'_kValue':0}}

        Parameters
        ----------
        image : numpy array
            The working image/frame to be checked against.
       
        '''
        tests = self.tests
        
        # Incase used without doing tests
        if tests is None:
            return self.isAurora(image)
        
        # Kclustering is handled in this test instead
        self.doKCluster = False 

        # Function to run a single test
        
        if self._doMultiProc is True:
            # Create a pool of workers to process the tests
            p = Pool(len(tests.items()))

            items = []
            for key, val in tests.items():
                items.append((image, key, val))
            
            p.starmap(self.runTest, items)
            
            p.close()
            p.join()
            # Make Process for each part of a test instead
            # p1 = Process(target=tester1, args=(stop_event,))
            # p2 = Process(target=tester2, args=(stop_event,))
            # p1.start()
            # p2.start()
            # while __name__ == "__main__":
            #     time.sleep(10)
            #     print('slept 10 sec')
            # stop_event.wait(10)
            # stop_event.set()
            # p1.join()
            # p2.join()
        else:
            # Do each test, saving a large kluster rep
            for key, val in tests.items():
                self.runTest(image, key, val)

        return None

    def isAurora(self, image, dictW = None, prev = ''):
        '''
        Check most images against previous for bright, green/blue areas and
        returns a flag (bool) if detected.

        Input an image.
        Return a boolean.

        NOTE: If instead of inputing an image, it is assigned directly the
        compared \'pre\' image will not be the last camera image.

        TODO: Fix pre-image assignment. We want to be able 
        '''
        start_proc = dt.now()  # Get start of processing time
        log.info("Starting to check for aurora")
        # Ensure there is an image to work with
        if image is None:
            log.warning("Image not provided, cannot check for aurora")
        
        img = image

        # Initialize dict to write
        if type(dictW) is None:
            dictW = self.auraDict
        elif type(dictW) is not dict:
            log.warning(f"Dictionary passed to \'isAurora\' is type:{type(dictW)}")
            raise(TypeError)

        # If there is no previous image, set current image as previous
        if self.pre is None and type(prev) is str:
            # If there is no previous image  AND  a no reference image
            # Assign given image
            log.info(f"self.pre is being set to {image}")
            self.pre = image
            self.img = image
            log.debug("pre is check to be None")
            log.debug(f"self.pre = [{self.pre}] and self.img = [{self.img}]")
            return None
            log.debug(f"after the return None")
        elif self.pre is not None and type(prev) is str:
            # If there is a previous image  AND  no reference image
            # Set the old image as the previous and updates the current for next time
            log.debug("pre has been assigned and no reference image was provided")

            log.info(f"self.pre is being set to {self.img}")
            self.pre = self.img
            pre = self.pre
            self.img = img
        elif prev is None:
            return None
        elif type(prev) is np.ndarray:
            # If a reference image is provided, use it for the test instead
            # Added for klustering without multiple runs
            pre = prev
        else:
            # If unknown situation, quit
            log.error(f"Situation unknown reference image \'prev\' = {prev}"
                      f"\nself.pre = {self.pre}"
                      f"\nself.img = {self.img}")

        # Kluster the image if true
        if self.doKCluster is True:
            img = self.kClust(image, Display=False)
        
        ### get rgb components as floats

        b, g, r = cv.split(img)
        r1 = r * 1.0
        g1 = g * 1.0
        b1 = b * 1.0

        dictW['Blue']   = b.sum()/b.size
        dictW['Green']  = g.sum()/b.size
        dictW['Red']    = r.sum()/b.size

        b_p, g_p, r_p = cv.split(pre)
        r1_p = r_p * 1.0
        g1_p = g_p * 1.0
        b1_p = b_p * 1.0
        

        def maskCheck():
            # Credit:
            # https://github.com/joncooper65/raspberry-aurora/blob/master/detect.py
            global dicty
            ### Create masks from current image
            log.log(DEBUG2,"maskedCheck in Progress")
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

            if img.shape != verygreen.shape:
                log.critical(f"img and mask \'verygreen\' shape do not match\n"
                             f"img shape = {img.shape} and maske shape = {verygreen.shape}")
            # Apply masks and get images
            masked_img = cv.bitwise_and(img, img, mask=verygreen)  # Display the image only whre the verygreen mask values are
            masked_pre = cv.bitwise_and(pre, pre, mask=verygreen)

            # Update contained images
            self.masked = masked_img
            self.premask = masked_pre

            # Use mse to determine the changes in time
            mask_img_diff = masked_img - masked_pre
            norm_of_diff = np.linalg.norm(mask_img_diff)  # Returns the normal vector
            mse = float(np.mean(mask_img_diff**2))  # Use a threshold instead?
            dictW['mask_mse'] = mse
            dictW['mask_norm'] = norm_of_diff
            return norm_of_diff, mse

        def netColorCheck():
            '''
            Check total change in color between current and previous image
            '''
            dr = (r - r_p).sum() / r.size
            log.info(f"r ({r.sum()}) - r_p({r_p.sum()}) = dr ({dr})")
            dg = (g - g_p).sum() / g.size
            db = (b - b_p).sum() / b.size
            
            # Check mathematically
            r2b = dr/db
            g2b = dg/db
            color_sums = [dr, dg, db]
            dictW['dRed'] = dr
            dictW['dGreen'] = dg
            dictW['dBlue'] = db
            dictW['d_red2blue'] = r2b
            dictW['d_green2blue'] = g2b
            dictW['d_green2red'] = dg/dr

            return color_sums

       


        mask_norm, mask_mse = maskCheck()
        color_sums = netColorCheck()
                 
        log.info(f"mask_norm = {mask_norm} and mask_mse = {mask_mse}")
        self._auroraFlag = bool(mask_norm)  # currently any difference in the 'very green' region will be marked as a potential aurora

        finish_proc = dt.now()  # Get end of processing
        proc_time = finish_proc - start_proc
        log.info(f"Processing tooking {proc_time}")
        dictW['Processing Time'] = proc_time

        # Write info to csv
        if self._fileHasHeader is False: self.startCSV(self.auraDict)
        self.write2CSV(self.auraDict)
        log.info(f"finished checking for aurora")

        return (mask_mse, mask_norm, color_sums)

    def kClust(self, img, Display=False):
        start = dt.now()
        K = self._kValue

        if type(img) is str:
            img = cv.imread(img)
        
        if self._kSmall == 2:
            img = cv.resize(img, [int(img.shape[0]/4),int(img.shape[1]/4)])
        
        Z = img.reshape((-1,3))
        
        ## convert to np.float32
        Z = np.float32(Z)


        log.debug("about to define the criteria")
        ## define criteria, number of clusters(K) and apply kmeans()
        criteria = (cv.TERM_CRITERIA_EPS + cv.TERM_CRITERIA_MAX_ITER, 10, 1.0)
        ret,label,center=cv.kmeans(Z,K,None,criteria,10,cv.KMEANS_RANDOM_CENTERS)

        log.debug("after kmeans are found")
        ## Now convert back into uint8, and make original image
        center = np.uint8(center)
        res = center[label.flatten()]
        res2 = res.reshape(img.shape)
        finish = dt.now()
        delta_time = finish - start

        # Do not display during image processing.
        if Display is True:    
            # Dont shrink image twice
            if self._kSmall == 2:
                res3 = res2
            else:
                res3 = cv.resize(res2, [int(res2.shape[0]/4),int(res2.shape[1]/4)])
            

            cv.putText(img=res3, text=f"{delta_time}", org=(10, int(res3.shape[1]-15)),
                fontFace=cv.FONT_HERSHEY_SIMPLEX, fontScale=0.5,color=(255, 255, 255), thickness=2,)
            cv.imshow('res3',res3)
            while True:
                key_press = cv.waitKey(1) & 0xFF
                log.debug(f"key press {key_press}")
                if key_press == ord('q'): break  # q for quit
                if key_press == ord('s'): cv.imwrite(os.path.join('Data',input('name of file')),res3) # [space] for pause
            cv.destroyAllWindows()

        if self._kSmall == 1:
            res1 = cv.resize(res2, [int(res2.shape[0]/4),int(res2.shape[1]/4)])
            return res1
        
        return res2

    def write2CSV(self, dicty):
        log.info("writing to csv")
        with open(self.file, 'a', newline='') as cfile:
            cwrite = csv.DictWriter(cfile,fieldnames=dicty.keys())
            cwrite.writerow(dicty)

    def startCSV(self,dicty):
        if self._fileHasHeader is False:
            if os.path.exists(self.file) is False:
                with open(self.file, 'a', newline='') as cfile:
                    if self._fileHasHeader is False:
                        cwrite = csv.DictWriter(cfile,fieldnames=dicty.keys())
                        cwrite.writeheader()
                        self._fileHasHeader = True
            else:
                self._fileHasHeader = True             
        else:
            pass

    def putText(self, frame):
        log.debug(f"before isAurora is called with frame: {frame.shape}")
        checked = self.isAurora(frame)
        log.debug(f"AFTER isAurora is called with frame: {frame.shape}\n"
                f"and checked : {checked}")
    
        if checked:
            log.log(DEBUG2,f"checked is {checked}")
            mask_mse, mask_norm, color_sum = checked[:]
            dr, dg, db = color_sum[:]
            aur_txt = (f"MSE from masking: {round(mask_mse,4)} \nNorm from masking"
                    f": {round(mask_norm,2)}\nRed:{round(dr,3)}\nGreen:{round(dg,3)}\nBlue:{round(db,3)}")
        else:
            aur_txt = "No previous image, wait until next image"
        
        txt_offset = cv.getTextSize(aur_txt,cv.FONT_HERSHEY_SIMPLEX,0.5,2)
        aur_txt = aur_txt.split('\n')
        x=0
        disp_frame = frame.copy()
        for i in (aur_txt):
            cv.putText(img=disp_frame, text=f"{i}", org=(10, int(disp_frame.shape[1]-15-x*1.25*txt_offset[0][1])),
            fontFace=cv.FONT_HERSHEY_SIMPLEX, fontScale=0.5,color=(255, 255, 255), thickness=2,)
            x=x+1
        
        return disp_frame

    def fromVideo(self, video_file, efficient_testing=False, vis_comp=False, filename=''):
        '''
        Reads a video files to analyze frame-by-frame.
        
        '''
        # Read the video file
        cap = cv.VideoCapture(video_file)
        vcd = {}
        vcd['Time(ms)'] = cv.CAP_PROP_POS_MSEC
        vcd['Time(frames)'] = cv.CAP_PROP_POS_FRAMES
        total_frames  = cap.get(cv.CAP_PROP_FRAME_COUNT)
        # Ensure there is a file to save data too
        if filename == '':
            # If no file name provided, generate generic filename with date
            self.file = dt.now().strftime(f"Data/test_files/{(video_file.split('/')[-1]).split('.')[0]}_%m-%d_%H.csv")
        else:
            self.file = filename

        # Begin frame by frame analysis
        state = True
        while cap.isOpened():
            if state:
                # Get next frame
                ret, frame = cap.read()

                # if frame is read correctly ret is True
                if not ret:
                    print("Can't receive frame (stream end?). Exiting ...")
                    break
                else:
                    cur_frame = cap.get(cv.CAP_PROP_POS_FRAMES)
                    log.info(f"On frame {cur_frame} of {total_frames}")
                # Get video properties
                self.auraDict['Time(ms)']     = cap.get(cv.CAP_PROP_POS_MSEC)
                self.auraDict['Time(frames)'] = cap.get(cv.CAP_PROP_POS_FRAMES)

                # Determine checking method
                if efficient_testing is True:
                    log.info("Do multiple tests in single run")
                    self.doTests(frame)
                else:
                    # If we do not have multiple tests check aurora directly
                    log.debug(f"before isAurora is called with frame: {frame.shape}")
                    checked = self.isAurora(frame)
                    log.debug(f"AFTER isAurora is called with frame: {frame.shape}\n"
                            f"and checked : {checked}")

                # should the image be display
                if vis_comp is True:
                    
                    # Check image
                    if checked:
                        log.log(DEBUG2,f"checked is {checked}")
                        mask_mse, mask_norm, color_sum = checked[:]
                        dr, dg, db = color_sum[:]
                        aur_txt = (f"MSE from masking: {round(mask_mse,4)} \nNorm from masking"
                                f": {round(mask_norm,2)}\nRed:{round(dr,3)}\nGreen:{round(dg,3)}\nBlue:{round(db,3)}")
                    else:
                        aur_txt = "No previous image, wait until next image"
                    
                    txt_offset = cv.getTextSize(aur_txt,cv.FONT_HERSHEY_SIMPLEX,0.5,2)
                    aur_txt = aur_txt.split('\n')
                    x=0
                    disp_frame = frame
                    for i in (aur_txt):
                        cv.putText(img=disp_frame, text=f"{i}", org=(10, int(disp_frame.shape[1]-15-x*1.25*txt_offset[0][1])),
                        fontFace=cv.FONT_HERSHEY_SIMPLEX, fontScale=0.5,color=(255, 255, 255), thickness=2,)
                        x=x+1



                    gray = cv.cvtColor(disp_frame, cv.COLOR_BGR2GRAY)
                    cv.imshow('frame', disp_frame)

                    key_press = cv.waitKey(1) & 0xFF
                    if key_press == ord('q'):
                        log.info(f"Frame shape: {disp_frame.shape}")

                        break
                    elif key_press == ord(' '): 
                        state = not state  # [space] for pause


        # Stop video after loop
        cap.release()
        if vis_comp is True:
            # Close the window if it is being diplayed
            cv.destroyAllWindows()

    def fromPhotos(self, folder="Data/test_photos", efficient_testing=False, vis_comp=False, filename=''):
        '''
        Test auroras from a series of photos given a directory.
        '''
        log.debug(f"starting the \'fromPhotos\' method with folder={folder}")
        
        # Get a list of photos from the directory
        photos = self.dir2files(folder)
        photos.sort()
        num_photos = len(photos)
        log.info(f"there is {num_photos}")
        

        # Ensure there is a file to write data too
        if filename == '':
            self.file = dt.now().strftime(f"Data/test_files/{(folder.split('/')[-1]).split('.')[0]}_%m-%d_%H.csv")
        else:
            self.file = filename

        # Prepare display params
        disp_size = 800
        border_width = 40 
        windowName = "Testing Images"

        def makeImage(img):
            'Create a display to show current and previous images'
            scale = img.shape[1]/img.shape[0]
            width = scale*disp_size
            pos1 = (border_width, border_width)
            pos2 = (2*border_width+width, border_width)
            canvas_size = 2*width + 3*border_width
            disp_image = np.full((canvas_size, disp_size,3),100, dtype=np.uint8)
            return disp_image

        def stopOrGo(msg='Press space/n/c to continue, q to quit, or s to save image'):  # -> bool:
            'Get user input to continue setup'
            while True:
                key_press = cv.waitKey(1) & 0xFF
                log.debug(f"key press {key_press}")
                if key_press == ord('q'): return 'quit'  # q for quit
                if key_press == ord(' '): return 'next' # [space] for pause
                if key_press == ord('s'): return 'save' # [space] for pause

        # Analyze photos in a sequence
        for p in photos:

            log.info(f"This is photo {p}\n there are {num_photos} left")
            num_photos = num_photos - 1
            self.auraDict['photo'] = p.rpartition('/')[2]
            self.auraDict['folder'] = p.split('/')[-2]
            if "Identifier" in p:
                # photos.remove(p)
                log.warning("Was not photo, skipping\n\n")
                continue

            cur = cv.imread(p)

            if efficient_testing is True:
                log.info("Do multiple tests in single run")
                self.doTests(cur)
            elif vis_comp:
                # put text on image after a test
                display_img = self.putText(cur)
                disp_this = cv.resize(display_img,[int(display_img.shape[0]/4),int(display_img.shape[1]/4)])
                cv.imshow(windowName, disp_this)
                cv.waitKey(1)
                sOg = stopOrGo()
                # Check for input
                if sOg == 'quit':  # Wait 25 ms before next frame
                    break
                elif sOg == 'save':
                    saveName = input("save name? (no safety)")
                    words = saveName.split(' ')
                    nameForCur = words[0] + '.png'
                    nameForFull= words[0] + '_display.png'
                    cv.imwrite(nameForCur, cur)
                    cv.imwrite(nameForFull,display_img)
                    continue
                elif sOg == 'next':
                    log.info("Moving to next photo\n\n\n")
                    continue
            else:
                # If we do not have multiple tests check aurora directly without displaying
                log.debug(f"before isAurora is called with frame: {cur.shape}")
                checked = self.isAurora(cur)
                log.debug(f"AFTER isAurora is called with frame: {cur.shape}\n"
                        f"and checked : {checked}")
        
        if vis_comp:
            cv.waitKey(1)
            cv.destroyAllWindows()
            log.info("Windows destroyed")
        
    def fromLive(self, ycam):
        '''
        Test auroras from a directory
        '''
        log.debug(f"starting the \'fromLive\' method ")
        # image height
        self.file = dt.now().strftime(f"Data/test_files/Live_%m-%d_%H.csv")

        disp_size = 800
        border_width = 40
        windowName = "Live Aurora Check"
        vis_comp = False
        display = False
        def stopOrGo(msg='Press space/n/c to continue, q to quit, or s to save image'):  # -> bool:
            'Get user input to continue setup'
            while True:
                key_press = cv.waitKey(1) & 0xFF
                log.debug(f"key press {key_press}")
                if key_press == ord('q'): return 'quit'  # q for quit
                if key_press == ord(' '): return 'pause' # [space] for pause
                if key_press == ord('s'): return 'save' # [space] for pause
 
        while True:
            log.info(f"This is photo {dt.now()}\n")
            self.auraDict['photo'] = dt.now().strftime("%d/%m/%Y, %H:%M:%S")

            # go in order  somehow.
            cur = ycam.shot(exposure=1, return_img=True)

            display_img = self.putText(cur)
            disp_this = cv.resize(display_img,[int(display_img.shape[0]/4),int(display_img.shape[1]/4)])
            if display is True: 
                cv.imshow(windowName, disp_this)
            cv.waitKey(1)

            key_press = cv.waitKey(1) & 0xFF
            log.debug(f"key press {key_press}")
            if key_press == ord('q'): break  # q for quit
            if key_press == ord(' '): vis_comp = True # [space] for pause

            if vis_comp:
                sOg = stopOrGo()
                # Check for input
                if sOg == 'quit':  # Wait 25 ms before next frame
                    break
                elif sOg == 'save':
                    saveName = input("save name? (no safety)")
                    words = saveName.split(' ')
                    nameForCur = words[0] + '.png'
                    nameForFull= words[0] + '_display.png'
                    cv.imwrite(nameForCur, cur)
                    cv.imwrite(nameForFull,display_img)
                    continue
                elif sOg == 'next':
                    log.info("Continuing\n\n\n")
                    continue
                vis_comp=False
            else:
                pass

    def dir2files(self, direc):
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
    
    def plotCSV(self, file='', avg_color=False):
        'Plot aurora checking data from csv file'

        # Declare global variables for external work
        global df, colors
        
        # Get latest file if none provided
        if file == '':
            try:
                path_true = os.path.exists(self.file)
            except TypeError:
                path_true = False
            if path_true:
                file=self.file
            else:
                files_to_choose = os.listdir("Data/test_files")
                files_to_choose.sort()
                for f in files_to_choose:
                    if f.find(".csv") == -1:
                        files_to_choose.remove(f)
                file = files_to_choose[-1]
                file = f"Data/test_files/{file}"
        # Read data
        df = pd.read_csv(file, header=0)
        # Get figure
        fig, ax = plt.subplots(3,2, sharex=True,sharey=False)
        r2g = df['dRed']/df['dGreen']
        ax0 = [ax[0,0].twinx(),ax[0,1].twinx()]
        ax2 = [ax[2,0].twinx(),ax[2,1].twinx()]
        average_color_diff = (df['dBlue'] + df['dGreen'] + df['dRed'] )/3

        # initialize constants
        x = range(0,df.shape[0])
        colors = {'mask_mse':'gray',
                  'mask_norm':'darkviolet',
                  'Red':'red',
                  'Green':'green',
                  'Blue':'blue',
                  'dRed':'tomato',
                  'dGreen':'lime',
                  'dBlue':'cornflowerblue',
                  'd_green2red':'navy'}
        xcx = ("color=colors[\'mask_mse\'], linewidth=1.0")

        # Edit figure
        fig.subplots_adjust(top=0.95,
                            bottom=0.05,
                            left=0.075,
                            right=0.925,
                            hspace=0.2,
                            wspace=0.2)
        # plt.xlim(0,1000)
        def plotLine(axes, value, twins=False, color = "black", linewidth=0.5, linestyle='solid'):
            dicts = {'df':df,'color':colors}
            vals_dict ={'color'       : "black", 
                        'linewidth'   : 0.5, 
                        'linestyle'   :'solid'}
            if type(value) is str:
                vals_dict['label'] = value
                for k in dicts.keys():
                    cur_dict = dicts[k]
                    if value in cur_dict.keys():
                        vals_dict[k] = cur_dict[value]
                    else:
                        pass
                
                try:
                    graphing_val = vals_dict.pop('df')
                except KeyError:
                    log.warning(f"No Data for {value}")
                    return
                axes.plot(graphing_val, **vals_dict)
            else:
                axes.plot(value, color=color, linewidth=linewidth, linestyle=linestyle, label='No name provided')
            
            if twins is True:
                axes.legend(loc='upper right')
            else:
                axes.legend(loc='upper left')

        # write data to plots side by side plots
        for l in [0,1]:
            
            # ax[0,l].plot(df['mask_mse'],  color=colors['mask_mse'], linewidth=0.5)
            # ax0[l].plot( df['mask_norm'], color=colors['mask_norm'],linewidth=0.5)
            plotLine(ax[0,l], "mask_mse")
            plotLine(ax0[l], "mask_norm", twins=True)
            if avg_color is False:
                plotLine(ax[1,l], 'dRed')
                plotLine(ax[1,l], 'dGreen')
                plotLine(ax[1,l], 'dBlue')
                # ax[1,l].plot(df['dRed'],      color=colors['dRed'],     linewidth=0.5)
                # ax[1,l].plot(df['dGreen'],    color=colors['dGreen'],   linewidth=1, linestyle='dashed')
                # ax[1,l].plot(df['dBlue'],     color=colors['dBlue'],    linewidth=0.5, linestyle=(0, (5, 10)))
            else:
                plotLine(ax[1,l], average_color_diff)

            #     ax[1,l].plot(average_color_diff,     color="Black",    linewidth=0.5)
            plotLine(ax[2,l], 'd_green2red')
            plotLine(ax2[l], "mask_mse", twins=True)
        
            # ax[2,l].plot(r2g,             color='navy',             linewidth=0.5)
            # ax2[l].plot( df['mask_mse'],  color=colors['mask_mse'], linewidth=0.5)

        # yscale on rightside plots
        for k in [0,1,2]:
            ax[k,1].set_yscale('log')
        ax0[1].set_yscale('log')
        ax2[1].set_yscale('log')

        # Make grid
        for g in [0,1,2]:
            for h in [0,1]:
                ax[g,h].grid(axis='x')
                if g == 0:
                    ax0[h].grid(axis='x')
                    ax2[h].grid(axis='x')
            # grax = fig.add_subplot(111)
            # for _, spine in grax.spines.items():
            #     spine.set_visible(False)
            # grax.tick_params(labelleft=False, labelbottom=False, left=False, right=False )
            # # grax.        
            # grax.grid(axis="x")


def plotLine(axes, value, twins=False, color = "black", linewidth=0.5, linestyle='solid'):
        dicts = {'df':df,'color':colors}
        vals_dict ={'color'       : "black", 
                    'linewidth'   : 0.5, 
                    'linestyle'   :'solid'}
        if type(value) is str:
            vals_dict['label'] = value
            for k in dicts.keys():
                cur_dict = dicts[k]
                if value in cur_dict.keys():
                    vals_dict[k] = cur_dict[value]
                else:
                    pass
            
            try:
                graphing_val = vals_dict.pop('df')
            except KeyError:
                log.warning(f"No Data for {value}")
                return
            axes.plot(graphing_val, **vals_dict)
        else:
            axes.plot(value, color=color, linewidth=linewidth, linestyle=linestyle, label='No name provided')
        
        if twins is True:
            axes.legend(loc='upper right')
        else:
            axes.legend(loc='upper left')


def plotColorComparison(df):
    'Plot aurora checking data from csv file'
    global fig, ax, ax0, ax1, ax2, plot
    # Get figure
    fig, ax = plt.subplots(3, sharex=True,sharey=False)
    r2g = df['dRed']/df['dGreen']
    ax0 = [ax[0],ax[0].twinx()]
    ax1 = [ax[1],ax[1].twinx()]
    ax2 = [ax[2],ax[2].twinx()]
    average_color_diff = (df['dBlue'] + df['dGreen'] + df['dRed'] )/3

    # initialize constants
    x = range(0,df.shape[0])

    xcx = ("color=colors[\'mask_mse\'], linewidth=1.0")

    # Edit figure
    fig.subplots_adjust(top=0.95,
                        bottom=0.05,
                        left=0.075,
                        right=0.925,
                        hspace=0.2,
                        wspace=0.2)
    # plt.xlim(0,1000)
    

    # write data to plots side by side plots
    plotLine(ax0[0], 'dRed')
    plotLine(ax1[0], 'dGreen')
    plotLine(ax2[0], 'dBlue')
    plotLine(ax0[1], 'Red',    twins=True, linewidth=1, linestyle='dashed')
    plotLine(ax1[1], 'Green',  twins=True, linewidth=1, linestyle='dashed')
    plotLine(ax2[1], 'Blue',   twins=True, linewidth=1, linestyle='dashed')

    # Make grid
    for g in [ax0,ax1,ax2]:
        for h in [0,1]:
            g[h].grid(axis='x')

if __name__ == "__main__":
    x = auraCheck()
    
    # File to analyze
    files2check = 'video_name.mp4'
    
    # Tests to do
    x.tests['No Clustering'] = {'doKCluster':False,'_kValue':0}
    x.tests['Kluster 2']     = {'doKCluster':True ,'_kValue':2}
    x.tests['Kluster 3']     = {'doKCluster':True ,'_kValue':3}
    x.tests['Kluster 4']     = {'doKCluster':True ,'_kValue':4}
    x.tests['Kluster 6']     = {'doKCluster':True ,'_kValue':6}
    x.tests['Kluster 8']     = {'doKCluster':True ,'_kValue':8}
    x.tests['Kluster 10']    = {'doKCluster':True ,'_kValue':10}

    
    x.fromVideo(video_file=files2check, efficient_testing=True,
                filename=dt.now().strftime(f"Nov3_25_gill_%m-%d_%H.csv"))