#!/usr/bin/env python3

import cv2 as cv
import numpy as np
import os
import csv
import toml
from time import sleep, time
from datetime import datetime as dt
import shutil
import logging


import matplotlib.pyplot as plt; plt.ion()
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
    global df, data, plotting_data
    df = pd.read_csv(file,header=0)
    data = splitDF(df)
    plotting_data = df
    return df.copy()


def splitDF(dfz) -> dict[str, pd.DataFrame]:
    data = {}
    try:
        for i in dfz['folder'].unique():
            _, mini_df = dfz.groupby(df['folder'] == i)
            data[i] = mini_df[1]
            print(i)
    except KeyError:
        print('No folder to split from')
        data['df'] = dfz
    except ValueError:
        pass
    return data

def checkDF(DF, dataz: dict[str, pd.DataFrame]) -> pd.DataFrame:
    global df, data, plotting_data
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


dfs = {}
local_path = os.path.dirname(__file__)
path_to_check = '/home/amland/mnt/g/My Drive/testing/video'
abs_dir = path_to_check.rpartition('/')[0]
for i in os.listdir(path_to_check):
    if '.csv' in i:
        csv_path = os.path.join(path_to_check,i)
        df2add = getDF(csv_path)
        print(csv_path)
        dfs[i.partition('_')[0]] = df2add
        print(f"adding {df2add} to {df}\n\n\n\n")
                # df = pd.concat(df,df2)


# Init Plots
fig, ax = plt.subplots(1, sharex=True,sharey=False)
# ax0 = ax[0]
# ax1 = ax[1]

# Plot data for each item
test = 'Test_es24_ei55'
inc_linew = 1
line_style = ['solid', (0, (5, 5)), (5, (10, 3)), (0, (1, 5))]
for k, v in dfs.items():
    
    vdata = splitDF(v)
    plot = checkDF(['Dark', test], vdata)
    # Edit figure
    fig.subplots_adjust(top=0.95,
                        bottom=0.05,
                        left=0.075,
                        right=0.925,
                        hspace=0.2,
                        wspace=0.2)
    # plt.xlim(0,1000)
    

    # write data to plots side by side plots
    ax.plot( plot['mask_norm'],label=f"{k}: {['mask_mse']}",linewidth=1, linestyle=line_style[inc_linew-1])
    # ax0.plot( v['Red'],     linewidth=1, linestyle='solid')
    # ax0.plot( v['Green'],   linewidth=1, linestyle='dashed')
    # ax0.plot( v['Blue'],    linewidth=2, linestyle='dotted')

    inc_linew = inc_linew + 1

ax.legend()
fig.suptitle(test, fontsize=16)
ax.set_xlabel('photo count')
ax.set_ylabel('mse value')