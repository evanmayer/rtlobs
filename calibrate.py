'''
by Evan Mayer

Library for calibration functions on an rtl-sdr based radio telescope.
'''

import numpy as np
from rtlsdr import RtlSdr
import time
import utils as ut


def run_total_power_int( num_samp, gain, rate, fc, t_int ):
    '''
    Implement a total-power radiometer.

    Inputs:
    num_samp: Number of elements to sample from the SDR IQ timeseries.
              Greater numbers are more efficient, until limited by device RAM.
    gain:     Requested SDR gain (dB)
    rate:     SDR sample rate, intrinsically tied to bandwidth in SDRs (Hz)
    fc:       Base center frequency (Hz)
    t_int:    Total integration time (s)

    Returns:
    p_tot:   Time-averaged power in the signal from the sdr, in 
             uncalibrated units
    '''

    # Start the RtlSdr instance
    print('Initializing rtl-sdr with pyrtlsdr:')
    sdr = RtlSdr()
    sdr.rs = rate
    sdr.fc = fc
    sdr.gain = gain
    print('  sample rate: {} MHz'.format(sdr.rs/1e6))
    print('  center frequency {} MHz'.format(sdr.fc/1e6))
    print('  gain: {} dB'.format(sdr.gain))
    print('  num samples per call: {}'.format(num_samp))
    print('  requested integration time: {}s'.format(t_int))

    p_tot = 0.0
    cnt = 0

    # Set the baseline time
    start_time = time.time()
    print('Integration began at {}'.format(time.strftime('%a, %d %b %Y %H:%M:%S', time.localtime(start_time))))
    # Time integration loop
    iq = np.zeros(num_samp, dtype=complex)
    while time.time()-start_time < t_int:
        iq = sdr.read_samples(num_samp)
        cnt += 1
        # The below is a total power measurement equivalent to
        # P = V^2 / R = (sqrt(I^2 + Q^2))^2 = (I^2 + Q^2) / 1,
        # ignoring R since it cancels out when using these in a 
        # calibration.
        p_tot += np.sum(np.real(iq*np.conj(iq)))
    
    end_time = time.time()
    print('Integration ended at {} after {} seconds.'.format(time.strftime('%a, %d %b %Y %H:%M:%S'), end_time-start_time))
    print('{} samples were measured at {}.'.format(cnt*num_samp, fc))

    # Compute the average power value based on the number of measurements
    p_avg = p_tot / num_samp / cnt

    # nice and tidy
    sdr.close()
    
    return p_avg


def y_factor_cal(p_hot, p_cold, t_hot, t_cold):
    '''
    Perform Y-factor calibration
                                                                               
    Inputs:
    p_hot:  Total power measurement taken from hot load
    p_cold: Total power measurement taken from cold load
    t_hot:  Temperature of the hot load in Kelvin
    t_cold: Temperature of the cold load in Kelvin
                                                                               
    Returns:
    t_sys:  System temperature estimate, K
    '''

    # Ref: K. O'Neil, Single-Dish Calibration Techniques at Radio Wavelengths
    # http://articles.adsabs.harvard.edu//full/2002ASPC..278..293O/0000293.000.html

    Y = p_cold / p_hot
    t_sys = (t_cold - Y*t_hot) / (Y - 1)
    print('T_sys estimate for cold load temp {:.2f}K and hot load temp {:.2f}K is {:.2f}K'.format(t_cold, t_hot, t_sys))

    return t_sys
