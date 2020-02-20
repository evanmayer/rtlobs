'''
by Evan Mayer

Experimental library for data collection functions on an rtl-sdr based radio 
telescope.
New stuff I'm trying out will appear here, with no guarantee of stability or 
functionality.
'''

import numpy as np
from scipy.signal import get_window
import sys
import time

from rtlsdr import RtlSdr


def run_gpu_spectrum_int( num_samp, nbins, gain, rate, fc, t_int ):
    '''
    Inputs:
    num_samp: Number of elements to sample from the SDR IQ per call;
              use powers of 2
    nbins:    Number of frequency bins in the resulting power spectrum; powers
              of 2 are most efficient, and smaller numbers are faster on CPU.
    gain:     Requested SDR gain (dB)
    rate:     SDR sample rate, intrinsically tied to bandwidth in SDRs (Hz)
    fc:       Base center frequency (Hz)
    t_int:    Total effective integration time (s)

    Returns:
    freqs:       Frequencies of the resulting spectrum, centered at fc (Hz), 
                 numpy array
    p_avg_db_hz: Power spectral density (dB/Hz) numpy array
    '''
    import cupy as cp
    import cusignal

    # Force a choice of window to allow converting to PSD after averaging
    # power spectra
    WINDOW = 'hann'
    # Force a default nperseg for welch() because we need to get a window
    # of this size later. Use the scipy default 256, but enforce scipy 
    # conditions on nbins vs. nperseg when nbins gets small. 
    if nbins < 256:
        nperseg = nbins
    else:
        nperseg = 256

    print('Initializing rtl-sdr with pyrtlsdr:')
    sdr = RtlSdr()

    try:
        sdr.rs = rate # Rate of Sampling (intrinsically tied to bandwidth with SDR dongles)
        sdr.fc = fc
        sdr.gain = gain
        print('  sample rate: %0.6f MHz' % (sdr.rs / 1e6))
        print('  center frequency %0.6f MHz' % (sdr.fc / 1e6))
        print('  gain: %d dB' % sdr.gain)
        print('  num samples per call: {}'.format(num_samp))
        print('  PSD binning: {} bins'.format(nbins))
        print('  requested integration time: {}s'.format(t_int))
        N = int(sdr.rs * t_int)
        num_loops = int(N / num_samp) + 1
        print('  => num samples to collect: {}'.format(N))
        print('  => est. num of calls: {}'.format(num_loops - 1))

        # Set up arrays to store power spectrum calculated from I-Q samples
        freqs = cp.zeros(nbins)
        p_xx_tot = cp.zeros(nbins, dtype=complex)
        # Create mapped, pinned memory for zero copy between CPU and GPU
        gpu_iq = cusignal.get_shared_mem(num_samp, dtype=np.complex128)
        cnt = 0

        # Set the baseline time
        start_time = time.time()
        print('Integration began at {}'.format(time.strftime('%a, %d %b %Y %H:%M:%S', time.localtime(start_time))))
        # Estimate the power spectrum by Bartlett's method.
        # Following https://en.wikipedia.org/wiki/Bartlett%27s_method: 
        # Use scipy.signal.welch to compute one spectrum for each timeseries
        # of samples from a call to the SDR.
        # The scipy.signal.welch() method with noverlap=0 is equivalent to 
        # Bartlett's method, which estimates the spectral content of a time-
        # series by splitting our num_samp array into K segments of length
        # nperseg and averaging the K periodograms.
        # The idea here is to average many calls to welch() across the
        # requested integration time; this means we can call welch() on each 
        # set of samples from the SDR, accumulate the binned power estimates,
        # and average later by the number of spectra taken to reduce the 
        # noise while still following Barlett's method, and without keeping 
        # huge arrays of iq samples around in RAM.
        
        # Time integration loop
        for cnt in range(num_loops):
            # Move USB-collected samples off CPU and onto GPU for calc
            gpu_iq[:] = sdr.read_samples(num_samp)
            
            freqs, p_xx = cusignal.welch(gpu_iq, fs=rate, nperseg=nperseg, nfft=nbins, noverlap=0, scaling='spectrum', window=WINDOW, detrend=False, return_onesided=False)
            p_xx_tot += p_xx
        
        end_time = time.time()
        print('Integration ended at {} after {} seconds.'.format(time.strftime('%a, %d %b %Y %H:%M:%S'), end_time-start_time))
        print('{} spectra were measured at {}.'.format(cnt, fc))
        print('for an effective integration time of {:.2f}s'.format(num_samp * cnt / rate))

        # Unfortunately, welch() with return_onesided=False does a sloppy job
        # of returning the arrays in what we'd consider the "right" order,
        # so we have to swap the first and last halves to avoid an artifact
        # in the plot.
        half_len = len(freqs) // 2
        # Swap frequencies:
        tmp_first = freqs[:half_len].copy() 
        tmp_last = freqs[half_len:].copy()
        freqs[:half_len] = tmp_last
        freqs[half_len:] = tmp_first

        # Swap powers:
        tmp_first = p_xx_tot[:half_len].copy()
        tmp_last = p_xx_tot[half_len:].copy()
        p_xx_tot[:half_len] = tmp_last
        p_xx_tot[half_len:] = tmp_first

        # Compute the average power spectrum based on the number of spectra read
        p_avg = p_xx_tot / cnt

        # Convert to power spectral density
        # A great resource that helped me understand the difference:
        # https://community.sw.siemens.com/s/article/what-is-a-power-spectral-density-psd
        # We could just divide by the bandwidth, but welch() applies a
        # windowing correction to the spectrum, and does it differently to
        # power spectra and PSDs. We multiply by the power spectrum correction 
        # factor to remove it and divide by the PSD correction to apply it 
        # instead. Then divide by the bandwidth to get the power per unit 
        # frequency.
        # See the scipy docs for _spectral_helper().
        win = get_window(WINDOW, nperseg)
        p_avg_hz = p_avg * ((win.sum()**2) / (win*win).sum()) / rate

        p_avg_db_hz = 10. * cp.log10(p_avg_hz)

        # Shift frequency spectra back to the intended range
        freqs = freqs + fc

        # nice and tidy
        sdr.close()

    except OSError as err:
        print("OS error: {0}".format(err))
        raise(err)
    except:
        print('Unexpected error:', sys.exc_info()[0])
        raise
    finally:
        sdr.close()

    return cp.asnumpy(freqs), cp.asnumpy(p_avg_db_hz)

