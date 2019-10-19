'''
by Evan Mayer

Library for data collection functions on an rtl-sdr based radio telescope.
'''

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