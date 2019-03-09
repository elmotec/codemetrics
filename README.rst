.. image:: https://img.shields.io/pypi/v/codemetrics.svg
    :target: https://pypi.org/pypi/codemetrics/
    :alt: PyPi version

.. image:: https://img.shields.io/pypi/pyversions/codemetrics.svg
    :target: https://pypi.org/pypi/codemetrics/
    :alt: Python compatibility

.. image:: https://img.shields.io/travis/elmotec/codemetrics.svg
    :target: https://travis-ci.org/elmotec/codemetrics
    :alt: Build Status

.. image:: https://img.shields.io/readthedocs/codemetrics.svg
    :target: https://codemetrics.readthedocs.org/
    :alt: Documentation

.. image:: https://coveralls.io/repos/github/elmotec/codemetrics/badge.svg?branch=master
    :target: https://coveralls.io/github/elmotec/codemetrics?branch=master
    :alt: Test coverage

.. image:: https://api.codacy.com/project/badge/Grade/dd4a11eb66674b3bbe518d8f829b6234
    :target: https://www.codacy.com/app/elmotec/codemetrics?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=elmotec/codemetrics&amp;utm_campaign=Badge_Grade
    :alt: Codacy

============
Code Metrics
============

Mine your SCM for insight on your software. A work of love
inspired by `Adam Tornhill`_'s books.

Code metrics is a simple Python module that leverage pandas and your source control management (SCM) tool togenerate
insight on your code base.

- pandas_: for data munching.
- lizard_: for code complexity calculation.
- cloc.pl (script): for line counts from cloc_
- For now, only Subversion and git are supported.


Installation
------------

To install codemetrics, simply use pip:

::

  pip install codemetrics



Usage
-----

This is a simple tool that makes it easy to retrieve information from your
Source Control Management (SCM) repository and hopefully gain insight from it.

::

  import codemetrics as cm
  import cm.git

  log_df = cm.get_git_log()
  ages_df = cm.get_ages(log_df)


To retrieve the number of lines changed by revision with Subversion:

::

  import codemetrics as cm
  import cm.git

  log_df = cm.get_svn_log().set_index(['revision', 'path'])
  log_df.loc[:, ['added', 'removed']] = log_df.reset_index().\
                                           groupby('revision').\
                                           apply(cm.svn.get_diff_stats, chunks=False)

See `module documentation`_ for more advanced functions or the `example notebook`_


License
-------

Licensed under the term of `MIT License`_. See attached file LICENSE.txt.


Credits
-------

- This package was inspired by `Adam Tornhill`_'s books.
- This package was created with Cookiecutter_.


.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _lizard: https://github.com/terryyin/lizard
.. _pandas: https://pandas.pydata.org/
.. _cloc: http://cloc.sourceforge.net/
.. _Pandas documentation: https://pandas.pydata.org/pandas-docs/stable/text.html
.. _MIT License: https://en.wikipedia.org/wiki/MIT_License
.. _Adam Tornhill: https://www.adamtornhill.com/
.. _module documentation: https://codemetrics.readthedocs.org/
.. _example notebook: https://github.com/elmotec/codemetrics/tree/master/notebooks
