
import glob
import os
import time

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objs as go
import plotly.express as px

DATA_PATH = '../data/raw'
PLOT_PATH = '../resources/figures'
CLOSE_LEVEL = -60 #dB

# load data options from raw, marked, data files
def load_raw(fname):
    df = pd.read_csv(fname)
    df['time'] = pd.to_datetime(df['time'])
    df.rename(columns=lambda x: x[1:].strip() if x.startswith("#") else x.strip(), inplace=True)
    # cleanup whitespaces in data
    df = df.applymap(lambda x: x.strip() if type(x)==str else x)
    return df

def load_marked(fname):
    df = pd.read_csv(fname)
    df['time'] = pd.to_datetime(df['time'])
    df['rssi'] = -df['rssi']
    # cleanup whitespaces in data
    df = df.applymap(lambda x: x.strip() if type(x)==str else x)
    return df

def load_data(fname):
    df = pd.read_csv(fname, skiprows=1)
    f = open(fname, 'rb')
    line = f.readline()
    f.close()
    line = line[1:].decode().strip()
    times = line.split(',')
    times = [int(times[0]), int(times[1])]
    # cleanup whitespaces in column names
    df.rename(columns=lambda x: x[1:].strip() if x.startswith("#") else x.strip(), inplace=True)
    # cleanup whitespaces in data
    df = df.applymap(lambda x: x.strip() if type(x)==str else x)
    #. Add columns in which the time on the dongle is converted UNIX EPOCH time, and "datetime64"
    df['time'] = (df['dongle_time']-times[0])/1000 + times[1] - 6*3600
    df['datetime'] = df['time'].astype('datetime64[s]')
    return df


# Matplotlib plotting
def plot_rssi(t, rssi):
    # compute histogram fast
    hist = np.array(np.unique(rssi, return_counts=True)).T

    # definitions for the axes
    left, width = 0.1, 0.65
    bottom, height = 0.1, 0.65
    spacing = 0.005


    rect_scatter = [left, bottom, width, height]
    rect_histy = [left + width + spacing, bottom, 0.2, height]

    # start with a rectangular Figure
    fig = plt.figure(figsize=(16, 8))

    ax_scatter = plt.axes(rect_scatter)
    ax_scatter.tick_params(direction='in', top=True, right=True)

    ax_histy = plt.axes(rect_histy)
    ax_histy.tick_params(direction='in', labelleft=False)

    ax_scatter.plot(t, rssi,'.',  markersize=1)
    ax_scatter.set_xlabel(r'time bin', fontsize=15)
    ax_scatter.set_ylabel(r'RSSI', fontsize=15)
    ax_scatter.set_title('strength of RSSI signal')
                 
    ax_histy.barh(hist[:,0], hist[:,1])
    ax_histy.set_ylim(ax_scatter.get_ylim())
    ax_histy.set_title('histogram of RSSI counts')
    ax_histy.set_xlabel('counts')
   # ax_histy.set_ylabel('RSSI')
    return fig

# Plotly check all data plot
# must input a df with time, rssi and encounter_id
def plot_data_check(df):
    fig = px.scatter(df, x="time", y="rssi", color="encounter_id", hover_data=["close encounter"])
    for trace in fig.data:
        trace.name = trace.name[:4]
    return fig

# Matplotlib plot to check window on single encounter_id data
def plot_window_check(df, transitions):
    fig, ax = plt.subplots(figsize=[12, 8])
    df['rssi'].plot(linestyle='none', marker='o', ax=ax)
    for i in range(0, len(transitions), 2):
        ax.axvspan(transitions[i], transitions[i+1], alpha=0.5)
    ax.set_ylim((-90, -40))
    return fig

#functions
def get_unique(df):
    return np.unique(df['encounter_id'], return_counts=True)

def dbm_to_mw(rssi_dbm):
    return 10**((rssi_dbm)/10.)

def mw_to_dbm(rssi_mw):
    return 10.*np.log10(rssi_mw)

def num_above(window, level=CLOSE_LEVEL):
    # TODO find a cleaner way to do this
    return np.sum([1 if i > level else 0 for i in window])

# take care to apply this to a single encounter_id
def mofn_filter(df, window, readings, level=CLOSE_LEVEL):
    # TODO make suspected_encounter regress to first possible encounter in window?
    df['window_sum'] = df['rssi'].rolling(window).apply(lambda x: num_above(x, level))
    df['suspected_encounter'] = df['window_sum'].apply(lambda x: 1 if x>=readings else 0)
    df['encounter_transition'] = df['suspected_encounter'].shift(1) != df['suspected_encounter']
    return df

# notes transition between yes/no encounter and adds last data point as end transition, if needed
def transitions(df):
    transitions = df[df['encounter_transition']].index[1:]
    if len(transitions)%2:
        transitions = pd.DatetimeIndex.append(transitions,df.index[-1:])
    return transitions


if __name__=='__main__':
    filenames=['kim.csv', 'saewoo.csv']

    for fname in filenames:
        df = load_data(os.path.join(DATA_PATH, fname))

        figure = plot_rssi(df['datetime'], df['rssi'])
        plt.savefig(os.path.join(PLOT_PATH, fname[:-4]))
        plt.close()

        encounter_count = get_unique(df)
        print(f'{fname[:-4]}: {encounter_count}')
