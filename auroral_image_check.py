#!/usr/bin/env python3
'''
Given an image (or file), create masking steps to identify
potential aurora in image comparison.

Save the created masks in a grid image titled 'MaskGrid.jpeg'
for viewing and analysis by calling the stackImages() method.
'''

import cv2 as cv
import numpy as np
import os
from os import path
import psutil
import gc
import logging
from argparse import ArgumentParser, RawDescriptionHelpFormatter
import matplotlib.pyplot as plt
plt.ion()
# from memory_profiler import profile ### Commented out while not debugging
# import shutil

# Variables
ratio_low = 0.9
ratio_high = 1.3
dom_percent = 1.05

# Constants
IMAGE_EXTENSIONS = ['png', 'jpeg', 'jpg', 'jpe', 'webp']
DIC_RGB = {0: 'RED', 1: 'GREEN', 2: 'BLUE', slice(0, 3): 'RGB'}
RGB_CHANNEL = slice(0, 3)

# region Input
parser = ArgumentParser(description=__doc__,
                        formatter_class=RawDescriptionHelpFormatter)
parser.add_argument("-i", "--infile", default=None,  help="Set file to read.")
parser.add_argument("-o", "--outfile", default='MaskGrid.jpeg',  help="Set " +
                    "output file name. Defaults to \'MaskGrid.jpeg\'.")
parser.add_argument('-l', '--loglevel',  type=int, default=20,
                    help='Logger level for debugging' +
                    '10 for max, 19 for memory, 30 for warnings/errors.')

# Handle arguments:
args = parser.parse_args()

infile = args.infile  # File to read, if not provided skip
outfile = args.outfile  # File to output too
logging_value = args.loglevel  # Level to display logging information


# memory
def get_memory(label=""):
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    mem_text = (f"{label} - RSS: {mem_info.rss / 1024 / 1024:.2f} MB, " +
                f"VMS: {mem_info.vms / 1024 / 1024:.2f} MB")
    return mem_text


def log_mem(txt=''):
    log.log(19, get_memory(txt))


# Log
logging.basicConfig()
DEBUG2 = 11
HIGH_DEBUG = 24
DATA = 28

# Add logging levels
logging.addLevelName(DEBUG2, "DEBUG2")
logging.addLevelName(HIGH_DEBUG, "HIGH_DEBUG")
logging.addLevelName(DATA, "DATA")

log = logging.getLogger("auraCheck")
log.setLevel(level=logging_value)
# endregion

log.info(get_memory("Script start"))


