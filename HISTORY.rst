=======
History
=======

0.9.4 (2019-09-02)
------------------
* Fixed test_core following https://github.com/pandas-dev/pandas/pull/24748 (Pandas 0.25.X)
* Added script `cm_func_stats` that generates statistics on the function passed as argument.
* Added appveyor support for Windows.
* Documentation.

0.9.3 (2019-04-01)
------------------
* Fixed retrieval of added and removed lines when there are spaces in a file name.
* Fixed indexed input in `get_mass_changes`.
* Fixed handling of removed files in `svn.get_diff_stats`.
* Fixed handling of branches in `svn.get_diff_stats`.

0.9 (2019-03-19)
----------------

* Started changing interfaces to leverage apply and groupby.
* Added lines added/removed for Subversion.

0.8.2 (2019-02-26)
------------------

* Added `svn.get_diff_stats` to retrieve line changes stats per diff.

0.8 (2019-02-13)
----------------

* Integrated lizard to calculate average and function level cyclomatic complexity.

0.7 (2019-01-09)
----------------

* Function oriented interface.
* Visualization via Vega, Altair.
* Documentation.

0.6
---

* Alpha work.

0.5 (2018-05-12)
----------------

* First release on PyPI.


