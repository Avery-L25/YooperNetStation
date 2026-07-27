#!/usr/bin/env python3

import cv2 as cv
import numpy as np
import os
from os.path import join  # isfile,   getsize,  isdir
from datetime import datetime as dt
# import h5py
# from os import path # , listdir
# import glob
# import toml
# import csv
# import toml
# from time import sleep, time
# import shutil
# from multiprocessing import Process, Pool
# import pandas as pd

import logging
from argparse import ArgumentParser, RawDescriptionHelpFormatter
import matplotlib.pyplot as plt
plt.ion()

# region Input
parser = ArgumentParser(description=__doc__,
                        formatter_class=RawDescriptionHelpFormatter)
parser.add_argument('-l', '--loglevel',  type=int, default=25,
                    help='Logger level for debugging' +
                    '10 for max, 21 for high, 30 for warnings/errors.')
parser.add_argument("-o", "--outfile", default='',  help="Set " +
                    "output file name. Defaults to generic csv from datetime.")
parser.add_argument("-i", "--infile", default='',  help="Assign file to read.")

# Handle arguments:
args = parser.parse_args()

logging_value = args.loglevel
outfile = args.outfile
infile = args.infile

# Log
logging.basicConfig()
DEBUG2 = 11
HIGH_DEBUG = 24
DATA = 28

logging.addLevelName(DEBUG2, "DEBUG2")
logging.addLevelName(HIGH_DEBUG, "HIGH_DEBUG")
logging.addLevelName(DATA, "DATA")

log = logging.getLogger("auraCheck")
log.setLevel(level=10)
# endregion

# region Masks


def neutralMask(Num, Den, uBnd, lBnd) -> np.ndarray:
    '''
    Creates a neutral mask between two numpy array given bounds.
    Made to handle potential zero issues in divisions.

    Parameters
    ----------
    Num: np.ndarray
        The numerator array for the mask.
    Den: np.ndarray
        The denominator array for the mask.
    uBnd: float
        The upper bound for the mask. When the ratio is no longer 'nuetral.'
    lBnd: float
        The lower bound for the mask. When the ratio is no longer 'nuetral.'

    Output
    ------
    mask: np.ndarray
        This mask will be a boolean array that covers the portion
        of the image that is 'neutral' within the provided bounds.

    '''
    # Find zeros in numerator.
    # If numerator == 0 it will not be neutral.
    num_zero = np.where(Num == 0)
    Den[num_zero] = 1

    # Find remaining zeros in denominator.
    # Consider all cases to be 'Not Neutral'
    # #! This could be adjusted to give certain level neutral
    den_zero = np.where(Den == 0)
    Num[den_zero] = 0
    Den[den_zero] = 1

    # Should have no errors now
    ratio = Num/Den
    return (lBnd <= ratio) & (ratio <= uBnd)


def threeDimMasked(dicty,  key, image,  mask) -> dict:
    '''
    Make 2D masks 3D to match the image format

    Parameters
    ----------
    dicty:  dict
        Store the mask and masked image for analysis.
    key:    str
        The name to store value under in dicty.
    image:  np.ndarray
        The image being worked with. Will be masked for
        trial detections.
    mask:   np.ndarray
        A boolean array to show what portions of the image
        are being looked at.

    Output
    ------
    dicty: dict
        returns the input dictionary with the new 3D mask and masked image
    '''
    mask3d = np.repeat(mask[:, :, np.newaxis],
                       3, axis=2)

    # Apply masks to images
    masked_image = image * mask3d
    dicty['Images'][key] = masked_image
    dicty['Masks'][key] = mask3d
    return dicty


# endregion


