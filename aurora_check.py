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


import matplotlib.pyplot as plt; plt.ion()
import pandas as pd


logging.basicConfig()
DEBUG2 = 11
DATA = 28
logging.addLevelName(DEBUG2,"DEBUG2")
logging.addLevelName(DATA,"DATA")

log = logging.getLogger("auraCheck")
log.setLevel(level=30)

data_log = logging.getLogger("writeData")
data_1 = logging.FileHandler("data.log")
data_formatter = logging.Formatter('%(asctime)s - %(message)s')
data_1.setFormatter(data_formatter)
data_log.addHandler(data_1)
def data(msg): data_log.log(DATA, msg)

class auraCheck():
    def __init__(self) -> None:
        self.img = None
        self.pre = None
        self.masked = None
        self.premask = None
        self.file = None # dt.now().strftime("Data/test_files/check_data_%Y-%m-%d_%H-%M-%S.csv")
        self.auraDict = {}
        self._fileHasHeader = False
        
        pass

    def auroraDetection(self,*args,**kwargs) -> str:
        '''
        Checks for aurora and returns a true or false string. 
        Run \"isAurora\" for a bool
        '''
        isAuro = self.isAurora(*args,**kwargs)
        if isAuro is True:
            return "Aurora Present"
        else:
            return "No Aurora Detected"

    def _resetAuroraImages(self,size) -> None:
        '''
        Sets up default testing images for aurora detection, takes a size 
        assuming image is a square for an all-sky image
        '''
        for image_detecting_vars in ['img','pre','masked','premask']:
            setattr(self,image_detecting_vars,np.zeros((size, size, 3)))  # todo: fix property
        return None

    def isAurora(self,img):
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
        log.debug("before checking if there is a previous image")
        if self.pre is None:
            self.pre = img
            self.img = img
            log.debug("pre is check to be None")
            log.debug(f"self.pre = [{self.pre}] and self.img = [{self.img}]")
            return None
            log.debug(f"after the return None")
        log.debug("after the pre image is checked")
        log.debug(f"1.\nimg = {img.shape}\n"
                  f"self.pre = {self.pre.shape}\n"
                  f"self.img = {self.img}")

        self.pre = self.img
        log.debug(f"2.\nimg = {img.shape}\n"
                  f"self.pre = {self.pre.shape}\n"
                  f"self.img = {self.img}")
        pre = self.pre
        log.debug(f"3.\nimg = {img.shape}\n"
                  f"self.pre = {self.pre.shape}\n"
                  f"self.img = {self.img}")
        self.img = img
        log.debug(f"4.\nimg = {img.shape}\n"
                  f"self.pre = {self.pre.shape}\n"
                  f"self.img = {self.img}")
        ### get rgb components as floats

        b, g, r = cv.split(img)
        r1 = r * 1.0
        g1 = g * 1.0
        b1 = b * 1.0

        self.auraDict['Blue']   = b.sum()/b.size
        self.auraDict['Green']  = g.sum()/b.size
        self.auraDict['Red']    = r.sum()/b.size

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
            self.auraDict['mask_mse'] = mse
            self.auraDict['mask_norm'] = norm_of_diff
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
            self.auraDict['dRed'] = dr
            self.auraDict['dGreen'] = dg
            self.auraDict['dBlue'] = db
            self.auraDict['red2blue'] = r2b
            self.auraDict['green2blue'] = g2b
            self.auraDict['green2red'] = dg/dr

            return color_sums



        mask_norm, mask_mse = maskCheck()
        color_sums = netColorCheck()
                 
        log.info(f"mask_norm = {mask_norm} and mask_mse = {mask_mse}")
        self._auroraFlag = bool(mask_norm)  # currently any difference in the 'very green' region will be marked as a potential aurora

        if self._fileHasHeader is False: self.startCSV(self.auraDict)
        self.write2CSV(self.auraDict)
        return (mask_mse, mask_norm, color_sums)

    def write2CSV(self, dicty):
        with open(self.file, 'a', newline='') as cfile:
            cwrite = csv.DictWriter(cfile,fieldnames=dicty.keys())
            cwrite.writerow(dicty)

    def startCSV(self,dicty):
        if self._fileHasHeader is False:
            try:
                with open(self.file, 'rb') as cfile:
                    sniffer = csv.Sniffer()
                    self._fileHasHeader = sniffer.has_header(cfile.read(2048))
            except FileNotFoundError:
                log.debug(f"File was not found. {self.file}")
                self._fileHasHeader = False
            with open(self.file, 'a', newline='') as cfile:
                if self._fileHasHeader is False:
                    cwrite = csv.DictWriter(cfile,fieldnames=dicty.keys())
                    cwrite.writeheader()
                    self._fileHasHeader = True
        else:
            pass


    def fromVideo(self, video_file):
        
        cap = cv.VideoCapture(video_file)
        self.file = dt.now().strftime(f"Data/test_files/{(video_file.split('/')[-1]).split('.')[0]}_%d_%H-%M.csv")
        state = True
        while cap.isOpened():
            if state:
                ret, frame = cap.read()

                # if frame is read correctly ret is True
                if not ret:
                    print("Can't receive frame (stream end?). Exiting ...")
                    break
                
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


        cap.release()
        cv.destroyAllWindows()

    def fromPhotos(self,folder="Data/test_photos"):
        '''
        Test auroras from a directory
        '''
        log.debug(f"starting the \'fromPhotos\' method with folder={folder}")
        photos = os.listdir(folder)
        windowName = "Testing Images"

        # image height
        disp_size = 800
        border_width = 40 

        def makeImage(img):
            scale = img.shape[1]/img.shape[0]
            width = scale*disp_size
            pos1 = (border_width, border_width)
            pos2 = (2*border_width+width, border_width)
            canvas_size = 2*width + 3*border_width
            disp_image = np.full((canvas_size, disp_size,3),100, dtype=np.uint8)
            return disp_image

        def stopOrGo(msg='Press space/n/c to continue, q to quit, or s to save image'):  # -> bool:
            'Get user input to continue setup'
            usr_in = None
            while True:
                usr_in = input(f"{msg}\n")
                if usr_in.lower() in ['q', 'Q', 'quit']:
                    return 'quit'
                elif usr_in.lower() in [' ', '  ', 'n', 'next', 'c']:
                    return 'next'
                elif usr_in.lower() in ['s']:
                    return 'save'

        for p in photos:
            # go in order  somehow.
            photo = f"{folder}/{p}"
            cur = cv.imread(photo)

            checked = self.isAurora(cur)

            disp_img = makeImage(cur)
            if checked:
                mask_mse, mask_norm = checked
                aur_txt = (f"MSE from masking: {mask_mse}\nNorm (???) from masking"
                        f": {mask_norm}")
            else:
                aur_txt = "No previous image, wait until next image"
            cv.putText(disp_img, f"{aur_txt}", (10, disp_size-30), cv.FONT_HERSHEY_SIMPLEX, 1,(255, 255, 255), 2,)

            cv.imshow(windowName, cur)
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
                cv.imwrite(nameForFull,disp_img)
                continue
            elif sOg == 'next':
                continue

    def plotCSV(self, file='', avg_color=False):
        'Plot aurora checking data from csv file'
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
        df = pd.read_csv(file,header=0)
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
                  'dRed':'red',
                  'dGreen':'green',
                  'dBlue':'blue',
                  'green2red':'navy'}
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
            plotLine(ax[2,l], 'green2red')
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
        

if __name__ == "__main__":
    x = auraCheck()
    log.debug("in main if statement")
    log.debug("after video attempt")
    x.plotCSV()
            