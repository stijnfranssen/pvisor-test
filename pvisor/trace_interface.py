"""
Contains the code for reading TRACE XTV files.

The keyword for the TRACE interface for using in the ``pvisor.read_file()`` function is: ``TRACE``.

Reads in a binary TRACE XTV file and returns it in a pandas dataframe.

The TRACE XTV file is based on the eXternal Data Representation format.
Until Python 12 and below the `xdrlib` was part of the standard library,
however from Python 13 onwards it is removed.
The py-xdrlib should function as a drop-in replacement.

"""

################################################################################
### Modules                                                                  ###
################################################################################

## External modules ############################################################
import pandas as pd  # Using the pd.DataFrame to handle the data
from pathlib import Path  # For handeling paths/directories and files
import numpy as np  # For storing the data

# Check if this library is needed.
import xdrlib  # Note until 3.12 in standard lib, after that available through py-xdrlib
from xdrlib import Unpacker

# For handeling the binary data
from struct import unpack
import struct  # so it is clear that where struc.error comes from

# For type hints
from typing import Union, List


################################################################################
### XDR helper functions                                                     ###
################################################################################

# The XTV file is stored in the XDR fileformat
# The following functions help with unpacking the data


def _nCells_checker(nCells: int, unpacker: Unpacker):
    """
    Checks if the next integer in the packed data is the same.

    Advances the unpacker by 1 int of bytes
    Parameters
    ----------
    n_Cells : int
        The integer to test against
    unpacker : Unpacker
        The XDR data to unpack
    """
    nCellsp1 = unpacker.unpack_int()  # nCells + 1
    if nCells + 1 != nCellsp1:
        raise IOError(
            f"Maybe not a valid TRACE file, 'nCells' and 'nCells + 1' do not match"
            f"\ngot {nCells=} and {nCellsp1=}"
        )
    return


def _read_trace(path: Union[str, Path]) -> pd.DataFrame:
    """
    Reads in a TRACE XTV file.

    Reads in a binary TRACE XTV file and returns it in a pandas dataframe.

    Parameters
    ----------
    path: str or Path
        The path to the relap restart file to read.

    Returns
    -------
    df: pd.DataFrame
        The data
    """
    # temporary empty dataframe to appease the linter
    df = pd.DataFrame()

    # Cast the path into a proper Path for clearer file handeling
    if type(path) == str:
        path = Path(path)

    # Open the file
    with open(path, "rb") as restart_file:
        xdr_data = restart_file.read()
    unpacker: Unpacker = xdrlib.Unpacker(xdr_data)

    # Read the header
    nComp, nSVar, nDVar, dataLen, nPoints = _read_header_init(unpacker=unpacker)

    # Read the variable names
    varNames = _read_var_names(unpacker, nComp, nSVar, nDVar)
    # return

    """Read the data in as a list of 1d numpy dataframe's that are joined at the end"""

    list_of_time_steps = []
    npDataFormat = None
    unpackDataFormat = None
    n_vars = len(varNames)  # Number of variables, including time

    for timestep in range(nPoints):
        temp = unpacker.unpack_fopaque(16)  # Discard the first 16 bytes, DATA
        nDataPoints = unpacker.unpack_int()

        # Determine if data is single or double precision and initiliaze the dataframe
        if not npDataFormat:
            nDataPoints_check = unpack(">I", temp[-4:])[0]
            if nDataPoints == (nDataPoints_check - 20) / 4:
                npDataFormat = np.single
                unpackDataFormat = unpacker.unpack_float
            else:
                npDataFormat = np.double
                unpackDataFormat = unpacker.unpack_double

            # Initialise the time and data arrays
            time_array = np.empty(nPoints, dtype=npDataFormat)

            data_array = np.empty((nPoints, n_vars), dtype=npDataFormat)

        time_array[timestep] = unpackDataFormat()
        data_array[timestep] = unpacker.unpack_farray(nDataPoints - 1, unpackDataFormat)

    df = pd.DataFrame(
        data=data_array,
        index=time_array,
        columns=varNames,
        dtype=npDataFormat,
    )
    df.index.name = "time"

    return df


