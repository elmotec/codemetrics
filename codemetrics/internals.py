#!/usr/bin/env python
# encoding: utf-8

"""Metrics offer a bunch of function useful to analyze a code base."""

import datetime as dt
import pathlib as pl
import subprocess
import logging

import pandas as pd

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


def get_now():
    """Get current time stamp as pd.TimeStamp (UTC).

    This is also useful to patch retrieval of the current date/time.

    """
    return dt.datetime.now(dt.timezone.utc)


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


def _check_run_in_root(path):
    """Throw an exception if path is not a root directory."""
    candidate = pl.Path.cwd() / path
    for _ in candidate.glob(pattern='.gitattributes'):
        return
    for _ in candidate.glob(pattern='.svn'):
        return
    raise ValueError(f'{candidate} does not appear to be a git or svn root')


def _run(command, errors=None, **kwargs):
    """Execute command passed as argument and return output.

    Forwards the call to subprocess.run.

    If the command does not return 0, will throw subprocess.CalledProcessError.

    Args:
        command: command to execute.
        errors: error policy during bytes decoding. Defaults to ignore.
        **kwargs: additional kwargs are passed to subprocess.run().

    Returns:
        Output of the command as iter(str).

    """
    if errors is None:
        errors = 'ignore'
    try:
        log.info(command)
        result = subprocess.run(command, check=True,
                                stdout=subprocess.PIPE, errors=errors,
                                **kwargs)
        return result.stdout.split('\n')
    except subprocess.CalledProcessError as err:
        log.warning(err)
        raise
