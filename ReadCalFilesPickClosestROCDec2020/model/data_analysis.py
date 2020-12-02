
import glob
import os
import sys
import time

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objs as go
import plotly.express as px

module_path = os.path.abspath(os.path.join('..'))
if module_path not in sys.path:
    sys.path.append(module_path)
from model import en_convert

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

def load_cal(fname):
    df = pd.read_csv(fname)
    df['time'] = pd.to_datetime(df['time'])
    # cleanup whitespaces in data
    df = df.applymap(lambda x: x.strip() if type(x)==str else x)
    # parse filename string for calibration test specifications
    fname_parts = fname.split("_")
    fname_cal_parts = fname_parts[-1].split(".")
    cal_char = list(fname_cal_parts[0])
    distance = float(''.join((cal_char[-3], '.', cal_char[-1])))
    if len(cal_char) == 4:
        cal_config = cal_char[0]
    elif len(cal_char) == 5:
        cal_config = ''.join((cal_char[0], cal_char[1]))
    # add column distance based on filename string
    df['distance'] = distance
    # add column orientation based on filename string
    df['cal_config'] = cal_config
    # copy or rename mac to encounter_id
    df['encounter_id'] = df['mac']
    return df

def load_cal_bin(fname, n_pts):
    print(fname)
    # parse filename to check cal config and distance
    fname_parts = fname.split("_")
    fname_cal_parts = fname_parts[-1].split(".")
    print(fname_cal_parts)
    cal_char = list(fname_cal_parts[0])
    distance = float(''.join((cal_char[-3], '.', cal_char[-1])))
    if len(cal_char) == 4:
        cal_config = cal_char[0]
    elif len(cal_char) == 5:
        cal_config = ''.join((cal_char[0], cal_char[1]))
    else: print(fname, cal_char) # testing
    print(cal_char, cal_config)
    marks = en_convert.find_marks(fname)
    datasets = {}
    # DO need to loop over datasets to make the complete dataframe
    for index in range(len(marks) - 1):
        datasets[index] = {}
        datasets[index]['header'], datasets[index]['data'] = en_convert.read_segment(fname, marks[index], marks[index+1])
    # now have the header & data. need to form into a dataframe
    # from the header, get epochtime, distance (now cm), orientation(was cal_config)
    # need timestamp, channel, mac or encounter id
    # “time since device boot”, “mac — a vector with 6 values”, “rssi”, “channel”, “rpi — a vector with 20 values”
    # convert mac vector with 6 values to hexadecimal

        if len(datasets[index]['data']) > 2*n_pts:
            i=0
            device_time = np.empty(len(datasets[index]['data']))
            mac = [None]*len(datasets[index]['data'])
            rssi = np.empty(len(datasets[index]['data']))
            ch = np.empty(len(datasets[index]['data']))

            for row in datasets[index]['data']:
                device_time[i] = row[0]
                mac[i] = (bytes(row[1]).hex())
                rssi[i] = row[2]
                ch[i] = row[3]
                i += 1

        # make the dataframe
            d = {'device_time':device_time, 'mac':mac, 'rssi':rssi, 'ch':ch}
            df = pd.DataFrame(data=d)
            if df['ch'][1] > 0:
                df['ch'] = -df['ch']
            df['epochtime'] = datasets[index]['header']['epochtime']
            df['offsettime'] = datasets[index]['header']['offsettime']
            df['offsetovflw'] = datasets[index]['header']['offsetovflw']
            df['distance_header'] = datasets[index]['header']['distance']
            df['distance_fname'] = distance*100 #make both distances in cm
            df['cal_config'] = cal_config
            df['orientation'] = datasets[index]['header']['orientation']
            df['encounter_id'] = df['mac']
            df['time'] = (df['device_time']-datasets[index]['header']['offsettime'])/1000 + datasets[index]['header']['epochtime'] - 6*3600
            df['time'] = df['time'].astype('datetime64[s]')
            df['source_filename'] = fname
            
            # discard the first and last n data points
            df.drop(df.head(n_pts).index, inplace = True)
            df.drop(df.tail(n_pts).index, inplace = True)
            
            # Could try here to discard encounter_ids with most negative RSSI averages
            #Max = 0
            #df.groupby('encounter_id').agg("mean")
            
    return df

