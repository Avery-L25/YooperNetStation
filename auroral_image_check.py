#!/usr/bin/env python3
'''
Given an image (or file), create masking steps to identify
potential aurora for image comparisons.

Saves the created masks in a grid image titled 'MaskedGrid.jpeg'
for viewing and analysis.
'''

import cv2 as cv
import numpy as np
import os
from os import path
import psutil
import logging
from argparse import ArgumentParser, RawDescriptionHelpFormatter
import matplotlib.pyplot as plt
plt.ion()
# from memory_profiler import profile ### Commented out while not debugging
# import shutil

# Variables
ratio_low = 0.9
ratio_high = 1.3
dom_percent = 0.95

# Constants
IMAGE_EXTENSIONS = ['png', 'jpeg', 'jpg', 'jpe', 'webp']
DIC_RGB = {0: 'RED', 1: 'GREEN', 2: 'BLUE', slice(0, 3): 'RGB'}

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
def log_mem(label=""):
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    log.log(19, f"{label} - RSS: {mem_info.rss / 1024 / 1024:.2f} MB, " +
            f"VMS: {mem_info.vms / 1024 / 1024:.2f} MB")


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

log_mem("Script start")


class AuroraImage(object):
    '''
    Class to mask images
    '''

    def init(self, imagedata):

        # Get image as numpy array from provided data
        if type(imagedata) is str:
            # imagedate is a file, attempt to load image from string location
            rawimg = cv.imread(imagedata)

            # if image was not read, search for file in subdirectories
            if rawimg is None:
                # Ensure that only looking for file name
                filename = imagedata.rpartition('/')[2]

                # Search subdirectories for file containing provided name
                for root, _, files in os.walk('Data', topdown=False):

                    if files == []:
                        # Pass if no files in directory
                        continue
                    elif type(files) is list:
                        for file in files:
                            # Check each file for matching name
                            if filename.lower() in file.lower():
                                # Pass if file is not in accepted file type
                                file_ext = file.rpartition('.')[2]
                                if file_ext not in IMAGE_EXTENSIONS:
                                    log.debug('File with incorrect '
                                              + f'extension \'{file_ext}\''
                                              + 'found, continuing.')
                                    continue

                                # Write path to file that matches
                                imgpath = path.join(root, file)
                                if rawimg is None:
                                    # Read first image found and log
                                    log.info('First file found matching ' +
                                             f'input criteria: {imgpath}')
                                    rawimg = cv.imread(imgpath)
                                else:
                                    log.warning('Found additional file ' +
                                                'matchin input criteria: ' +
                                                imgpath)

                    if rawimg is None:
                        raise LookupError('Could not find image file '
                                          + f'\'{imagedata}\'')
        elif type(imagedata) is np.array:
            rawimg = imagedata
        else:
            raise TypeError('Imagedata is not a path or numpy array ' +
                            f'(Type: {type(imagedata)})')

        # Set current image
        self.curimg = rawimg.astype('uint16')

        # Set file name
        self.save_file = 'MaskGrid'

        # Setup dictionary
        self.maskDict = {}

        # Set configuring variables
        # When masking based on a single RGB channel, display only 1 color
        self.rgb_channels = False
        # When true creates inverse masks, ie mask = img > img.mean() and ~mask
        self.inverse_masks = False

    # region Masks

    def normMask(self, image):
        '''
        Returns norm masks for r, g, and b channels.
        If image is provided, automatically do masked version.

        When img_ref is uint8 the greater than mean isolates
        aurora better than uint16.
        '''
        img_ref = image.astype('uint16')
        mask_dict = self.maskDict
        sum_squares_rgb = (np.square(img_ref[:, :, 0]) +
                           np.square(img_ref[:, :, 1]) +
                           np.square(img_ref[:, :, 2]))

        # Set up masking variables

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

        mask_dict['Norm >Mean Green'] = mask_g_rgb
        mask_dict['Norm <Mean Green'] = ~mask_g_rgb
        mask_dict['Norm >Mean Red'] = mask_r_rgb
        mask_dict['Norm <Mean Red'] = ~mask_r_rgb
        mask_dict['Norm >Mean Blue'] = mask_b_rgb
        mask_dict['Norm <Mean Blue'] = ~mask_b_rgb

        return mask_r_rgb, mask_g_rgb, mask_b_rgb

    def neutralMask(self, Num, Den, uBnd=255.0, lBnd=0.0):
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
            The upper bound for the mask.
            When the ratio is no longer 'neutral'.
        lBnd: float, default 0
            The lower bound for the mask.
            When the ratio is no longer 'neutral'.

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
        array([[True,  True,  True],
            [False, False, False]])

        If instead we are looking to mask where 95% of the blue
        is greater than the green values, we would only include
        an upperbound, uBnd.
        >>> green = np.array([[13,12,9], [8, 2, 1]])
        >>> blue  = np.array([[10,10,10],[10,10,10]])
        >>> neutralMask(green, blue, uBnd=0.95)
        array([[False, False,  True],
            [True,  True,  True]])

        '''
        # Find Greater/Less than conditions
        upCon = uBnd * Den
        loCon = lBnd * Den

        # Create mask
        return (loCon <= Num) & (Num <= upCon)

    def threeDimMasked(self, mask):
        '''
        Make 2D masks 3D to match the image format

        Parameters
        ----------
        mask:   np.ndarray
            A boolean array to show what portions of the image
            are being looked at.

        Output
        ------
        mask3d: np.array
            Returns the input mask as a 3D mask.
            If the input mask was 2D, is is copied across RGB channels.
        '''

        # Ensure that the mask is across all RGB channels
        if mask.shape.count(3) != 1:
            # If mask is 2D, copy along RGB channels
            mask3d = np.repeat(mask[:, :, np.newaxis],
                               3, axis=2)
        else:
            # if mask is already 3D, return
            mask3d = mask

        return mask3d

    # def maskImages(mask, text):

    # endregion

    def maskSingleImage(self, image):
        # Start empty dictionary
        mask_dict = self.maskDict
        mask_dict['Raw Image'] = np.ones(image.shape, dtype=bool)

        # Image statistics
        # region Dominant Percentage
        # Find Where green is dominant
        mask_dom_green = (self.neutralMask(image[:, :, 2], image[:, :, 1],
                                           dom_percent)
                          | self.neutralMask(image[:, :, 0], image[:, :, 1],
                                             dom_percent))
        mask_dict['Dominat Percent Green Mask'] = mask_dom_green

        # endregion

        # region Neutral Green Top
        # Get Green/Blue Ratio
        log.debug('Get Green/Blue Ratio')
        maskGB_neutral = self.neutralMask(image[:, :, 1], image[:, :, 2],
                                          ratio_high, ratio_low)
        mask_dict['Green/Blue Neutral Masked'] = maskGB_neutral

        # Get Green/Red Ratio
        log.debug('Get Green/Red Ratio')
        maskGR_neutral = self.neutralMask(image[:, :, 1], image[:, :, 0],
                                          ratio_high, ratio_low)
        mask_dict['Green/Red Neutral Masked'] = maskGR_neutral

        # Get Neutral Masks
        mask_Gtop_neutral = (maskGB_neutral & maskGR_neutral)
        mask_dict['Total Neutral Gt Masked'] = mask_Gtop_neutral
        mask_dict['Inverse Neutral Gt Masked'] = ~mask_Gtop_neutral

        # Create Mask where green is dominant and the color is not neutral
        mask_inv_very_green = (~mask_Gtop_neutral & mask_dom_green)
        mask_very_green = (mask_Gtop_neutral & mask_dom_green)
        mask_dict['Regular Top Very Green Mask'] = mask_very_green
        mask_dict['Inverse Top Very Green Mask'] = mask_inv_very_green
        # endregion

        # region Neutral Green Bottom
        # Get Blue/Green Ratio/Mask
        log.debug('Get Blue/Green Ratio')
        maskBG_neutral = self.neutralMask(image[:, :, 2], image[:, :, 1],
                                          ratio_high, ratio_low)
        mask_dict['BG Neutral Masked'] = maskBG_neutral

        # Get Red/Green Ration
        log.debug('Get Red/Green Ratio')
        maskRG_neutral = self.neutralMask(image[:, :, 0], image[:, :, 1],
                                          ratio_high, ratio_low)
        mask_dict['RG Neutral Masked'] = maskRG_neutral

        # Get Neutral Masks
        mask_Gbot_neutral = (maskBG_neutral & maskRG_neutral)
        mask_dict['Total Neutral Gbot Masked'] = mask_Gbot_neutral
        mask_dict['Inverse Neutral Gbot Masked'] = ~mask_Gbot_neutral

        # Create Mask where green is dominant and the color is not neutral
        mask_inv_very_bot_green = (~mask_Gbot_neutral & mask_dom_green)
        mask_very_bot_green = (mask_Gbot_neutral & mask_dom_green)
        mask_dict['Regular Bottom Very Green Mask'] = mask_very_bot_green
        mask_dict['Inverse Bottom Very Green Mask'] = mask_inv_very_bot_green
        # endregion

        # Norm Masks for rgb channels
        mask_r_rgb, mask_g_rgb, mask_b_rgb = self.normMask(image)

        # region Trial Combos
        # Greater Green Mean Less Red Mean
        gr_not_red = mask_g_rgb & ~mask_r_rgb
        mask_dict['>MeanG & <MeanR'] = gr_not_red

        # >MeanG & <MeanB and the opposite
        gb_green = mask_g_rgb & ~mask_b_rgb
        mask_dict['>MeanG & <MeanB'] = gb_green
        gb_red = ~mask_g_rgb & mask_b_rgb
        mask_dict['<MeanG & >MeanB'] = gb_red

        # Combine
        both_gr_from_gb = gb_green | gb_red
        mask_dict['Green Blue Norm'] = both_gr_from_gb

        # # endregion

    # @profile
    def maskStatsImage(self, image):
        # Start empty dictionary
        masks_dict = self.maskDict

        # Image statistics
        img_mean = image.mean()
        img_stdv = image.std()

        for i in [0, 1, 2, slice(0, 3)]:
            # Save memory by overwriting images
            cur = image[:, :, i]

            log.debug(f'Stat masks for {DIC_RGB[i]}')
            # Cur masks are based of the stats of the specific channel
            masks_dict[f'{DIC_RGB[i]}: Cur >Mean'] = cur >= cur.mean()
            masks_dict[f'{DIC_RGB[i]}: Cur >Mean+STD'] = cur >= (cur.mean()
                                                                 + cur.std())
            masks_dict[f'{DIC_RGB[i]}: Cur >Mean+2STD'] = cur >= (cur.mean()
                                                                  + cur.std()
                                                                  * 2)

            # Img masks_dict are based on stats of all image channels
            masks_dict[f'{DIC_RGB[i]}: IMG >Mean'] = cur >= img_mean
            masks_dict[f'{DIC_RGB[i]}: IMG >Mean+STD'] = cur >= (img_mean
                                                                 + img_stdv)
            masks_dict[f'{DIC_RGB[i]}: IMG >Mean+2STD'] = cur >= (img_mean
                                                                  + img_stdv*2)

    # region Create Visual

    def textOverlay(self, img, text):
        shape = img.shape
        offset = 0.90
        font_scale = 0.5 + shape[1] // 500
        font_bold = 2 + shape[1] // 700

        log.debug(f'Writing text overlay: {text}')
        name_img = cv.putText(img, text, (int(shape[1]*(1-offset)),
                                          int(shape[0]*offset)),
                              cv.FONT_HERSHEY_SIMPLEX, font_scale,
                              (255, 255, 255), font_bold,)
        return name_img

    # @profile
    def stackImages(self, img_dict, width=0):
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
                log.debug(f'Stacking image {dict_len-len(keys)} of {dict_len}')
                log_mem("")

                if len(keys) == 0:
                    current_row.append(np.zeros(img_shape))
                else:
                    k = keys[0]
                    cur_img = self.textOverlay(img_dict[k], k)
                    current_row.append(cur_img)
                    img_dict.pop(k)
                    keys.remove(k)
                    del cur_img
            np.hstack(current_row)
            stack.append(np.hstack(current_row))

        full = np.vstack(stack)
        img_dict.clear()
        return full

    def writeGrid(self, img_dict, width, img_width=4000):
        grid_img = self.stackImages(img_dict, width=width)

        img_width = 4000
        aspect = grid_img.shape[0]/grid_img.shape[1]
        img_height = int(img_width * aspect)

        log.debug('Resize image')
        small_grid = cv.resize(grid_img, (img_width, img_height))

        log.debug('Write images')
        cv.imwrite(f'{self.save_file}.jpeg',  small_grid)

        # cv.imwrite(f'{self.save_file}_{photo2find}{uni}.jpeg',  small_grid)
    # endregion


log_mem("Script end")
