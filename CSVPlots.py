#!/usr/bin/env python3

import cv2 as cv
import numpy as np
import os
import sys
import csv
import toml
from time import sleep, time
from datetime import datetime as dt
import shutil
import logging

from scipy.interpolate import interp1d

import matplotlib.pyplot as plt; plt.ion(); plt.close('all')
import pandas as pd


logging.basicConfig()
DEBUG2 = 11
DATA = 28
logging.addLevelName(DEBUG2,"DEBUG2")
logging.addLevelName(DATA,"DATA")

log = logging.getLogger("auraCheck")
log.setLevel(level=30)

colors = {'mask_mse':'gray',
            'mask_norm':'darkviolet',
            'Red':'red',
            'Green':'green',
            'Blue':'blue',
            'dRed':'tomato',
            'dGreen':'lime',
            'dBlue':'cornflowerblue',
            'd_green2red':'navy'}


# region Helper Functions
def getDF(file) -> pd.DataFrame:
    df = pd.read_csv(file,header=0)
    return df


def splitByFolder(dfz) -> dict[str, pd.DataFrame]:
    data = {}
    df2 = dfz.copy()
    try:
        for i in dfz['folder'].unique():
            _, mini_df = dfz.groupby(df2['folder'] == i)
            data[i] = mini_df[1]
            print(i)
    except KeyError:
        print('No folder to split from')
        data['df'] = dfz
    except ValueError:
        pass
    return data

def splitBy(dfz, What_Splitting) -> dict[str, pd.DataFrame]:
    '''
    Split a pandas dataframe into a dictionary of dfs by unique values in a 
    column. 

    Parameters
    ----------
    dfz: pandas.Dataframe
        The data frame being worked with
    What_Splitting: str
        The data you want to be sorted by, this will also be the name of 
        the dictionary item that contains the split dataframes

    Outputs
    -------
    data: dict[unique value, df of that unique value]

    Examples
    --------
    df = ([])
    df_dict = splitBy(df, 'folder')
    --> print
    '''
    data = {}
    df2 = dfz.copy()
    try:
        uniq_vals = dfz[What_Splitting].unique()
        for i in uniq_vals:
            if len(uniq_vals) == 1:
                data[i] = dfz
                return data
            
            _, mini_df = dfz.groupby(df2[What_Splitting] == i)
            data[i] = mini_df[1]
            print(mini_df)
            print(i)
    except KeyError:
        print(f'No {What_Splitting} to split from')
        data['df'] = dfz
    except ValueError:
        pass
    return data

def checkDF(DF, dataz: dict[str, pd.DataFrame]) -> pd.DataFrame:
    global plotting_data
    if type(DF) is pd.DataFrame:
        plotting_data = DF 
    elif type(DF) is list:
        try:
            Df2 = []
            for k in DF:
                if type(k) is pd.DataFrame:
                    Df2.append(k)
                elif type(k) is str:
                    
                    print(k)
                    Df2.append(dataz[k])
            plotting_data = pd.concat(Df2, ignore_index=True)
        except KeyError:
            plotting_data = dataz['df']
    else:
        raise TypeError(f'Incorrect Type of DF passed {type(DF)}')
    return plotting_data
                

def plotLine(axes, value, twins=False, color = "black", linewidth=0.5, linestyle='solid', xlabel='', ylabel='', ptitle=''):
    dicts = {'df':plotting_data,'color':colors}
    vals_dict ={'color'       : color, 
                'linewidth'   : linewidth, 
                'linestyle'   :linestyle}
    if type(value) is str:
        vals_dict['label'] = value
        for k in dicts.keys():
            cur_dict = dicts[k]
            if value in cur_dict.keys():
                vals_dict[k] = cur_dict[value]
            else:
                pass
        
        try:
            graphing_val = vals_dict.pop('df')
        except KeyError:
            log.warning(f"No Data for {value}")
            return
        axes.plot(graphing_val, **vals_dict)
    else:
        axes.plot(value, color=color, linewidth=linewidth, linestyle=linestyle, label='No name provided')
    
    if twins is True:
        axes.legend(loc='upper right')
    else:
        axes.legend(loc='upper left')

    if ylabel != '':
        axes.set_ylabel(ylabel)
    if xlabel != '':
        axes.set_xlabel(xlabel)
    if ptitle != '':
        axes.set_title(ptitle)
        

