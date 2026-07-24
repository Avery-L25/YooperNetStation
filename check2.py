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

from argparse import ArgumentParser, RawDescriptionHelpFormatter
import matplotlib.pyplot as plt; plt.ion()
import pandas as pd



def threeDimMasked(image, mask):
    # Make masks 3D
    mask3d = np.repeat(mask[:, :, np.newaxis], 
                                        3, axis=2)

    # Apply masks to images
    masked_image = image * mask3d
    return masked_image


def maskSingleImage(image) -> dict:
    # Start empty dictionary
    dicty = {}
    dicty['Raw Image'] = image
    
    # Variables
    ratio_low = 0.9
    ratio_high = 1.3
    dom_percent = 0.95

    # Get Green/Blue Ratio/Mask
    ratGB = image[:, :, 1]/image[:, :, 2]    
    maskGB_neutral = ((ratio_low <= ratGB) & (ratGB <= ratio_high))
    dicty['GrBl Neutral Masked'] = threeDimMasked(image, maskGB_neutral)

    # Get Green/Red Ration
    ratGR = image[:, :, 1]/image[:, :, 0]    
    maskGR_neutral = ((ratio_low <= ratGR) & (ratGR <= ratio_high))
    dicty['GrR Neutral Masked'] = threeDimMasked(image, maskGR_neutral)

    # Get Neutral Masks
    mask_neutral = ((ratio_low <= ratGB) & (ratGB <= ratio_high)
                        & (ratio_low <= ratGR) & (ratGR <= ratio_high))
    dicty['Total Neutral Masked'] = threeDimMasked(image,mask_neutral)
    dicty['Inverse Neutral Masked'] = threeDimMasked(image, ~mask_neutral)

    # Find Where green is dominant
    mask_dom_green = ((dom_percent * image[:, :, 1] > image[:, :, 2])
                      | (dom_percent * image[:, :, 1] > image[:, :, 0]))
    dicty['Dominat Percent Green Mask'] = threeDimMasked(image, mask_dom_green)

    # Create Mask where green is dominant and the color is not neutral
    mask_inv_very_green = (~mask_neutral & mask_dom_green)
    mask_very_green = (mask_neutral & mask_dom_green)
    dicty['Regular Very Green Mask'] = threeDimMasked(image, mask_very_green)
    dicty['Inverse Very Green Mask'] = threeDimMasked(image, mask_inv_very_green)

    # Green 
    img16 = image.astype('uint16')
    sum_squares_rgb = (np.square(img16[:,:,0]) + np.square(img16[:,:,1])
                        + np.square(img16[:,:,2]))
    been_greened = img16[:,:,1] / np.sqrt(sum_squares_rgb)
    dan_gre_mask = been_greened > (been_greened.mean())
    dicty['Dan 50% Green Masked'] = threeDimMasked(image, dan_gre_mask)
    dicty['Dan 50% NOT Green Masked'] = threeDimMasked(image, ~dan_gre_mask)

    return dicty


