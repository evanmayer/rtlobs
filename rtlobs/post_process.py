'''
by Evan Mayer

Library for post-processing functions on an rtl-sdr based radio telescope.
'''

import numpy as np
import matplotlib.pyplot as plt


def plot_spectrum(freqs, powers, savefig=None):
    '''
    Plots an iterable of frequencies on the x axis against
    an iterable of powers on the y axis.
                                                                               
    Parameters
    ----------
    freqs
        Array of frequencies (assumed Hz). Index-aligned to array of powers
    powers
        Array of power spectral density estimates (assumed dB/Hz uncalibrated)
    savefig (optional)
        Filename, if provided, will save a plot there

    Returns
    -------
    fig
        matplotlib figure handle to the generated plot
    ax
        in case you want to add more traces later
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

    return fig, ax


def f_throw_fold(freqs_on, freqs_off, p_on, p_off):
    '''
    Perform a "folding" technique on two spectra with the target signal present
    in order to nearly completely subtract off baseline variation and increase
    singal-to-noise.
    As a matter of convention, I have assumed that the spectrum centered on the
    frequency of interest is freqs_on, p_on. This doesn't matter, up to a
    minus sign in the folded spectrum y-vals.
    It is assumed that all input iterables have matching length.

    The center frequency of freqs_on MUST be contained by freqs_off.

    This is meant to implement the method described here:
    http://herschel.esac.esa.int/hcss-doc-15.0/load/hifi_um/html/hcb_pfsw.html 
    Which was in turn taken from:
    https://aas.aanda.org/articles/aas/abs/1997/10/ds1263/ds1263.html

    Parameters
    ----------
    freqs_on
        Array of frequencies in power spectrum, taken at the target frequency
    freqs_off
        Array of frequencies in power spectrum, taken shifted off of the target
        frequency. For "in-band" switching mode, this should still contain the
        spectral line of interest.
    p_on
        Array, a power spectrum estimate (assumed uncalibrated V^2), taken at
        the target frequency
    p_off
        Array, a power spectrum estimate (assumed uncalibrated V^2), taken
        shifted off of the target frequency.

    Returns
    -------
    freqs_fold
        Array of frequencies at which the two switched spectra overlap
    p_fold
        Folded power spectrum in uncalibrated power units
    '''

    # Shift-and-add to fold
    # Find the center frequency in freqs_on
    fc = freqs_on[len(freqs_on)//2]
    # Magnitude of the frequency switch in frequency space
    fthrow = abs(freqs_on[0] - freqs_off[0])
    # Magnitude of frequency shift in bin space:
    epsilon = (freqs_on[1] - freqs_on[0]) / 2.
    fc_idx = np.where(np.abs(freqs_on - fc) < epsilon)[0][0]
    fthrow_idx = np.where(np.abs(freqs_on - (fc-fthrow)) < epsilon)[0][0]
    bin_throw = np.abs(fthrow_idx - fc_idx)

    # Folding procedure is a shift-and-add-negate, then average
    # Work in absolute values instead of ratios so subtraction and 
    # division work out right
    p_diff = p_on - p_off
    # Average the spectrum of interest with the spectrum off by fthrow
    p_fold = (p_diff[bin_throw:] - p_diff[0:len(p_diff)-bin_throw]) / 2.
    # Get the folded, upper segment of freqs to return it, throwing away the 
    # part the two spectra did not have in common.
    freqs_fold = freqs_on[bin_throw:]

    return freqs_fold, p_fold

