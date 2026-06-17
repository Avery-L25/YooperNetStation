#!/usr/bin/env python3

import schedule
import time
from SPRL_Observatory.Data_processing.file_transmission_2 import upload_file_to_drive
import os
import datetime


def uploadFileToDrive(folder_id: str,file_path):  # Upload data to Google Drive
    '''
    Upload data to the google drive.
    '''
    upload_file_to_drive(file_path, folder_id)
    get_direcs()



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
    Deletes files after upload verification.
    '''
    pass

while __name__ == '__main__':
    # runs any pending programs every hour to account for variable size thresholds                                                                                                                                                                 
    schedule.run_pending()
    time.sleep(60*60)
