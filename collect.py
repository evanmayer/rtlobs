'''
by Evan Mayer

Library for data collection functions on an rtl-sdr based radio telescope.
'''

import numpy as np
import sys
import time

from rtlsdr import RtlSdr


def meas_brightness_temp(num_samp, gain, rate, fc, t_int, T_sys):
    '''
    Implement a total-power radiometer. Raw, uncalibrated power values.

    Inputs:
    num_samp: Number of elements to sample from the SDR IQ timeseries.
              Greater numbers are more efficient, until limited by device RAM.
    gain:     Requested SDR gain (dB)
    rate:     SDR sample rate, intrinsically tied to bandwidth in SDRs (Hz)
    fc:       Base center frequency (Hz)
    t_int:    Total integration time (s)
    T_sys:    System temperature value, used to convert from raw power meas
              to brightness temp

    Returns:
    T_tot:   Time-averaged brightness temperature in Kelvin
    '''


def run_total_power_int( num_samp, gain, rate, fc, t_int ):
    '''
    Implement a total-power radiometer. Raw, uncalibrated power values.

    Inputs:
    num_samp:   Number of elements to sample from the SDR IQ timeseries.
                2**11 recommended based on testing my rtl-sdr.com v3 dongle.
    gain:       Requested SDR gain (dB)
    rate:       SDR sample rate, intrinsically tied to bandwidth in SDRs (Hz)

    fc:         Base center frequency (Hz)
    t_int:      Total integration time (s)

    Returns:
    p_tot:   Time-averaged power in the signal from the sdr, in 
             uncalibrated units
    '''
    import rtlsdr.helpers as helpers

    # Start the RtlSdr instance
    print('Initializing rtl-sdr with pyrtlsdr:')
    sdr = RtlSdr()

    try:
        sdr.rs = rate
        sdr.fc = fc
        sdr.gain = gain
        print('  sample rate: {} MHz'.format(sdr.rs/1e6))
        print('  center frequency {} MHz'.format(sdr.fc/1e6))
        print('  gain: {} dB'.format(sdr.gain))
        print('  num samples per call: {}'.format(num_samp))
        print('  requested integration time: {}s'.format(t_int))
        # For Nyquist sampling of the passband dv over an integration time
        # tau, we must collect N = 2 * dv * tau real samples.
        # https://www.cv.nrao.edu/~sransom/web/A1.html#S3
        # Because the SDR collects complex samples at a rate rs = dv, we can
        # Nyquist sample a signal of band-limited noise dv with only rs * tau
        # complex samples.
        # The phase content of IQ samples allows the bandlimited signal to be
        # Nyquist sampled at a data rate of rs = dv complex samples per second 
        # rather than the 2* dv required of real samples.
        N = int(sdr.rs * t_int)
        print('  => num samples to collect: {}'.format(N))
        print('  => est. num of calls: {}'.format(int(N / num_samp)))

        global p_tot
        global cnt
        p_tot = 0.0
        cnt = 0

        # Set the baseline time
        start_time = time.time()
        print('Integration began at {}'.format(time.strftime('%a, %d %b %Y %H:%M:%S', time.localtime(start_time))))

        # Time integration loop
        @helpers.limit_calls(N / num_samp)
        def p_tot_callback(iq, context):
            # The below is a total power measurement equivalent to
            # P = V^2 / R = (sqrt(I^2 + Q^2))^2 = (I^2 + Q^2) / 1,
            # setting R=1 since it cancels out when using these in a 
            # calibration.
            global p_tot 
            p_tot += np.sum(np.real(iq*np.conj(iq)))
            global cnt 
            cnt += 1
        sdr.read_samples_async(p_tot_callback, num_samples=num_samp)
        
        end_time = time.time()
        print('Integration ended at {} after {} seconds.'.format(time.strftime('%a, %d %b %Y %H:%M:%S'), end_time-start_time))
        print('{} calls were made to SDR.'.format(cnt))
        print('{} samples were measured at {} MHz'.format(cnt*num_samp, fc/1e6))
        print('for an effective integration time of {:.2f}s'.format(num_samp * cnt / rate))

        # Compute the average power value based on the number of measurements we actually did
        p_avg = p_tot / num_samp / cnt

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
    
    return p_avg


