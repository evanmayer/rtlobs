# rtlobs:
The RTL-SDR Radio Observatory.

Turn your RTL-SDR dongle into a radio astronomy workhorse. Perform functions such as total power integration, taking spectra to observe the 21cm hydrogen line, and performing spectral observations in frequency-switched mode to flatten bandpass shape and increase signal-to-noise.

### A quick example:
```python
from rtlobs import collect as col
from rtlobs import post_process as post
# 8192 samples per call to the SDR
# 2048 bin resolution power spectrum 
# 49.6 dB of RtlSdr gain
# 2.32 MHz sample rate/bandwidth
# 1.420 GHz center frequency
# 10 sec integration time
f, p = col.run_spectrum_int(8192, 2048, 49.6, 2.32e6, 1.420e9, 10)
# Show the figure containing the plotted spectrum
fig, ax = post.plot_spectrum(f, p, savefig='../images/spectrum_int.png')
fig.show()
```
![Time-averaged power spectral density estimate](https://github.com/evanmayer/rtl-obs/blob/master/images/spectrum_int.png)

Since this spectrum is taken indoors with a V-dipole antenna next to a desktop computer, we can see quite a bit of RFI near 1.42 GHz!

## Installation:
Until rtlobs is on PyPI, I'd recommend installing from git:

`git clone https://github.com/evanmayer/rtlobs.git`

and handling access to the modules yourself, either through setting up your `sys.path` or by simply developing your scripts inside the checkout. Making an observing routine using jupyter notebooks works great!
A `setup.py` file is included for `python setup.py install`, in case you're using virtual environments or don't mind a messy uninstall if you decide you don't want rtlobs down the road. This will work better once `pip` install is supported.

## Known dependencies:
Python 3 libraries:
  - matplotlib
  - numpy
  - roger-'s pyrtlsdr library
  - time
  
Compiled libraries:
  - librtlsdr
  
## Optional dependencies:
These are required for additional controls based on features your hardware may or may not have.

Python 3 libraries:
- gpiozero (optional, enables addressing noise source switches with GPIO pins)
- subprocess (optional, functions in utils package for turning on/off biast use subprocess features requiring Python >=3.7)

Binaries:
- rtl_biast (optional, enables control for powering an external low noise amplifier through the RTL-SDR coax)

## Features:
The code is structured to support the observing workflow:
- Calibration:
  - A function implementing Y-factor calibration using two integrated total power values from measuring hot and cold loads and their respective known temperatures using the total-power radiometer implemented below.
- Collection:
  - Functions for using the RTL-SDR as total-power radiometer, integrating I-Q samples for use in an estimate of the total power incident over an amount of time
  - Functions for recording time-averaged spectra
  - Functions for recording frequency-switched spectra on-the-fly
- Post-processing:
  - Basic spectrum plotting
  - Applying calibration to recorded spectra\*\*
  - Applying the frequency-switching folding technique to spectra taken at two different frequencies
  - Baseline subtraction of one spectrum from another
  - Doppler relative velocity shift calculation for spectra given galactic coordinates\*\*
- Utilities:
  - Subroutines shared between functions
  - Implementations of optional hardware interface features as described below

\*\* Working on it

## Assumptions:
It is assumed that you have an RtlSdr device set up with the proper drivers on your machine. Although this code can run on Windows or Linux, it was developed and tested on a Raspberry Pi 4. I try my best to make the core observation functions cross-platform, and avoid assumptions about processor speed and memory. Hardware-interfacing functions may require additional customization for your hardware and platform.

Several aspects of this code assume the presence of outside hardware:
- RtlSdr USB dongle (I use the rtl-sdr.com v3 dongle)
- Some reasonable means of amplification/gain: a dish, yagi, or horn antenna, properly filtered for the band of interest, and with a low noise amplifier as one of the first stages after the antenna.
- Code is provided to optionally use Python to switch on/off an on-board bias tee (a device for delivering power through DC over the SDR coax input) provided on the rtl-sdr.com v3 dongle. It comes hard-coded with the location my rtl-biast driver is installed to. It's easy to configure with the location of your driver executable.
- Code is provided to optionally use a Raspberry Pi's addressable GPIO pins to control output voltages to a noise source that is switchable across the device input at 5V logic levels. Such a noise source is provided in the form of a 50Ohm resistor onboard the nooelec SAWbird H1 barebones LNA, but could be just as easily sourced elsewhere.

## Known issues:
- This is a work in progress. Not all features are implemented yet.
- This code has not been peer reviewed, although it has been viewed many times. This either means everything is correct, or no one has looked closely enough.
- This library has not been verified against a noise source with a known power, and has not been tested for agreement with standalone utilities such as rtl-power when calculating total power or power spectral density estimates.
- Because making spectra with Python is slightly slower than the equivalent compiled C/C++ code (see rtl-power or rtl-power-fftw) when you ask for a 100 sec integration, it will take slightly longer than 100 seconds, but your effective integration time will be what you asked for.
- I write a lot of comments, which you might not want to read.

Contact me here with your issues and questions and we'll work together to make them right. 
