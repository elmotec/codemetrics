#!/usr/bin/env python
# encoding: utf-8

"""Test internals function."""

import datetime as dt
import unittest
from unittest import mock

import codemetrics.internals


class DefaultDatesTest(unittest.TestCase):
    """Test internals helper function"""

    today = dt.datetime(2019, 2, 1, tzinfo=dt.timezone.utc)
    year_ago = dt.datetime(2018, 2, 1, tzinfo=dt.timezone.utc)

    @mock.patch('codemetrics.internals.get_now', autospec=True,
                return_value=today)
    def test_nothing_specified(self, get_now):
        """Test get_log without argument start a year ago."""
        after, before = codemetrics.internals.handle_default_dates(None, None)
        get_now.assert_called_with()
        self.assertEqual(self.year_ago, after)
        self.assertIsNone(before)

    def test_just_today(self):
        """Test get_log without argument start a year ago."""
        after, before = codemetrics.internals.handle_default_dates(self.today, None)
        self.assertEqual(self.today, after)
        self.assertIsNone(before)

