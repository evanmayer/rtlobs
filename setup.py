from setuptools import setup, find_packages

import rtlobs

brief = "The RTL-SDR radio observatory."
verbose = """
rtl-obs wraps roger-'s pyrtlsdr (in turn, a wrap of librtlsdr) and adds common signal processing functions needed when using these USB radio dongles as receivers in radio astronomy. It is structured to support a typical observation workflow and encourages interactive use in jupyter notebooks or ipython.
"""

setup(
    name='rtlobs',
    version='0.1',
    description=brief,
    long_description=verbose,
    url='https://github.com/evanmayer/rtl-obs',
    packages=find_packages(),
    author='Evan Mayer',
)
