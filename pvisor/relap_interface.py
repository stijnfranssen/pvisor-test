"""
Contains the code for reading RELAP plot files

The keyword for the relap interface for using in the ``pvisor.read_file()`` function is: ``RELAP``.

Reads in a binary relap restart/plot file and returns it in a pandas dataframe.

The RELAP plot file is stored using a fortran(eqsue) format: every
dataline/datablock is constructed out of 2 'lines' of form A and B.

The A line looks like this:

``value:     8            10          8             8``

``varname: checkbytes1  n_entries  word_length  checkbytes2``

``bytes:     4            4           4             4``

Here checkbytes 1 and 2 are words (of 4 bytes each)that specify/check the
amount of bytes in the actual contents. Since n_entries and word_length are
both 4 bytes long, checkbytes1 and checkbytes2 both contain the value 8.  All
words in this line are 4 bytes long.  word_length denotes the word length of
the variables on the next line (usually 4 or 8). n_entries denotes the amount
of entries on the next line (in our case usually the number of plot
parameters). In this example there are 10 data entries with a length of 8 bytes
per entry.

The B line looks something like this:

``value:     80            X    ...    Y       80``

``varname: checkbytes1   var1   ...  var10   checkbytes2``

``bytes:     4             8    ...    8       4``

Here checkbytes1 and checkbytes2 should be n_entries*word_length.
All vars (1 through n_entries=10) are word_length=8 bytes long and contain
the actual data (here reprsented as X and Y, these could be characters
(i.e. a string) or floats/ints/etc.).

After the B line a new set of A&B lines will be present (or End of File).

There are types of B lines. The relevant B lines start with these keywords:
    1. Plotalf: the names of the variables
    2. Plotnum: the numbers of the variables
    3. Plotrec: the actual data
"""

################################################################################
### Modules                                                                  ###
################################################################################

## External modules ############################################################
import pandas as pd  # Using the pd.DataFrame to handle the data
from pathlib import Path  # For handeling paths/directories and files

# Use numpy to cast the 1D list to a 2D array, to pass to pandas
# https://stackoverflow.com/questions/42593104/convert-1d-list-into-a-2d-pandas-dataframe
# Maybe check if making a list of lists and then converting directly to a df is
# faster than just appending everything to 1 big flat list and using numpy in
# between?
import numpy as np

# For type hints
from typing import Union  # For handeling typehints
from typing import BinaryIO  # For typehinting the binary file
from typing import Tuple  # For returning a tuple

# For handeling the binary data
from struct import unpack  # for shorthand
import struct  # so it is clear that where struc.error comes from

################################################################################
### Functions                                                                ###
################################################################################


def _read_relap(path: Union[str, Path]) -> pd.DataFrame:
    """
    Reads in a RELAP plot file.

    Reads in a binary relap restart/plot file and returns it in a pandas
    dataframe.

    Parameters
    ----------
    path: str or Path
        The path to the relap restart file to read.

    Returns
    -------
    df: pd.DataFrame
        The data
    """

    # Cast the path into a proper Path for clearer file handeling
    if type(path) == str:
        path = Path(path)

    with open(path, "rb") as restart_file:
        # Checks the first byte and tries to infer the RELAP version.
        _check_first_byte(restart_file)

        # Read the header
        n_entries, word_length, header_B_line = _get_next_line(restart_file)

        header_text, header_number = _read_header(n_entries, word_length, header_B_line)

        # Read the bulk of the file
        while True:
            try:
                n_entries, word_length, B_line = _get_next_line(restart_file)
            except EOFError as e:
                break

            # Get the keyword of the current line to see what kind of data it
            # contains
            keyword = B_line[:8]

            # The following is out of order for performance reasons. Order as
            # encounterd in the plot file is: plotalf, plotnum, plotrecs

            # Plotrec contains the actual numerical data
            if keyword == b"plotrec ":
                time[t_step] = unpack("<1f", B_line[8:12])[0]
                data[t_step, :] = unpack(unpack_fmt, B_line[12:])[:n_vars]
                t_step += 1
                if t_step % data_expand_size == 0:
                    time = _expand_np_array(time, data_expand_size, n_vars=1)
                    data = _expand_np_array(data, data_expand_size, n_vars)
                continue

            # Plotalf contains the name of the variables
            elif keyword == b"plotalf ":
                var_names = [""] * (n_entries)
                for ij in range(2, n_entries):
                    var_names[ij - 2] = B_line[ij * 8 : (ij + 1) * 8].decode().strip()
                while var_names[-1] == "":
                    var_names.pop()

                n_vars = len(var_names)
                n_bytes = n_vars
                if (n_vars) % 2 == 0:
                    n_bytes += 1

                unpack_fmt = "<" + n_bytes * "f"

                # Prepare data list
                data_expand_size = 10000
                time = np.zeros(data_expand_size, dtype="float32")
                data = np.zeros([data_expand_size, n_vars], dtype="float32")
                t_step = 0
                continue

            # Plotnum contains the number of the variables
            elif keyword == b"plotnum ":
                for ij in range(1, n_entries):
                    # note that only the last 4 bytes contain information
                    word = unpack("i", B_line[ij * 8 : (ij + 1) * 8][4:])[0]
                    #  Skip if the word is 0
                    if word == 0:
                        continue
                    var_names[ij - 2] += "-" + str(word)

                # var_names = var_names[1:]  # Remove the time variable from the list
                continue

    df = pd.DataFrame(data[:t_step, :], columns=var_names, index=time[:t_step])
    df.index.name = "time"

    return df