# endregion


# region Plotting Functions
# def plotCSV2Much(data_frame, avg_color=False):
#         'Plot aurora checking data from csv file'
#         data_frame = checkDF(data_frame)
#         # Declare global variables for external work
#         global  colors
        
  
#         # Get figure
#         fig, ax = plt.subplots(3,2, sharex=True,sharey=False)
#         r2g = data_frame['dRed']/data_frame['dGreen']
#         ax0 = [ax[0,0].twinx(),ax[0,1].twinx()]
#         ax2 = [ax[2,0].twinx(),ax[2,1].twinx()]
#         average_color_diff = (data_frame['dBlue'] + data_frame['dGreen'] + data_frame['dRed'] )/3

#         # Edit figure
#         fig.subplots_adjust(top=0.95,
#                             bottom=0.05,
#                             left=0.075,
#                             right=0.925,
#                             hspace=0.2,
#                             wspace=0.2)
#         # plt.xlim(0,1000)
        

#         # write data to plots side by side plots
#         for l in [0,1]:
            
#             # ax[0,l].plot(data_frame['mask_mse'],  color=colors['mask_mse'], linewidth=0.5)
#             # ax0[l].plot( data_frame['mask_norm'], color=colors['mask_norm'],linewidth=0.5)
#             plotLine(ax[0,l], "mask_mse")
#             plotLine(ax0[l], "mask_norm", twins=True)
#             if avg_color is False:
#                 plotLine(ax[1,l], 'dRed')
#                 plotLine(ax[1,l], 'dGreen')
#                 plotLine(ax[1,l], 'dBlue')
#                 # ax[1,l].plot(data_frame['dRed'],      color=colors['dRed'],     linewidth=0.5)
#                 # ax[1,l].plot(data_frame['dGreen'],    color=colors['dGreen'],   linewidth=1, linestyle='dashed')
#                 # ax[1,l].plot(data_frame['dBlue'],     color=colors['dBlue'],    linewidth=0.5, linestyle=(0, (5, 10)))
#             else:
#                 plotLine(ax[1,l], average_color_diff)

#             #     ax[1,l].plot(average_color_diff,     color="Black",    linewidth=0.5)
#             plotLine(ax[2,l], 'd_green2red')
#             plotLine(ax2[l], "mask_mse", twins=True)
        
#             # ax[2,l].plot(r2g,             color='navy',             linewidth=0.5)
#             # ax2[l].plot( data_frame['mask_mse'],  color=colors['mask_mse'], linewidth=0.5)

#         # yscale on rightside plots
#         for k in [0,1,2]:
#             ax[k,1].set_yscale('log')
#         ax0[1].set_yscale('log')
#         ax2[1].set_yscale('log')

#         # Make grid
#         for g in [0,1,2]:
#             for h in [0,1]:
#                 ax[g,h].grid(axis='x')
#                 if g == 0:
#                     ax0[h].grid(axis='x')
#                     ax2[h].grid(axis='x')
#             # grax = fig.add_subplot(111)
#             # for _, spine in grax.spines.items():
#             #     spine.set_visible(False)
#             # grax.tick_params(labelleft=False, labelbottom=False, left=False, right=False )
#             # # grax.        
#             # grax.grid(axis="x")



# def plotColorComparison(data_frame):
#     'Plot aurora checking data from csv file'
#     global fig, ax, ax0, ax1, ax2, plot
#     data_frame = checkDF(data_frame)
#     # Get figure
#     fig, ax = plt.subplots(3, sharex=True,sharey=False)
#     r2g = data_frame['dRed']/data_frame['dGreen']
#     ax0 = [ax[0],ax[0].twinx()]
#     ax1 = [ax[1],ax[1].twinx()]
#     ax2 = [ax[2],ax[2].twinx()]
#     average_color_diff = (data_frame['dBlue'] + data_frame['dGreen'] + data_frame['dRed'] )/3


#     # Edit figure
#     fig.subplots_adjust(top=0.95,
#                         bottom=0.05,
#                         left=0.075,
#                         right=0.925,
#                         hspace=0.2,
#                         wspace=0.2)
#     # plt.xlim(0,1000)
    

