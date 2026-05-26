#!

import camera_zwo_asi as cza  
import zwo as cammod
import numpy as np
import cv2 as cv

# import supporting libraries
import os
from pathlib import Path
import matplotlib.pyplot as plt


def nothing(x):
    pass

# Initialize Camera
yoo = cza.camera.Camera(0)  # get first camera
# same as cza.Camera(0)

# Define configuration
config_name = 'zwo_asi.toml'
CONFIG_FILE = Path(os.getcwd() + '/' + config_name)  # path to intended config file
conROI = None
conTroll = None
# Use file or script
use_file = True

# Configure Camera From toml
try:
    if use_file is True:
        yoo.configure_from_toml(CONFIG_FILE)  # configure camera from setting in zwo_asi.toml
        yoo.to_toml('zwo_asi.toml')
        print("\nConfiguring camera using " + '\033[94m' + f"{config_name}\n"
            + '\033[0m')
    elif use_file is False:
        yoo.configure(conROI, conTroll)
        print("THIS SHOULDN'T HAPPEN")
    else:
        raise
except RuntimeError:
    print("Camera was not configured")
    pass  # This error will happen if camera was configured but had not taken an image



# ? changing some controllables
# (supported arguments: the one that are
# indicated as 'writable' in the information
# printed above)
yoo.set_control("Gain",300)
yoo.set_control("Exposure","auto")

con = yoo.get_controls()
# con.items()
dict_keys = con.keys()  # the dictionary, not used for lookup
keys = list(dict_keys)



# ? changing the ROI (region of interest)
roi = yoo.get_roi()
roi.type = cza.ImageType.rgb24
roi.start_x = 00
roi.start_y = 00
roi.bins = 2
roi.width = 2744
roi.height = 1836
yoo.set_roi(roi)

# saving this updated configuration to a file
conf_path = Path("/tmp") / "asi.toml"
yoo.to_toml(conf_path)

# ? Capture Image
image = yoo.capture()       # take picture
img = image.get_image()     # save picture to (numpy array) for display
# taking the picture
filepath = Path("/tmp") / "asi.bmp"
show = True
# filepath and show are optional, if you do not
# want to save the image or display it
image = yoo.capture(filepath=filepath,show=show)

# ! =============================================
quit(1)
# Take image frame as list to array  of shape
height = roi.get_y_size()
width = zwo.get_x_size()
shape = (width, height)
small_shape = tuple(int(ti/4) for ti in shape)
img_array = np.array(frame, dtype=np.uint16).reshape(shape)
print("resizing image with opencv")


# ! =========== Making Display ==================

# Create a black image, a window
img = cv.resize(img_array, small_shape )
cv.namedWindow('image')
 
# create trackbars for color change
cv.createTrackbar('G', 'image', 0, 255, nothing)
cv.createTrackbar('R', 'image', 0, 255, nothing)
cv.createTrackbar('B', 'image', 0, 255, nothing)
 
# create switch for ON/OFF functionality
switch = '0 : OFF \n1 : ON'
cv.createTrackbar(switch, 'image', 0, 1, nothing)

cv.imwrite("frame_img.png", img)

print("window created, showing images")
while True:
    cv.imshow('image', img)
    k = cv.waitKey(1) & 0xFF
    if k == 27:
        break
 
    # get current positions of four trackbars
    g = cv.getTrackbarPos('G', 'image')
    b = cv.getTrackbarPos('B', 'image')
    r = cv.getTrackbarPos('R', 'image')
    s = cv.getTrackbarPos(switch, 'image')
#    if s == 0:
#    else:
 
#        img[:] = [b,g,r]
#        img[:] = 0
 
cv.destroyAllWindows()