"""Test for the spectra interface

@author: Stijn Franssen-van Rijsingen, stijn.franssen@nrgpallas.com
@date: 05-03-2026
"""

# Internal packages
from pvisor import read_file

# External packages
from pathlib import Path

# Data handeling
import pandas as pd
import numpy as np


# Get directory so the relap files can be found
current_dir = Path(__file__).parent


def test_read_SPECTRA_9_digit():

    filename = Path("9_digit.PLT")

    df = read_file(current_dir / filename, code="SPECTRA")

    # df.to_csv(current_dir / filename.with_suffix(".csv"))

    df_expected = pd.read_csv(
        current_dir / filename.with_suffix(".csv"),
        dtype=np.float64,
        index_col="time",
    )

    pd.testing.assert_frame_equal(df, df_expected)


if __name__ == "__main__":
    test_read_SPECTRA_9_digit()