class AuroraImage(object):
    '''
    Apply a variety of masks to an image.
    Use masks to compare multiple images and
    analyze for potential aurora.

    Use AuroraImage_1 - AuroraImage_2 to
    calculate the MSE using standard masks.
    '''

    def __init__(self, imagedata):

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
        self.image = rawimg.astype('uint16')

        # Set file name
        self.save_file = 'MaskGrid.jpeg'

        # Set configuring variables
        # When masking based on a single RGB channel, display only 1 color
        self.rgb_channels = False
        # When true creates inverse masks, ie mask = img > img.mean() and ~mask
        self.inverse_masks = False
        # Determines if standard deviation masks are made in norm masking
        self.thoroughNorm = False
        # Exclude values above the minimum when using mean in the image
        self.nonMinStat = True
        self.minRGBValue = 10

        # Setup dictionary
        self.maskDict = {}

        # Define comparison criteria
        self.compareMasks = ['Inverse Neutral Gt Masked', 'RGB: Cur >Mean',
                             'Norm >Mean - 0.25 STD Green']

    def __sub__(self, other):
        product = self.compare(other, masks=self.compareMasks)
        return product

    # region Masks

    def normMask(self, channels=[0, 1, 2]):
        '''
        Returns norm masks for r, g, and b channels.
        If image is provided, automatically do masked version.

        When img_ref is uint8 the greater than mean isolates
        aurora better than uint16.

        If the thoroughNorm attribute is True, in addition to
        the greater than and less than the mean masks, several
        masks using standard deviation will be made including:
        > mean - 0.5 * std
        > mean + 0.5 * std
        > mean + 2.0 * std

        Parameters
        ----------
        channels: list, defaults to [0,1,2]
            Choose which channels to get masks for.
            Defaults to all RGB channels
        '''
        img_ref = self.image.astype('uint16')
        mask_dict = self.maskDict
        sum_squares_rgb = (np.square(img_ref[:, :, 0]) +
                           np.square(img_ref[:, :, 1]) +
                           np.square(img_ref[:, :, 2]))

        # Set up masking variables
        mean_masks = []
        # If dividing by 0, it is 0/0
        sum_squares_rgb[sum_squares_rgb == 0] = 1

        for i in channels:
            # Get working value
            norm = img_ref[:, :, i] / np.sqrt(sum_squares_rgb)
            clr = DIC_RGB[i]  # Current color for the dictionary

            # Get mask above the mean
            mean = norm > (norm.mean())
            mean_masks.append(mean)

            if self.thoroughNorm is True:
                # Get Several STD numbers
                stdm0_25 = norm > (norm.mean() - norm.std() * 0.25)
                stdm0_5 = norm > (norm.mean() - norm.std() * 0.5)
                stdm1 = norm > (norm.mean() - norm.std())
                std0_25 = norm > (norm.mean() + norm.std() * 0.25)
                std0_5 = norm > (norm.mean() + norm.std() * 0.5)
                std1 = norm > (norm.mean() + norm.std())
                std2 = norm > (norm.mean() + norm.std() * 2)

                # Save masks
                mask_dict[f'Norm >Mean - 1 STD {clr}'] = stdm1
                mask_dict[f'Norm >Mean - 0.5 STD {clr}'] = stdm0_5
                mask_dict[f'Norm >Mean - 0.25 STD {clr}'] = stdm0_25
                mask_dict[f'Norm >Mean {clr}'] = mean
                mask_dict[f'Norm <Mean {clr}'] = ~mean
                mask_dict[f'Norm >Mean + 0.25 STD {clr}'] = std0_25
                mask_dict[f'Norm >Mean + 0.5 STD {clr}'] = std0_5
                mask_dict[f'Norm >Mean + 1 STD {clr}'] = std1
                mask_dict[f'Norm >Mean + 2 STD {clr}'] = std2
            else:
                mask_dict[f'Norm >Mean {clr}'] = mean
                mask_dict[f'Norm <Mean {clr}'] = ~mean

        return mean_masks

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

    def domPercentMask(self, Channel=1, dom=1.05):
        '''
        Creates a mask where the given rgb channel excedes
        other channel values by a given ratio.

        Parameters
        ----------
        Channel: int, defaults to 1 (green)
            The integer value for RGB channels.
            R=0, G=1, B=2
        dom: float, defaults to 1.05
            The ratio that Channel over the remaining
            channels must excede for the mask.

        Output
        ------
        mask: np.ndarray
            This mask will be a boolean array that covers the portion
            of the image that is 'dominant' with the given ratio.

        Examples
        --------
        We want a mask where Green/Blue is greater than 1.05.
        This is the same as where Green is 105% of the Blue value.
        >>> green = np.array([[13,12,9], [8, 2, 1]])
        >>> blue  = np.array([[10,10,10],[10,10,10]])
        >>> green / blue
        array([[1.3,1.2,0.9],
               [0.8,0.2,0.1]])
        >>> neutralMask(green, blue, uBnd=0.95)
        array([[True,  True,  False],
               [False, False, False]])
        '''
        image = self.image
        rgb = [0, 1, 2]
        rgb.remove(Channel)

        return ((image[:, :, Channel] >= image[:, :, rgb[0]] * dom)
                | (image[:, :, Channel] >= image[:, :, rgb[1]] * dom))

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

    # region Library of Masks

    def allDefaultMasks(self):
        '''
        Get the basic group of masks from the
        Basic, Norm, and Stats methods
        '''
        self.maskBasicImage()
        self.maskNormImage()
        self.maskStatsImage()

    def maskBasicImage(self):
        '''
        Add ratio based masks to the dictionary.
        Uses the neutralMask and domPercentMask methods
        with the high and low ratios, and the dominant percentage
        to get several default masking combinations.
        '''
        mask_dict = self.maskDict
        image = self.image

        # Find Where green is dominant
        mask_dom_green = self.domPercentMask(Channel=1, dom=dom_percent)
        mask_dict['Dominat Percent Green Mask'] = mask_dom_green

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

    def maskNormImage(self):
        '''
        Add norm based masks to the dictionary.
        Uses the normMask method to get several
        default masking combinations.
        '''
        mask_dict = self.maskDict

        # Norm Masks for rgb channels
        mask_r_rgb, mask_g_rgb, mask_b_rgb = self.normMask()

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

    # @profile
    def maskStatsImage(self, image=None):
        '''
        Add statistics based masks to the dictionary.
        Uses the mean value of different channels of the
        image to isolate dominant portions of the image.
        '''

        masks_dict = self.maskDict

        # Image statistics
        if image is None:
            image = self.image

        if self.nonMinStat is True:
            img_mean = image[image >= self.minRGBValue].mean()
            img_stdv = image[image >= self.minRGBValue].std()
        else:
            img_mean = image.mean()
            img_stdv = image.std()

        for i in [0, 1, 2, slice(0, 3)]:
            # Save memory by overwriting images
            cur = image[:, :, i]
            chan = DIC_RGB[i]

            if self.nonMinStat is True:
                cur_mean = cur[cur >= self.minRGBValue].mean()
                cur_std = cur[cur >= self.minRGBValue].std()
            else:
                cur_mean = cur.mean()
                cur_std = cur.std()

            log.debug(f'Stat masks for {chan}')
            # Cur masks are based of the stats of the specific channel
            masks_dict[f'{chan}: Cur >Mean'] = cur >= cur_mean
            masks_dict[f'{chan}: Cur >Mean+STD'] = cur >= (cur_mean
                                                           + cur_std)
            masks_dict[f'{chan}: Cur >Mean+2STD'] = cur >= (cur_mean
                                                            + cur_std
                                                            * 2)

            # Img masks_dict are based on stats of all image channels
            masks_dict[f'{chan}: IMG >Mean'] = cur >= img_mean
            masks_dict[f'{chan}: IMG >Mean+STD'] = cur >= (img_mean
                                                           + img_stdv)
            masks_dict[f'{chan}: IMG >Mean+2STD'] = cur >= (img_mean
                                                            + img_stdv*2)

    # endregion

    # region Create Visual
    def compare(self, other, masks=None):
        '''
        Compare two images using the same masking method.

        Parameters
        ----------
        masks: list, defaults to None
            List of mask keys to use while comparing two images.
        '''
        if masks is None:
            log.error('No masks where given to compare.')
            masks = self.maskDict.keys()

        cur_img = self.applyMasks(masks)
        pre_img = other.applyMasks(masks)

        # Calculate MSE
        mask_img_diff = cur_img - pre_img
        mse = float(np.mean(mask_img_diff**2))
        # rmse = np.sqrt(np.mean((mask_img_diff)**2))
        # norm_of_masked = np.linalg.norm(mask_img_diff)

        return mse

    def applyMasks(self, masks=None):
        '''
        Apply masks to an image.

        Parameters
        ----------
        masks: list[str] or dict_keys, defaults to None
            List of masks to apply to an image.
            If no masks are provided all saved masks will
            be applied to the image.
        '''
        # make copy of raw image to apply masks
        im_masked = np.copy(self.image)

        # Get masks as list
        if masks is None:
            # if no masks are provided, apply generated masks
            log.info('No masks were provided, using all in maskDict')
            masks = self.maskDict.keys()
        elif type(masks) in [list, type({}.keys())]:
            # Correct type
            pass
        elif type(masks) is str:
            # If single mask is passed, make it a list
            masks = [masks]
        else:
            error_msg = f'Masks is unexpected type {type(masks)}'
            log.error(error_msg)
            raise TypeError(error_msg)

        # Iterate through masks
        for m in masks:
            if type(m) is np.ndarray:
                # Not made to handle a passed mask
                warning_msg = 'A masked array was provided instead of a key.'
                log.warning(warning_msg)
                cur_mask = m
            else:
                cur_mask = self.maskDict[m]

            if cur_mask.shape.count(3) == 1:
                # if mask is already 3D apply
                im_masked *= cur_mask
            else:
                # if mask is 2D, apply to each RGB channel
                im_masked[:, :, :] *= self.threeDimMasked(cur_mask)

        return im_masked

    def textOverlay(self, img, text):
        '''
        Write text at the bottom left corner of an image.
        Text size and boldness scales with the size of the image.

        Useful while making a grid to determine which masks
        will be most suitable for comparison.

        Parameters
        ----------
        img: np.array
            The image to write text over
        text: str
            The text to write on an image

        Output
        ------
        name_img: np.array
            The image with text written over it.
            Text scales with the size of the image and
            is written to the bottom left corner.'''

        shape = img.shape

        # How far from the bottom left corner to place text origin
        offset = 0.90

        # Scale the font size to be visibile on any size image
        font_scale = 0.5 + shape[1] // 500
        font_bold = 2 + shape[1] // 700

        log.debug(f'Writing text overlay: {text}')
        name_img = cv.putText(img, text, (int(shape[1]*(1-offset)),
                                          int(shape[0]*offset)),
                              cv.FONT_HERSHEY_SIMPLEX, font_scale,
                              (255, 255, 255), font_bold,)
        return name_img

    # @profile
    def stackImages(self, mask_dict=None, width=0, height=0):
        '''
        Create grid of images depicting the different masks
        applied to the current working image.
        The grid is then saved to the stored name.
            Default: \'MaskedGrid.jpeg\'

        Parameters
        ----------
        img_dict: dictionary
            Dictionary containing the masks for the grid.
            If None use the maskDict property.
        width: int, defaults to 0
            If width is given, set the number of masks
            to show horizontally. If not, use height.
        height: int, defaults to 0
            If width is not given, set the number of masks
            to show vetically. If neither height nor width
            is given, the grid will default to a square image.

        Output
        ------
        full: None, save an image
            Will save an image grid depicting the different masks
            for analysis. Default file name is \'MaskedGrid.jpeg\'

        '''

        if mask_dict is None:
            mask_dict = self.maskDict

        # Get keys as a list
        keys = mask_dict.keys()
        dict_len = len(keys)
        keys = list(keys)

        # Determine the shape of the grid
        if (width == 0) & (height == 0):
            # Get a square shaped grid
            log.debug('finding the square size')
            width = int(np.round(np.sqrt(dict_len)))
        elif width != 0:
            log.debug('width given')
            pass
        else:
            # Use height to determine the width of each row
            log.debug(f'height given {dict_len}/{height}={dict_len / height}')
            width = int(dict_len / height) + (dict_len % height > 0)

        # Initialize the grid to stack
        grid = []
        current_row = []

        while len(keys) != 0:
            # Make one row of images
            for i in range(0, width):
                # Log
                log_mem(f'Stacking image {dict_len-len(keys)} of {dict_len}')

                if len(keys) == 0:
                    # if there are no more masks fill shape with black images
                    current_row.append(np.zeros(self.image.shape))
                else:
                    k = keys[0]
                    # Get and label current image
                    mask_img = self.applyMasks(k)
                    cur_img = self.textOverlay(mask_img, k)
                    current_row.append(cur_img)  # Add to horizonstal stack

                    # Remove key
                    keys.remove(k)
                    del cur_img

            # Add row to grid before
            grid.append(np.hstack(current_row))
            current_row = []

        # Create full grid
        grid_array = np.vstack(grid)

        # Resize grid and save
        img_width = 4000
        aspect = grid_array.shape[0]/grid_array.shape[1]
        img_height = int(img_width * aspect)

        cv.imwrite(self.save_file,
                   cv.resize(grid_array, (img_width, img_height)))

        # Delete locations holding extra image
        del current_row
        del grid_array
        gc.collect()

    # endregion

    def filterImage(self, channels, min=None, image=None):
        '''Filter low light image conditions'''
        if image is None:
            # If no image provided, filter the reference image
            filtered_image = np.copy(self.image)
        else:
            # if filtering a reference image
            filtered_image = np.copy(image)

        if min is None:
            min = self.minRGBValue

        if type(channels) is slice:
            filtered_image *= [filtered_image[:, :, channels] >= min][0]
        elif type(channels) is int:
            filtered_image *= [filtered_image[:, :, channels] >= min][0]
        else:
            for c in channels:
                filtered_image *= [filtered_image[:, :, c] >= min][0]

        if image is None:
            return None
        else:
            return filtered_image

    def showImage(self):
        plt.imshow(self.image)


def getAura(file=''):
    if file == '':
        log.error('No file given')
        return None

    aura = AuroraImage(file)
    aura.maskNormImage()
    aura.save_file = outfile
    return aura


# if run with a file given to read, a masked grid is created
if infile is not None:
    aura0 = getAura(infile)

do_masks = ['Norm >Mean RED']
log.info(get_memory("Script end"))
