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
import datetime as dt
import psutil
import gc
import logging
from argparse import ArgumentParser, RawDescriptionHelpFormatter
import matplotlib.pyplot as plt
import matplotlib.colorizer as mcolorizer
import matplotlib.colors as mcolors
plt.ion()

# Variables
ratio_low = 0.9
ratio_high = 1.3
dom_percent = 1.05
rg_aurora = [0.70, 0.75]  # The red/green ratio found in green aurora
# 185/255 +- 2.5%

# Constants
IMAGE_EXTENSIONS = ['png', 'jpeg', 'jpg', 'jpe', 'webp']
DIC_RGB = {0: 'RED', 1: 'GREEN', 2: 'BLUE', slice(0, 3): 'RGB'}
RGB_CHANNEL = slice(0, 3)
DIC_RGB2CHANNEL = {'RED': 0, 'GREEN': 1, 'BLUE': 2, 'RGB': slice(0, 3)}

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
    'Return text info about memory usage'
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    mem_text = (f"{label} - RSS: {mem_info.rss / 1024 / 1024:.2f} MB, " +
                f"VMS: {mem_info.vms / 1024 / 1024:.2f} MB")
    return mem_text


def log_mem(txt=''):
    'Log method for memory info'
    log.log(19, get_memory(txt))


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

        # Save time of init
        self.captureTime = dt.datetime.now()

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

            # Ensure RGB format when read in using opencv
            rawimg = cv.cvtColor(rawimg, cv.COLOR_BGR2RGB)  # type: ignore
        elif type(imagedata) is np.ndarray:
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
        'MSE of two images using masks'
        product = self.compare(other)
        return product

    # region Image Attributes
    @property
    def brightness(self):
        '''
        The brightness of the image as an array
        '''
        img_ref = self.image.astype(float)

        sum_squares_rgb = np.square(img_ref[:, :, 0]) + \
            np.square(img_ref[:, :, 1]) + \
            np.square(img_ref[:, :, 2])

        # sum_squares_rgb[sum_squares_rgb == 0] = 1
        brightness = np.sqrt(sum_squares_rgb)

        return brightness

    @property
    def r(self):
        'Red Channel'
        return self.image[:, :, 0]

    @property
    def g(self):
        'Green Channel'
        return self.image[:, :, 1]

    @property
    def b(self):
        'Blue Channel'
        return self.image[:, :, 2]

    # endregion
    # region Masks

    def getMask(self, mask_func, **kwargs):
        '''
        Given the type of mask and a list of parameters,
        create the necessary mask.

        Parameters
        ----------
        mask_type: func
            The masking function to be applied.
        inverse: bool, defaults to False
            If True, get the inverse of the mask.
        '''
        # mask = mask_func(**kwargs)

        pass

    def normMask(self, channel=slice(0, 3), std_dev=0.0):
        '''
        Returns norm mask for r, g, and b channels.
        If image is provided, automatically do masked version.

        When img_ref is uint8 the greater than mean isolates
        aurora better than uint16.

        Parameters
        ----------
        channels: int | slice, defaults to slice(0, 3)
            Choose which channels to get mask for.
            Defaults to all RGB channels.
        std_dev: float, defaults to 0.0
            The multiple of the standard deviation
            to add while masking.

        Output
        ------
        mask: np.ndarray
            This mask will be a boolean array that covers the portion
            of the image that is 'neutral' within the provided bounds.

        '''
        img_ref = self.image.astype('uint16')
        sum_squares_rgb = (np.square(img_ref[:, :, 0]) +
                           np.square(img_ref[:, :, 1]) +
                           np.square(img_ref[:, :, 2]))

        # If dividing by 0, it is 0/0
        sum_squares_rgb[sum_squares_rgb == 0] = 1

        # Get working value
        norm = img_ref[:, :, channel] / np.sqrt(sum_squares_rgb)

        # Get mask above the mean
        mask = norm > (norm.mean() + norm.std() * std_dev)

        return mask

    def statMask(self, channel=slice(0, 3), std_dev=0.0, image_stats=True):
        '''
        Returns stat-based mask for r, g, and b channels.
        If image is provided, automatically do masked version.

        Parameters
        ----------
        channels: int | slice, defaults to slice(0, 3)
            Choose which channels to get masks for.
            Defaults to all RGB channels.
        std_dev: float, defaults to 0.0
            The multiple of the standard deviation
                        to add while masking.

        Output
        ------
        mask: np.ndarray
            This mask will be a boolean array that covers the portion
            of the image that is 'neutral' within the provided bounds.

        '''
        image = self.image
        chan = image[:, :, channel]

        log.debug(f'Stat mask for {chan}')

        if image_stats is True:
            # Get mask based on image means
            if self.nonMinStat is True:
                # Filter out below threshold values before calulating the mean
                img_mean = image[image >= self.minRGBValue].mean()
                img_stdv = image[image >= self.minRGBValue].std()
            else:
                img_mean = image.mean()
                img_stdv = image.std()

            # Get mask
            mask = chan >= (img_mean + img_stdv * std_dev)
        else:
            # Get mask based on channel means
            if self.nonMinStat is True:
                # Filter out below threshold values before calulating the mean
                chan_mean = chan[chan >= self.minRGBValue].mean()
                chan_std = chan[chan >= self.minRGBValue].std()
            else:
                chan_mean = chan.mean()
                chan_std = chan.std()

            # Get mask
            mask = chan >= (chan_mean + chan_std * std_dev)

        return mask

    def neutralMask(self, num=None, den=None, uBnd=255.0, lBnd=0.0):
        '''
        Creates a neutral mask between two numpy array given ratios.
        If a bound is not provided, defaults to extremes.

        Parameters
        ----------
        num: int, defaults to 1; np.ndarray
            The numerator channel for the mask.
            If an array is provided, it will be used directly.
        den: int, defaults to 1; np.ndarray
            The denomiator channel for the mask.
            If an array is provided, it will be used directly.
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

        # Allow flexibility in masking
        def getArray(val, val_name=''):
            'Take num or den and ensure it is an array'
            if type(val) is int:
                # Get RGB channel of integer
                val = self.image[:, :, val]
            elif type(val) is str:
                # attempy to use string as key
                try:
                    chan = DIC_RGB2CHANNEL[val]
                except KeyError:
                    log.error(f'Unknown key passed: {val}, try using an '
                              'integer. Defaulting to green channel.')
                    chan = 1
                val = self.image[:, :, chan]
            elif type(val) is np.ndarray:
                # Used for mask
                pass
            elif val is None:
                log.error('No value passed, defaulting to green channel.')
                val = self.image[:, :, 1]
            else:
                log.critical(f"Uknown type of {val_name} passed: {type(val)}"
                             " is not accepted. Defaulting to green channel.")
                val = self.image[:, :, 1]

            # return val as array
            return val

        # Ensure Denominator and Numerator are arrays.
        den = getArray(den, 'Denominator')
        num = getArray(num, 'Numerator')

        # Find Greater/Less than conditions
        upCon = uBnd * den
        loCon = lBnd * den

        # Create mask
        return (loCon <= num) & (num <= upCon)

    def domPercentMask(self, channel=1, dom=1.05):
        '''
        Creates a mask where the given rgb channel excedes
        other channel values by a given ratio.

        Parameters
        ----------
        channel: int, defaults to 1 (green)
            The integer value for RGB channels.
            R=0, G=1, B=2
        dom: float, defaults to 1.05
            The ratio that channel over the remaining
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

        # Handle potential Key/Type Errors
        if type(channel) is str:
            try:
                channel = DIC_RGB2CHANNEL[channel.upper()]
            except KeyError:
                log.error(f'KeyError, {channel} not in {DIC_RGB2CHANNEL} '
                          'defaulting to green')
                channel = 1
        elif type(channel) is not int:
            log.error(f'TypeError, {channel} not in {DIC_RGB2CHANNEL} '
                      'defaulting to green')
            channel = 1

        rgb.remove(channel)

        return ((image[:, :, channel] >= image[:, :, rgb[0]] * dom)
                | (image[:, :, channel] >= image[:, :, rgb[1]] * dom))

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

    # endregion

    def brightRatio(self, channel, byPixel=True, dimVal=6, briVal=442):
        '''
        Get the ratio of color in relation to the brightness of the
        image by normalizing or the average brightness of the image.

        Parameters
        ----------
        channel: int
            RGB channel to evaluate
        byPixel: bool, defaults to True
            When True, use the average brightness of the image for comparison
            When False, use the pixel brightnes for comparison
        dimVal: int | float, defaults to 6
            The minimum brightness to consider in an image
            Handles nAn / divide by 0 conditions
            Only applies when byPixel is False
        briVal: int | float, defaults to 422
            The maximum brightness to consider in an image
            442 will not filter any pixels
            Only applies when byPixel is False

        Output
        ------
        ratio: np.ndarray
            image channel / brightness
        '''

        brightness = self.brightness
        if byPixel is False:
            # Use average brightness of the image
            brightness = np.mean(brightness)

        # Get the ratio
        ratio = self.image[:, :, channel] / brightness

        # Ensure brightnesses of 0 are filtered out
        if dimVal < 0:
            dimVal = 0

        # remove dim areas
        ratio[brightness <= dimVal] = 0
        ratio[brightness >= briVal] = 0
        return ratio

    def greenAuroraRatio(self, lBnd=rg_aurora[0], uBnd=rg_aurora[1]):
        '''
        Use the \'aurora\' green for masking
        '''
        # Get pixel Red/Green ratio
        r_g = self.r / self.g

        # Check that R/G ratio is within range
        aurora_green = (lBnd <= r_g) & (uBnd >= r_g)

        # Return boolean array
        return aurora_green

    # region Create Visual
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
    def compare(self, other, masks=None):
        '''
        Compare two images using the same masking method.

        Parameters
        ----------
        masks: list, defaults to None
            List of mask keys to use while comparing two images.
        '''
        if masks is None:
            log.debug('No masks where given to compare.')
            # If no masks provided, use general set
            masks = self.compareMasks

            # Check that masks exist
            for m in masks:
                if self.maskDict.get(m) is None:
                    # If a mask doe not exists set to None
                    log.debug('Given mask list is missing 1 or more masks'
                              ', using all masks instead.')
                    masks = None
            if (masks == []) | (masks is None):
                # use all masks attached to image.
                masks = self.maskDict.keys()

        cur_img = self.applyMasks(masks)
        pre_img = other.applyMasks(masks)

        # Calculate MSE
        mask_img_diff = cur_img - pre_img
        mse = float(np.mean(mask_img_diff**2))
        # rmse = np.sqrt(np.mean((mask_img_diff)**2))
        # norm_of_masked = np.linalg.norm(mask_img_diff)

        return mse

    def filterImage(self, channels, min=None, image=None):
        '''
        Filter low light image conditions for consistent channel averages.
        Helpful in isolating image contents when using a fisheye lens.

        Parameters
        ----------
        channels: int | slice
            Which pixel channels to filter. This will accept RGB
            channels individually, as a splice, or a list.
            If a splice is provided, channels will be filtered
            individually. See examples for more details.
        min: int, defaults to AuroraImage.minRGBValue
            The pixel channel minimum that will be set to 0.
        image: np.ndarray, defaults to AuroraImage.image
            The image to filter. Will make copy default image if
            no image is provided.

        Output
        ------
        filtered_image: np.ndarray
            Image with no channel values below the minimum.

        Examples
        --------
        >>> red   = np.array([[[ 0, 0, 0],[ 0, 0, 0]],
        >>> green = np.array( [[13,12, 9],[ 8, 2, 1]],
        >>> blue  = np.array( [[10,10,10],[10,10,10]]])
        >>> image = np.array([[[ 0, 0, 0],[ 0, 0, 0]],
                              [[13,12, 9],[ 8, 2, 1]],
                              [[10,10,10],[10,10,10]]])
        >>> filtered = filteredImage(splice(0:3), min=10, image=image)
        filtered = np.array([[[ 0, 0, 0],[ 0, 0, 0]],
                             [[13,12, 0],[ 0, 0, 0]],
                             [[10,10,10],[10,10,10]]])
        NOTE that only the values below the set minimum (min=10) were
        filtered out.
        >>> filtered = filteredImage([0, 1, 2], min=10, image=image)
        filtered = np.array([[[ 0, 0, 0],[ 0, 0, 0]],
                             [[ 0, 0, 0],[ 0, 0, 0]],
                             [[10,10,10],[10,10,10]]])
        NOTE that using a list filters out the entire pixel while
        a slice only looks at individual channels.
        Looking at only 1 channel would have the same effect, this
        allows values below the minimum to be found in other channels.
        '''
        if image is None:
            # If no image provided, filter the reference image
            filtered_image = np.copy(self.image)
        else:
            # if filtering a reference image
            filtered_image = np.copy(image)

        if min is None:
            # Get default minimum filtering value
            min = self.minRGBValue

        if type(channels) is slice:
            # Filter all seperately
            filtered_image *= [filtered_image[:, :, channels] >= min][0]
        elif type(channels) is int:
            # Filter a single channel
            filtered_image *= [filtered_image[:, :, channels] >= min][0]
        else:
            for c in channels:
                # Filters for each channel given
                filtered_image *= [filtered_image[:, :, c] >= min][0]

        return filtered_image

    def switchGRB2RGB(self):
        'Switch GRB channels to RGB'
        self.image = cv.cvtColor(self.image, cv.COLOR_BGR2RGB)

    def showImage(self):
        'Show the working image using matplotlib'
        plt.imshow(self.image)


