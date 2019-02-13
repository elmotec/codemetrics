#!/usr/bin/env python
# -*- coding: utf-8 -*-


"""Test utility functions and wrappers."""


import unittest
import io

import codemetrics.scm as scm

import pandas as pd
import numpy as np
import pandas.testing as pdt


def add_data_frame_equality_func(test):
    """Define test class to handle assertEqual with `pandas.DataFrame`."""
    def frame_equal(lhs, rhs, msg=None):
        """Adapter for pandas.testing.assert_frame_equal."""
        if msg:
            try:
                pdt.assert_frame_equal(lhs, rhs)
            except AssertionError:
                raise test.failureException(msg)
        else:
            # FIXME. Getting weird errors on categorical differences.
            pdt.assert_frame_equal(lhs, rhs, check_categorical=False)
    test.addTypeEqualityFunc(pd.DataFrame, frame_equal)


class DataFrameTestCase(unittest.TestCase):
    """Adds pandas.DataFrame to unittest framework."""

    def setUp(self):
        """Calls add_data_frame_equality_func"""
        add_data_frame_equality_func(self)


def csvlog_to_dataframe(csv_log: str) -> pd.DataFrame:
    """Converts csv data to pandas.DataFrame.

    Columns are expected to match the fields of the type `scm.LogEntry`.

    Leverages pandas.read_csv. Also fixes the type of 'date' column to be
    a datet/time in UTC tz.

    Args:
        csv_log: csv representation of fields of `scm.LogEntry`

    """
    df = pd.read_csv(io.StringIO(csv_log), parse_dates=['date'],
                     dtype={'revision': 'object',
                            'author': 'object',
                            'message': 'object',
                            'action': 'object',
                            'textmods': 'bool',
                            'propmods': 'bool',
                            'copyfromrev': 'object',
                            'copyfrompath': 'object'},
                     false_values=['', 'False', '0'])
    # Adds missing float columns w/ default np.nan.
    for column in ['added', 'removed']:
        if column not in df.columns:
            df[column] = np.nan
    # Adds missing object columns w/ default None.
    for column in ['action', 'copyfromrev', 'copyfrompath']:
        if column not in df.columns:
            df[column] = None
    if 'textmods' not in df.columns:
        df['textmods'] = True
    if 'propmods' not in df.columns:
        df['propmods'] = False
    # Reorder columns.
    df = df[scm.LogEntry.__slots__]
    return scm._dtype_and_cats(df)
