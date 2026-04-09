"""
Contains the code for reading MELCOR plot files.

The keyword for the relap interface for using in the ``pvisor.read_file()``
function is: ``MELCOR``.

Reads in a binary MELCOR restart/plot file and returns the data in a pandas DataFrame.

The MELCOR plot file is stored using a fortran(esuqe) format:
Before and after the actual data is a check word with the line length.

The relevant parts of the MELCOR plot file start with the following keywords:

    1. 'TITL': The start of the file
    2. 'KEY ': Channels names
    3. '.TR/': Lines containing the data
"""

################################################################################
### Modules                                                                  ###
################################################################################

## External modules ############################################################
import pandas as pd  # Using the pd.DataFrame to handle the data

from pathlib import Path  # For handeling paths/directories and files

import numpy as np  # To hold the data while reading before handing to pandas

from typing import Union, BinaryIO, Tuple, List  # For typehints

from struct import unpack  # For handeling the binary data


def _read_melcor(path: Union[str, Path]) -> pd.DataFrame:
    """
    Reads in a MELCOR plot file.

    Reads in a binary MELCOR restart/plot file and resturns the data in a pandas
    DataFrame.

    Parameters
    ----------
    path : str or Path
        The path to the MELCOR restart file to read.

    Returns
    -------
    df : pd.DataFrame
        The data.
    """
    # print("Welcome to the MELCOR parser")
    if type(path) == str:
        path = Path(path)

    with open(path, "rb") as restart_file:
        # Check melcor version
        melcor_version = _check_melcor_version(restart_file)

        # Some checks to see if it is a valid MELCOR file
        # First string should be "./*/"
        _ = _check_string(restart_file, path, "./*/")
        # Next string hould be "TITL"
        _ = _check_string(restart_file, path, "TITL")

        # Keep reading the file until EOF is reached
        while True:

            # Try to get the next line, at EOF this breaks the loop
            try:
                _, line = _get_line(restart_file)
            except EOFError as e:
                break  # End loop at EoF
            flag: str = line.decode()

            ### An actual data line
            # Note that this is out of order, to speed up the reading
            # A .TR/ block is build like this:
            # [(line_length), time, dt, cpu, ncycle, [actual_data], padding]
            #
            if flag == ".TR/":
                _, line = _get_line(restart_file)

                # Get the time of the data
                time[t_step] = unpack("f", line[:4])[0]

                # Get the actual data in the df
                data[t_step, 1:] = unpack(unpack_fmt, line[start_byte:end_byte])

                # Increment time step, and expand array if it is full
                t_step += 1
                if t_step % data_expand_size == 0:
                    time, data = _expand_np_array(time, data, data_expand_size, n_vars)

            ### Variable name block, get the variable names and prepare for reading data.
            elif flag == "KEY ":
                var_names: list[str] = _get_var_names(restart_file)

                ### Some steps to setup the first data set
                (
                    n_vars,
                    data_expand_size,
                    time,
                    data,
                    t_step,
                    start_byte,
                    end_byte,
                    unpack_fmt,
                ) = _prepare_data(var_names)

            # Skip the next line since it doesn't contain relevant data
            # Maybe replace with a function that skips (using file.read()) to speed up
            else:
                _, _ = _get_line(restart_file)

    df = pd.DataFrame(data[:t_step, :], columns=var_names, index=time[:t_step])
    df.index.name = "time"
    return df


