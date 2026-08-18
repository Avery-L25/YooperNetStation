#!/usr/bin/env python3
'''
Setup YooperNetStation from scratch.

Actions
-------
1. Update & Upgrade system
2. Install system dependencies
3. Ensure git repository is up to date
4. Setup Python Virtual Environment
5. Install Python Requirements
6. Make data locations
7. Setup and start yoopernet.service
'''
import subprocess
import os.path
import sys
import tomllib
from urllib.request import urlretrieve as geturl
from zipfile import ZipFile
import tarfile

# Get directories and paths
wkdir = os.path.dirname(os.path.realpath(__file__))
PROJECT_DIR = wkdir.rpartition('/')[0]
PROJECT_NAME = PROJECT_DIR.rpartition('/')[1]
USERNAME = os.environ['LOGNAME']

# Load TOML
with open(os.path.join(PROJECT_DIR, '.YooperConfig.toml'), 'rb') as f:
    yoopconfig = tomllib.load(f)

# Get install specifics: Virtual Environment, Reference Files, Etc
y_install = yoopconfig['install']
VENV_NAME = y_install['Venv_Name']
VENV_DIR = os.path.join(PROJECT_DIR, VENV_NAME)
SERVICE_USER = y_install['Service_User']
SERVICE_DIR = "/etc/systemd/system"

# Get data locations
dirs_list = []
direcs_folders = ['Images_Folder', 'HDF5_Folder', 'Log_Folder']  # TOML keys
y_dirs = yoopconfig['paths']
for df in direcs_folders:
    dirs_list.append(y_dirs[df])

PKG_LIST = os.path.join(wkdir, 'Ref_Files', "dependencies.txt")
PYTHON_REQS = os.path.join(wkdir, 'Ref_Files', "requirements.txt")
SERVICE_FILE = os.path.join(wkdir, 'Ref_Files', "yoopernet.service")

camera_sdk_url = 'https://dl.zwoastro.com/software?app=DeveloperCameraSdk' + \
    '&platform=windows86&region=Overseas'
sdk_zip_name = 'ASI_SDK.zip'
sdk_tar_dir = 'ASI_Camera_SDK/ASI_linux_mac_SDK_V1.41.tar.bz2'
sdk_rules_file = 'ASI_linux_mac_SDK_V1.41/lib/asi.rules'
sdk_armv8_start = 'ASI_linux_mac_SDK_V1.41/lib/armv8'
sdk_armv8_end = '/home/yoopernet/YooperNetStation/venv/lib/python3.13/site-packages/pyzwoasi/lib/Linux/x64'

# Conditions
make_venv = True
all_check_yes = True  # If true, does all commands unless manually overridden


# region functions
#  Run commands from strings
def runStr(cmd: str):
    command = cmd.split(' ')
    subprocess.run(command, check=True)


# Get user
def stopOrGo(msg='continue', cnt_override=False, pass_override=False):
    'Get user input to continue setup'
    usr_in = None
    if pass_override is False:
        # immediately return false to pass action.
        return False
    elif cnt_override is True:
        # If the continute override is true, force operation.
        return True
    while True:
        usr_in = input(f"Do you wish to {msg}? y or n (or e to exit)\n")
        if usr_in.lower() in ['y', 'yes']:
            return True
        elif usr_in.lower() in ['n', 'no']:
            return False
        elif usr_in.lower() in ['e', 'exit']:
            print("Exiting")
            sys.exit()
        else:
            print("Not recognized\n")


# Logging/Output functions
class bcolors():

    def __init__(self) -> None:
        self.HEADER = "\033[95m"
        self.BLUE = "\033[94m"
        self.CYAN = "\033[96m"
        self.LOG = "\033[92m"
        self.WARNING = "\033[93m"
        self.ENDC = "\033[0m"
        self.BOLD = "\033[1m"
        self.ERROR = "\033[91m"
        self.UNDERLINE = "\033[4m"
        self.lict = ['HEADER', 'OKBLUE', 'OKCYAN', 'OKGREEN', 'WARNING',
                     'FAIL', 'ENDC', 'BOLD', 'UNDERLINE']
        pass

    def testCodes(self):

        for k in self.lict:
            if k[0] == '_':
                pass
            else:
                print(f"\n{(getattr(self, k))} This is an example of {k}")

    def unoPartMsg(self, color='', format='', msg=''):
        end = self.ENDC

        print(f"\n{color}{format}{msg}{end}")

    def error(self, msg):
        'Prints errors as red'
        self.unoPartMsg(color=self.ERROR, msg=msg)

    def log(self, msg):
        'Prints info as green'
        self.unoPartMsg(color=self.LOG, msg=msg)

    def success(self, msg):
        'Prints successful operations as blue'
        self.unoPartMsg(color=self.BLUE, msg=msg)

    def bold(self, msg):
        'Prints boldened message'
        self.unoPartMsg(format=self.BOLD, msg=msg)


