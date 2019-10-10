# rtl-obs:
The RTL-SDR Radio Observatory.

## Assumptions:

It is assumed that you have RtlSdr device set up with the proper drivers on your machine. Although this code can run on Windows or Linux, it was developed and tested on a Raspberry Pi 4.

Several aspects of this code assume the presence of outside hardware:
- RtlSdr USB dongle (I use the rtl-sdr.com v3 dongle)
- Some reasonable means of amplification: a dish, yagi, or horn antenna, properly filtered for the band of interest, and with a low noise amplifier as one of the first stages after the antenna.
- Code is provided to optionally use Python to switch on/off and on-board bias tee (a device for delivering power through DC over the SDR coax input) provided on the rtl-sdr.com v3 dongle. It comes hard-coded with the location my rtl-biast driver is installed to. It's easy to configure.
- Code is provided to optionally use a Raspberry Pi's addressable GPIO pins to control output voltages to a noise source that is switchable across the device input at 5V logic levels. Such a noise source is provided in the form of a 50Ohm resistor onboard the nooelec SAWbird H1 barebones LNA, but could be just as easily sourced elsewhere.

## Installation:
For now, you'll have to check out the repo by the usual means, and write your own scripts to use the utilities, or use them interactively in IPython or jupyter or something similar. Soon, an installation utility will be provided.

## Usage:
The code is structured to support the observing workflow:
- Calibration:
  - A function implementing Y-factor calibration using two integrated total power values from measuring hot and cold loads and their respective known temperatures using the total-power radiometer implemented below.
- Collection:
  - Functions for using the RTL-SDR as total-power radiometer, integrating I-Q samples for use in an estimate of the total power incident over an amount of time
  - Functions for recording time-averaged spectra*
  - Functions for recording frequency-switched spectra*
- Post-processing:
  - Applying calibration to recorded spectra*
  - Applying the frequency-switching folding technique to spectra taken at two different frequencies*
  - Baseline subtraction of one spectra from another*
- Utilities:
  - Subroutines shared between functions
  - Implementations of optional hardware-interface (HWIF) features as described above

\* Expected to be implemented before 2020

## Known dependencies:
- Linux-based OS
  - I try my best to make the core observation functions cross-platform, and avoid assumptions about processor speed and memory. HWIF functions may require additional customization for your hardware and platform.
- Python 3
  - gpiozero (optional, enables addressing noise source switches with GPIO pins)
  - numpy
  - os
  - roger-'s pyrtlsdr library
  - subprocess
  - time
- librtlsdr
- rtl_biast (optional, enables powering an external low noise amplifier through the RTL-SDR coax)

## Known issues:
- This is a work in progress. Not all features are implemented yet. 
- It requires much more fiddling to set up and take observations now than it eventually will. 
- Recorded and calibration values may not invalid due to mistakes in math, mistakes of omission, and assumptions involved in the implementation.
- Robustness and exception handling, as well as SIGINT, etc., handling are not implemented beyond that handled by default in Python. 
- RTL-SDR devices may not surrender permissions and throw a usb_claim_interface_error -6 if a SIGINT is passed at the wrong time. The USB device should be remounted or the interactive session restarted to regain command of the dongle.
- I write a lot of comments, which you might not want to read.

Contact me here with your issues andquestions and we'll work together to make them right. 
