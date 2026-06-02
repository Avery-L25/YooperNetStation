#!/usr/bin/env python3

import cv2
import numpy as np


class Image(object):
    def __init__(self, img):  # "img" is the current image, "pre" is the one
        'Initialize Image Object with testing values'
        self.img = img        # from previous timstamp
        self.pre = img

        self.masked = img
        self.premask = img
        # not necessary
        self.black = np.zeros((512, 512, 3))
        self.red = np.zeros((512, 512, 3))
        self.red[:, :, 0] = 255
        self.green = np.zeros((512, 512, 3))
        self.green[:, :, 1] = 255
        self.blue = np.zeros((512, 512, 3))
        self.blue[:, :, 2] = 255

    def resize(self):   # resize any size of image in "self.img" to be 512x512
        'Resize image to 0.25 MP'
        self.img = cv2.resize(self.img, (512, 512))

    # Credit:
    # https://github.com/joncooper65/raspberry-aurora/blob/master/detect.py
    def aurora_detection(self):
        '''OpenCV Masking to detect BRIGHT, GREEN/BLUE areas and flag as
        potential aurora'''
        b, g, r = cv2.split(self.img)

        r1 = r * 1.0
        g1 = g * 1.0
        b1 = b * 1.0

        # Mask "img" and "pre" to retrieve the green part, ignore white color
        gbratio = cv2.divide(b1, g1)
        maskgbratio = cv2.inRange(gbratio, 0.9, 1.3)
        grratio = cv2.divide(r1, g1)
        maskgrratio = cv2.inRange(grratio, 0.9, 1.3)

        mask1 = cv2.compare(0.95*g, 1.0*b, cv2.CMP_GT)
        mask2 = cv2.compare(0.95*g, 1.0*r, cv2.CMP_GT)
        maskgreendominant = cv2.bitwise_and(mask1, mask2)
        verygreen = cv2.bitwise_and(maskgreendominant, cv2.bitwise_not( cv2.bitwise_and(maskgrratio, maskgbratio)))

        masked_img = cv2.bitwise_and(self.img, self.img, mask=verygreen)
        masked_pre = cv2.bitwise_and(self.pre, self.pre, mask=verygreen)

        self.masked = masked_img
        self.premask = masked_pre
        # Use mse to determine the changes in time
        mse = np.linalg.norm(masked_img-masked_pre)
        cv2.imwrite('masked.jpg', masked_img)
        
        return bool(mse)