txt = bcolors()
error = txt.error
log = txt.log
success = txt.success
bold = txt.bold
# endregion


# ============================================
# region Upgrade system
# ============================================

# 1: Update and Upgrade
log("Update")
runStr("sudo apt-get update")

log("Upgrade")
runStr("sudo apt-get upgrade -y")

# 2: Get dependencies
log("Getting Dependencies")
if stopOrGo(msg=f"install system dependencies from {PKG_LIST}",
            cnt_override=all_check_yes):

    try:
        runStr(f"xargs sudo apt-get install < {PKG_LIST}")
        log("Success")
    except subprocess.CalledProcessError as e:
        error("Error occurred while attempting to install dependencies."
              + f"\nError Code: {bold(e.returncode)}")
        # ! No error code returning.
        pass
# endregion

# ============================================
# region Setup Python
# ============================================

# 3: Update repository
log(f"Pulling to latest commit to: \"{PROJECT_DIR}\"")
runStr(f"git -C {PROJECT_DIR} pull")
success("Repository is up to date with main")


# 4: Create virtual Environment
make_venv = stopOrGo(msg=f"Create virtual environment {VENV_NAME}"
                     " on this device", cnt_override=all_check_yes,
                     pass_override=make_venv)
if make_venv is True:
    if os.path.exists(VENV_DIR):
        log(f"Virtual Environment \"{VENV_NAME}\" exists, continuing install.")
    else:
        log(f"Creating virtual python environment: \"{VENV_DIR}\"")
        runStr(f"python -m venv {VENV_DIR}")
        success(f"Succesfully created {VENV_NAME}")


# 5: Install Libraries
log(f"Installing libaries for YooperNET from {PYTHON_REQS}")
try:
    # Install the libraries to specified version using the requirements file
    runStr(f"{VENV_DIR}/bin/pip install -r {PYTHON_REQS}")
    success("Python requirement successfully installed")
except subprocess.CalledProcessError as e:
    error("Error occurred while attempting to install dependencies."
          + f"\nError Code: {bold(e.returncode)}")
    pass
success("Successfully installed python libraries")

# 6: Setup Data Files
for dirs in dirs_list:
    if os.path.exists(dirs) is False:
        os.makedirs(dirs)
# endregion

# ============================================
# region Install Camera SDK
# ============================================
# Download the zip file
geturl(camera_sdk_url, sdk_zip_name)

with ZipFile(sdk_zip_name) as zip_top:
    # extract the tar file from the zip
    zip_top.extract(sdk_tar_dir)
    with tarfile.open(sdk_tar_dir, "r:bz2") as tar_fold:
        # extract the tar file contents
        tar_fold.extractall()

# Move the right files to the reference library
runStr(f'cp -r {sdk_armv8_start} {sdk_armv8_end}')
# Install the rules
runStr(f'sudo install {sdk_rules_file} /lib/udev/rules.d')
runStr(f'sudo install {sdk_rules_file} /etc/udev/rules.d')
# endregion

# ============================================
# region Setup Services
# ============================================
# 7: Start and enable service for start-on-boot
log(f"Setting up {SERVICE_FILE}")

# Put service file in proper directory
runStr(f"sudo mv {SERVICE_FILE} {SERVICE_DIR}")
success(f"Moved {SERVICE_FILE} to {SERVICE_DIR}")

# Start service file now and enable device to run system on its own
runStr(f"sudo systemctl start {SERVICE_FILE}")
if stopOrGo(msg="enable service now", cnt_override=all_check_yes):
    # enable service to start on device power on.
    runStr(f"sudo systemctl enable {SERVICE_FILE}")
success(f"{SERVICE_FILE} successfully started!")

# endregion

log('rclone must be set up manually')