def maskCheck(img_cur, img_pre):

    global masked_img_cur, masked_img_pre

    # green / sqrt( r^2 b^2 g^2)
    # Grab masks into a dictionary by
    # Variables
    ratio_low = 0.9
    ratio_high = 1.3
    dom_percent = 0.95

    # Get Green/Blue Ratio
    ratGB_cur = img_cur[:, :, 1]/img_cur[:, :, 2]    
    ratGB_pre = img_pre[:, :, 1]/img_pre[:, :, 2]    

    # Get Green/Red Ration
    ratGR_cur = img_cur[:, :, 1]/img_cur[:, :, 0]    
    ratGR_pre = img_pre[:, :, 1]/img_pre[:, :, 0]

    # Get Neutral Masks
    mask_neutral_cur = ((ratio_low <= ratGB_cur) & (ratGB_cur <= ratio_high)
                        & (ratio_low <= ratGR_cur) & (ratGR_cur <= ratio_high))
    mask_neutral_pre = ((ratio_low <= ratGB_pre) & (ratGB_pre <= ratio_high)
                        & (ratio_low <= ratGR_pre) & (ratGR_pre <= ratio_high))

    # Find Where green is dominant
    mask_dom_green_pre = ((dom_percent * img_pre[:, :, 1] > img_pre[:, :, 2])
                          | (dom_percent * img_pre[:, :, 1] > img_pre[:, :, 0]))
    mask_dom_green_cur = ((dom_percent * img_cur[:, :, 1] > img_cur[:, :, 2])
                          | (dom_percent * img_cur[:, :, 1] > img_cur[:, :, 0]))

    # Create Mask where green is dominant and the color is not neutral
    mask_very_green_cur = (~mask_neutral_cur & mask_dom_green_cur)
    mask_very_green_pre = (~mask_neutral_pre & mask_dom_green_pre)

    # Make masks 3D
    mask_very_green_3D_pre = np.repeat(mask_very_green_pre[:, :, np.newaxis], 
                                       3, axis=2)
    mask_very_green_3D_cur = np.repeat(mask_very_green_cur[:, :, np.newaxis], 
                                       3, axis=2)

    # Apply masks to images
    masked_img_cur = img_cur * mask_very_green_3D_cur
    masked_img_pre = img_pre * mask_very_green_3D_pre

    # Calculate Norm and MSE
    mask_img_diff = masked_img_cur-masked_img_pre
    rmse = mask_img_diff.sum()**2
    norm_of_masked = np.linalg.norm(masked_img_cur-masked_img_pre)  # Returns the normal vector
    mse = float(np.mean(mask_img_diff**2))  # Use a threshold instead?

    print(f"RMSE: {rmse}\nMSE: {mse}\nNorm: {norm_of_masked}")


def netColorCheck(img, pre):
    '''
    Check total change in color between current and previous image
    '''
    b, g, r = cv.split(img)
    r1 = r * 1.0
    g1 = g * 1.0
    b1 = b * 1.0
    b_p, g_p, r_p = cv.split(pre)
    r1_p = r_p * 1.0
    g1_p = g_p * 1.0
    b1_p = b_p * 1.0
    dr = (r - r_p).sum() / r.size
    print(f"r ({r.sum()}) - r_p({r_p.sum()}) = dr ({dr})")
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


def displayImg(img_dict):
    key_press = None
    while True:
        for k, v in img_dict.items():
            vimg = cv.resize(v, (int(v.shape[0]/4), int(v.shape[1]/4)))
            cv.imshow('displaying images', vimg)
            print(f'currently displaying {k}')
            while True:
                key_press = cv.waitKey(100) & 0xFF
                
                if key_press == ord('q'): break  # q for quit
                if key_press == ord('n'): 
                    
                    break # [space] for pause
                if key_press == ord('s'): 
                    name_img = input('save current image as???') # [space] for pause
                    cv.imwrite(name_img, v)
            if key_press == ord('q'): 
                print('breaking 2')
                break

        if key_press == ord('q'): 
            print('breaking 3')
            break
    print('destroying windows')
    cv.destroyAllWindows()

