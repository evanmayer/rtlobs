'''
by Evan Mayer

Library for calibration functions on an rtl-sdr based radio telescope.
'''


def y_factor_cal(p_hot, p_cold, t_hot, t_cold):
    '''
    Perform Y-factor calibration

    Parameters
    ----------
    p_hot
        Raw total power measurement taken from hot load
    p_cold
        Raw total power measurement taken from cold load
    t_hot
        Temperature of the hot load in Kelvin
    t_cold
        Temperature of the cold load in Kelvin

    Returns
    -------
    t_sys
        System temperature estimate, K
    '''

    # Ref: K. O'Neil, Single-Dish Calibration Techniques at Radio Wavelengths
    # http://articles.adsabs.harvard.edu//full/2002ASPC..278..293O/0000293.000.html

    Y = p_cold / p_hot
    t_sys = (t_cold - Y*t_hot) / (Y - 1)
    print('T_sys estimate for cold load temp {:.2f}K and hot load temp {:.2f}K is {:.2f}K'.format(t_cold, t_hot, t_sys))

    return t_sys

