#!/usr/bin/env python
# encoding: utf-8

"""Metrics offer a bunch of function useful to analyze a code base."""

import datetime as dt
import logging
import pathlib as pl
import subprocess
import typing

import pandas as pd
from typing import Optional

log = logging.getLogger("codemetrics")
log.addHandler(logging.NullHandler())


def get_now():
    """Get current time stamp.

    This is also useful to patch retrieval of the current date/time.

    Returns:
        dt.datetime (UTC)

    """
    return dt.datetime.now(dt.timezone.utc)


def get_year_ago(from_date: Optional[dt.datetime] = None):
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
        path = "."
    if pattern is None:
        pattern = "**/*"
    # noinspection SpellCheckingInspection
    fnames = pl.Path(path).glob(pattern)
    files = [(str(fname),) for fname in fnames]
    return pd.DataFrame.from_records(files, columns=["path"])


def check_run_in_root(path, cwd=None):
    """Throw an exception if path is not a root directory.

    Args:
        path: path to work in.
        cwd: current working directory.

    """
    if cwd is None:
        candidate = pl.Path(path)
    else:
        candidate = (pl.Path(cwd) / path).absolute()
    for _ in candidate.glob(pattern=".git"):
        return
    for _ in candidate.glob(pattern=".svn"):
        return
    raise ValueError(f"{candidate} does not appear to be a git or svn root")


def run(cmd_list: typing.List[str], **kwargs) -> str:
    """Execute command passed as argument and return output.

    Forwards the call to `subprocess.run`.

    If the command does not return 0, will throw subprocess.CalledProcessError.

    Args:
        cmd_list: command to execute.
        **kwargs: additional kwargs are passed to subprocess.run(). In particular:
        cwd: path in which to execute the command.


    Returns:
        Output of the command.

    Raise:
        ValueError if the command is not executed properly.

    If interested in the actual call made to the operating system, use
    `codemetrics.log` like:

    ```
    codemetrics.log.setHandler(logging.StreamHandler()).setLevel(logging.INFO)
    ```

    _subprocess.run:: https://docs.python.org/3/library/subprocess.html

    """
    if "errors" not in kwargs:
        kwargs["errors"] = "ignore"
    cwd = pl.Path(kwargs.get("cwd", ".")).absolute()
    command = " ".join(cmd_list) + f" (in {cwd})"
    log.info(command)
    try:
        result = subprocess.run(
            cmd_list,
            check=True,
            shell=False,  # see https://security.openstack.org/guidelines/dg_avoid-shell-true.html
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            **kwargs,
        )
    except subprocess.CalledProcessError as err:
        raise ValueError(f"failed to execute {command}: {err.stderr}")
    except FileNotFoundError:
        raise ValueError(f"failed to execute {command}: file not found")
    return result.stdout  # No split. See __doc__.


def handle_default_dates(
    after: typing.Optional[dt.datetime], before: typing.Optional[dt.datetime]
) -> typing.Tuple[dt.datetime, typing.Optional[dt.datetime]]:
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
            raise ValueError("dates are expected to be tzinfo-aware")
    if not after:
        after = get_year_ago(from_date=before)
    assert after is not None, "None found where dt.datetime expected"
    assert after.tzinfo is not None, "after is not tzinfo-aware"
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
