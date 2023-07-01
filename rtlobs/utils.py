'''
by Evan Mayer

Library for common functions used by an rtl-sdr based radio telescope.
'''

import subprocess


def biast(state: int, index=0, gpio=0):
    '''
    Turn the bias tee on the device on or off.
    You should configure the path here to call the rtl_biast
    executable on your machine.

    Parameters
    ----------
    state : int
        nonzero = on, zero = off
    index : int (optional)
        RTL-SDR device index, in the event of more than one SDR
    gpio : int (optional)
        The rtl_biast utility allows access to RTL2832U GPIO outputs. The
        RTL-SDRblog v3 dongle has these broken out on the board:
        5: RTL-SDRblog breakout header 30
        4: RTL-SDRblog breakout header 31
        2: RTL-SDRblog breakout header 32
        0: RTL2832U pin 37 (used for RTL-SDRblog v3 bias-tee)
    '''

    if state != 0:
        state = 1
        print(f'Enabling GPIO {gpio}')
    else:
        print(f'Disabling GPIO {gpio}.')

    cmd = 'rtl_biast -d {} -b {} -g {}'.format(index, state, gpio).split()
    ret = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    if ret.returncode == 0:
        print(ret.stdout.decode())
    else:
        if ret.stdout:
            print(ret.stdout.decode())
        if ret.stderr:
            print(ret.stderr.decode())
    return


def noise_src(noise_ctrl, state):
    '''
    Turn a noise source on the device on or off.
    You should configure the method of switching for your own device here.

    Inputs
    ------
    noise_ctrl : gpiozero DigitalOutputDevice
        gpiozero object assigned to the pin controlling the noise source
    state : int
        nonzero = on, zero = off
    '''

    if state != 0:
        state = 1
        print('Enabling noise source.')
        noise_ctrl.on()
        assert 1 == noise_ctrl.value, '{} did not return HIGH, noise source not switched on.'.format(noise_ctrl.pin)
    else:
        print('Disabling noise source.')
        noise_ctrl.off()
        assert 0 == noise_ctrl.value, '{} did not return LOW, noise source not switched off.'.format(noise_ctrl.pin)
    return
