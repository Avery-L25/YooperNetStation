#!/usr/bin/env python3

import cv2 as cv
import numpy as np
import os
from os.path import join  # isfile,   getsize,  isdir
# from datetime import datetime as dt
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
import psutil
from memory_profiler import profile
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


# memory
def print_memory_usage(label=""):
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    print(f"{label} - RSS: {mem_info.rss / 1024 / 1024:.2f} MB, VMS: {mem_info.vms / 1024 / 1024:.2f} MB")


# Log
logging.basicConfig()
DEBUG2 = 11
HIGH_DEBUG = 24
DATA = 28

logging.addLevelName(DEBUG2, "DEBUG2")
logging.addLevelName(HIGH_DEBUG, "HIGH_DEBUG")
logging.addLevelName(DATA, "DATA")

log = logging.getLogger("auraCheck")
log.setLevel(level=20)
# endregion

# region Masks


def normMask(image='', dicty=''):
    '''
    Returns norm masks for r, g, and b channels. 
    If image is provided, automatically do masked version.

    When img_ref is uint8 the greater than mean isolates
    aurora better than uint16.
    '''
    sum_squares_rgb = (np.square(img_ref[:, :, 0]) + np.square(img_ref[:, :, 1])
                       + np.square(img_ref[:, :, 2]))

    # Set up masking variables
    means = []
    std1 = []
    std2 = []
    

    # If dividing by 0, it is 0/0
    sum_squares_rgb[sum_squares_rgb == 0] = 1

    # Green
    norm_g_rgb = img_ref[:, :, 1] / np.sqrt(sum_squares_rgb)
    mask_g_rgb = norm_g_rgb > (norm_g_rgb.mean())
    
    # Red
    norm_r_rgb = img_ref[:, :, 0] / np.sqrt(sum_squares_rgb)
    mask_r_rgb = norm_r_rgb > (norm_r_rgb.mean())
    
    # Blue
    norm_b_rgb = img_ref[:, :, 2] / np.sqrt(sum_squares_rgb)
    mask_b_rgb = norm_b_rgb > (norm_b_rgb.mean())
    if (dicty != '') & (image != ''):
        dicty = threeDimMasked(dicty, 'Norm >Mean Green', image,  mask_g_rgb)
        dicty = threeDimMasked(dicty, 'Norm <Mean Green', image, ~mask_g_rgb)
        dicty = threeDimMasked(dicty, 'Norm >Mean Red',   image,  mask_r_rgb)
        dicty = threeDimMasked(dicty, 'Norm <Mean Red',   image, ~mask_r_rgb)
        dicty = threeDimMasked(dicty, 'Norm >Mean Blue',  image,  mask_b_rgb)
        dicty = threeDimMasked(dicty, 'Norm <Mean Blue',  image, ~mask_b_rgb)
    return mask_r_rgb, mask_g_rgb, mask_b_rgb



