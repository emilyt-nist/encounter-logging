import numpy as np
import glob


def read_segment(filename, start, stop):
    dt = np.dtype([('time', '<u4'), ('mac', np.uint8, (6,)), ('rssi','i1'),
                   ('ch', 'u1'), ('rpi', np.uint8,(20,))])
    time_dt = np.dtype([('a', np.void, 4), ('epochtime','<u4'),
                        ('offsettime', '<u4'), ('offsetovflw','<u4'),
                        ('distance', '<u2'), ('orientation','<u2'),
                        ('b', np.void,12)])
    raw_header = np.fromfile(filename, dtype=time_dt, count=1, offset=32)
    header = {}
    for key in raw_header.dtype.fields.keys():
        if len(key)>1:
            header[key] = raw_header[key][0]
    data = np.fromfile(filename, dtype=dt, count=stop-2, offset = 32*(start+2))
    return header, data

def find_marks(fname):
    # Find first marker

    f = open(fname,'rb')
    line_count = 0
    last_mark = 0;
    found = False
    marks = []
    while not found:
        chunk = f.read(32)
        # print(chunk.hex().upper())
        marker = b'\x00'*32
        if chunk == marker:
            # print(f'chunk {line_count} has 32bytes of zero')
            marks.append(line_count)
            last_mark = line_count
        if len(chunk)==0:
            # print("Reached end of file, add chunk number")
            break;
        line_count += 1
    marks.append(line_count)
    f.close()
    return marks


if __name__ == '__main__':
    files = glob.glob('raw_NIST0002*.bin')
    files.sort()
    files = files[::-1]
    print(files)



    fname = files[0]
    
    marks = find_marks(fname)
    marks = np.array(marks)
    print(marks)
    idx = np.where(np.diff(np.array(marks))>1)[0]
    ranges = np.array([marks[idx], marks[idx+1]]).T
    segment = 1
    for r in ranges:
        print(r)
        offset = r[0]*32 + 64
        count = (r[1] - r[0]) // 2 - 1
        write_segment(fname, segment, offset, count)
        segment += 1