def _prepare_data(
    var_names: List[str],
) -> Tuple[int, int, np.ndarray, np.ndarray, int, int, int, str]:
    """
    After reading the variable names, prepare the reading of the data.

    Parameters
    ----------
    var_names : list of str
        The list of all the parameters.

    Returns :
    --------
    n_vars : int
        The number of vars (i.e. len(var_names))
    data_expand_size : int
        Increase the dataframe by this amount to speed up
    time : np.ndarray
        The inizialisation of the time index
    data : np.ndarray
        The inizialisation of the data
    t_step : int
        The current time step (0)
    start_byte : int
        The byte at which to start reading the .TR/ data lines
    end_byte : int
        The byte at which to end reading the .TR/ data lines
    unpack_fmt : str
        The format that unpack uses to convert the bytes to floats
    """
    n_vars: int = len(var_names)  # Number of variables

    # Increase the df by this value to better allocate memory
    # This value was found by timing the function for a particular file.
    # Maybe do more research to find a better time.
    data_expand_size: int = 100
    time: np.ndarray = np.zeros(data_expand_size, dtype="float32")
    data: np.ndarray = np.zeros([data_expand_size, n_vars], dtype="float32")

    # The initial time step
    t_step: int = 0

    ###
    # Some stuff to get the reading of data going
    ###

    # The number of bytes of actual data per data line
    # Note: reduced by 1 because the time word is read elsewhere.
    n_words: int = n_vars - 1

    # Tells unpack which bytes to read
    word_length: int = 4
    start_byte: int = 4 * word_length  # Actual data start at the 4th word
    end_byte: int = start_byte + word_length * n_words

    # The unpack format to convert from bytes to a list of numbers
    unpack_fmt: str = "<" + n_words * "f"
    return (
        n_vars,
        data_expand_size,
        time,
        data,
        t_step,
        start_byte,
        end_byte,
        unpack_fmt,
    )


def _get_var_names(restart_file: BinaryIO) -> List[str]:
    """
    Get the list of variable names

    The variable names are read in 3 steps:

        1. First all unique possible keywords are read
        2. Then the number of occurences of those keywords is read.
            Note that the number of occurences is a cumulative sum row.
            So for example if the data is [1, 2, 3, 5, 14, 15],
            the variables occur [1, 1, 1, 2, 9, 1] times.
        3. The numeric part of the variable names is attached to the keywords
            Note some variables do not have a numerical part, they do not get
            number appended.
    At the end the variable time is inserted at the start of the list.

    Parameters
    ----------
    restart_file : BinaryIO
        The MELCOR restart file.

    Returns
    -------
    var_names : list[str]
        The list of variable names
    """

    _, line = _get_line(restart_file)
    (n_keys,) = unpack("i", line[:4])  # Number of keys
    (n_records,) = unpack(
        "i", line[4:]
    )  # Number of records (i.e. total number of variables)

    ##########################################
    # Part 1. Unique keywords
    ##########################################

    # Continue with getting the keywords
    line_length, line = _get_line(restart_file)
    keyword_length: int = int(line_length / n_keys)

    # Convert each header into a string (and remove spaces)
    # List comprehension for speed reasons
    keywords: List[str] = [
        line[ii * keyword_length : (ii + 1) * keyword_length].decode().strip()
        for ii in range(n_keys)
    ]

    #########################################
    # Part 2. Occurences per keyword
    #########################################
    # The list of occurences is cumulative

    # Read the number of variables per keyword
    _, line = _get_line(restart_file)

    # i_cumulative counting at which occurence we are
    (i_cumulative,) = unpack("i", line[:4])

    var_names: list[str] = []
    for ii, keyword in enumerate(keywords):

        if ii != (len(keywords) - 1):  # For the non-final key's
            start_byte: int = 4 * (ii + 1)
            end_byte: int = 4 * (ii + 2)
            (n_occurences,) = unpack("i", line[start_byte:end_byte])
        else:  # The last keyword has n_records+1 occurences
            n_occurences = n_records + 1

        n_occurences -= i_cumulative  # Remove the cumulative part

        var_names.extend((n_occurences) * [keyword])
        # print(f"{ii=}, {i_cumulative=}, {n_occurences=}, {keyword=}")
        # print(var_names)
        i_cumulative += n_occurences
    if len(var_names) != n_records:
        raise IOError(
            f"Invalid Melcor Plotfile!\n"
            f"Number of variables ({len(var_names)}) does not match expected number {n_records}."
        )

    # Skip over the units
    _, _ = _get_line(restart_file)

    #########################################
    # Part 3. Add numerical part to the variable names
    #########################################
    # Get the var numbers
    _, line = _get_line(restart_file)
    for ii in range(n_records):
        # print(f"{n_records=}, {ii=}")
        start_byte: int = 4 * (ii)
        end_byte: int = 4 * (ii + 1)

        (var_number,) = unpack("i", line[start_byte:end_byte])

        # Only append the variable number if it is NOT 0.
        if var_number != 0:
            var_names[ii] = f"{var_names[ii]}.{var_number}"

    # # Add the variable for time as the first variable
    # var_names.insert(0, "time")
    return var_names


