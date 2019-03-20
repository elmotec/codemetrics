#!/usr/bin/env python
# encoding: utf-8

"""Metrics offer a bunch of function useful to analyze a code base."""

import datetime as dt
import pathlib as pl
import subprocess
import logging
import typing

import pandas as pd

log = logging.getLogger('codemetrics')
log.addHandler(logging.NullHandler())


def get_now():
    """Get current time stamp.

    This is also useful to patch retrieval of the current date/time.

    Returns:
        dt.datetime (UTC)

    """
    return dt.datetime.now(dt.timezone.utc)


def get_year_ago(from_date: dt.datetime = None):
    """Get current time stamp minus 1 year.

    Decrements by one the year of the date returned by `get_now()`.

    Returns:
        dt.datetime (UTC)

    """
    from_date = from_date or get_now()
    date = from_date.replace(year=from_date.year - 1)
    return date


# noinspection SpellCheckingInspection
def get_files(path=None, pattern=None):
    """Retrieve the list of the files currently in the directory."""
    if path is None:
        path = '.'
    if pattern is None:
        pattern = '**/*'
    # noinspection SpellCheckingInspection
    fnames = pl.Path(path).glob(pattern)
    files = [(str(fname),) for fname in fnames]
    return pd.DataFrame.from_records(files, columns=['path'])


def check_run_in_root(path):
    """Throw an exception if path is not a root directory."""
    candidate = pl.Path.cwd() / path
    for _ in candidate.glob(pattern='.gitattributes'):
        return
    for _ in candidate.glob(pattern='.svn'):
        return
    raise ValueError(f'{candidate} does not appear to be a git or svn root')


def run(command, **kwargs):
    """Execute command passed as argument and return output.

    Forwards the call to `subprocess.run`.

    If the command does not return 0, will throw subprocess.CalledProcessError.

    Args:
        command: command to execute.
        **kwargs: additional kwargs are passed to subprocess.run().

    Returns:
        Output of the command long single string

    Note that if some process may want a list of string, others may need one
    long string so the eventual split call is pushed to the caller.

    _subprocess.run:: https://docs.python.org/3/library/subprocess.html

    """
    if 'errors' not in kwargs:
        kwargs['errors'] = 'ignore'
    log.info(command)
    result = subprocess.run(command, check=True,
                            stdout=subprocess.PIPE,
                            **kwargs)
    return result.stdout  # No split. See __doc__.


def handle_default_dates(after: typing.Union[dt.datetime, None],
                         before: typing.Union[dt.datetime, None]):
    """Handles defaults when before, after is None.

    Also checks that the dates are tz-aware and that after.

    Args:
        after: start of the range.
        before: end of the range.

    Returns:
        pair of datetime.datetime for (after, before).

    """
    for date in [after, before]:
        if date and date.tzinfo is None:
            raise ValueError('dates are expected to be tzinfo-aware')
    if not after:
        after = get_year_ago(from_date=before)
    return after, before


def _check_columns(df: pd.DataFrame, names: typing.Sequence[str]) -> None:
    """Checks columns names are found in the data frame.

    Args:
        df: input dataframe.

    Raise:
        ValueError if one of the name is not found.

    """
    for expected in names:
        if expected not in df.columns:
            raise ValueError(f"'{expected}' column not found in input")
    return


def extract_values(data: typing.Union[pd.DataFrame, pd.Series],
                   columns: typing.Union[str, typing.Sequence[str]]) -> typing.Tuple:
    """Extract the specific columns in data.

    Args:
        data: can be either a pandas.DataFrame-like object or pandas.Series.
        columns: scalar str or column list for a frame, label for a series. Note
        we Handles list of just one element as if it were just a scalar.


    Returns:
        tuple of the size of args with one value for each argument.

    """
    assert 0 < data.ndim <= 2, 'series or dataframe expected'
    if data.ndim == 2:
        s = data.iloc[0]
    else:
        s = data
    if hasattr(columns, '__len__') and len(columns) == 1:
        return s.loc[columns[0]]
    return s.loc[columns]

