"""Contains the main code for PVISOR"""

################################################################################
### Modules                                                                  ###
################################################################################

###############################
### Internal modules
from .relap_interface import _read_relap
from .spectra_interface import read_spectra, _get_params_and_width
from .pvisor import rust_read_spectra
from .melcor_interface import _read_melcor
from .trace_interface import _read_trace

###############################
### External modules

# For type hints
from typing import Union  # For handeling typehints
from pathlib import Path
import pandas as pd

################################################################################
### Modules                                                                  ###
################################################################################


def read_file(file_path: Union[str, Path], code: str) -> pd.DataFrame:
    """
    Wrapper for reading the plot data.

    Passes the path to the function that reads the plot file. For now supports
    RELAP, SPECTRA, TRACE and MELCOR.

    Parameters
    ----------
    file_path: str or Path
        The path to the file to read.
    code: str
        The output file type.
        Options:

          * ``RELAP``

          * ``SPECTRA``, ``SPECTRA_RUST`` or ``SPECTRA_LEGACY``

          * ``MELCOR``

          * ``TRACE``

        .. warning::
            ``SPECTRA_LEGACY`` is deprecated and might be removed in a future version.

    Returns
    ----------
    df: pd.DataFrame
        The data of the plot file.
    """

    # Clean up user input
    code = code.strip().upper()

    if type(file_path) != type(Path()):
        file_path = Path(file_path)

    if code == "RELAP":
        df = _read_relap(file_path)
    elif code == "SPECTRA_LEGACY":
        print(
            f"Warning, using '{code}' is depcreated and might be removed in a future version.\n"
            f"Please consider using 'SPECTRA' instead."
        )
        df = read_spectra(file_path)
    elif (code == "SPECTRA_RUST") or (code == "SPECTRA"):
        param_names, _, data_width = _get_params_and_width(file_path)
        time, data = rust_read_spectra(file_path=str(file_path), n_digits=data_width)
        data_dict = {
            variable: column for variable, column in zip(param_names[1:], data)
        }
        df = pd.DataFrame(data_dict, index=time)
        df.index.name = "time"
    elif code == "MELCOR":
        df = _read_melcor(file_path)
    elif code == "TRACE":
        df = _read_trace(file_path)
    else:
        raise ValueError(f"No parser for {code=} is implemented in pvisor.")

    return df