#     # write data to plots side by side plots
#     plotLine(ax0[0], 'dRed')
#     plotLine(ax1[0], 'dGreen')
#     plotLine(ax2[0], 'dBlue')
#     plotLine(ax0[1], 'Red',    twins=True, linewidth=1, linestyle='dashed')
#     plotLine(ax1[1], 'Green',  twins=True, linewidth=1, linestyle='dashed')
#     plotLine(ax2[1], 'Blue',   twins=True, linewidth=1, linestyle='dashed')

#     # Make grid
#     for g in [ax0,ax1,ax2]:
#         for h in [0,1]:
#             g[h].grid(axis='x')

# def plotMask(data_frame,SubTitle=''):
#     global fig, ax, ax0, ax1, ax2, plot
#     data_frame = checkDF(data_frame)
#     # Get figure
#     fig, ax = plt.subplots(2, sharex=True,sharey=False)
#     r2g = data_frame['dRed']/data_frame['dGreen']
#     ax0 = [ax[0]]
#     ax1 = [ax[1],ax[1].twinx()]

#     average_color_diff = (data_frame['dBlue'] + data_frame['dGreen'] + data_frame['dRed'] )/3


#     # Edit figure
#     fig.subplots_adjust(top=0.95,
#                         bottom=0.05,
#                         left=0.075,
#                         right=0.925,
#                         hspace=0.2,
#                         wspace=0.2)
#     # plt.xlim(0,1000)
    

#     # write data to plots side by side plots
#     plotLine(ax1[0], 'Red', linewidth=1, linestyle='solid', ylabel='Red average value', xlabel = "Photo Count")
#     plotLine(ax1[1], 'mask_mse', linewidth=3,    twins=True, linestyle='dashed', ylabel = "Mean Squared Error")
#     plotLine(ax0[0], 'Red',    linewidth=1, linestyle='solid', ylabel='RGB average value', xlabel = "Photo Count")
#     plotLine(ax0[0], 'Green',   linewidth=1, linestyle='dashed')
#     plotLine(ax0[0], 'Blue',    linewidth=2, linestyle='dotted')
#     if SubTitle != '':
#         fig.suptitle(SubTitle, fontsize=16)
#     # Make grid
#     for g in [ax0[0],ax1[0],ax1[1]]:
#         g.grid(axis='x')
# endregion

def getMoreCSVs(path_to_check):
    dfs = {}
    local_path = os.path.dirname(__file__)
    abs_dir = path_to_check.rpartition('/')[0]
    for i in os.listdir(path_to_check):
        if '.csv' in i:
            csv_path = os.path.join(path_to_check,i)
            df2add = getDF(csv_path)
            print(csv_path)
            dfs[i.partition('_')[0]] = df2add
            print(f"adding {df2add} to {df}\n\n\n\n")
                    # df = pd.concat(df,df2)
    return dfs



# Current Plotting Info
kluster_plots = False
interp_plots = False
xkey = 'Time(ms)'
ykey = 'mask_mse'
# try:
#     if Data_Was_Collected is False:
#         df = getDF('Nov3_25_newCheck.csv')
#         data_tests = splitBy(df, 'Test Name')
#         triple_data = {}
#         for k, v in data_tests.items():
#             vdata = splitBy(v, 'Cluster Method')
#             triple_data[k] = vdata
#     else:
#         pass
# except NameError:
#     print('Collecting data')
#     df = getDF('Nov3_25_11pmTest.csv')
#     data_tests = splitBy(df, 'Test Name')
#     triple_data = {}
#     for k, v in data_tests.items():
#         vdata = splitBy(v, 'Cluster Method')
#         triple_data[k] = vdata
    
#     # Get main plot Data
#     Data_Was_Collected = True

