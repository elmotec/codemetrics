#!/usr/bin/env python
# -*- coding: utf-8 -*-


"""Test utility functions and wrappers."""


import unittest

import pandas as pd
import pandas.testing as pdt


def add_data_frame_equality_func(test):
    """Define test class to handle assertEqual with `pandas.DataFrame`."""
    def frame_equal(lhs, rhs, msg=None):
        """Adapter for pandas.testing.assert_frame_equal."""
        if msg:
            try:
                pdt.assert_frame_equal(lhs, rhs)
            except AssertionError as err:
                raise test.failureException(msg)
        else:
            pdt.assert_frame_equal(lhs, rhs)
    test.addTypeEqualityFunc(pd.DataFrame, frame_equal)


class DataFrameTestCase(unittest.TestCase):
    """Adds pandas.DataFrame to unittest framework."""

    def setUp(self):
        """Calls add_data_frame_equality_func"""
        add_data_frame_equality_func(self)


