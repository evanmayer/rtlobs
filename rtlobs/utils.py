'''
by Evan Mayer

Library for common functions used by an rtl-sdr based radio telescope.
'''

import os
import subprocess


def biast(state, index=0):
    '''
    Turn the bias tee on the device on or off.
    You should configure the path here to call the rtl_biast
    executable on your machine.

    Inputs:
    state (int): nonzero = on, zero = off
    index (int)(optional): RTL-SDR device index, in the event of more than one SDR
    Returns:
    None
    '''
    if state != 0:
        state = 1
        print('Enabling bias tee.')
    else:
        print('Disabling bias tee.')

    # Ensure the bias tee is turned off, then turn it on.                       
    basepath = os.path.expanduser('~/github/')
    cmd = [os.path.join(basepath, 'rtl-sdr-blog', 'build', 'src', 'rtl_biast'),  '-d {}'.format(index), '-b {}'.format(state)]
    ret = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)#, text=True)

    if ret.returncode == 0:
        print(ret.stdout)
    else:
        if ret.stdout:
            print(ret.stdout)
        if ret.stderr:
            print(ret.stderr)

    return


def noise_src(noise_ctrl, state):
    '''
    Turn a noise source on the device on or off.
    You should configure the method of switching for your own device here.

    Inputs:
    noise_ctrl (gpiozero DigitalOutputDevice): gpiozero object assigned to the
        pin controlling the noise source
    state (int): nonzero = on, zero = off
    Returns:
    None
    '''
    #import gpiozero
    
    #CTRL_PIN = 'GPIO17'
    #noise_ctrl = gpiozero.DigitalOutputDevice(CTRL_PIN) 

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

