import numpy as np
from model import en_convert

def read_raw(filename, start, stop):
    dt = np.dtype([('time', '<u4'), ('mac', np.uint8, (6,)), ('rssi','i1'),
                   ('ch', 'u1'), ('rpi', np.uint8,(20,))])
    time_dt = np.dtype([('a', np.void, 4), ('epochtime','<u4'),
                        ('offsettime', '<u4'), ('offsetovflw','<u4'),
                        ('distance', '<u2'), ('orientation','<u2'),
                        ('b', np.void,12)])
    raw_header = np.fromfile(filename, dtype=time_dt, count=1, offset=32)
    data = np.fromfile(filename, dtype=dt, count=stop-2, offset = 32*(start+2))
    return raw_header, data

def append_raw(filename, header, data):
    f = open(filename, 'ab')
    zero_mark = 32*b'\x00'
    f.write(zero_mark)
    header.tofile(f)
    data.tofile(f)
    f.flush()
    
def filter_file(input_filename, output_filename, mac_addr):
    """ write a new binary file that has only the mac_addr events that were in
    the input file
    """
    print(f'processing {input_filename} to {output_filename}')
    marks = en_convert.find_marks(input_filename)
    print('marks', marks)
    for mark_index in marks[:-1]:
        print('\t section ', mark_index, end=' ')
        header, data = read_raw(input_filename, marks[mark_index], marks[mark_index + 1] )
        print('checking mac', data[:]['mac'])
        print('hex',bytes(data[2]['mac']).hex().upper())
        macs = [bytes(mac).hex().upper() for mac in data[:]['mac']] 
        print(np.unique(macs, return_counts=True))
        mac_match_bool = [bytes(mac).hex().upper()==mac_addr.upper() for mac in data[:]['mac']]
     #   print('tested:', [bytes(mac).hex().upper() for mac in data[:]['mac']])
        print(f'number of mac {mac_addr} matches:', np.array(mac_match_bool).sum(),f'/ {len(data)}')

        append_raw(output_filename, header, data[mac_match_bool])

    print('done')
    
def findMaxrssi(input_filename):
    """  For the given input filename find the mac address for the closest device (largest RSSI)"""
    marks = en_convert.find_marks(input_filename)
    print('marks', marks)
    for mark_index in marks[:-1]:
        print('\t section ', mark_index, end=' ')
        header, data = read_raw(input_filename, marks[mark_index], marks[mark_index + 1] )
#        print(data[:]['rssi'])
#        print(data[:]['mac'])
## I'm not sure if the below should be indented?
    macs = [bytes(mac).hex().upper() for mac in data[:]['mac']] 
    whichmacs = np.array((np.unique(macs)))  # This gives a list of unique mac addresses in this file
    mydata = np.zeros(len(macs), dtype={'names':('mac', 'rssi'),
                          'formats':('U12', 'f8')}) # This makes a new numpy array with mac address as
    #                                                 unicode string for easy comparison
#   print(mydata.dtype)
    MeanRSSIs = [(mydata[mydata[:]['mac']==address]['rssi']).mean() for address in whichmacs]
    # The above gives the mean rssi value for each unique mac address
    ClosestMac = whichmacs[MeanRSSIs.index(max(MeanRSSIs))]
    # The above gives the Mac address with the largest mean RSSI value
    return ClosestMac
        #        RSSImean =[data[data['mac']==mac]['rssi'].mean() for mac in data[:]['mac']]
#        data[data['age'] < 30]['name']
        
#        RSSIs = [bytes(rssi) for RSSI in data[:]['rssi']]
#        print(RSSIs)
    print('done')
    
def findMaxrssiFilterFile(input_filename, output_filename):
    """ write a new binary file that has only the mac_addr events from the closest device
    """
    print(input_filename)
    marks = en_convert.find_marks(input_filename)
    print('marks', marks)
    for mark_index in marks[:-1]:
        print('\t section ', mark_index, end=' ')
        header, data = read_raw(input_filename, marks[mark_index], marks[mark_index + 1] )
#        print(data[:]['rssi'])
#        print(data[:]['mac'])
    macs = [bytes(mac).hex().upper() for mac in data[:]['mac']] 
    whichmacs = np.array((np.unique(macs)))  # This gives a list of unique mac addresses in this file
    mydata = np.zeros(len(macs), dtype={'names':('mac', 'rssi'),
                          'formats':('U12', 'f8')}) # This makes a new numpy array with mac address as
#                                                      unicode string for easy comparison
    mydata['mac']=macs
    mydata['rssi']=data['rssi']
    MeanRSSIs = [(mydata[mydata[:]['mac']==address]['rssi']).mean() for address in whichmacs]
        # The above gives the mean rssi value for each unique mac address
    print(whichmacs)
    print(MeanRSSIs)
    ClosestMac = whichmacs[MeanRSSIs.index(max(MeanRSSIs))]
        # The above gives the Mac address with the largest mean RSSI value
    print('ClosestMac', ClosestMac)    
    for mark_index in marks[:-1]:
        print('\t section ', mark_index, end=' ')
        header, data = read_raw(input_filename, marks[mark_index], marks[mark_index + 1] )
#        print('checking mac', data[:]['mac'])
#        print('hex',bytes(data[:]['mac']).hex().upper())
        macs = [bytes(mac).hex().upper() for mac in data[:]['mac']] 
#        print('checking mac', data[:]['mac'])
#        print('hex',bytes(data[2]['mac']).hex().upper())
#        print(np.unique(macs, return_counts=True))
        mac_match_bool = [bytes(mac).hex().upper()==ClosestMac for mac in data[:]['mac']]
 #       print('tested:', [bytes(mac).hex().upper() for mac in data[:]['mac']])
        print(f'number of mac {ClosestMac} matches:', np.array(mac_match_bool).sum(),f'/ {len(data)}')

        append_raw(output_filename, header, data[mac_match_bool])

    print('done')
    