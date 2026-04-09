# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "pvisor"
copyright = "2025, NRG PALLAS"
author = "NRG PALLAS"
release = "0.1.0"

# For using autodoc, insert one dir above in the python path
# https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html
import sys
from pathlib import Path

# sys.path.insert(0, str(Path("..", "pvisor").resolve()))
sys.path.insert(0, str(Path("..").resolve()))
# sys.path.insert(0, str(Path("..", "src").resolve()))


# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.napoleon",  # For using numpy type docstrings
    "sphinx_rtd_theme",  # For read the docs theme
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"  # For read the docs theme
html_static_path = ["_static"]