def maskSingleImage(image) -> dict:
    # Start empty dictionary
    dicty = {}
    dicty['Images'] = {}
    dicty['Masks'] = {}
    dicty['Images']['Raw Image'] = image
    dicty['Masks']['Raw Image'] = np.zeros(image.shape)

    # Make img an unsigned 16-bit integer to handle 0 errors
    img16 = image.astype('uint16')

    # Variables
    ratio_low = 0.9
    ratio_high = 1.3
    dom_percent = 0.95

    # region Dominant Percentage
    # Find Where green is dominant
    mask_dom_green = ((dom_percent * img16[:, :, 1] > img16[:, :, 2])
                      | (dom_percent * img16[:, :, 1] > img16[:, :, 0]))
    dicty = threeDimMasked(dicty,  'Dominat Percent Green Mask',  image,
                           mask_dom_green)

    # endregion

    # region Neutral Green Top
    # Get Green/Blue Ratio
    log.debug('Get Green/Blue Ratio')
    maskGB_neutral = neutralMask(img16[:, :, 1], img16[:, :, 2], ratio_high,
                                 ratio_low)
    dicty = threeDimMasked(dicty, 'GrBl Neutral Masked', image,
                           maskGB_neutral)

    # Get Green/Red Ratio
    log.debug('Get Green/Red Ratio')
    maskGR_neutral = neutralMask(img16[:, :, 1], img16[:, :, 0], ratio_high,
                                 ratio_low)
    dicty = threeDimMasked(dicty, 'GrR Neutral Masked', image,  maskGR_neutral)

    # Get Neutral Masks
    mask_Gtop_neutral = (maskGB_neutral & maskGR_neutral)
    dicty = threeDimMasked(dicty, 'Total Neutral Gt Masked', image,
                           mask_Gtop_neutral)
    dicty = threeDimMasked(dicty, 'Inverse Neutral Gt Masked', image,
                           ~mask_Gtop_neutral)

    # Create Mask where green is dominant and the color is not neutral
    mask_inv_very_green = (~mask_Gtop_neutral & mask_dom_green)
    mask_very_green = (mask_Gtop_neutral & mask_dom_green)
    dicty = threeDimMasked(dicty, 'Regular Top Very Green Mask', image,
                           mask_very_green)
    dicty = threeDimMasked(dicty, 'Inverse Top Very Green Mask', image,
                           mask_inv_very_green)
    # endregion

    # region Neutral Green Bottom
    # Get Blue/Green Ratio/Mask
    log.debug('Get Blue/Green Ratio')
    maskBG_neutral = neutralMask(img16[:, :, 2], img16[:, :, 1], ratio_high,
                                 ratio_low)
    dicty = threeDimMasked(dicty, 'BG Neutral Masked', image,  maskBG_neutral)

    # Get Red/Green Ration
    log.debug('Get Red/Green Ratio')
    maskRG_neutral = neutralMask(img16[:, :, 0], img16[:, :, 1], ratio_high,
                                 ratio_low)
    dicty = threeDimMasked(dicty, 'RG Neutral Masked', image,  maskRG_neutral)

    # Get Neutral Masks
    mask_Gbot_neutral = (maskBG_neutral & maskRG_neutral)
    dicty = threeDimMasked(dicty, 'Total Neutral Gbot Masked', image,
                           mask_Gbot_neutral)
    dicty = threeDimMasked(dicty, 'Inverse Neutral Gbot Masked', image,
                           ~mask_Gbot_neutral)

    # Create Mask where green is dominant and the color is not neutral
    mask_inv_very_bot_green = (~mask_Gbot_neutral & mask_dom_green)
    mask_very_bot_green = (mask_Gbot_neutral & mask_dom_green)
    dicty = threeDimMasked(dicty, 'Regular Bottom Very Green Mask', image,
                           mask_very_bot_green)
    dicty = threeDimMasked(dicty, 'Inverse Bottom Very Green Mask', image,
                           mask_inv_very_bot_green)
    # endregion

    # region Norm Masks
    sum_squares_rgb = (np.square(img16[:, :, 0]) + np.square(img16[:, :, 1])
                       + np.square(img16[:, :, 2]))
    # If dividing by 0, it is 0/0
    sum_squares_rgb[sum_squares_rgb == 0] = 1

    # Green
    norm_g_rgb = img16[:, :, 1] / np.sqrt(sum_squares_rgb)
    mask_g_rgb = norm_g_rgb > (norm_g_rgb.mean())
    dicty = threeDimMasked(dicty, 'Norm >Mean Green', image,  mask_g_rgb)
    dicty = threeDimMasked(dicty, 'Norm <Mean Green', image,
                           ~mask_g_rgb)
    # Red
    norm_r_rgb = img16[:, :, 0] / np.sqrt(sum_squares_rgb)
    mask_r_rgb = norm_r_rgb > (norm_r_rgb.mean())
    dicty = threeDimMasked(dicty, 'Norm >Mean', image,  mask_r_rgb)
    dicty = threeDimMasked(dicty, 'Norm <Mean Red', image,
                           ~mask_r_rgb)
    # Blue
    norm_b_rgb = img16[:, :, 2] / np.sqrt(sum_squares_rgb)
    mask_b_rgb = norm_b_rgb > (norm_b_rgb.mean())
    dicty = threeDimMasked(dicty, 'Norm >Mean Blue', image,  mask_b_rgb)
    dicty = threeDimMasked(dicty, 'Norm <Mean Blue', image,
                           ~mask_b_rgb)

    # endregion

    # region Trial Combos
    # Greater Green Mean Less Red Mean
    gr_not_red = mask_g_rgb & ~mask_r_rgb
    dicty = threeDimMasked(dicty, '>MeanG & <MeanR', image,
                           gr_not_red)

    # >MeanG & <MeanB and the opposite
    gb_green = mask_g_rgb & ~mask_b_rgb
    dicty = threeDimMasked(dicty, '>MeanG & <MeanB', image,
                           gb_green)
    gb_red = ~mask_g_rgb & mask_b_rgb
    dicty = threeDimMasked(dicty, '<MeanG & >MeanB', image,
                           gb_red)
    # Combine
    both_gr_from_gb = gb_green | gb_red
    dicty = threeDimMasked(dicty, 'Green Blue Norm', image,
                           both_gr_from_gb)

    # endregion
    return dicty