def label_cal_data(df):
    df['encounter_label'] = 1
    for i, row in df.iterrows():
        if row['distance'] >= 200: #now in cm
            df.loc[i, 'encounter_label'] = 0
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

    ax_histy.barh(hist[:,0], hist[:,1])
    ax_histy.set_ylim(ax_scatter.get_ylim())
    return fig

# Plotly check all data plot
# must input a df with time, rssi and encounter_id
def plot_data_check(df):
    if "close encounter" in df:
        fig = px.scatter(df, x="time", y="rssi", color="encounter_id", hover_data=["close encounter"])
    else:
        fig = px.scatter(df, x="time", y="rssi", color="encounter_id")
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

# plot the roc curve
def plot_roc_curve_custom(fpr, tpr, rssi50, rssi60, WINDOW_SIZE, REQUIRED_READINGS):
    plt.plot(fpr, tpr, 'co', label='ROC')
    plt.plot([0, 1], [0, 1], color='grey', linestyle='--')
    plt.plot(fpr[rssi60],tpr[rssi60],'ro', label='RSSI 60')
    plt.plot(fpr[rssi50],tpr[rssi50],'ko', label='RSSI 50')
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title('MofN ROC: M=' + str(REQUIRED_READINGS) + ', N=' + str(WINDOW_SIZE))
    plt.legend()
    plt.show()

# plot the roc curve
def plot_roc_curve_save(fpr, tpr, rssi50, rssi60, WINDOW_SIZE, REQUIRED_READINGS,output_filename):
    plt.plot(fpr, tpr, 'co', label='ROC')
    plt.plot([0, 1], [0, 1], color='grey', linestyle='--')
    plt.plot(fpr[rssi60],tpr[rssi60],'ro', label='RSSI 60')
    plt.plot(fpr[rssi50],tpr[rssi50],'ko', label='RSSI 50')
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title('MofN ROC: M=' + str(REQUIRED_READINGS) + ', N=' + str(WINDOW_SIZE))
    plt.legend()
    plt.show()
    plt.savefig(output_filename)
    
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
    #df['window_sum'] = df['rssi'].rolling(window).apply(lambda x: num_above(x, level))
    df.loc[:, ('window_sum')]  = df['rssi'].rolling(window).apply(lambda x: num_above(x, level))
    df.loc[:,('suspected_encounter')] = df['window_sum'].apply(lambda x: 1 if x>=readings else 0)
    df.loc[:,('encounter_transition')] = df['suspected_encounter'].shift(1) != df['suspected_encounter']
    #    df['window_sum'] = df['rssi'].rolling(window).apply(lambda x: num_above(x, level))
    # df['suspected_encounter'] = df['window_sum'].apply(lambda x: 1 if x>=readings else 0)
    #df['encounter_transition'] = df['suspected_encounter'].shift(1) != df['suspected_encounter']
    return df

# notes transition between yes/no encounter and adds last data point as end transition, if needed
def get_transitions(df):
    transitions = df[df['encounter_transition']].index[1:]
    if len(transitions)%2:
        transitions = pd.DatetimeIndex.append(transitions,df.index[-1:])
    return transitions

def find_gaps(df):
    i = 0
    for eid, df_eid in df.groupby('encounter_id'):
        df_eid.loc[df_eid['time'].diff()<= pd.Timedelta(minutes=10),'gap'] = 0
        df_eid.loc[df_eid['time'].diff()> pd.Timedelta(minutes=10),'gap'] = 1
        df_eid.loc[:,('count')]=df_eid['gap'].sum()
        df.loc[df['encounter_id']==eid, 'count'] = df_eid['count']
        df.loc[df['encounter_id']==eid, 'eid_index'] = i
#        df_eid['gap'] = df_eid['time'].diff() > pd.Timedelta(minutes=10)
#        df_eid['count'] = df_eid['gap'].map(lambda x: 1 if x else 0).cumsum()
#        df.loc[df['encounter_id']==eid, 'count'] = df_eid['count']
#        df.loc[df['encounter_id']==eid, 'eid_index'] = i
        i += 1
    #df['trace'] = df[['encounter_id', 'count']].apply(lambda x: '_'.join((x[0][:4], str(x[1]))), axis=1)
    df.loc[:,('trace')] = df[['encounter_id', 'count']].apply(lambda x: '_'.join((x[0][:4], str(x[1]))), axis=1)

