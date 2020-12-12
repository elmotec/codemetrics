#!/usr/bin/env python
# -*- coding: utf-8 -*-


"""Test utility functions and wrappers."""


import io
import unittest

import pandas as pd
import pandas.testing as pdt

import codemetrics.scm as scm


def add_data_frame_equality_func(test):
    """Define test class to handle assertEqual with `pandas.DataFrame`."""

    def frame_equal(lhs, rhs, msg=None):
        """Adapter for pandas.testing.assert_frame_equal."""
        try:
            pdt.assert_frame_equal(lhs, rhs, check_categorical=False)
        except AssertionError as err:
            if not msg:
                msg = str(err)
            raise test.failureException(msg)

    test.addTypeEqualityFunc(pd.DataFrame, frame_equal)


def add_series_equality_func(test):
    """Define test class to handle assertEqual with `pandas.Series`."""

    def series_equal(lhs, rhs, msg=None):
        """Adapter for pandas.testing.assert_frame_equal."""
        try:
            pdt.assert_series_equal(lhs, rhs, check_categorical=False)
        except AssertionError as err:
            if not msg:
                msg = str(err)
            raise test.failureException(msg)

    test.addTypeEqualityFunc(pd.Series, series_equal)


class DataFrameTestCase(unittest.TestCase):
    """Adds pandas.DataFrame to unittest framework."""

    def setUp(self):
        """Calls add_data_frame_equality_func"""
        add_data_frame_equality_func(self)
        add_series_equality_func(self)


def csvlog_to_dataframe(csv_log: str) -> pd.DataFrame:
    """Converts csv data to pandas.DataFrame.

    Columns are expected to match the fields of the type `scm.LogEntry`.

    Leverages pandas.read_csv. Also fixes the type of 'date' column to be
    a datet/time in UTC tz.

    Args:
        csv_log: csv representation of fields of `scm.LogEntry`

    """
    df = pd.read_csv(
        io.StringIO(csv_log),
        dtype={
            "copyfromrev": "string",
            "textmods": "bool",
            "propmods": "bool",
        },
        parse_dates=["date"],
        false_values=["", "False", "0"],
    )
    # Adds missing columns w/ default None.
    for column in ["action", "copyfromrev", "copyfrompath", "added", "removed"]:
        if column not in df.columns:
            df[column] = None
    if "textmods" not in df.columns:
        df["textmods"] = True
    if "propmods" not in df.columns:
        df["propmods"] = False
    # Reorder columns.
    df = df[scm.LogEntry.__slots__].pipe(scm.normalize_log)
    return df
