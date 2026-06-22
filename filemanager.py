#!/usr/bin/env python3

import schedule
import time
from SPRL_Observatory.Data_processing.file_transmission_2 import upload_file_to_drive
import os
import datetime

import os.path
import h5py
import numpy as np
import time
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaUpload
from os.path import isfile, join
import subprocess

SCOPES = ["https://www.googleapis.com/auth/drive.file"]

def rclone(folder=str()):
    '''Given a folder (and path???) uploads the folder and its contents to 
    the set "remote" path in rclone.'''
    print(folder)
    command = ["rclone", "copy", "/home/amland/Documents/txt_duds", "remote:"]
    print(command)
    
    command[-1] = command[-1] + folder
    print(command)
    subprocess.run(command)


def getDataLoc():
    'Returns the data collection locations (file/directory)'
    pass


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


def create_hdf5_file(file_name):
    """Creates an HDF5 file and writes random data."""
    with h5py.File(file_name, "w") as f:
        data = np.random.rand(100, 100)
        f.create_dataset("random_data", data=data)
    print(f"{file_name} created successfully.")


def uploadFileToDrive(folder_id: str,file_name: str):  # Upload data to Google Drive
    '''
    Upload data to the google drive.
    '''
    creds = None
    token_path = '/home/amland/SPRL_Observatory/Token_management/token_2.json'
    creds_path = '/home/amland/SPRL_Observatory/Token_management/credentials.json'

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                creds_path, SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open(token_path, "w") as token:
            token.write(creds.to_json())

    try:
        service = build("drive", "v3", credentials=creds)

        file_metadata = {"name": file_name, "parents": [folder_id]}
        media = MediaFileUpload(
            file_name, mimetype="application/x-hdf5", resumable=True
        )
        
        file = (
            service.files()
            .create(body=file_metadata, media_body=media, fields="id",
                    supportsAllDrives=True)
            .execute()
        )
        print(f"File ID: {file['id']} uploaded successfully to folder"
              f"{folder_id}.")
    except HttpError as error:
        print(f"An error occurred: {error}")


while __name__ == '__main__':
    # runs any pending programs every hour to account for variable size thresholds                                                                                                                                                                 
    schedule.run_pending()
    time.sleep(60*60)
