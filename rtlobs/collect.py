'''
by Evan Mayer

Library for data collection functions on an rtl-sdr based radio telescope.
'''

import logging
import numpy as np
from scipy.signal import welch, get_window
import sys
import time

from rtlsdr import RtlSdr
import rtlsdr.helpers as helpers


def get_sdr(rate=2.32e6, fc=1.4204e9, gain=35.0):
    # Start the RtlSdr instance
    logging.debug('Initializing rtl-sdr with pyrtlsdr')
    sdr = RtlSdr()
    sdr.rs = rate
    sdr.fc = fc
    sdr.gain = gain
    logging.debug('sample rate: {} MHz'.format(sdr.rs / 1e6))
    logging.debug('center frequency {} MHz'.format(sdr.fc / 1e6))
    logging.debug('gain: {} dB'.format(sdr.gain))
    return sdr


def run_total_power_int(num_samp, gain, rate, fc, t_int, sdr=None):
    '''
    Implement a total-power radiometer. Raw, uncalibrated power values.

    Parameters
    ----------
    num_samp
        Number of elements to sample from the SDR IQ timeseries per call
    gain
        Requested SDR gain (dB)
    rate
        SDR sample rate, intrinsically tied to bandwidth in SDRs (Hz)
    fc
        Bandpass center frequency (Hz)
    t_int
        Total integration time (s)
    sdr : RtlSdr (optional)
        If provided, do not initialize a new instance.

    Returns
    -------
    p_tot
        Time-averaged power in the signal from the sdr, in uncalibrated units
    '''
    try:
        if sdr is None:
            sdr = get_sdr(rate, fc, gain)
            close_sdr = True
        else:
            close_sdr = False
        logging.debug('  num samples per call: {}'.format(num_samp))
        logging.debug('  requested integration time: {}s'.format(t_int))
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
        logging.debug('  => num samples to collect: {}'.format(N))
        logging.debug('  => est. num of calls: {}'.format(int(N / num_samp)))

        global p_tot
        global cnt
        p_tot = 0.0
        cnt = 0

        # Set the baseline time
        start_time = time.time()
        logging.info('Integration began at {}'.format(time.strftime('%a, %d %b %Y %H:%M:%S', time.localtime(start_time))))

        # Time integration loop
        @helpers.limit_calls(N / num_samp)
        def p_tot_callback(iq, context):
            # The below is a total power measurement equivalent to summing
            # P = V^2 / R = (sqrt(I^2 + Q^2))^2 = (I^2 + Q^2)
            global p_tot
            # compensate for DC spike
            iq = (iq.real - iq.real.mean()) + (1j * (iq.imag - iq.imag.mean()))
            p_tot += np.sum(np.real(iq * np.conj(iq)))
            global cnt 
            cnt += 1
        sdr.read_samples_async(p_tot_callback, num_samples=num_samp)
        
        end_time = time.time()
        logging.info('Integration ended at {} after {} seconds.'.format(time.strftime('%a, %d %b %Y %H:%M:%S'), end_time-start_time))
        logging.debug('{} calls were made to SDR.'.format(cnt))
        logging.debug('{} samples were measured at {} MHz'.format(cnt * num_samp, fc / 1e6))
        logging.debug('for an effective integration time of {:.2f}s'.format( (num_samp * cnt) / rate))

        # Compute the average power value based on the number of measurements 
        # we actually did
        p_avg = p_tot / (num_samp * cnt)

        if close_sdr:
            # nice and tidy
            sdr.close()

    except:
        print('Unexpected error:', sys.exc_info()[0])
        raise
    finally:
        if sdr is not None and close_sdr:
            sdr.close()

    return p_avg