def _expand_np_array(data, data_expand_size, n_vars):
    """Expands an existing array

    Input:
      - data, np.array: the existing array.
      - data_expand_size, int: the number of time steps that need to be added
      - n_vars, int: the number of variables in the dataframe
    Output:
      - data, np.array: the modified array.
    """
    return np.append(
        data, np.zeros([data_expand_size, n_vars], dtype="float32"), axis=0
    )


def _split_into_words(B_line, n_entries, word_length):
    """For debugging: Split a line into words

    Input:
      - B_line, bytes: the line to be split
      - n_entries, int: the number of entries
      - word_length, int: The number of bytes per word
    output:
      - words, list of length n_entries with bytes: The list of words
    """

    words = [""] * n_entries
    for ii in range(n_entries):
        words[ii] = B_line[ii * 8 : (ii + 1) * 8]

    return words


def _check_first_byte(restart_file: BinaryIO):
    """Checks the first byte and tries to infer the RELAP version.

    The binary restart format is different for different types of relap
    versions. The first byte of the restart file can be used to infer the relap
    version and how to interpret the file.
    Know version and start bytes are:
       8: RELAP5.mod3.2 New version
       253: RELAP5.mod3.2 Old version
       0: RELAP5.mod2.5 (Tractabel UNIX version)
    Only RELAP5.mod3.2 New version is implemented.

    This function checks the first byte.

    After reading the first byte the file pointer is reset to the start of the
    file.

    Input:
        - restart_file, BinaryIO, the restart file
    Output:
      - None
    """
    # Find the first byte
    byte = restart_file.read(1)

    # The pointer needs to be reset for further reading
    restart_file.seek(0)

    # Check the first byte
    if byte == b"\x08":
        relap_version = "RELAP5.mod3.3 new version"
    else:
        raise IOError("Start byte indicates that RELAP version is not " "supported.")
    return


def _get_next_line(restart_file: BinaryIO) -> Tuple[int, int, bytes]:
    """Gets the next B_line data line out, without checkbytes

    First reads the A line and gets out n_entries and word_length, uses those
    values to get the data from the B line.

    Input:
      - restart_file, BinaryIO: The restart file
    Output:
      - n_entries, int: The number of entries in the next B line
      - word_length, int: The number of bytes per entry for the next B line
        (usually 8)
      - line_B_no_checkbytes, bytes: The B_line, without the checkbytes
    """
    # Read the A line to get the number of entries and the length of the words
    n_entries, word_length = _read_A(restart_file)

    # Read line_B from the file
    line_B = restart_file.read(n_entries * word_length + 8)

    # Check the checkbytes
    (checkbytes1,) = unpack("i", line_B[0:4])
    (checkbytes2,) = unpack("i", line_B[-4:])
    _ = _check_checkbytes_Bline(checkbytes1, checkbytes2, n_entries, word_length)

    # Get the relevant data and return it
    line_b_no_checkbytes = line_B[4:-4]
    return n_entries, word_length, line_b_no_checkbytes


def _read_A(restart_file: BinaryIO) -> Tuple[int, int]:
    """Reads an A type of line

    The A line looks like this:

    value:     8            xxx         yyy             8
    varname: checkbytes1  n_entries  word_length  checkbytes2
    bytes:     4            4           4             4

    Return the number of entries (n_entries, int, xxx) and the word_length
    (int, yyy) for the next B line.

    Input:
      - restart_file, BinaryIO: the restart file object
    Output:
      - n_entries, int: The number of entries in the next B line
      - word_length, int: The number of bytes per entry for the next B line
        (usually 8)
    """
    line_A = restart_file.read(16)
    if line_A == b"":
        raise EOFError
    (checkbytes1,) = unpack("i", line_A[0:4])
    (n_entries,) = unpack("i", line_A[4:8])
    (word_length,) = unpack("i", line_A[8:12])
    (checkbytes2,) = unpack("i", line_A[12:16])

    if not all(cb == 8 for cb in [checkbytes1, checkbytes2]):
        raise IOError(
            "Invalid restart file. \n" "{checkbytes1=} or {checkbytes2=} != 8."
        )

    return n_entries, word_length


def _read_header(
    n_entries: int, word_length: int, header_B_line: bytes
) -> Tuple[str, int]:
    """Reads the header, returns the header text and a number

    The header contains a text with:
    <<TO DO>> Fill in what hapens in the header
    And ends with what is assumed a number
    <<TO DO>> Figure out what that number means!

    Input:
      - n_entries, int: The number of entries in the header block (usually 10)
      - word_length, int: The number of bytes per word, usually 8
      - header_B_line, bytes: The data in the first B line of the file
    Output:
      - header_text, str: The header text
      - header_number, int: A number (to do, check what this number is and
        does)
    """

    header_text = header_B_line[:-word_length].decode()

    header_number_bytes = header_B_line[-word_length:]
    (header_number,) = unpack("<q", header_number_bytes)

    return header_text, header_number


def _check_checkbytes_Bline(
    checkbytes1: int, checkbytes2: int, n_entries: int, word_length: int
) -> None:
    """Fortran lines have checkbytes at the start and end of the line. For
    B-lines they should be equal to n_entries*word_length.

    n_entries and word_legth are gotten form the A line preceding the current B
    line.

    Input:
     - checkbytes1, int: The first checkbyte
     - checkbytes2, int: The seccond checkbyte
     - n_entries, int: the number of entries in the B line
     - word_length, int: the number of entries in the B line
    Output:
     - None
    """
    checkbytes_target = n_entries * word_length
    if not all(cb == checkbytes_target for cb in [checkbytes1, checkbytes2]):
        raise IOError(
            "Invalid restart file, when reading header \n"
            "{checkbytes1=} or {checkbytes2=} != {checkbytes_target}"
        )
    return


if __name__ == "__main__":
    main()
