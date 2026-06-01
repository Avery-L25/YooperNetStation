#!/usr/bin/env python3

import schedule
import time
from Data_processing.transmission.file_transmission_2 import upload_file_to_drive
import os
import datetime


def upload_data():  # Upload data to Google Drive
    '''
    Upload data to the University of Michigans "CRABYSS" server.
    '''
    global hdf_file  # ! add path on server
    folder_id = "1vgaHd2zrHlnLKV55_ARNKjABrqwS_hxM"
    print('uploading data to the ... google drive')
    upload_file_to_drive(hdf_file, folder_id)
    # os.remove(hdf_file)
    get_direcs()

    # * print("UPLOADING TO THE CRABYSS")
    # todo os.system(f'rsync -ahP {hdf_path} *USER*@crabyss.engin.umich.edu:{directory to save}')
    # ! ensure that the delete flag is here unless addressed seperately


def get_direcs():  # Get working file
    '''
    Calculates the working file name based on UTC time.
    If it is after 4pm UTC a new file name is created for the current day.
    If it is before 4pm UTC the file is the prior day.
    '''
    global folder, hdf_file, cur_day
    now = datetime.datetime.now(datetime.timezone.utc)

    folder = now.strftime('%y%B')
    if now.hour >= 20:
        hdf_file = now.strftime('%d_%m_%y.hdf5')
    else:
        cur_day = now - datetime.timedelta(1)
        hdf_file = cur_day.strftime('%d_%m_%y.hdf5')


def delete_files():
    '''
    Deletes any files from before the previous day.
    '''
    pass

while __name__ == '__main__':
    # runs any pending programs
    schedule.run_pending()
    time.sleep(60*60)
