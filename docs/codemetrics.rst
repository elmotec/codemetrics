codemetrics interface
=====================

Getting useful data from your source control management tool is really a 2 steps process: first
you need to get the log entries (e.g. ``svn log`` or ``git log``) as a pandas.DataFrame, then process
this output with the functions described below.

The pandas.DataFrame returned by each SCM specific function contains colums corresponding to the
fields of :class:`codemetrics.scm.LogEntry`:

.. autoclass:: codemetrics.scm.LogEntry


codemetrics.scm
---------------

Common logic for source control management tools.

.. automodule:: codemetrics.scm
    :members:


codemetrics.svn
---------------

Getting your data from Subversion.

.. automodule:: codemetrics.svn
    :members:


codemetrics.git
---------------

Getting your data from git.

.. automodule:: codemetrics.git
    :members:


codemetrics.core
----------------

The main functions are located in core but can be accessed directly from the main module.

For instance::

    >>>import codemetrics as cm
    >>>import cm.svn
    >>>log_df = cm.svn.get_svn_log()
    >>>ages_df = cm.get_ages(log_df)


.. automodule:: codemetrics.core
    :members:


codemetrics.vega
----------------

Brdges visualization in Jupyter_ notebooks with Vega_ and Altair_.

.. automodule:: codemetrics.vega
    :members:


Command line scripts
--------------------

.. _cm_func_stats:

cm_func_stats
^^^^^^^^^^^^^

The `codemetrics` offers a command line tool `cm_func_stats` to compute statistics on functions.

For now the statistics are limited to the number of line of code (LOC), the complexity of the function (CCN), and
the most frequent tokens together with the their span (see https://www.fluentcpp.com/2018/10/23/word-counting-span/
for more information)::

    >cm_func_stats --help
    Usage: cm_func_stats [OPTIONS] FILE_PATH LINE_NO

      Generate statistics on the function specified by FILE_PATH LINE_NO.

    Options:
      --version  Show the version and exit.
      --help     Show this message and exit.

And for an example::

    >cm_func_stats codemetrics\cmdline.py 42
    codemetrics\cmdline.py(39): cm_func_stats@39-55@codemetrics\cmdline.py, NLOC: 16, CCN: 4
    codemetrics\cmdline.py(43): f occurs 7 time(s), spans 13 lines (76.47%)
    codemetrics\cmdline.py(41): func_info occurs 4 time(s), spans 9 lines (52.94%)
    codemetrics\cmdline.py(49): token occurs 3 time(s), spans 4 lines (23.53%)
    codemetrics\cmdline.py(45): write occurs 2 time(s), spans 9 lines (52.94%)
    codemetrics\cmdline.py(45): sys occurs 2 time(s), spans 9 lines (52.94%)
    codemetrics\cmdline.py(45): stdout occurs 2 time(s), spans 9 lines (52.94%)
    codemetrics\cmdline.py(48): span occurs 2 time(s), spans 5 lines (29.41%)
    codemetrics\cmdline.py(48): func_span occurs 2 time(s), spans 5 lines (29.41%)
    codemetrics\cmdline.py(43): msg occurs 2 time(s), spans 2 lines (11.76%)
    codemetrics\cmdline.py(39): line_no occurs 2 time(s), spans 3 lines (17.65%)
    codemetrics\cmdline.py(39): file_path occurs 2 time(s), spans 3 lines (17.65%)


.. _Jupyter: https://jupyter.org/
.. _Vega: https://vega.github.io/
.. _Altair: https://altair-viz.github.io/

