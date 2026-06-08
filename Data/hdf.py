#!/usr/bin/env python3

import h5py
import glob
import numpy as np
import datetime


def build_hdf(date, gps, temp, pres, mag, img, file):
    print('build hdf')
    with h5py.File(file, "w") as f:
        f.create_dataset("date", maxshape=(None,), dtype=h5py.string_dtype(),
                         data=[date])
        f.create_dataset("gps", maxshape=(None,), dtype='f', data=[gps])
        f.create_dataset("temperature", maxshape=(None, 2), dtype='f',
                         data=[temp])
        f.create_dataset("pressure", maxshape=(None,), dtype='f', data=[pres])
        f.create_dataset("magnetic field", maxshape=(None, 3), dtype='f',
                         data=[mag])

        # create group for images and their own timestamps
        i = f.require_group("images")
        i.create_dataset("date", maxshape=(None,), dtype=h5py.string_dtype(),
                         data=[date])
        i.create_dataset("aurora img", maxshape=(None, 512, 512, 3),
                         dtype='uint8', data=[img])
        i.create_dataset("aurora flag", maxshape=(None,), dtype=h5py.string_dtype(),
                         data=['Start of file'])


def add_data(date, gps, temp, pres, mag, img, file, camflag, aurflag):
    print('add data')
    with h5py.File(file, "a") as f:
        f["date"].resize((f["date"].shape[0] + 1), axis=0)
        f['date'][-1] = date
        f["gps"].resize((f["gps"].shape[0] + 1), axis=0)
        f["gps"][-1:] = gps
        f["temperature"].resize((f["temperature"].shape[0] + 1), axis=0)
        f['temperature'][-1] = temp
        f["pressure"].resize((f["pressure"].shape[0] + 1), axis=0)
        f['pressure'][-1] = pres
        f["magnetic field"].resize((f["magnetic field"].shape[0] + 1), axis=0)
        f['magnetic field'][-1] = mag

        # adds photos and their appropriate timestamp
        if camflag is True:  # if image was taken upload image
            i = f.require_group("images")
            i["date"].resize((i["date"].shape[0] + 1), axis=0)
            i['date'][-1] = date
            i['aurora img'][-1] = img
            i["aurora img"].resize((i["aurora img"].shape[0] + 1), axis=0)
            i['aurora flag'].resize((i["aurora flag"].shape[0] + 1), axis=0)
            if aurflag is True:
                i['aurora flag'][-1] = "True"
            else:
                i['aurora flag'][-1] = "False"


def hdf(mag, pres, temp, gps, img, file, camflag, aurflag):
    global utc_now

    d_t = np.datetime64('now').item().strftime('%Y_%m_%d_%H_%M_%S')

    utc_now = datetime.datetime.now(datetime.timezone.utc)
    if glob.glob(file):
        add_data(d_t, gps, temp, pres, mag, img, file, camflag, aurflag)
    else:
        build_hdf(d_t, gps, temp, pres, mag, img, file)
