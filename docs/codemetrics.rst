codemetrics API
===============

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

.. _Jupyter: https://jupyter.org/
.. _Vega: https://vega.github.io/
.. _Altair: https://altair-viz.github.io/