# region Old Functions

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
                          | (dom_percent * img_pre[:, :, 1] > img_pre[:, :, 0])
                          )
    mask_dom_green_cur = ((dom_percent * img_cur[:, :, 1] > img_cur[:, :, 2])
                          | (dom_percent * img_cur[:, :, 1] > img_cur[:, :, 0])
                          )

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
    # Returns the normal vector
    norm_of_masked = np.linalg.norm(masked_img_cur-masked_img_pre)
    mse = float(np.mean(mask_img_diff**2))  # Use a threshold instead?

    print(f"RMSE: {rmse}\nMSE: {mse}\nNorm: {norm_of_masked}")


def netColorCheck(img, pre):
    '''
    Check total change in color between current and previous image
    '''
    b, g, r = cv.split(img)
    # r1 = r * 1.0
    # g1 = g * 1.0
    # b1 = b * 1.0
    b_p, g_p, r_p = cv.split(pre)
    # r1_p = r_p * 1.0
    # g1_p = g_p * 1.0
    # b1_p = b_p * 1.0
    dr = (r - r_p).sum() / r.size
    print(f"r ({r.sum()}) - r_p({r_p.sum()}) = dr ({dr})")
    dg = (g - g_p).sum() / g.size
    db = (b - b_p).sum() / b.size

    # Check mathematically
    # r2b = dr/db
    # g2b = dg/db
    color_sums = [dr, dg, db]
    # dictW['dRed'] = dr
    # dictW['dGreen'] = dg
    # dictW['dBlue'] = db
    # dictW['d_red2blue'] = r2b
    # dictW['d_green2blue'] = g2b
    # dictW['d_green2red'] = dg/dr

    return color_sums


def fromVideo(self, video_file,  efficient_testing=False,  vis_comp=False,
              filename=''):
    '''
    Reads a video files to analyze frame-by-frame.

    '''
    # Read the video file
    cap = cv.VideoCapture(video_file)
    self._startTime = dt.now()
    vcd = {}
    vcd['Time(ms)'] = cv.CAP_PROP_POS_MSEC
    vcd['Time(frames)'] = cv.CAP_PROP_POS_FRAMES
    total_frames = cap.get(cv.CAP_PROP_FRAME_COUNT)
    disp_h = int(cap.get(cv.CAP_PROP_FRAME_HEIGHT))
    disp_w = int(cap.get(cv.CAP_PROP_FRAME_WIDTH))
    # Ensure there is a file to save data too
    if filename == '':
        # If no file name provided, generate generic filename with date
        self.file = dt.now().strftime("Data/test_files/" +
                                      (video_file.split('/')[-1]).split('.')[0]
                                      + "_%m-%d_%H.csv")
    else:
        self.file = filename

    # Initialize Window for video feed
    windowName = "Video Analysis"
    four_windows = True
    cv.namedWindow(windowName)
    shrink = 2

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

    def make4Frames(disp_img, cur, pre,  m_cur, m_pre):
        '''
        Make the display image. Write any text over image(s).
        Will put activate the multiwindow view.
        '''

        cur = cv.resize(cur, (disp_h, disp_w))
        pre = cv.resize(pre,  (disp_h, disp_w))
        m_cur = cv.resize(m_cur, (disp_h, disp_w))
        m_pre = cv.resize(m_pre,  (disp_h, disp_w))

        def addImg(canvas, img, pos, txt):
            '''
            canvas: the display to write on
            img: the image to write on canvas
            pos: int, which position to put on
            txt: string, what will title each image

            Writes the image and its titles
            '''
            try:
                canvas[pos[0, 0]:pos[1, 0], pos[0, 1]:pos[1, 1]] = img
                cv.putText(disp_image,  txt, (pos[0, :]),
                           cv.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2,)
            except ValueError:

                pass
            return canvas

        # Write Image Names
        disp_img = addImg(disp_image,  cur, pos1, "Current Image")
        disp_img = addImg(disp_image,  pre,  pos2, "Previous Image")
        disp_img = addImg(disp_image,  m_cur, pos3, "Current Mask")
        disp_img = addImg(disp_image,  m_pre,  pos4, "Previous Mask")

        return disp_img

    state = True
    log.log(HIGH_DEBUG, f"Video Capture status before: {cap.isOpened()}")
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
                    display_image = make4Frames(disp_image,  self.newCur,
                                                self.newPre,
                                                self.newMaskCur,
                                                self.newMaskPre)
                # Check image
                if checked:
                    log.log(DEBUG2, f"checked is {checked}")
                    mask_mse,  mask_norm, color_sum = checked[:]
                    dr, dg, db = color_sum[:]
                    aur_txt = (f"MSE from masking: {round(mask_mse, 4)} \n" +
                               "Norm from masking"
                               f": {round(mask_norm, 2)}\nRed:{round(dr, 3)}\n"
                               + f"Green:{round(dg, 3)}\nBlue:{round(db, 3)}")
                else:
                    aur_txt = "No previous image,  wait until next image"

                txt_offset = cv.getTextSize(aur_txt, cv.FONT_HERSHEY_SIMPLEX,
                                            0.5, 2)
                aur_txt = aur_txt.split('\n')
                x = 0
                disp_frame = frame
                for i in (aur_txt):
                    cv.putText(img=disp_frame,  text=f"{i}",
                               org=(10, int(disp_frame.shape[1]-15-x * 1.25 *
                                            txt_offset[0][1])),
                               fontFace=cv.FONT_HERSHEY_SIMPLEX, fontScale=0.5,
                               color=(255, 255, 255), thickness=2,)
                    x = x + 1

                if four_windows is True:
                    cv.imshow('windows',  display_image)
                else:
                    # gray = cv.cvtColor(disp_frame,  cv.COLOR_BGR2GRAY)
                    cv.imshow('frame',  disp_frame)

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


