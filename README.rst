.. image:: https://img.shields.io/pypi/v/codemetrics.svg
    :target: https://pypi.org/pypi/codemetrics/
    :alt: PyPi version

.. image:: https://img.shields.io/pypi/pyversions/codemetrics.svg
    :target: https://pypi.org/pypi/codemetrics/
    :alt: Python compatibility

.. image:: https://img.shields.io/travis/elmotec/codemetrics.svg
    :target: https://travis-ci.org/elmotec/codemetrics
    :alt: Build Status


============
Code Metrics
============

Code metrics is a simple Python module that leverage the libraries below to 
generate insight from a source control management (SCM) tool:

- pandas_: for data munching.
- lizard_: for code complexity calculation.
- cloc.pl (script): for line counts from cloc_
- and your SCM: for now, only Subversion is supported. Looking to add git.

It can generate reports based on Adam Tornhill awesome books.


Installation
------------

To install codemetrics, simply use pip:

::

  pip install codemetrics



Usage
-----

This is a simple tool that makes it easy to retrieve information from your
Source Control Management (SCM) repository and hopefully gain insight from it.

The reports available for now are:

- AgeReport: 
    help see what files/component has not changed in a while or who is most
    familiar with a particular set of files.

- HotSpotReport:
    combines line count from cloc with SCM information to identify
    files/components that are complex (many lines of code) and that
    change often. There are ways to post process the SCM log so
    that you adjust for mass edits or intraday changes.

- CoChangeReport:
    help identify what file/component changes when another part
    of the code base change. This is useful to identify hidden
    dependencies.


Recipes
-------

Date from timestamp
~~~~~~~~~~~~~~~~~~~

::

    df['day'] = df['date'].apply(lambda ts: pd.to_datetime(ts.date()))

There is probably a better way. Seems pretty slow.


Derive components from path
~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    df['component'] = df['path'].str.split('\\').str.get(-2)


Will add a component column equal to the parent folder of the path. If no
folder exists, it will show N/A.

For more advanced manipulation like extractions, see `Pandas documentation`_


Aggregate hotspots by component
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    hotspots_report = cm.HotSpotReport('.')
    log, cloc = hotspots_report.get_log(), hotspots_report.get_cloc()
    cloc['component'] = cloc['path'].str.split('\\').str.get(-2)
    log['component'] = log['path'].str.split('\\').str.get(-2)
    hspots = hotspots_report.generate(log,
                                      cloc.groupby('component').sum().reset_index(),
                                      by='component').dropna()
    hspots.set_index(['component']).sort_values(by='score', ascending=False)


Will order hotspots at the component level in descending order based on the 
complexity and the number of changes (see score column).


Exclude massive changesets
~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    age_report = cm.AgeReport('.')
    log = age_report.get_log()
    threshold = int(log[['revision', 'path']].groupby('revision').
                    sum().quantile(.99))
    massive = get_massive_changesets(log, threshold)
    log_ex_massive = log[~log['revision'].isin(massive['revision'])]


Will exclude changesets with a number of path changed in excess of the 99%
percentile.

License
-------

Licensed under the term of `MIT License`_. See attached file LICENSE.txt.

.. _lizard: https://github.com/terryyin/lizard
.. _pandas: https://pandas.pydata.org/
.. _cloc: http://cloc.sourceforge.net/
.. _Pandas documentation: https://pandas.pydata.org/pandas-docs/stable/text.html
.. _MIT License: https://en.wikipedia.org/wiki/MIT_License
