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
    """Get current time stamp as pd.TimeStamp.

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


def _run(command, errors=None, **kwargs):
    """Execute command passed as argument and return output.

    If the command does not return 0, will throw subprocess.CalledProcessError.

    :param list(str) command: command to execute.
    :param str errors: error policy during bytes decoding. Defaults to ignore.
    :param dict **kwargs: additional kwargs are passed to subprocess.run().
    :return: output of the command as iter(str)

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
