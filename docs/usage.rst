.. _usage:

Usage
#####

Read in a plot file using the ``read_file()`` function which returns a pandas dataframe.

In the example below the relap plot file ``output.plt`` is returned in a pandas dataframe:

``df = pvisor.read_file(file_path="output.plt", code="RELAP")``

.. autofunction:: pvisor.pvisor_module.read_file