# region Kluster Plots
if kluster_plots is True:
    fig, ax = plt.subplots(3, sharex=True,sharey=True)
    ax0 = ax[0]
    ax1 = ax[1]
    ax2 = ax[2]

    # Plot data for each item
    test = 'Nov3_25_11'
    inc_linew = 1
    line_style = ['solid', (0, (5, 5)), (5, (10, 3)), (0, (1, 5))]


    # Subplots
    for test_key in triple_data.keys():
        cur_test = triple_data[test_key]
        if len(cur_test.keys()) == 1:
            plot = cur_test[-1]
            for axes in ax:
                axes.plot( plot['Time(ms)']/1000, plot[ykey],
                        label=f"{test_key}: {ykey}",linewidth=3,
                            linestyle='solid')
        else:
            for key, vals in cur_test.items():
                ax[key].plot(vals['Time(ms)']/1000, vals[ykey],
                            label=f"{test_key}({key}): {ykey}",
                            linewidth=1, linestyle='dashed')


        # plt.xlim(0,1000)
        

        # write data to plots side by side plots
        # ax.plot( plot['mask_norm'],label=f"{k}: {['mask_mse']}",linewidth=1, linestyle=line_style[inc_linew-1])
        # ax0.plot( v['Red'],     linewidth=1, linestyle='solid')
        # ax0.plot( v['Green'],   linewidth=1, linestyle='dashed')
        # ax0.plot( v['Blue'],    linewidth=2, linestyle='dotted')

        inc_linew = inc_linew + 1



    # Edit figure
    fig.subplots_adjust(top=0.90,
                        bottom=0.05,
                        left=0.075,
                        right=0.925,
                        hspace=0.2,
                        wspace=0.2)
    fig.suptitle(test, fontsize=16)

    subtitles = {0:'Full Size',
                1:'Shrunk After',
                2:'Small Size',
                3:'Full Size'}
    j = 0 

    for i in ax:
        i.legend()
        i.set_title(subtitles[j])   
        i.set_xlabel('Time (Seconds)')
        i.set_ylabel('Norm Value')

        # Plot Boundary Lines
        i.axvline(126)
        i.axvline(160)
        i.axvline(226)
        i.axvline(231)

        j = j + 1
        print('hi')

# endregion

# region Interpolated Plot
if interp_plots is True:   
    fig2, axis2 = plt.subplots(2, sharex=True)

    # Set up interpollation type
    interp_kinds = [None, 'slinear','quadratic', 'zero']
    #[None,'linear', 'nearest', 'nearest-up', 'zero',
     #   'slinear', 'quadratic', 'cubic', 'previous', 'next']
    noklust = triple_data['No Clustering'][-1]
    x_data = noklust['Time(ms)']
    y_data = noklust[ykey]

    if type(axis2) == np.ndarray:
        axis2s = axis2
    else:
        axis2s = [axis2]

    jk = 0
    yscales = ['linear','log']

    for axnumber in axis2s:
        for ikind in interp_kinds:
            
            if ikind is None: 
                y = y_data
                x = x_data
                lw = 0.25
                ls = 'solid'
            else:
                interpolation_model = interp1d(x_data, y_data,kind=ikind)
                x = np.linspace(x_data.min(),x_data.max(), int(x_data.size * 0.05))
                y = interpolation_model(x)
                lw=1
                ls = 'dashed'

            
            axnumber.plot(x/1000,y,
                            label=f"Interpolated: {ikind}",
                            linewidth=lw, linestyle=ls)

        i = axnumber
        i.legend()
        i.set_title('Interpollated No Clustering')   
        i.set_xlabel('Time (Seconds)')
        i.set_ylabel('Norm Value')

        # Plot Boundary Lines
        for vl in [126, 160, 226, 231]:
            i.axvline(vl, linewidth=0.5, color='black', linestyle='dotted')
        

        # Plot Horizontal lines to find flagging conditions
        for hl in [1,0.5,0.25,0.01]:
            i.axhline(hl, linewidth=0.5, color='black', linestyle='dotted')
        
        i.set_yscale(yscales[jk])

        jk = jk + 1

# endregion

# region New Data
filename_ = 'gillam.csv'
df = getDF(f'Data/csv_files/{filename_}')
fig, axN = plt.subplots(1, sharex=True)

y_vars = ['mask_mse', 'old_mask_mse']
x_data = df['Time(ms)']
if type(axN) == np.ndarray:
    axin = axN
else:
    axin = [axN]

jk = 0
yscales = ['linear','log']

for axnumber in axin:
    for yv in y_vars:
        y_data = df[yv]
        if yv.find('old') != -1: 
            lw = .75
            ls = 'solid'
        else:
            lw = 1
            ls = 'dashed'
        
        axnumber.plot(x_data/1000, y_data,
                      label=f"Data: {yv}",
                      linewidth=lw, linestyle=ls)

    i = axnumber
    i.legend()
    i.set_title(filename_)
    i.set_xlabel('Time (Seconds)')
    i.set_ylabel('MSE')

    i.set_yscale(yscales[jk])

    jk = jk + 1