def _read_var_names(
    unpacker: Unpacker, nComp: int, nSVar: int, nDVar: int
) -> List[str]:
    """
    Read the variable names.

    Loop over every component, which has a header with things like number of junctions etc.
    The information in this header is then used to determine how to read the variable names.

    Parameters
    ----------
    unpacker : Unpacker
        The XTV file read in using xdrlib
    nComp : int
        Number of components output
    nSVar : int
        Total number of static variable output (maybe not needed?)
    nDVar : int
        Total number of dynamic variable output (maybe not needed?)

    Returns
    -------
    varNames : List[str]
        The list of variable names
    """
    varNames: List[str] = []  # Full list of variable names

    for n_component in range(nComp):
        temp = unpacker.unpack_fopaque(16)  # Discard the first 16 bytes
        compId = unpacker.unpack_int()  # Component ID number from TRACE
        _ = unpacker.unpack_int()  # compSsId
        [unpacker.unpack_string() for _ in range(2)]  # cType, cTitle
        cDim = unpacker.unpack_int()  # Dimension of the component
        nTempl = unpacker.unpack_int()  # Number of graphics display templates
        nJun = unpacker.unpack_int()  # Number of junctions
        nLegs = unpacker.unpack_int()  # Number of legs
        nSVar = unpacker.unpack_int()  # Number of static variables
        nDVar = unpacker.unpack_int()  # Number of dynamic variables
        [unpacker.unpack_int() for _ in range(2)]  # nVect, nChild
        nDynAx = unpacker.unpack_int()  # Number of dynamically sized axes
        auxStrT = unpacker.unpack_string()  # Type of Aux structure to follow

        # Ignore all data in the dynamically sized axes [4.2.2]
        for n_axis in range(nDynAx):
            _ = unpacker.unpack_fopaque(16)  # Discard the first 16 bytes
            [unpacker.unpack_string() for _ in range(4)]
            _ = unpacker.unpack_int()

        for n_display_templates in range(nTempl):  # Graphics Display template [4.2.3]
            n_display_header = unpacker.unpack_fopaque(16)  # Read the first 16 bytes
            xDim = n_display_header[6] - 48  # The dimension of the display [1, 2, 3]

            if xDim == 1:
                nCells = unpacker.unpack_int()  # Number of cells in this component
                _ = unpacker.unpack_int()  # dynAxI
                temp = unpacker.unpack_fopaque(16)  # Discard 16 bytes: GD1A

                for _ in range(3):  # fl, grav, fa (all with dimension nCells+1)
                    _nCells_checker(nCells, unpacker)
                    [unpacker.unpack_double() for _ in range(nCells + 1)]
            elif xDim == 2:
                nCells = unpacker.unpack_int()  # Number of cells in this component
                nCellI = unpacker.unpack_int()  # Dimension of the I axis
                nCellJ = unpacker.unpack_int()  # Dimension of the J axis
                # Skip the further blocks
                [unpacker.unpack_int() for _ in range(2)]  # dynAxI, dynAxJ
                _ = unpacker.unpack_string()  # coordSys

                _ = unpacker.unpack_fopaque(16)  # Discard 16 bytes: GD2A

                # fI(size: nCellI+1), fJ(size: nCellJ+1) and grav (size: nCellJ+1)
                for _ in range(3):
                    nCellsXp1 = unpacker.unpack_int()  # nCell (I or J) +1
                    [unpacker.unpack_double() for _ in range(nCellsXp1)]

            elif xDim == 3:  # [4.2.3.3.1. Dimensions of the 3D graphics Template]
                nCells = unpacker.unpack_int()  # Number of cells in this component
                nCellI = unpacker.unpack_int()  # Dimension of the I axis
                nCellJ = unpacker.unpack_int()  # Dimension of the J axis
                nCellK = unpacker.unpack_int()  # Dimension of the K axis
                [unpacker.unpack_int() for _ in range(3)]  # dynAxI, dynAxJ, dynAxK
                _ = unpacker.unpack_string()  # coordSys

                _ = unpacker.unpack_fopaque(16)  # Discard 16 bytes
                # fI(nCellI+1), fJ(nCellJ (??+1??)), fK(nCellK+1), grav(nCellK+1)
                for _ in range(4):
                    nCellXp1 = unpacker.unpack_int()  #
                    [unpacker.unpack_double() for _ in range(nCellXp1)]
            else:
                raise IOError(
                    f"Maybe not a valid TRACE file, for component {compId} expected xDim in [1, 2, 3]"
                    + f"\ngot {xDim=}"
                )

        # Skip junction information [4.2.4 Junction Sub-Block]
        for _ in range(nJun):
            temp = unpacker.unpack_fopaque(16)  # Discard the first 16 bytes: GDJn

            # junId, jCellI, jCellJ, jCellK
            [unpacker.unpack_int() for _ in range(4)]

            # Expecting a string of 4 bytes, so using fstring to force that
            # If not forced EOF error is encoutered.
            jFace = unpacker.unpack_bytes()  # jFace
            # jFace = unpacker.unpack_bytes()  # jFace

        # Skip Leg information [4.2.5 Leg Sub-Block]
        for _ in range(nLegs):
            temp = unpacker.unpack_fopaque(16)  # Discard the first 16 bytes: GD..
            [unpacker.unpack_int() for _ in range(3)]

        # Skip PlenAux information [4.2.6.2 PlenAux Structure Block]
        if auxStrT == "PlenAux ":
            _ = unpacker.unpack_fopaque(16)  # Discard the first 16 bytes
            _ = unpacker.unpack_string()
            [unpacker.unpack_int() for _ in range(3)]
            [unpacker.unpack_double() for _ in range(nJun)]
        elif auxStrT not in [b"AUX_NONE", b"        "]:
            raise IOError(
                f"Not a valid TRACE XTV file, for component {compId}\n"
                f"expected auxStrT in [b'AUX_NONE', b'        ']"
                f"\ngot {auxStrT=}"
            )

        # Variable definition block [4.2.7]
        for var_number in range(nSVar + nDVar):
            # Read the varname variables
            temp = unpacker.unpack_fopaque(16)  # Discard the first 16 bytes: VARD

            varName = unpacker.unpack_string().decode()  # Assumes utf-8

            _ = unpacker.unpack_string()  # VarLabel
            # uType # Note: should be readbytes, but read string works better...
            _ = unpacker.unpack_string()
            _ = unpacker.unpack_string()  # uLabel

            # Variable dimension / position attribute
            dimPosAt = unpacker.unpack_string()

            # freqAt, cMapAt, vectA, spOptAt, vectName
            [unpacker.unpack_string() for _ in range(5)]

            _ = unpacker.unpack_int()  # vTmpl
            vLength = unpacker.unpack_int()  # Numerical length of the variable
            # For the staticaly created variables
            if var_number < nSVar:
                temp = unpacker.unpack_fopaque(16)  # Discard the first 16 bytes
                nVals = unpacker.unpack_int()
                [unpacker.unpack_double() for _ in range(nVals)]

            # Actually create variable names
            else:
                # compId = f"{compId:03d}"
                if dimPosAt == b"0D   ":
                    if compId == 0:
                        varNames.append(varName)
                    else:
                        varNames.append(f"{varName}-{compId}")

                # To follow AptPlot output
                # For the 3D components first the K is given, then the J then the I.
                # Unclear if in 2D components first the J then the I must be given.
                # Unclear if the order is always Axx(Ryy(Tzz)) or the letters can be ordered differently

                elif dimPosAt == b"2dCc ":
                    if (nCellI * nCellJ) != vLength:
                        raise IOError(
                            f"Not a valid TRACE file.\n"
                            f"Expected nCellI * nCellJ == vLength\n"
                            f"got: {nCellI=}, {nCellJ=} and {vLength=}"
                        )
                    for iiI in range(nCellI):
                        for iiJ in range(nCellJ):
                            varNames.append(
                                f"{varName}-{compId}A{iiJ+1:02d}R{iiI+1:02d}"
                            )

                elif dimPosAt == b"2dFaI ":
                    if ((nCellI + 1) * nCellJ) != vLength:
                        raise IOError(
                            f"Not a valid TRACE file.\n"
                            f"Expected (nCellI+1) * nCellJ == vLength\n"
                            f"got: {nCellI+1=}, {nCellJ=} and {vLength=}"
                        )
                    for iiI in range(nCellI + 1):
                        for iiJ in range(nCellJ):
                            varNames.append(
                                f"{varName}-{compId}A{iiJ+1:02d}R{iiI+1:02d}"
                            )

                elif dimPosAt == b"2dFaJ ":
                    if (nCellI * (nCellJ + 1)) != vLength:
                        raise IOError(
                            f"Not a valid TRACE file.\n"
                            f"Expected nCellI * (nCellJ + 1) == vLength\n"
                            f"got: {nCellI=}, {nCellJ+1=} and {vLength=}"
                        )
                    for iiI in range(nCellI):
                        for iiJ in range(nCellJ + 1):
                            varNames.append(
                                f"{varName}-{compId}A{iiJ+1:02d}R{iiJ+1:02d}"
                            )

                elif dimPosAt in [b"3dCc ", b"3dFaJ"]:
                    if (nCellI * nCellJ * nCellK) != vLength:
                        raise IOError(
                            f"Not a valid TRACE file.\n"
                            f"Expected nCellI * nCellJ * nCellK == vLength\n"
                            f"got: {nCellI=}, {nCellJ=}, {nCellK=} and {vLength=}"
                        )
                    for iiI in range(nCellI):
                        for iiJ in range(nCellJ):
                            for iiK in range(nCellK):
                                varNames.append(
                                    f"{varName}-{compId}A{iiK+1:02d}R{iiJ+1:02d}T{iiI+1:02d}"
                                )

                elif dimPosAt == b"3dFaI":
                    if ((nCellI + 1) * nCellJ * nCellK) != vLength:
                        raise IOError(
                            f"Not a valid TRACE file.\n"
                            f"Expected (nCellI+1) * nCellJ * nCellK == vLength\n"
                            f"got: {nCellI+1=}, {nCellJ=}, {nCellK=} and {vLength=}"
                        )
                    for iiI in range(nCellI + 1):
                        for iiJ in range(nCellJ):
                            for iiK in range(nCellK):
                                varNames.append(
                                    f"{varName}-{compId}A{iiK+1:02d}R{iiJ+1:02d}T{iiI+1:02d}"
                                )

                elif dimPosAt == b"3dFaK":
                    if (nCellI * nCellJ * (nCellK + 1)) != vLength:
                        raise IOError(
                            f"Not a valid TRACE file.\n"
                            f"Expected nCellI * nCellJ * (nCellK+1) == vLength\n"
                            f"got: {nCellI=}, {nCellJ=}, {nCellK+1=} and {vLength=}"
                        )
                    for iiI in range(nCellI):
                        for iiJ in range(nCellJ):
                            for iiK in range(nCellK + 1):
                                varNames.append(
                                    f"{varName}-{compId}A{iiK+1:02d}R{iiJ+1:02d}T{iiI+1:02d}"
                                )

                else:
                    for ii in range(vLength):
                        varNames.append(f"{varName}-{compId}A{ii+1:02d}")

    return varNames


