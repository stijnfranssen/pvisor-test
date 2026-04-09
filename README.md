# PVISOR - Reading plot files from thermohydraulic codes

The PVISOR library, developed at [NRG PALLAS](https://www.nrgpallas.com/),
allows you to read in plot files from thermohydraulic codes for further
data analysis using python.
Data is represented in a pandas DataFrame.
PVISOR is compatible with plot files from the following codes:

- RELAP5
- SPECTRA
- TRACE
- MELCOR


## Usage

PVISOR can be called installed using pip:

```bash
pip install pvisor
```

Import the library and use the `read_file()` function,
which allows all suported datafiles to be read.

```python
# Import the library
import pvisor

# Read a file, code should be "RELAP", "SPECTRA", "TRACE" or "MELCOR"
data = pvisor.read_file("plotfile.plt", code="RELAP")

# Print a variable in your file
print(data["rktpow"])
print(data["rho-1010000"])
```

## Building from source

To install from source, first install requirements.
For Ubuntu these are

```bash
# For ubuntu
sudo apt install rust python
```

Then clone this repository

```bash
git clone git@github.com:stijnfranssen/pvisor.git
cd pvisor
```

Create a virtual environment and install the prerequisites:

```bash
python3 -m venv venv
source venv/bin/activate
python3 -m pip install maturin
```

Build the rust elements

```bash
maturin develop --release
```

Test if output works

```bash
pytest
```

### Optional: Build documentation

The documentation is created using Sphinx and are build using:

```bash
cd docs
make html
```