""" Contains the code for reading SPECTRA plot files

Reads in a SPECTRA plot file and returns it in a pandas datafame.

The keyword for the relap interface for using in the ``pvisor.read_file()`` function is: 

#. ``SPECTRA`` or ``SPECTRA_RUST`` for the rustic implementation.
#. ``SPECTRA_LEGACY`` for the pythonic implementation or 

.. warning::
    ``SPECTRA_LEGACY`` is deprecated and might be removed in a future version.

The SPECTRA plot files are in human readable text format.
The first line of SPECTRA plot file contains the total number of variables.
And is, for example, like: ``NPLT  =   6160``
Then every plot parameter name is stated.

This is followed by the data. 
First the time data is printed, then every parameter data.
These are either in 6 or 9 digit precision.
Values are ordered in a fixed column width format, in a scientific format, 
separated by spaces. If however a value is negative, the space if replaced by
a minus symbol.
Every block is at most 10 columns wide, with the last row being shorter if 
necessary. 
Blocks are separated by a blank line.
"""

################################################################################
### Modules                                                                  ###
################################################################################
# For paths
from pathlib import Path

# For reading the spectra file
import itertools

# For handeling the data
import pandas as pd
import numpy as np

# For type hints
from typing import Tuple  # For returning a tuple

################################################################################
### Functions                                                                ###
################################################################################


def read_spectra(filename: Path) -> pd.DataFrame:
    params, n_params, data_width = _get_params_and_width(filename)
    data = _read_data(filename, n_params, data_width)
    data_dict = {param: data_col for param, data_col in zip(params, data)}

    df = pd.DataFrame(data_dict, dtype=float)
    return df


def _get_params_and_width(filename: Path) -> Tuple[list, int, int]:
    """
    Reads the start of the file to get the parameter list

    get the param name
    Split the line using spaces
    Then split the param with dashes
    Take all parts, except the unit (the last part of the splits)
    And rejoin those parts using a dash
    Finally append to the list of params

    Parameters
    ----------
    file_path: str or Path
        The path to the file to read.

    Returns
    -------
    params: list
        The list of parameter names
    n_params: int
        The number of parameters
    data_width: int
        The width of the data fields
    """
    # Init the parameter list
    params = []

    # Read the file
    with open(filename, "r") as f_in:

        n_params = int(f_in.readline().split()[-1])

        # Check if the end of params has been reached
        for ii, line in enumerate(f_in):
            # Read the data
            if ii < n_params:
                params.append("-".join(line.split()[-1].split("-")[:-1]))
            # Determine the precision of the data
            else:
                line = f_in.readline()  # Skip the empty line
                # Determine the precision of the data (data_lines[1] is always first data line entry)
                pos_dec = line.find(".")
                pos_exp = line.find("E")

                # function find(#) returns '-1' when input is not found
                if pos_dec != -1 and pos_exp != -1:
                    # +6 due to: scientific notation E+00 (4) and in front of decimal point f.e. 0. (2)
                    data_width = pos_exp - pos_dec + 6
                else:
                    raise IOError(
                        f"Could not determine the precision "
                        f"of the first entry on line:\n{line}"
                    )
                break
    return params, n_params, data_width


def _read_data(filename: Path, n_params: int, data_width: int) -> list:
    """
    Reads the actual data.

    Parameters
    ----------
    filename: Path
        The .plt file to read
    n_params: int
        the number of parameters
    data_width: (int)
        The width of the data field

    Returns:
    ----------
    vars_data: lst
        A list of lists(/time steps) containing the data
    """

    with open(filename, "r") as f_in:
        # Skip parameter name block
        data_lines = f_in.readlines()[n_params + 1 :]

    # Initialize the list of lists
    vars_data = [[] for _ in range(n_params)]

    # Process each "data block", which consists of all data per time step.
    # Data blocks are identified by a helper function from itertools
    for is_data, data_block in itertools.groupby(
        data_lines, key=lambda x: bool(x.strip())
    ):
        if is_data:
            time_step_data = []  # stores all data for a single time step
            for line in data_block:
                entries = [
                    line[i : i + data_width].strip()
                    for i in range(0, len(line) - 1, data_width)
                ]
                time_step_data.extend(entries)

            for i, val in enumerate(time_step_data):
                vars_data[i].append(float(val.strip()))
    return vars_data
