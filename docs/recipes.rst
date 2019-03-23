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

