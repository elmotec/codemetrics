## Unreleased

## v2.0.1 (2026-10-29)

## v2.0.0 (2026-10-29)

### Fix

- restore test suite compatibility with current dependencies (#31)


- add support for python3.15, drop 3.10

## v1.0.0 (2025-09-14)

### BREAKING CHANGE

- upgrade numpy, pandas and scipy to v2

## v0.11.7 (2022-04-24)

### Fix

- fix lizard removing length (#19)

## v0.11.6 (2022-03-22)

- Added support for Python 3.10.

## v0.11.5 (2021-07-24)

- Fixed handling of files with spaces (credit: @Wonshtrum).

## v0.11.4 (2021-05-31)

- Handled errors from `git show`, such as requests for deleted files.

## v0.11.3 (2021-01-30)

- Added `cm.get_log` for consistency with the rest of the interface.

## v0.11.2 (2021-01-17)

## v0.11.1 (2021-01-16)

## v0.11.0 (2021-01-16)

- Introduced `GitProject` and `SvnProject` to simplify references to the tree, client, and utility functions.

## v0.10.0 (2020-12-12)

- Fixed handling of file names containing commas.
- Fixed the HTML visualization of the pandas example.
- Used new pandas data types and introduced type hints.
- Switched CI from Travis CI to GitHub Actions.

## v0.9.6 (2019-09-29)

- Fixed incorrect usage of `subprocess.run()` (issue #1).
- Factored common logic between Git and Subversion and fixed related bugs.
- Fixed `test_core` for pandas 0.25.
- Added the `cm_func_stats` command.
- Added AppVeyor support for Windows and expanded documentation.
- Fixed retrieval of added and removed lines for file names containing spaces.
- Fixed indexed input in `get_mass_changes`.
- Fixed handling of removed files and branches in `svn.get_diff_stats`.
- Began changing interfaces to use `apply` and `groupby`.
- Added line change statistics for Subversion.

## v0.9.5 (2019-09-05)

## v0.9.3 (2019-04-01)

## v0.9.2 (2019-03-28)

## v0.9.1 (2019-03-23)

## v0.9.0 (2019-03-19)

## v0.8.2 (2019-02-27)

## v0.8.1 (2019-02-26)

- Added `svn.get_diff_stats` to retrieve line changes per diff.
- Integrated lizard for average and function level cyclomatic complexity.

## v0.8.0 (2019-02-13)

## v0.7.1 (2019-01-26)

## v0.7.0 (2019-01-09)

- Introduced the function oriented interface and Vega/Altair visualizations.
- Added documentation.

## v0.5 (2018-05-12)

- First release on PyPI.