def run_spectrum_int( NFFT, gain, rate, fc, t_int ):
    '''
    Inputs:
    NFFT:     Number of elements to sample from the SDR IQ timeseries: powers of 2 are most efficient
    gain:     Requested SDR gain (dB)
    rate:     SDR sample rate, intrinsically tied to bandwidth in SDRs (Hz)
    fc:       Base center frequency (Hz)
    t_int:    Total effective integration time (s)

    Returns:
    freqs:    Frequencies of the resulting spectrum, centered at fc (Hz), numpy array
    p_xx_avg: Power spectral density spectrum (dB/Hz) numpy array,
    '''
    from scipy.signal import welch
    import rtlsdr.helpers as helpers

    sdr = RtlSdr()

    try:
        sdr.rs = rate # Rate of Sampling (intrinsically tied to bandwidth with SDR dongles)
        sdr.fc = fc
        sdr.gain = gain
        print('  sample rate: %0.6f MHz' % (sdr.rs/1e6))
        print('  center frequency %0.6f MHz' % (sdr.fc/1e6))
        print('  gain: %d dB' % sdr.gain)
        print('  num samples per call: {}'.format(NFFT))
        print('  requested integration time: {}s'.format(t_int))
        N = int(sdr.rs * t_int)
        num_loops = int(N/NFFT)+1
        print('  => num samples to collect: {}'.format(N))
        print('  => est. num of calls: {}'.format(num_loops))

        # Set up arrays to store power spectrum calculated from I-Q samples
        freqs = np.zeros(NFFT)
        p_xx_tot = np.zeros(NFFT)
        cnt = 0

        # Set the baseline time
        start_time = time.time()
        print('Integration began at {}'.format(time.strftime('%a, %d %b %Y %H:%M:%S', time.localtime(start_time))))
        # Since we essentially sample as long as we want on each frequency,
        # Estimate the power spectrum by Bartlett's method.
        # Following https://en.wikipedia.org/wiki/Bartlett%27s_method: 
        # Use scipy.signal.welch to compute 1 periodogram for each set of 
        # samples taken.
        # For non-overlapping intervals, which we have because we are 
        # sampling the timeseries as it comes in, the welch() method is 
        # equivalent to Bartlett's method.
        # We therefore have an N=NFFT-point data segment split up into K=1 
        # non- overlapping segments, of length M=NFFT. This means we can 
        # call welch() on each set of samples from the SDR, accumulate them,
        # and average later by the number of spectra taken to reduce the 
        # noise while still following Barlett's method, and without keeping 
        # huge arrays of iq samples around in RAM.

        # Time integration loop
        for cnt in range(num_loops):
            iq = sdr.read_samples(NFFT)
            
            freqs, p_xx = welch(iq, fs=rate, nperseg=NFFT, noverlap=0, scaling='spectrum', return_onesided=False)
            p_xx_tot += p_xx
        
        end_time = time.time()
        print('Integration ended at {} after {} seconds.'.format(time.strftime('%a, %d %b %Y %H:%M:%S'), end_time-start_time))
        print('{} spectra were measured at {}.'.format(cnt, fc))
        print('for an effective integration time of {:.2f}s'.format(NFFT * cnt / rate))

        # Unfortunately, welch() with return_onesided=False does a sloppy job
        # of returning the arrays in what we'd consider the "right" order,
        # so we have to swap the first and last halves to avoid artifacts
        # in the plot.
        half_len = len(freqs)//2
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
        p_avg = 10.*np.log10(p_xx_tot / cnt)

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

    return freqs, p_avg