def neutralMask(Num, Den, uBnd=255, lBnd=0) -> np.ndarray:
    '''
    Creates a neutral mask between two numpy array given ratios.
    If a bound is not provided, defaults to extremes.

    Parameters
    ----------
    Num: np.ndarray
        The numerator array for the mask.
    Den: np.ndarray
        The denominator array for the mask.
    uBnd: float, default 255
        The upper bound for the mask. When the ratio is no longer 'nuetral.'
    lBnd: float, default 0
        The lower bound for the mask. When the ratio is no longer 'nuetral.'

    Output
    ------
    mask: np.ndarray
        This mask will be a boolean array that covers the portion
        of the image that is 'neutral' within the provided bounds.

    Examples
    --------
    We want a mask where Green/Blue is between 1.3 and 0.9.
    >>> green = np.array([[13,12,9], [8, 2, 1]])
    >>> blue  = np.array([[10,10,10],[10,10,10]])
    >>> green / blue
    array([[1.3,1.2,0.9],
           [0.8,0.2,0.1]])
    >>> neutralMask(green, blue,  uBnd=1.3, lBnd=0.9)
    array([[ True,  True,  True],
           [False, False, False]])
    
    If instead we are looking to mask where 95% of the blue 
    is greater than the green values, we would only include
    an upperbound, uBnd.
    >>> green = np.array([[13,12,9], [8, 2, 1]])
    >>> blue  = np.array([[10,10,10],[10,10,10]])
    >>> neutralMask(green, blue, uBnd=0.95)
    array([[False, False,  True],
           [ True,  True,  True]])

    '''
    # Find Greater/Less than conditions
    upCon = uBnd * Den
    loCon = lBnd * Den

    # Create mask
    return (loCon <= Num) & (Num <= upCon)


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
    global save_masks

    if mask.shape.count(3) != 1:
        mask3d = np.repeat(mask[:, :, np.newaxis],
                           3, axis=2)
    else:
        mask3d = mask

    # Apply masks to images
    masked_image = image * mask3d
    dicty['Images'][key] = masked_image

    if save_masks is True:
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


    # Variable Constraints
    ratio_low = 0.9
    ratio_high = 1.3
    dom_percent = 0.95

    # Image statistics
    # img_mean = img_ref.mean()
    # img_stdv = img_ref.std()

    # region Dominant Percentage
    # Find Where green is dominant
    mask_dom_green = ((dom_percent * img_ref[:, :, 1] > img_ref[:, :, 2])
                      | (dom_percent * img_ref[:, :, 1] > img_ref[:, :, 0]))
    dicty = threeDimMasked(dicty,  'Dominat Percent Green Mask',  image,
                           mask_dom_green)

    # endregion

    # region Neutral Green Top
    # Get Green/Blue Ratio
    log.debug('Get Green/Blue Ratio')
    maskGB_neutral = neutralMask(img_ref[:, :, 1], img_ref[:, :, 2], ratio_high,
                                 ratio_low)
    dicty = threeDimMasked(dicty, 'GrBl Neutral Masked', image,
                           maskGB_neutral)

    # Get Green/Red Ratio
    log.debug('Get Green/Red Ratio')
    maskGR_neutral = neutralMask(img_ref[:, :, 1], img_ref[:, :, 0], ratio_high,
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
    maskBG_neutral = neutralMask(img_ref[:, :, 2], img_ref[:, :, 1], ratio_high,
                                 ratio_low)
    dicty = threeDimMasked(dicty, 'BG Neutral Masked', image,  maskBG_neutral)

    # Get Red/Green Ration
    log.debug('Get Red/Green Ratio')
    maskRG_neutral = neutralMask(img_ref[:, :, 0], img_ref[:, :, 1], ratio_high,
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

    # Norm Masks for rgb channels
    dicty = normMask(image, dicty)


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

# @profile
def maskStatsImage(image) -> dict:
    # Start empty dictionary
    dicty = {}
    dicty['Images'] = {}
    dicty['Masks'] = {}

    dic_rgb = {0:'RED', 1:'GREEN', 2:'BLUE', slice(0, 3):'ORIGINAL'}

    # Variable Constraints
    ratio_low = 0.9
    ratio_high = 1.3
    dom_percent = 0.95

    # Image statistics
    img_mean = img_ref.mean()
    img_stdv = img_ref.std()

    for i in [0, 1, 2, slice(0, 3)]:

        # Save memory by overwriting images
        # dicty['Images'] = {}

        masks = {}
        cur = img_ref[:, :, i]

        log.debug(f'Stat masks for {dic_rgb[i]}')
        # Cur masks are based of the stats of the specific channel
        masks['Cur >Mean'] = cur >= cur.mean()
        masks['Cur >Mean+STD'] = cur >= (cur.mean() + cur.std())
        masks['Cur >Mean+2STD'] = cur >= (cur.mean() + cur.std()*2)

        # Img masks are based on stats of all image channels
        masks['IMG >Mean'] = cur >= img_mean
        masks['IMG >Mean+STD'] = cur >= (img_mean + img_stdv)
        masks['IMG >Mean+2STD'] = cur >= (img_mean + img_stdv*2)

        # Save memory by ignoring these masks
        if inverse_masks is True:
            masks['Cur <Mean'] = ~masks['Cur >Mean'] 
            masks['Cur <Mean+STD'] = ~masks['Cur >Mean+STD']
            masks['Cur <Mean+2STD'] = ~masks['Cur >Mean+2STD']
            masks['IMG <Mean'] = ~masks['IMG >Mean']
            masks['IMG <Mean+STD'] = ~masks['IMG >Mean+STD'] 
            masks['IMG <Mean+2STD'] = ~masks['IMG >Mean+2STD'] 

        for k, m in masks.items():
            # if (k[0] == 'C'):
            if (type(i) is int) & (rgb_channels is True):
                # dicty = threeDimMasked(dicty,  f'{dic_rgb[i]} CHANNEL: {k}',
                #                        image, m)
                # cur3d = np.repeat(cur[:, :, np.newaxis], 3, axis=2)
                zero_cur = np.zeros(cur.shape)
                cur3d = np.repeat(zero_cur[:, :, np.newaxis], 3, axis=2)
                cur3d[:, :, i] = cur
                
                dicty = threeDimMasked(dicty, f'{dic_rgb[i]} CHANNEL: {k}',
                                        cur3d, m)
                continue

            dicty = threeDimMasked(dicty,  f'{dic_rgb[i]}: {k}',
                                   image, m)
        
    return dicty


# region Create Visual
def textOverlay(img, text):
    shape = img.shape
    offset = 0.90
    font_scale = 0.5 + shape[1] // 500
    font_bold = 2 + shape[1] // 700

    log.debug(f'Writing text overlay: {text}')
    name_img = cv.putText(img, text, (int(shape[1]*(1-offset)),
                          int(shape[0]*offset)), cv.FONT_HERSHEY_SIMPLEX,
                          font_scale,  (255, 255, 255), font_bold,)
    return name_img


# @profile
def stackImages(img_dict, width=0):
    keys = img_dict.keys()
    dict_len = len(keys)
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
            log.debug(f'Stacking image {dict_len - len(keys)} of {dict_len}')
            print_memory_usage("")

            if len(keys) == 0:
                current_row.append(np.zeros(img_shape))
            else:
                k = keys[0]
                cur_img = textOverlay(img_dict[k], k)
                current_row.append(cur_img)
                img_dict.pop(k)
                keys.remove(k)
                del cur_img
        np.hstack(current_row)
        stack.append(np.hstack(current_row))

    full = np.vstack(stack)
    img_dict.clear()
    return full


def writeGrid(img_dict, width, img_width=4000):
    grid_img = stackImages(img_dict, width=width)

    img_width = 4000
    aspect = grid_img.shape[0]/grid_img.shape[1]
    img_height = int(img_width * aspect)

    log.debug('Resize image')
    small_grid = cv.resize(grid_img, (img_width, img_height))

    log.debug('Write images')
    cv.imwrite(f'{grid_name}.jpeg',  small_grid)

    cv.imwrite(f'{grid_name}_{photo2find}{uni}.jpeg',  small_grid)
# endregion


print_memory_usage("Script start")

path2photos = 'Data/Masking'
pathList = os.listdir(path2photos)
fileOptions = [x.split('.')[0] for x in pathList]
if infile == '':
    photo2find = 'northernlightsIphone'
else:
    photo2find = infile
photoIndex = fileOptions.index(photo2find)
photo2read = join(path2photos, pathList[photoIndex])


img = cv.imread(photo2read)


# reference image as uin8 (default) or uint16 ()
img_ref = img.astype('uint16')
grid_name = 'MaskGrid16'  # default 'MaskGrid'

og = True
save_masks = False
continuing = True
rgb_channels = False  # If TRUE stats will show only the rgb channel in 
inverse_masks = False  # If TRUE stats will show a mask and inverse (double)

if continuing is True:
    if og is True:
        full_dictionary = maskSingleImage(img)
        uni = ''
        width = 0
    else:
        full_dictionary = maskStatsImage(img)
        uni = '_st'
        width = 6
    mask_dict = full_dictionary['Masks']
    img_dict = full_dictionary['Images']

    print_memory_usage('Before making grids')
    writeGrid(img_dict, width)
    print(img_dict.keys())
print_memory_usage("Script end")
