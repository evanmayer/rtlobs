'''
by Evan Mayer

Library for post-processing functions on an rtl-sdr based radio telescope.
'''

import numpy as np
import matplotlib.pyplot as plt


def plot_spectrum(freqs, powers, savefig=None):
    '''
    Plots an iterable of frequencies on the x axis against
    an iterable of frequencies on the y axis.
                                                                               
    Inputs:
    freqs:    Array of frequencies (assumed Hz). Index-aligned to array of 
              powers
    powers:   Array of power spectral density estimates (assumed dB/Hz 
              uncalibrated)
    
    kwargs:
    savefig:  Optional filename. If provided, will save plot.

    Returns:
    fig:      matplotlib figure handle to the generated plot
    '''

    fig = plt.figure()
    ax = fig.subplots(1)
    ax.plot(freqs, powers)
    ax.grid()
    plt.locator_params(axis='x', nbins=9)
    plt.locator_params(axis='y', nbins=12)
    ax.set_xlabel('Frequency (Hz)')
    ax.set_ylabel('Power Spectral Density (dB/Hz)')
    plt.title('Power Spectral Density Estimate')

    if savefig:
        plt.savefig(savefig)

    return fig
































































































































# by Evan Mayer

import sys
# Import plotting necessities
import numpy as np
import matplotlib.pyplot as plt


def plot_file(ax, filename):
    '''
    Parse contents of filename, ignoring any lines that dont start with a float
    '''
    freqs, powers = np.loadtxt(filename, dtype=float, unpack=True, skiprows=5, comments='#',
        delimiter=' ')

    freqs_ghz = freqs / 1.e9
    ax.plot(freqs_ghz, powers, label=filename)
    plt.locator_params(axis='x', nbins=9)
    plt.locator_params(axis='y', nbins=12)
    # ax.set_ylim([-50, -30])
    ax.set_xlabel('Frequency (GHz)')
    ax.set_ylabel('Power Spectral Density (dB/Hz)')
    plt.title('Power Spectral Density Estimate')

    return

if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit("Expected at least one filename as an argument.")

    # handle inputs
    filenames = sys.argv[1:]

    for i, file in enumerate(filenames):
        plt.figure(1)
        ax = plt.gca()
        plot_file(ax, file)
        plt.legend()
    ax.grid()
    plt.show()
    plt.close()
