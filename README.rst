.. image:: https://img.shields.io/pypi/v/codemetrics.svg
    :target: https://pypi.python.org/pypi/codemetrics/
    :alt: PyPi version

.. image:: https://img.shields.io/pypi/pyversions/codemetrics.svg
    :target: https://pypi.python.org/pypi/codemetrics/
    :alt: Python compatibility

.. image:: https://img.shields.io/github/workflow/status/elmotec/codemetrics/Python%20application
    :target: https://github.com/elmotec/codemetrics/actions?query=workflow%3A%22Python+application%22
    :alt: GitHub Workflow Python application

.. image:: https://img.shields.io/appveyor/ci/elmotec/codemetrics/main?label=AppVeyor
    :target: https://ci.appveyor.com/project/elmotec/codemetrics
    :alt: AppVeyor main status

.. image:: https://img.shields.io/librariesio/release/pypi/codemetrics.svg?label=libraries.io
    :alt: Libraries.io dependency status for latest release
    :target: https://libraries.io/pypi/codemetrics

.. image:: https://img.shields.io/readthedocs/codemetrics.svg
    :target: https://codemetrics.readthedocs.org/
    :alt: Documentation

.. image:: https://codecov.io/gh/elmotec/codemetrics/branch/main/graph/badge.svg?token=ELJW941FET
    :target: https://codecov.io/gh/elmotec/codemetrics
    :alt: Coverage

.. image:: https://img.shields.io/codacy/grade/dd4a11eb66674b3bbe518d8f829b6234.svg
    :target: https://www.codacy.com/app/elmotec/codemetrics/dashboard
    :alt: Codacy


===========
codemetrics
===========

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

  project = cm.GitProject('path/to/project')
  loc_df = cm.get_cloc(project, cloc_program='/path/to/cloc')
  log_df = cm.get_log(project)
  ages_df = cm.get_ages(log_df)


To retrieve the number of lines changed by revision with Subversion:

::

  import codemetrics as cm
  import cm.git

  project = cm.SvnProject('path/to/project')
  log_df = cm.get_log(project).set_index(['revision', 'path'])
  log_df.loc[:, ['added', 'removed']] = log_df.reset_index().\
                                           groupby('revision').\
                                           apply(cm.svn.get_diff_stats, chunks=False)

See `module documentation`_ for more advanced functions or the `example notebook`_ where codemetrics is applied to pandas.

There is also an `example notebook`_ running codemetrics on the pandas code base, and
the `example html export`_ of that notebook output (some features are missing like
the display of file names when hovering on the circles).

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
.. _example notebook: https://github.com/elmotec/codemetrics/blob/main/notebooks/pandas.ipynb
.. _example html export: https://github.com/elmotec/codemetrics/blob/main/notebooks/pandas.html

