Recipes
=======

Getting added and removed lines from Subversion log
---------------------------------------------------

Subversion log (unlike git) does not provide the number of lines added and removed for each commit so
`codemetrics <readme>` resort to a 2 passes process retrieving the log first:

.. code-block:: python

    log = cm.get_svn_log()


At this point, added and removed column will be NaN. To populate then run the second pass. It is slow
because it relies on repeatedly calling ``svn diff -c`` for each revision:

.. code-block:: python

    log.loc[:, ['added', 'removed']] = log.groupby('revision').apply(cm.get_diff_stats)


Note ``chunks=True`` returns diff stats with a row for each diff chunks.


.. seealso::

    Function `codemetrics.svn.get_diff_stats`


Leverage dask to speed up retrieval of added and removed line with Subversion
-----------------------------------------------------------------------------

Retrieving added and removed line with Subversion can be slow because codemetrics makes repeated calls to
``svn diff --git -c XXX`` to count the number of pluses and minuses. To speed up the process somewhat, one can try to
leverage dask like so:

.. code-block:: python

    import dask.dataframe as dd
    import dask.diagnostics as ddiags
    import multiprocessing as mp

    n_cpus = mp.cpu_count()
    log = cm.get_svn_log().reset_index()
    meta = get_diff_stats(log[-1:]).iloc[0:0]
    partitioned_log = dd.from_pandas(log, npartitions=n_cpus)
    wf = partioned_log.groupby('revision').apply(get_diff_stats, chunks=False, meta=meta)
    with ddiags.ProgressBar():  # optional
        addrem_df = wf.conpute()   # returns a pandas.DataFrame


Note that there is a significant overhead to start the parallel process.