def fromVideo(self, video_file, efficient_testing=False, vis_comp=False, filename=''):
    '''
    Reads a video files to analyze frame-by-frame.

    '''
    # Read the video file
    cap = cv.VideoCapture(video_file)
    self._startTime = dt.now()
    vcd = {}
    vcd['Time(ms)'] = cv.CAP_PROP_POS_MSEC
    vcd['Time(frames)'] = cv.CAP_PROP_POS_FRAMES
    total_frames  = cap.get(cv.CAP_PROP_FRAME_COUNT)
    disp_h = int(cap.get(cv.CAP_PROP_FRAME_HEIGHT))
    disp_w = int(cap.get(cv.CAP_PROP_FRAME_WIDTH))
    # Ensure there is a file to save data too
    if filename == '':
        # If no file name provided, generate generic filename with date
        self.file = dt.now().strftime(f"Data/test_files/{(video_file.split('/')[-1]).split('.')[0]}_%m-%d_%H.csv")
    else:
        self.file = filename

    # Initialize Window for video feed
    windowName = "Video Analysis"
    four_windows =  True
    cv.namedWindow(windowName)
    shrink=2

    # Show 4 images: current, previous, masked_cur, masked_pre
    if four_windows is True:
        # define new dimensions
        disp_w = int(disp_w / shrink)
        disp_h = int(disp_h / shrink)

        # Get Display Positions
        border_width = 40

        def makePosArray(ul, dh, dw):
            '''
            ul is upper left corner of position
            dw is the display width
            dh is display heigth
            
            br is bottom right corner
            
            returns postion array:
            [[ul_x, ul_y],
                [br_x, br_y]]
                '''
            br = np.array(ul) + np.array((dw, dh))
            return np.array([ul, br])
        
        pos1 = (border_width, border_width)
        pos1 = makePosArray(pos1, disp_h, disp_w)

        pos2 = (border_width, 2*border_width+disp_w)
        pos2 = makePosArray(pos2, disp_h, disp_w)

        pos3 = (2*border_width+disp_h, border_width)
        pos3 = makePosArray(pos3, disp_h, disp_w)

        pos4 = (2*border_width+disp_h, 2*border_width+disp_w)
        pos4 = makePosArray(pos4, disp_h, disp_w)

        # Get Display Dimensions
        canvas_w = 2*disp_w + 3*border_width
        canvas_h = 2*disp_h + 3*border_width

        # Create Blank Canvas
        disp_image = np.full((canvas_h, canvas_w, 3), 100, dtype=np.uint8)
    else:
        # Create Blank Image
        disp_image = np.zeros((disp_h, disp_w, 3))

    # region Live Functions
    def make4Frames(disp_img, cur, pre, m_cur, m_pre):
        '''
        Make the display image. Write any text over image(s).
        Will put activate the multiwindow view.
        '''
        
        cur = cv.resize(cur, (disp_h, disp_w))
        pre = cv.resize(pre, (disp_h, disp_w))
        m_cur = cv.resize(m_cur, (disp_h, disp_w))
        m_pre = cv.resize(m_pre, (disp_h, disp_w))
        
        def addImg(canvas, img, pos, txt):
            '''
            canvas: the display to write on
            img: the image to write on canvas
            pos: int, which position to put on
            txt: string, what will title each image
            
            Writes the image and its titles
            '''
            try:
                canvas[pos[0, 0]:pos[1,0], pos[0,1]:pos[1, 1]] = img
                cv.putText(disp_image, txt, (pos[0, :]),
                            cv.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2,)
            except ValueError:
                
                pass
            return canvas

        # Write Image Names
        disp_img = addImg(disp_image, cur, pos1, "Current Image")
        disp_img = addImg(disp_image, pre, pos2, "Previous Image")
        disp_img = addImg(disp_image, m_cur, pos3, "Current Mask")
        disp_img = addImg(disp_image, m_pre, pos4, "Previous Mask")

        return disp_img

    state = True
    log.log(HIGH_DEBUG,f"Video Capture status before: {cap.isOpened()}")
    while cap.isOpened():

        if state:
            # Get next frame
            ret, frame = cap.read()
            self.startTime = dt.now()

            # if frame is read correctly ret is True
            if not ret:
                print("Can't receive frame (stream end?). Exiting ...")
                break
            else:
                cur_frame = cap.get(cv.CAP_PROP_POS_FRAMES)
                log.log(DATA,f"On frame {cur_frame} of {total_frames}")

            # Get video properties
            self.auraDict['Time(ms)'] = cap.get(cv.CAP_PROP_POS_MSEC)
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
            if vis_comp is True and efficient_testing is False:

                if four_windows is True:
                    display_image = make4Frames(disp_image, self.newCur,
                                                self.newPre,
                                                self.newMaskCur,
                                                self.newMaskPre)
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


                if four_windows is True:
                    cv.imshow('windows', display_image)
                else:
                    gray = cv.cvtColor(disp_frame, cv.COLOR_BGR2GRAY)
                    cv.imshow('frame', disp_frame)

                key_press = cv.waitKey(50) & 0xFF
                if key_press == ord('q'):
                    log.info(f"Frame shape: {disp_frame.shape}")

                    break
                elif key_press == ord(' '):
                    state = not state  # [space] for pause
            self.endTime = dt.now()
            self.deltaTime = self.endTime - self.startTime

    # Stop video after loop
    self._endTime = dt.now()
    cap.release()
    if vis_comp is True:
        # Close the window if it is being diplayed
        cv.destroyAllWindows()


img = cv.imread('Data/5mins.png')
img_dict = maskSingleImage(img)