def _read_header_init(unpacker: Unpacker):
    """
    Reads the header.

    Read the header and return the relevant information.

    Parameters
    ----------
    unpacker : Unpacker
        The XTV file read in using xdrlib

    Returns
    -------
    nComp : int
        Number of components output
    nSVar : int
        Total number of static variable output
    nDVar : int
        Total number of dynamic variable output
    dataLen : int
        Length of each data edit
    nPoints : int
        Number of datapoints in file
    """
    _ = unpacker.unpack_string()  # header_string
    # Skip the next 4 variables
    [
        unpacker.unpack_int() for _ in range(4)
    ]  # xtvMarjorversion, xtvMinorVersion, xtvRevision, xtvRes
    nUnits = unpacker.unpack_int()  # The number of units information blocks output
    nComp = unpacker.unpack_int()  # Number of components output
    nSVar = unpacker.unpack_int()  # Total number of static variable output
    nDVar = unpacker.unpack_int()  # Total number of static variable output
    [unpacker.unpack_int() for _ in range(3)]  # nSChannels, nDChannels, dataStart
    dataLen = unpacker.unpack_int()  # Length of each data edit
    nPoints = unpacker.unpack_int()  # Number of datapoints in file
    [unpacker.unpack_int() for _ in range(4)]
    [unpacker.unpack_string() for _ in range(7)]

    if nUnits:
        # <STIJN> @Pieter, do i understand this correctly? What is going on here?
        raise IOError(f"Reading of nUnits not yet implemented.")

    return nComp, nSVar, nDVar, dataLen, nPoints
