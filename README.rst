.. image:: https://img.shields.io/pypi/v/codemetrics.svg
    :target: https://pypi.org/pypi/codemetrics/
    :alt: PyPi version

.. image:: https://img.shields.io/pypi/pyversions/codemetrics.svg
    :target: https://pypi.org/pypi/codemetrics/
    :alt: Python compatibility

.. image:: https://img.shields.io/travis/elmotec/codemetrics.svg
    :target: https://travis-ci.org/elmotec/codemetrics
    :alt: Build Status

.. image:: https://img.shields.io/readthedocs/:packageName.svg
    :target: https://codemetrics.readthedocs.org/
    :alt: Documentation

============
Code Metrics
============

Mine your SCM for insight on your software. A work of love
inspired by `Adam Tornhill`_'s books.

Code metrics is a simple Python module that leverage your source control
management (SCM) tool to generate insight on your code base.

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

  log_df = cm.git.get_git_log()
  ages_df = cm.get_ages(log_df)


See `module documentation`_ for more advanced functions.


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
