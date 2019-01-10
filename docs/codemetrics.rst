Package interface
=================

Getting useful data from your source control management tool is really a 2 steps process: first
you need to get the log entries (e.g. ``svn log`` or ``git log``) as a pandas.DataFrame, then process
this output with the functions described below.

The pandas.DataFrame returned by each SCM specific function contains colums corresponding to the
fields of :class:`codemetrics.scm.LogEntry`:

.. autoclass:: codemetrics.scm.LogEntry


Getting your data from Subversion
---------------------------------

.. automodule:: codemetrics.svn
    :members:


Getting your data from Git
--------------------------

.. automodule:: codemetrics.git
    :members:


Main functions
--------------

The main functions are located in core but can be accessed directly from the main module.

For instance::

    >>>import codemetrics as cm
    >>>import cm.svn
    >>>log_df = cm.svn.get_svn_log()
    >>>ages_df = cm.get_ages(log_df)


.. toctree::
   :maxdepth: 2


.. automodule:: codemetrics.core
    :members:


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