#def keep_2_lowest(df)
#    i = 0
#    for eid, df_eid in df.groupby('encounter_id'):
#        df_eid.loc[:,('SumRSSI')]=df_eid['rssi'].sum()
#        #sorted(df_eid['sum'])
#        temp = df.sort_values(by='SumRSSI')#, ascending=False)
#    df.loc(:,('use')) =
    
def count_traces(df):
#     print(df['trace'].value_counts())
    return len(df['trace'].unique())

def plot_these_traces(df, fig, WINDOW_SIZE, REQD_READINGS, CLOSE_LEVEL, ylim0, ylim1, figcolors):
    i=0
    for trace, df_trace in df.groupby(['trace']):

        plot_a_trace(df_trace, fig, i, WINDOW_SIZE, REQD_READINGS, CLOSE_LEVEL, ylim0, ylim1, figcolors)
        i += 1
    fig.show()

def plot_a_trace(df_eid, fig, plot_index, WINDOW_SIZE, REQD_READINGS, CLOSE_LEVEL, ylim0, ylim1, figcolors):
    eid_index = int(df_eid.head(1).squeeze()['eid_index'])
    df_eid = mofn_filter(df_eid, WINDOW_SIZE, REQD_READINGS, CLOSE_LEVEL)
    df_eid.set_index('time', inplace=True)
    transitions = get_transitions(df_eid)
    #print(eid_index)
    for i in range (0, len(transitions), 2):
        fig.add_trace(go.Scatter(x=[transitions[i], transitions[i], transitions[i+1], transitions[i+1], transitions[i]],
                                 y=[ylim0, ylim1, ylim1, ylim0, ylim0], mode="lines",
                                 fill="toself",line_width=0, fillcolor=figcolors[eid_index], opacity = 0.5, showlegend=False),
                     row=1, col=plot_index+1)

    fig.add_trace(go.Scatter(x=df_eid.index, y=df_eid.rssi,
                             mode="markers", marker_color=figcolors[eid_index], hovertext=df_eid.ch), row=1, col=plot_index+1)

def roc_these_traces(df, WINDOW_SIZE, REQD_READINGS, close_level_min=0, close_level_max=-90, step=1):
    fpr = np.zeros(len(range(close_level_min, close_level_max, -step)))
    tpr = np.zeros(len(range(close_level_min, close_level_max, -step)))

    for index, close_level in enumerate(range(close_level_min, close_level_max, -step)):
        col = f'suspected_{close_level}'
        for trace, df_trace in df.groupby(['trace']):
            label_a_trace(df_trace, close_level, WINDOW_SIZE, REQD_READINGS)
            df.loc[df['trace']==trace, 'suspected_encounter'] = df_trace['suspected_encounter'].values
        fpr[index], real_neg = get_fpr(df[['suspected_encounter', 'encounter_label']])
        tpr[index], real_pos = get_tpr(df[['suspected_encounter', 'encounter_label']])
        data_check = real_neg/real_pos
    return fpr, tpr, data_check

def label_a_trace(df_eid, close_level, WINDOW_SIZE, REQD_READINGS):
    df_eid = mofn_filter(df_eid, WINDOW_SIZE, REQD_READINGS, close_level)
    df_eid.set_index('time', inplace=True)

# generates false positive rate
def get_fpr(df):
    fp = 0
    for i in range(0,len(df)):
        if df.suspected_encounter[i] > df.encounter_label[i]:
            fp = fp + 1
    real_neg = np.sum(1-df.encounter_label)
    fpr = fp/real_neg
    return fpr, real_neg

# generates true positive rate
def get_tpr(df):
    tp = 0
    for i in range(0,len(df)):
        if df.suspected_encounter[i] == 1 & df.encounter_label[i] == 1:
            tp = tp + 1
    real_pos = np.sum(df.encounter_label)
    tpr = tp/real_pos
    return tpr, real_pos



if __name__=='__main__':
    filenames=['kim.csv', 'saewoo.csv']

    for fname in filenames:
        df = load_data(os.path.join(DATA_PATH, fname))

        figure = plot_rssi(df['datetime'], df['rssi'])
        plt.savefig(os.path.join(PLOT_PATH, fname[:-4]))
        plt.close()

        encounter_count = get_unique(df)
        print(f'{fname[:-4]}: {encounter_count}')