def getAura(file=''):
    'Initialize a AuroraImage object'
    if file == '':
        log.error('No file given')
        return None

    aura = AuroraImage(file)
    # aura.maskNormImage()
    aura.save_file = outfile
    return aura


def makeBasicImages(aura=''):
    'Make 3 images containing default masks'
    if type(aura) is AuroraImage:
        aura.save_file = 'GridNorm.jpeg'
        aura.maskNormImage()
        aura.stackImages()
        aura.maskDict.clear()

        aura.save_file = 'GridStats.jpeg'
        aura.maskStatsImage()
        aura.stackImages()
        aura.maskDict.clear()

        aura.save_file = 'GridBasic.jpeg'
        aura.maskBasicImage()
        aura.stackImages()
        aura.maskDict.clear()
    else:
        log.warning('Need AuroraImage object to run')
        return None


# if run with a file given to read, a masked grid is created
if infile is not None:
    aura = getAura(infile)

do_masks = ['Norm >Mean RED']
log.info(get_memory("Script end"))


def plotCol(img, byPixel=True, dimVal=10, briVal=442, gen_cmap=None):
    'Plot per [RGB] channel view using \'brightRatio\' method (2-by-2 plot)'
    # Get axes
    fig, axes = plt.subplots(2, 2)
    axes = axes.flatten()
    fig.set_size_inches(16, 9)

    # Get color ratios
    imgs = []
    for color in [0, 1, 2]:  # R G B
        imgs.append(img.brightRatio(color, byPixel=byPixel, dimVal=dimVal,
                                    briVal=briVal))

    # Get subplots variables
    plot_titles = ['image', 'red', 'green', 'blue']
    plot_cmaps = ['Greys_r', 'Reds_r', 'Greens_r', 'Blues_r']
    if gen_cmap is None:
        gen_cmap = plot_cmaps[0]

    # create a colorizer with a predefined norm to be shared across all images
    norm = mcolors.Normalize(vmin=np.min(imgs), vmax=np.max(imgs))
    colorizer = mcolorizer.Colorizer(norm=norm, cmap=gen_cmap)

    # Add imag to list
    imgs = [img.image] + imgs
    color_images = []

    # Plot Raw Image
    color_images.append(axes[0].imshow(img.image[:, :, :]))
    axes[0].set_title(plot_titles[0])

    # Plot Color Map Ratios
    for a in range(1, 4):
        color_images.append(axes[a].imshow(imgs[a], colorizer=colorizer))
        axes[a].set_title(plot_titles[a])

    cb = fig.colorbar(color_images[1], ax=axes, orientation='horizontal',
                      fraction=.1, cmap='hot')
    for a in range(1, 4):
        cb.ax.plot([imgs[a].mean()]*2, [0, 1], plot_titles[a])
        cb.ax.plot([imgs[a].mean()+imgs[a].std()]*2, [0, 1], plot_titles[a])
        cb.ax.plot([imgs[a].mean()+imgs[a].std()*2]*2, [0, 1], plot_titles[a])
