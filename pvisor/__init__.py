"""

From the .pvisor_module file the read_file() function is imported which is a wrapper
for all the different loading functions.
The rust function for reading spectra files needs to be loaded in sepperately.

"""

from .pvisor_module import read_file
from .pvisor import rust_read_spectra