def _expand_np_array(time, data, data_expand_size, n_vars):
    """Expands an existing array

    Parameters
    ----------
    time: np.array
        The time array
    data : np.array
        The existing array
    data_expand_size : int
        The number of time steps that need to be added
    n_vars : int
        The number of variables in the dataframe

    Returns
    -------
    time : np.array
        The time array
    data : np.array
        the modified array.
    """
    time = np.append(time, np.zeros(data_expand_size, dtype="float32"), axis=0)
    data = np.append(
        data, np.zeros([data_expand_size, n_vars], dtype="float32"), axis=0
    )
    return time, data


def _check_string(restart_file: BinaryIO, path: Path, string: str) -> str:
    """
    Checks the string in the next line to see if it matches the given string.

    If the string does not match, throws a IO error.

    Parameters
    ----------
    restart_file : BinaryIO
        The MELCOR restart file.
    path : Path
        The path to the MELCOR restart file.
    string : str
        The string to check against

    Returns
    -------
    flag : str
        The matched string.
    """
    _, line = _get_line(restart_file)
    flag = line.decode()

    if flag != string:
        raise IOError(
            f"'{path}' is not a valid MELCOR file.\n"
            f"    '{string}' was expected, but found '{flag}'."
        )
    return flag


def _get_line(restart_file: BinaryIO) -> Tuple[int, bytes]:
    """
    A line is flanked by two checkwords of 4 bytes that contain the number of
    bytes in the line (i.e. line length).
    If end and start words are not the same, throws an IO error.

    Parameters
    ----------
    restart_file : BinaryIO
        The MELCOR restart file.

    Returns
    -------
    line_length : int
        The length of the line in bytes, without the 4 start and 4 end bytes used
        for the check words.
    line : bytes
        The actual line without the check words.
    """
    first_bytes = restart_file.read(4)
    # Assume EOF if the
    if first_bytes == b"":
        raise EOFError
    (line_length_start,) = unpack("i", first_bytes)
    line = restart_file.read(line_length_start)
    (line_length_end,) = unpack("i", restart_file.read(4))

    # Check if check words are the same.
    if line_length_start != line_length_end:
        raise IOError(f"Error reading Melcor file, check words do not match.")
    return line_length_start, line


def _check_melcor_version(restart_file: BinaryIO) -> str:
    """
    Checks the first byte of the plot file, which indicates which type of
    MELCOR file is used.
    Known start bytes are:

      * 4, MELCOR 1.8.6 (NRG PC version)
      * 67108864, MELCOR 1.8.3 (NRG Unix version), not supported

    Version 1.8.3 is not supported, so when a byte that is not 4 is found,
    the program throws an IO exception.

    Parameters
    ----------
    restart_file: BinaryIO
        The MELCOR restart file.

    Returns
    -------
    melcor_version: str
        The melcor version.
    """
    # Find the first byte
    byte = restart_file.read(1)

    # Get back to the start of the file
    restart_file.seek(0)

    # Advance the pointer 3 bytes from the current position
    # restart_file.seek(3, 1)

    # Check the first byte
    if byte == b"\x04":
        melcor_version = "1.8.6"
    else:
        raise IOError(
            f"Start byte (byte) indicates that melcor version is not supported."
        )
    return melcor_version