def displayImg(img_dict):
    key_press = None
    while True:
        for k, v in img_dict.items():
            vimg = cv.resize(v, (int(v.shape[0]/4), int(v.shape[1]/4)))
            cv.imshow('displaying images',  vimg)
            print(f'currently displaying {k}')
            while True:
                key_press = cv.waitKey(100) & 0xFF

                if key_press == ord('q'):
                    break  # q for quit
                if key_press == ord('n'):
                    break  # [space] for pause
                if key_press == ord('s'):
                    # [space] for pause
                    name_img = input('save current image as???')
                    cv.imwrite(name_img, v)
            if key_press == ord('q'):
                print('breaking 2')
                break

        if key_press == ord('q'):
            print('breaking 3')
            break
    print('destroying windows')
    cv.destroyAllWindows()


# endregion


def textOverlay(img, text):
    shape = img.shape
    offset = 0.90
    font_scale = 1 + shape[1] // 500
    font_bold = 3 + shape[1] // 1250
    name_img = cv.putText(img, text, (int(shape[1]*(1-offset)),
                          int(shape[0]*offset)), cv.FONT_HERSHEY_SIMPLEX,
                          font_scale,  (255, 255, 255), font_bold,)
    return name_img


def stackImages(img_dict, width=0):
    keys = img_dict.keys()
    list(keys)
    keys = list(keys)
    if width == 0:
        width = int(np.round(np.sqrt(len(keys))))

    # Get Shape to finish a row with blank squares
    img_shape = img_dict[keys[0]].shape

    stack = []

    while len(keys) != 0:
        current_row = []
        for i in range(0, width):
            if len(keys) == 0:
                current_row.append(np.zeros(img_shape))
            else:
                k = keys[0]
                cur_img = textOverlay(img_dict[k], k)
                current_row.append(cur_img)
                keys.remove(k)
        np.hstack(current_row)
        stack.append(np.hstack(current_row))

    full = np.vstack(stack)
    return full


path2photos = 'Data/Masking'
pathList = os.listdir(path2photos)
fileOptions = [x.split('.')[0] for x in pathList]
if infile == '':
    photo2find = '5mins'
else:
    photo2find = infile
photoIndex = fileOptions.index(photo2find)
photo2read = join(path2photos, pathList[photoIndex])


img = cv.imread(photo2read)

full_dictionary = maskSingleImage(img)
mask_dict = full_dictionary['Masks']
img_dict = full_dictionary['Images']

grid_img = stackImages(img_dict)

img_width = 4000
aspect = grid_img.shape[0]/grid_img.shape[1]
img_height = int(img_width * aspect)

small_grid = cv.resize(grid_img, (img_width, img_height))

cv.imwrite('MaskGrid.jpeg',  small_grid)
cv.imwrite(f'MaskGrid_{photo2find}.png',  small_grid)
