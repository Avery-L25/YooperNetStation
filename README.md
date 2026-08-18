# YooperNetStation
Software module for operating a YooperNet Station. Intended for use with the following operations.
- An all-sky camera checking for visible aurora.
- Data collection from a magnetometer, thermometer, and barometer.
- Automatic file uploads.

## Requirements
_Incomplete List_
- Raspberry Pi with 64-bit Raspberry Pi OS installed
- ZWO ASI Camera with appropriate lens
- Chip based magnetometer
- Python >=3.12


## Installation/Setup
1. Image an SD card for the Raspberry Pi using the [Raspberry Pi imager](https://www.raspberrypi.com/software/)
     - Choose a hostname, username, and password
     - Enable SSH
     - Optional: Enable [Raspberry Pi Connect](https://connect.raspberrypi.com/devices) for VNC access
2. Enable SPI, I2C, Serial Port, and 1-Wire
     - In a terminal, type `sudo raspi-config`
     - Navigate to option 3, Interface options
     - Enable SPI, I2C, Serial Port, and 1-Wire
     - Once complete, select 'finish' and reboot
4. Clone the Github repository and customize the .YooperConfig.toml file for install.
   - Clone the repository `git clone <repo> YooperNetStation`
   - Change to directory `cd YooperNetStation`
   - Edit the toml file, the 'paths' and 'install' sections are used by the installer
5. Run Setup/installer.py to update the system, download and install necessary packages/libraries, and setup the yoopernet service.
   - NOTE: Do this through this directly on the device or via the desktop in case of a crash
   - Run `python3 Setup/installer.py`
   - This should create the python virtual environment and start the services
   - The code will not run until camera software is installed
6. Install Camera Software \(This is a guide if the installer fails to acquire the SDK\)
   - Navigate to [ZWO's software product SDK page](https://www.zwoastro.com/software/product-sdk/)
   - Install _ASI Camera SDK_
   - Extract the zip file and locate the 'ASI_linux_mac_SDK_V1.41/lib/**armv8**' folder
   - Move the contents into the pyzwoasi 'x64' folder location
7. Run `rclone config` and follow [these instructions](https://rclone.org/drive/) to setup rclone on google drive.
   - NOTE: You can use a seperate device to authorize rclone without the need to log in on the device to be set up.
   1. Create a new remote
   2. Name it 'remote' \(If changed, update the name in '.YooperConfig.toml'\)
   3.  Select google drive by tying `drive` or `18`
   4.  client_id is optional
   5.  client_secret is optional
   6.  Scope 3 is good for uploading only, Scope 1 allows for further access but is unnecessary
   7.  service_account_file is optional
   8.  Advanced Config
       - Select yes to choose a specific folder to upload to or configure other settings.
       - Paste the **folder id** found in the URL when asked for `Option root_folder_id.`
       - Leave other options blank until asked again to edit advanced config
   9.  Auto config
       - If connected headless, select NO and authenticate on separate device.
       - If working on the Raspberry Pi, select yes and authenticate using the browser.
   10. Shared Drive \(Team Drive\)
       - Seek further information for this configuration
   11. Keep this remote
9. Configure toml file to customize camera settings, file locations, and user data.
10. Run `sudo systemctl status yoopernet` to ensure that the code is operational

## Usage
Intended to automatically run after setup. Will collect data to an **hdf5 file**. 
The YooperNet repository (link) offers operations to interpret data collected by the YooperNet station.
