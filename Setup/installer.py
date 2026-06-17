#!/usr/bin/env python3

import subprocess
import os.path
from os.path import isfile, join
import sys
import toml
import csv
import h5py
import time

### Assign paths
#! Update to be in JSON
# Project Vars
PROJECT_NAME="SPRL_Observatory"
USERNAME=os.environ['LOGNAME']
PROJECT_DIR=f"/home/{USERNAME}/{PROJECT_NAME}"
VENV_NAME="venv"
VENV_DIR=f"{PROJECT_DIR}/$VENV_NAME"
GIT_REPO="https://github.com/Avery-L25/$PROJECT_NAME.git"
SERVICE_USER="python_service"

# Setup files
pkglist="dependencies.txt"
PYTHON_REQS="requirements.txt"

# Services / automation scripts
SERVICE_DIR=NotImplemented
SERVICE_FILE="yoopernet.service"
STARTER_SCRIPT="startup.sh"                                                 #! UPDATE THIS

# Run commands from strings
def runStr(cmd: str):
    command = cmd.split(' ')
    subprocess.run(command, check=True)

# Get user
def stopOrGo(msg='continue',override=False):  # -> bool:
    'Get user input to continue setup'
    usr_in = None
    if override is True:
        # This is to pass if flag or otherwise an not needed for whatever.
        return
    while True:
        usr_in = input(f"Do you wish to {msg}? y or n\n")
        if usr_in.lower() in ['y', 'yes']:
            break
        elif usr_in.lower() in ['n', 'no']:
            break

# Logging/Output functions
class bcolors():

    def __init__(self) -> None:
        self.HEADER =   "\033[95m"
        self.BLUE =   "\033[94m"
        self.CYAN =   "\033[96m"
        self.LOG =  "\033[92m"
        self.WARNING =  "\033[93m"
        self.ENDC =     "\033[0m"
        self.BOLD =     "\033[1m"
        self.ERROR =     "\033[91m"
        self.UNDERLINE ="\033[4m"
        self.lict = ['HEADER','OKBLUE','OKCYAN','OKGREEN','WARNING','FAIL',
                     'ENDC','BOLD','UNDERLINE']
        pass

    def testCodes(self):

        for k in self.lict:
            if k[0] == '_':
                pass
            else:
                print(f"\n{(getattr(self,k))} This is an example of {k}")

    def unoPartMsg(self,color='',format='',msg=''):
        end = self.ENDC

        print(f"\n{color}{format}{msg}{end}")

    def error(self,msg):
        'Prints errors as red'
        self.unoPartMsg(color=self.ERROR,msg=msg)

    def log(self,msg):
        'Prints info as green'
        self.unoPartMsg(color=self.LOG,msg=msg)

    def success(self,msg):
        'Prints successful operations as blue'
        self.unoPartMsg(color=self.BLUE,msg=msg)

    def bold(self,msg):
        'Prints boldened message'
        self.unoPartMsg(format=self.BOLD,msg=msg)

txt=bcolors()
error = txt.error
log = txt.log
success = txt.success
bold = txt.bold

# ============================================
# Upgrade system with necessary packages
# ============================================

# 1: Update and Upgrade
log("Update")
runStr("sudo apt-get update")

log("Upgrade")
runStr("sudo apt-get upgrade -y")

# 2: Get dependencies
log("Getting Dependencies")
try:
    runStr(f"sudo apt-get install {pkglist}")
    log("Success")
except subprocess.CalledProcessError as e:
    error(f"Error occurred while attempting to install dependencies."
          + f"\nError Code: {bold(e.returncode)}")  #! No error code returning.
    pass

# ============================================
# Setup Python
# ============================================
stopOrGo()
# 1: Update repository
log(f"Pulling to latest commit to: \"{PROJECT_DIR}\"")
runStr(f"git -C {PROJECT_DIR} pull")
success( "Repository is up to date with main")


# # 2: Create virtual Environment
if os.path.exists(VENV_DIR):
    log(f"Virtual Environment \"{VENV_NAME}\" exists, continuing install.")
else:
    log( f"Creating virtual python environment: \"{VENV_DIR}\"")
    runStr(f"sudo python -m venv \"{VENV_DIR}\"")
    success(f"Succesfully created {VENV_NAME}")


# 3: Install Libraries
log(f"Installing libaries for YooperNET from {PYTHON_REQS}")
try:
    runStr(f"source {VENV_DIR}/bin/activate")                                   #! Can we do this without ipython for station
    runStr(f"pip install -r {PYTHON_REQS}")
    success(f"Python requirement successfully installed")
except subprocess.CalledProcessError as e:
    error(f"Error occurred while attempting to install dependencies."
          + f"\nError Code: {bold(e.returncode)}")
    pass
success( "Successfully installed python libraries")

# TODO: Make section that assigns files to system (ie. yoopercam when called)

### ============================================
# Setup Services for Scripts
# ============================================
#! NEED TO ADD THE STARTER SCRIPT SETUP WHEN THAT IS FINISHED
sys.exit()
while True:
    input('There is no escape, quit now.')
log(f"Setting up {SERVICE_FILE}")
runStr(f"sudo mv {SERVICE_FILE} {SERVICE_DIR}")
success(f"Moved {SERVICE_FILE} to {SERVICE_DIR}")
runStr(f"sudo systemctl start {SERVICE_FILE}")
runStr(f"sudo systemctl enable {SERVICE_FILE}")
success(f"{SERVICE_FILE} successfully starte!")

log('Run testing script before operation begins')

