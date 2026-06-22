#!/usr/bin/env python3

# // import time
import board
# // import busio
# // import csv
import adafruit_lps35hw
import adafruit_sht31d


def temp_n_pres():
    '''
    Set up I2C and sensor, assigns data addresses to the sensors automatically.
    '''
    i2c = board.I2C()  # uses board.SCL and board.SDA

    LPS35HW = adafruit_lps35hw.LPS35HW(i2c)  # barometer
    SHT31D = adafruit_sht31d.SHT31D(i2c)  # Thermometer

    ext_temp = SHT31D.temperature  # temperature reading outside of the case
    int_temp = LPS35HW.temperature  # temperature reading inside of the case
    pressure = LPS35HW.pressure  # pressure reading

    return [ext_temp, int_temp], pressure