def run_fswitch_int( NFFT, gain, rate, fc, fthrow, t_int ):
    '''
    Inputs:
    NFFT:     Number of elements to sample from the SDR IQ timeseries: powers of 2 are most efficient
    gain:     Requested SDR gain (dB)
    rate:     SDR sample rate, intrinsically tied to bandwidth in SDRs (Hz)
    fc:       Base center frequency (Hz)
    fthrow:   Alternate frequency (Hz)
    t_int:    Total effective integration time (s)

    Returns:
    freqs_fold: Frequencies of the spectrum resulting from folding according to the folding method implemented in the f_throw_fold (post_process module)
    p_fold:     Folded frequency-switched power spectral density, centered at fc,(dB/Hz) numpy array.
    '''
    from scipy.signal import welch
    from post_process import f_throw_fold 
    import rtlsdr.helpers as helpers

    sdr = RtlSdr()

    try:
        sdr.rs = rate # Rate of Sampling (intrinsically tied to bandwidth with SDR dongles)
        sdr.fc = fc
        sdr.gain = gain
        print('  sample rate: %0.6f MHz' % (sdr.rs/1e6))
        print('  center frequency %0.6f MHz' % (sdr.fc/1e6))
        print('  gain: %d dB' % sdr.gain)
        print('  num samples per call: {}'.format(NFFT))
        print('  requested integration time: {}s'.format(t_int))
        N = int(sdr.rs * t_int)
        num_loops = (N//NFFT)+1
        print('  => num samples to collect: {}'.format(N))
        print('  => est. num of calls: {}'.format(num_loops))

        # Set up arrays to store power spectrum calculated from I-Q samples
        freqs_on = np.zeros(NFFT)
        freqs_off = np.zeros(NFFT)
        p_xx_on = np.zeros(NFFT)
        p_xx_off = np.zeros(NFFT)
        cnt = 0

        # Set the baseline time
        start_time = time.time()
        print('Integration began at {}'.format(time.strftime('%a, %d %b %Y %H:%M:%S', time.localtime(start_time))))

        # Swap between the two specified frequencies, integrating signal.
        # Time integration loop
        for cnt in range(num_loops):
            tick = (cnt%2 == 0)
            if tick:
                sdr.fc = fc
            else:
                sdr.fc = fthrow

            iq = sdr.read_samples(NFFT)

            if tick:
                freqs_on, p_xx = welch(iq, fs=rate, nperseg=NFFT, noverlap=0, scaling='spectrum', return_onesided=False)
                p_xx_on += p_xx
            else:
                freqs_off, p_xx = welch(iq, fs=rate, nperseg=NFFT, noverlap=0, scaling='spectrum', return_onesided=False)
                p_xx_off += p_xx
        
        end_time = time.time()
        print('Integration ended at {} after {} seconds.'.format(time.strftime('%a, %d %b %Y %H:%M:%S'), end_time-start_time))
        print('{} spectra were measured, split between {} and {}.'.format(cnt, fc, fthrow))
        print('for an effective integration time of {:.2f}s'.format(NFFT * cnt / rate))

        half_len = len(freqs_on)//2
        # Swap frequencies:
        tmp_first = freqs_on[:half_len].copy() 
        tmp_last = freqs_on[half_len:].copy()
        freqs_on[:half_len] = tmp_last
        freqs_on[half_len:] = tmp_first

        tmp_first = freqs_off[:half_len].copy() 
        tmp_last = freqs_off[half_len:].copy()
        freqs_off[:half_len] = tmp_last
        freqs_off[half_len:] = tmp_first

        # Swap powers:
        tmp_first = p_xx_on[:half_len].copy()
        tmp_last = p_xx_on[half_len:].copy()
        p_xx_on[:half_len] = tmp_last
        p_xx_on[half_len:] = tmp_first

        tmp_first = p_xx_off[:half_len].copy()
        tmp_last = p_xx_off[half_len:].copy()
        p_xx_off[:half_len] = tmp_last
        p_xx_off[half_len:] = tmp_first

        # Compute the average power spectrum based on the number of spectra read
        p_avg_on  = 10.*np.log10(p_xx_on  / cnt)
        p_avg_off = 10.*np.log10(p_xx_off / cnt)
        # Shift frequency spectra back to the intended range
        freqs_on = freqs_on + fc
        freqs_off = freqs_off + fthrow

        # Fold switched spectra
        freqs_fold, p_fold = f_throw_fold(freqs_on, freqs_off, p_avg_on, p_avg_off)

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

    return freqs_fold, p_fold


def save_spectrum(filename, freqs, p_xx):
    '''
    Save the results of integration to a file.
    '''
    header='\n\n\n\n\n'
    np.savetxt(filename, np.column_stack((freqs, p_xx)), delimiter=' ', header=header)
    print('Results were written to {}.'.format(filename))

    return

