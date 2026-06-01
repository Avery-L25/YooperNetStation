#!/usr/bin/env python3

import os.path
import h5py
import numpy as np
import time
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def create_hdf5_file(file_name):
    """Creates an HDF5 file and writes random data."""
    with h5py.File(file_name, "w") as f:
        data = np.random.rand(100, 100)
        f.create_dataset("random_data", data=data)
    print(f"{file_name} created successfully.")


def upload_file_to_drive(file_name, folder_id):
    """Uploads a file to Google Drive in the specified folder."""
    creds = None
    token_path = 'token_2.json'
    creds_path = '/home/sprlobs/SPRL_Observatory/Data_processing/transmission/credentials.json'

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


def main():
    """Creates an HDF5 file, uploads it to Google Drive,
    and repeats every 10 seconds."""
    folder_id = "1vgaHd2zrHlnLKV55_ARNKjABrqwS_hxM"
    file_counter = 1

    while True:
        file_name = f"random_data_{file_counter}.h5"
        create_hdf5_file(file_name)
        upload_file_to_drive(file_name, folder_id)
        file_counter += 1
        time.sleep(10)
