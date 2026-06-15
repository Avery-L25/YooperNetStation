#!/bin/bash

# ============================================
#todo future developments/additions/questions
#* camera setup
#? should there be user inputs? what should they be?
#? should this be a one stop shop? meaning code the services and scripts to
#? written in this .sh file
#! chmod for privilege 
# ============================================

# ============================================
# Preparing to work with three scripts of the YooperNET Observatory
# ============================================
# The Camera, Magnetomer/Sensor, and File Manager Scripts will be colored as
# Red, Green, and Blue Respectively

# Color output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'
BOLD='\033[1m'

set -e # exit on ERROR
dry_run=true
HELP_TEXT="
Usage: bash getpython.sh [--version VERSION]

Options:
  --version               Which python version you'd like to install (e.g. 3.6.5, 3.9.5, 3.11.0)
  --help, -h              Show this help message
"
# ============================================
## Getting the user input
## Can be used to add configurations later!!!
# ============================================
while [[ "$#" -gt 0 ]]; do
  case $1 in
    --help|-h)
    echo "$HELP_TEXT"
    exit 0
    ;;
    --real-run) dry_run=false; echo "$#"; shift 1;;
    --version) VERSION="$2"; shift 2 ;;
    *) echo "Unknown option: $1" && exit 0;;
  esac
done

### TESTING STUFFFFFFF
echo $VERSION
if [ "$1" = "--real-run" ] || [ "$2" = "--real-run" ]; then
    printf "${BOLD}${RED}This is dry run, no actual actions will be performed. Use this for testing installation script.${NC}\n"
    dry_run=false
fi
sleep_count=1
echo  dry_run = $dry_run


# ============================================
#! CONFIGURATION - CHANGE THESE VALUES
#todo update if multiple scripts
# ============================================
# Project Vars
PROJECT_NAME="SPRL_Observatory"
USERNAME="yoopernet"
PROJECT_DIR="/home/${USERNAME}/${PROJECT_NAME}"
VENV_NAME="venv"
VENV_DIR="${PROJECT_DIR}/$VENV_NAME"
GIT_REPO="https://github.com/Avery-L25/$PROJECT_NAME.git"
SERVICE_USER="python_service"

# Setup files
pkglist="dependencies.txt"
PYTHON_REQS="requirements.txt"

# Services / automation scripts
SERVICEFILE="yoopernet.service"
STARTER_SCRIPT="startup.sh"

# Helpful Functions
echo -e "\n ${BLUE}Log information will be output as blue${NC} \n $1"
log_info() {
    echo -e "\n${BLUE}[$1]${NC}\n"
}

log_success() {
    echo -e "\n${GREEN}[$1]${NC}\n"
}

log_error() {
    echo -e "\n${RED}[$1]${NC}\n"
}


# ============================================
# Upgrade system with necessary packages
# ============================================
if ! $dry_run; then
    log_error "THIS IS A REAL RUN! CODE IS IN DEVELOPMENT!"
    sleep 10
else
    log_success "This is a dry run testing purposes!"
    sleep $sleep_count
fi

# 1: Update and Upgrade
log_info "Update"
if ! $dry_run; then
    sudo apt-get update 
fi
log_info  "Upgrade"
if ! $dry_run; then
    sudo apt-get upgrade -y
fi

# 2: Get dependencies
log_info "Getting Dependencies"
if ! $dry_run; then
    { # try

    sudo apt-get install $(cat pkglist)
    log_success "Success"
    #save your output

    } || { # catch
        log_error "Error"
        # save log for exception 
    }
fi


# ============================================
# Setup Python
# ============================================

# 1: Fetch Repository
log_info "Setting up Git Repository at: \"$PROJECT_DIR\""
if !  $dry_run; then
    if [ -d "${PROJECT_DIR}/.git" ]; then
        log_info "Repository exists, continuing install."
    else
        sudo git clone "${GIT_REPO}" "${PROJECT_DIR}"
        log_success "Repository Cloned"
    fi
fi

# 2: Create virtual Environment
log_info "Creating virtual python environment: ${VENV_DIR}"
if !  $dry_run; then
    if [ -d "${VENV_DIR}" ]; then
        log_info "Virtual Environment \"$VENV_NAME\" exists, continuing install."
    else
        sudo python -m venv "${VENV_DIR}"
        log_success "Succesfully created ${VENV_NAME}"
    fi
fi

# 3: Install Libraries
log_info "Installing libaries for YooperNET from $PYTHON_REQS"
if !  $dry_run; then
    source $VENV_DIR/bin/activate
    pip install -r $PYTHON_REQS
    log_success "Successfully installed python libraries"
fi

# TODO: Make section that assigns files to system (ie. yoopercam when called)

# TODO: Complicated zwo_asi_camera STUFFFFFFF if it needs that for the raspi still

# ============================================
# Setup Services for Scripts
# ============================================
