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

Mine your SCM for insight on your software. This package was inspired by
`Adam Torhill`_'s books.

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
    What files/component has not changed in a while or who is most
    familiar with a particular set of files.

- HotSpotReport:
    Combines line count from cloc with SCM information to identify
    files/components that are complex (many lines of code) and that
    change often. There are ways to post process the SCM log so
    that you adjust for mass edits or intraday changes.

- CoChangeReport:
    Identify what file/component changes when another part
    of the code base change. This is useful to identify dependencies.


License
-------

Licensed under the term of `MIT License`_. See attached file LICENSE.txt.

Features
--------

* TODO

Credits
-------

This package was created with Cookiecutter_.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _lizard: https://github.com/terryyin/lizard
.. _pandas: https://pandas.pydata.org/
.. _cloc: http://cloc.sourceforge.net/
.. _Pandas documentation: https://pandas.pydata.org/pandas-docs/stable/text.html
.. _MIT License: https://en.wikipedia.org/wiki/MIT_License
.. _Adam Torhill: https://www.adamtornhill.com/
