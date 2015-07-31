import socket
import numpy as np

class Scope(object):
    def __init__(self, host, port=4000):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host,port))

    def send(self, msg):
        if not msg.endswith('\n'):
            msg += '\n'
        self.sock.sendall(msg)

    def ask(self, msg):
        self.send(msg)
        return self.recv()

    def recv(self):
        reply = ''
        while not reply.endswith('\n'):
            reply += self.sock.recv(1024)
        return reply

    def trigger(self):
        self.send('acquire:state on')
        while not int(self.ask('*opc?')):
            pass

    def get_waveform(self, i):
        self.send('data:source CH%i' % i)
        self.send('curve?')
        _, n = self.sock.recv(2)
        nbytes = int(self.sock.recv(int(n)))
        data = ''
        while len(data) < nbytes:
            data += self.sock.recv(nbytes - len(data))
        assert self.sock.recv(1) == '\n'
        return np.fromstring(data,dtype=np.int16)

if __name__ == '__main__':
    import sys
    import h5py
    import argparse
    import time
    import signal

    parser = argparse.ArgumentParser()
    parser.add_argument('-n', type=int, default=100)
    parser.add_argument('filename', help='output filename')
    parser.add_argument('-c', '--chunk', type=int, default=1000)
    args = parser.parse_args()

    stop = False

    def ctrlc_handler(signum, frame):
        print 'ctrl-c caught. quitting...'
        stop = True

    signal.signal(signal.SIGINT, ctrlc_handler)

    t = Scope('pompidou.uchicago.edu')
    print 'connected to %s' % t.ask('*idn?').strip()

    # make sure the data is little endian
    t.send('data:encdg SRIBINARY')

    t.send('select:ch1 on')
    t.send('horizontal:recordlength 500')
    t.send('acquire:mode sample')
    t.send('acquire:stopafter sequence')
    t.send('horizontal:fastframe:state 1')
    t.send('horizontal:fastframe:count %i' % args.chunk)
    t.send('header 0')

    with h5py.File(args.filename,'w') as f:
        for k, v in [s.split(' ', 1) for s in t.ask('*lrn?').split(';')]:
            # set up the scope configuration
            f.attrs[k] = v

        f.create_dataset('c1', (args.n, 500), dtype=np.int16, compression='gzip')
        f.create_dataset('c2', (args.n, 500), dtype=np.int16, compression='gzip')

        # turn headers on so the output of wfmpre? has headers
        t.send('header 1')
        for channel in [1,2]:
            t.send('data:source CH%i' % channel)
            for k, v in [s.split(' ', 1) for s in t.ask('wfmoutpre?')[11:].split(';')]:
                    f[name].attrs[k] = v
        t.send('header 0')

        start = time.time()
        for i in range(0,args.n,args.chunk):
            if stop:
                break
            rate = i/(time.time() - start)
            print '\r%i/%i %.2f Hz' % (i,args.n,rate),
            sys.stdout.flush()
            # wait for trigger
            t.trigger()

            f['c1'][i:i+args.chunk] = t.get_waveform(1).reshape((args.chunk,-1))
            f['c2'][i:i+args.chunk] = t.get_waveform(2).reshape((args.chunk,-1))
        print '\r%i/%i' % (i+args.chunk,args.n)