def dicke(num_samp, gain, rate, fc, t, sdr=None, plot=False):
    '''
    Implement Dicke noise switching using RTL-SDRblog v3 GPIO

    Parameters
    ----------
    num_samp
        Number of elements to sample from the SDR IQ timeseries per call
    gain
        Requested SDR gain (dB)
    rate
        SDR sample rate, intrinsically tied to bandwidth in SDRs (Hz)
    fc
        Bandpass center frequency (Hz)
    t_int
        Total time (s)
    sdr : RtlSdr (optional)
        If provided, do not initialize a new instance.

    Returns
    -------
    iq
        Complex samples from the device
    '''

    if plot:
        import matplotlib.pyplot as plt
        import matplotlib.animation as animation
        fig, ax = plt.subplots()
        plt.ion()
        plt.show()
        window_size = 300
        t_window = np.arange(window_size)
        p_window = np.zeros(window_size)
        line, = ax.plot(t_window, p_window)
        fig.canvas.flush_events()
        fig.canvas.draw()

    try:
        if sdr is None:
            sdr = get_sdr(rate, fc, gain)
            close_sdr = True
        else:
            close_sdr = False
        sdr.rs = rate
        sdr.fc = fc
        sdr.gain = gain
        logging.debug('  sample rate: {} MHz'.format(sdr.rs / 1e6))
        logging.debug('  center frequency {} MHz'.format(sdr.fc / 1e6))
        logging.debug('  gain: {} dB'.format(sdr.gain))
        logging.debug('  num samples per call: {}'.format(num_samp))
        logging.debug('  requested integration time: {}s'.format(t))
        N = int(sdr.rs * t)
        logging.debug('  => num samples to collect: {}'.format(N))
        logging.debug('  => est. num of calls: {}'.format(int(N / num_samp)))

        # Set a GPIO pin (RTL-SDRblog v3 header 31) as noise source trigger
        sdr.set_gpio_output(4)

        ts = []
        ps = []
        noise_on = []
        flipflop = 1
        for i in range(N // num_samp):
            curtime = time.time()
            time_str = time.strftime('%a, %d %b %Y %H:%M:%S', time.localtime(curtime))

            if flipflop:
                sdr.set_gpio_bit(4, 1)
            else:
                sdr.set_gpio_bit(4, 0)

            iq = sdr.read_samples(num_samp)
            # compensate for DC spike
            iq = (iq.real - iq.real.mean()) + (1j * (iq.imag - iq.imag.mean()))
            p_tot = np.sum(np.real(iq * np.conj(iq)))
            
            ts.append(curtime)
            ps.append(p_tot)
            noise_on.append(flipflop)
            flipflop = 1 - flipflop

            if plot:
                if len(ts) < 4:
                    continue
                elif len(ts) < window_size:
                    cur_window = len(ts)
                else:
                    cur_window = window_size
                noise_on_window = noise_on[-cur_window:]
                t_window = ts[-cur_window:]
                p_window = ps[-cur_window:]
                mask_off = np.where(np.array(noise_on_window) < 1)[0]
                t_interp = [((t_window[i] + t_window[i-1]) / 2) for i in mask_off]
                p_window_dicke = [((p_window[i] - p_window[i-1])) for i in mask_off]

                line.set_xdata(t_interp[1:])
                line.set_ydata(p_window_dicke[1:])
                ax.set_xlim(np.min(t_interp[1:]), np.max(t_interp[1:]))
                ax.set_ylim(0.9 * np.min(p_window_dicke[1:]), 1.1 * np.max(p_window_dicke[1:]))
                ax.autoscale_view()
                fig.canvas.flush_events()
                fig.canvas.draw()

        np.save(f'../output/dicke_timeseries_{time_str}.npy', np.array([ts, ps, noise_on]))

        if close_sdr:
            # nice and tidy
            sdr.set_gpio_bit(4, 0)
            sdr.close()

    except:
        print('Unexpected error:', sys.exc_info()[0])
        raise
    finally:
        if sdr is not None and close_sdr:
            sdr.close()

    return ts, ps, noise_on


def run_spectrum_int(num_samp, nbins, gain, rate, fc, t_int, sdr=None):
    '''
    Parameters
    ----------
    num_samp
        Number of elements to sample from the SDR IQ per call; use powers of 2
    nbins
        Number of frequency bins in the resulting power spectrum; powers of 2
        are most efficient, and smaller numbers are faster on CPU.
    gain
        Requested SDR gain (dB)
    rate
        SDR sample rate, intrinsically tied to bandwidth in SDRs (Hz)
    fc
        Base center frequency (Hz)
    t_int
        Total effective integration time (s)
    sdr : RtlSdr (optional)
        If provided, do not initialize a new instance.

    Returns
    -------
    freqs
        Frequencies of the resulting spectrum, centered at fc (Hz), numpy array
    p_avg_db_hz
        Power spectral density (dB/Hz) numpy array
    '''
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

    try:
        if sdr is None:
            sdr = get_sdr(rate, fc, gain)
            close_sdr = True
        else:
            close_sdr = False
        sdr.rs = rate # Rate of Sampling (intrinsically tied to bandwidth with SDR dongles)
        sdr.fc = fc
        sdr.gain = gain
        logging.debug('  sample rate: %0.6f MHz' % (sdr.rs / 1e6))
        logging.debug('  center frequency %0.6f MHz' % (sdr.fc / 1e6))
        logging.debug('  gain: %d dB' % sdr.gain)
        logging.debug('  num samples per call: {}'.format(num_samp))
        logging.debug('  PSD binning: {} bins'.format(nbins))
        logging.debug('  requested integration time: {}s'.format(t_int))
        N = int(sdr.rs * t_int)
        num_loops = int(N / num_samp) + 1
        logging.debug('  => num samples to collect: {}'.format(N))
        logging.debug('  => est. num of calls: {}'.format(num_loops - 1))

        # Set up arrays to store power spectrum calculated from I-Q samples
        freqs = np.zeros(nbins)
        p_xx_tot = np.zeros(nbins)
        cnt = 0

        # Set the baseline time
        start_time = time.time()
        logging.info('Integration began at {}'.format(time.strftime('%a, %d %b %Y %H:%M:%S', time.localtime(start_time))))
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
            iq = sdr.read_samples(num_samp)
            # compensate for DC spike
            iq = (iq.real - iq.real.mean()) + (1j * (iq.imag - iq.imag.mean()))
            freqs, p_xx = welch(iq, fs=rate, nperseg=nperseg, nfft=nbins, noverlap=0, scaling='spectrum', window=WINDOW, detrend=False, return_onesided=False)
            p_xx_tot += p_xx
        end_time = time.time()
        logging.info('Integration ended at {} after {} seconds.'.format(time.strftime('%a, %d %b %Y %H:%M:%S'), end_time-start_time))
        logging.debug('{} spectra were measured at {}.'.format(cnt, fc))
        logging.debug('for an effective integration time of {:.2f}s'.format(num_samp * cnt / rate))

        freqs = np.fft.fftshift(freqs)
        p_xx_tot = np.fft.fftshift(p_xx_tot)

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

        p_avg_db_hz = 10. * np.log10(p_avg_hz)

        # Shift frequency spectra back to the intended range
        freqs = freqs + fc

        if close_sdr:
            # nice and tidy
            sdr.close()

    except:
        print('Unexpected error:', sys.exc_info()[0])
        raise
    finally:
        if sdr is not None and close_sdr:
            sdr.close()

    return freqs, p_avg_db_hz


def run_fswitch_int(num_samp, nbins, gain, rate, fc, fthrow, t_int, fswitch=10, sdr=None):
    '''
    Note: Because a significant time penalty is introduced for each retuning,
          a maximum frequency switching rate of 10 Hz is adopted to help 
          reduce the fraction of observation time spent retuning the SDR
          for a given effective integration time.
          As a consequence, the minimum integration time is 2*(1/fswitch)
          to ensure the user gets at least one spectrum taken on each
          frequency of interest.
    
    Parameters
    ----------
    num_samp
        Number of elements to sample from the SDR IQ timeseries: powers of 2
        are most efficient
    nbins
        Number of frequency bins in the resulting power spectrum; powers of 2
        are most efficient, and smaller numbers are faster on CPU.
    gain
        Requested SDR gain (dB)
    rate
        SDR sample rate, intrinsically tied to bandwidth in SDRs (Hz)
    fc
        Base center frequency (Hz)
    fthrow
        Alternate frequency (Hz)
    t_int
        Total effective integration time (s)
    fswitch (optiona)
         Frequency of switching between fc and fthrow (Hz)
    sdr : RtlSdr (optional)
        If provided, do not initialize a new instance.

    Returns
    -------
    freqs_fold
        Frequencies of the spectrum resulting from folding according to the
        folding method implemented in the f_throw_fold (post_process module)
    p_fold
        Folded frequency-switched power, centered at fc,(uncalibrated V^2)
        numpy array.
    '''

    from .post_process import f_throw_fold 

    # Check inputs:
    assert t_int >= 2.0 * (1.0/fswitch), '''At t_int={} s, frequency switching at fswitch={} Hz means the switching period is longer than integration time. Please choose a longer integration time or shorter switching frequency to ensure enough integration time to dwell on each frequency.'''.format(t_int, fswitch)

    if fswitch > 10:
        logging.warning('''Warning: high frequency switching values mean more SDR retunings. A greater fraction of observation time will be spent retuning the SDR, resulting in longer wait times to reach the requested effective integration time.''')

    try:
        if sdr is None:
            sdr = get_sdr(rate, fc, gain)
            close_sdr = True
        else:
            close_sdr = False
        sdr.rs = rate # Rate of Sampling (intrinsically tied to bandwidth with SDR dongles)
        sdr.fc = fc
        sdr.gain = gain
        logging.debug('  sample rate: %0.6f MHz' % (sdr.rs/1e6))
        logging.debug('  center frequency %0.6f MHz' % (sdr.fc/1e6))
        logging.debug('  gain: %d dB' % sdr.gain)
        logging.debug('  num samples per call: {}'.format(num_samp))
        logging.debug('  requested integration time: {}s'.format(t_int))
        
        # Total number of samples to collect
        N = int(sdr.rs * t_int)
        # Number of samples on each frequency dwell
        N_dwell = int(sdr.rs * (1.0 / fswitch))
        # Number of calls to SDR on each frequency
        num_loops = N_dwell//num_samp
        # Number of dwells on each frequency
        num_dwells = N//N_dwell
        logging.debug('  => num samples to collect: {}'.format(N))
        logging.debug('  => est. num of calls: {}'.format(N//num_samp))
        logging.debug('  => num samples on each dwell: {}'.format(N_dwell))
        logging.debug('  => est. num of calls on each dwell: {}'.format(num_loops))
        logging.debug('  => num dwells total: {}'.format(num_dwells))

        # Set up arrays to store power spectrum calculated from I-Q samples
        freqs_on = np.zeros(nbins)
        freqs_off = np.zeros(nbins)
        p_xx_on = np.zeros(nbins)
        p_xx_off = np.zeros(nbins)
        cnt = 0

        # Set the baseline time
        start_time = time.time()
        logging.info('Integration began at {}'.format(time.strftime('%a, %d %b %Y %H:%M:%S', time.localtime(start_time))))

        # Swap between the two specified frequencies, integrating signal.
        # Time integration loop
        for i in range(num_dwells):
            tick = (i%2 == 0)
            if tick:
                sdr.fc = fc
            else:
                sdr.fc = fthrow
            for j in range(num_loops):
                iq = sdr.read_samples(num_samp)
                # compensate for DC spike
                iq = (iq.real - iq.real.mean()) + (1j * (iq.imag - iq.imag.mean()))

                if tick:
                    freqs_on, p_xx = welch(
                        iq,
                        fs=rate,
                        nperseg=nbins,
                        noverlap=0,
                        scaling='spectrum',
                        detrend=False,
                        return_onesided=False
                    )
                    p_xx_on += p_xx
                else:
                    freqs_off, p_xx = welch(
                        iq,
                        fs=rate,
                        nperseg=nbins,
                        noverlap=0,
                        scaling='spectrum',
                        detrend=False,
                        return_onesided=False
                    )
                    p_xx_off += p_xx
                cnt += 1
        
        end_time = time.time()
        logging.info('Integration ended at {} after {} seconds.'.format(time.strftime('%a, %d %b %Y %H:%M:%S'), end_time-start_time))
        logging.debug('{} spectra were measured, split between {} and {}.'.format(cnt, fc, fthrow))
        logging.debug('for an effective integration time of {:.2f}s'.format(num_samp * cnt / rate))

        freqs_on = np.fft.fftshift(freqs_on)
        freqs_off = np.fft.fftshift(freqs_off)

        p_xx_on = np.fft.fftshift(p_xx_on)
        p_xx_off = np.fft.fftshift(p_xx_off)

        # Compute the average power spectrum based on the number of spectra read
        p_avg_on  = p_xx_on  / cnt
        p_avg_off = p_xx_off / cnt
        # Shift frequency spectra back to the intended range
        freqs_on = freqs_on + fc
        freqs_off = freqs_off + fthrow

        # Fold switched power spectra
        freqs_fold, p_fold = f_throw_fold(freqs_on, freqs_off, p_avg_on, p_avg_off)

        if close_sdr:
            # nice and tidy
            sdr.close()

    except:
        print('Unexpected error:', sys.exc_info()[0])
        raise
    finally:
        if sdr is not None and close_sdr:
            sdr.close()

    return freqs_fold, p_fold


def save_spectrum(filename, freqs, p_xx):
    '''
    Save the results of integration to a file.
    '''
    header='\n\n\n\n\n'
    np.savetxt(filename, np.column_stack((freqs, p_xx)), delimiter=' ', header=header)
    return

