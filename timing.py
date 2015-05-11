import h5py
import numpy as np
import matplotlib.pyplot as plt

def get_times(y, fraction=0.4):
    """
    Returns pulse times in `y` by looking for the pulse
    to cross a constant fraction `fraction` of the pulse height in each
    waveform. `y` should be a 2 dimensional array with shape (N,M) where
    N is the number of waveforms, and M is the number of samples per
    waveform.
    """
    # samples below threshold
    mask1 = y > np.min(y,axis=-1)[:,np.newaxis]*fraction
    # samples before the minimum
    mask2 = np.arange(y.shape[1]) < np.argmin(y,axis=-1)[:,np.newaxis]

    # right side of threshold crossing
    r = y.shape[1] - np.argmax((mask1 & mask2)[:,::-1], axis=-1)
    r[r == 0] = 1
    r[r == y.shape[1]] = y.shape[1] - 1
    l = r - 1

    yl = y[np.arange(y.shape[0]),l]
    yr = y[np.arange(y.shape[0]),r]

    return (np.min(y,axis=-1)*fraction - yl)/(yr-yl) + l

def fft_filter(y, dt, cutoff=500e6):
    """
    Filter the array `y` by removing frequency components above
    `cutoff` in Hz.
    """
    out = np.fft.rfft(y)
    freq = np.fft.rfftfreq(y.shape[1], d=dt)
    out[:,freq > cutoff] = 0
    return np.fft.irfft(out)

def main():
    import matplotlib.pyplot as plt
    import sys
    import time
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('-o', dest='output', default='out.txt')
    parser.add_argument('filenames', nargs='+', help='input files')
    parser.add_argument('-c', '--chunk', type=int, default=100000)
    args = parser.parse_args()

    t = []
    for filename in args.filenames:
        print filename
        with h5py.File(filename) as f:
            start = time.time()
            for i in range(0, f['c1'].shape[0], args.chunk):
                y1 = f['c1'][i:i+args.chunk]
                y2 = f['c2'][i:i+args.chunk]
                mask = np.min(y2,axis=-1) < -1000
                dt = float(f['c1'].attrs['XINCR'])*1e9
                y1 = fft_filter(y1[mask], dt)
                y2 = fft_filter(y2[mask], dt)
                t1 = get_times(-y1)*dt
                t2 = get_times(y2)*dt
                t.extend(t2 - t1)
            stop = time.time()
            print '%.2f seconds to process file' % (stop-start)

    if args.output:
        np.savetxt(args.output, t)

if __name__ == '__main__':
    main()
