import h5py
import numpy as np

def get_times(y, fraction=0.4):
    """
    Returns pulse times in `y` by looking for the pulse
    to cross a constant fraction `fraction` of the pulse height in each
    waveform. `y` should be a 2 dimensional array with shape (N,M) where
    N is the number of waveforms, and M is the number of samples per
    waveform.
    """
    # samples below threshold
    mask1 = y < np.min(y,axis=-1)[:,np.newaxis]*fraction
    # samples before the minimum
    mask2 = np.arange(y.shape[1]) < np.argmin(y,axis=-1)[:,np.newaxis]

    # right side of threshold crossing
    r = np.argmax(mask1 & mask2, axis=-1)
    r[r == 0] = 1
    # left side
    l = r -1

    yl = y[np.arange(y.shape[0]),l]
    yr = y[np.arange(y.shape[0]),r]

    return (np.min(y,axis=-1)*fraction - yl)/(yr-yl) + l

def fft_filter(y, cutoff=300e6, sample_rate=2e9):
    """
    Filter the array `y` by removing frequency components above
    `cutoff` in Hz.
    """
    out = np.fft.rfft(y)
    freq = np.fft.rfftfreq(y.shape[1], d=1.0/sample_rate)
    out[:,freq > cutoff] = 0
    return np.fft.irfft(out)

def main():
    import matplotlib.pyplot as plt
    import sys
    import time
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('-o', dest='output')
    parser.add_argument('filenames', nargs='+', help='input files')
    args = parser.parse_args()

    t2 = []
    for filename in args.filenames:
        print filename
        with h5py.File(filename) as f:
            start = time.time()
            y2 = f['c2'][:]
            stop = time.time()
            print '%.2f seconds to open file' % (stop-start)
            mask = np.min(y2,axis=-1) < -1000
            y1 = -f['c1'][:][mask,:]
            y1 = fft_filter(y1)
            y2 = fft_filter(y2[mask])
            t1 = get_times(y1)

            dt = float(f['c1'].attrs['XINCR'])*1e9
            t2.extend((get_times(y2) - t1)*dt) # convert to ns
    if args.output:
        np.savetxt(args.output, t2)
    plt.hist(t2, bins=1024, range=[-100,200],log=True)
    plt.xlabel('Time (ns)')
    plt.show()

if __name__ == '__main__':
    main()
