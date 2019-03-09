#!/usr/bin/env python
# encoding: utf-8

"""Test internals function."""

import datetime as dt
import unittest
from unittest import mock
import subprocess

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


class SubprocessRunTest(unittest.TestCase):
    """Test wrapper around subprocess run"""

    cmdline = 'do something'

    @mock.patch('subprocess.run', autospec=True)
    def test_default_call(self, sprun):
        """Test default arguments"""
        codemetrics.internals.run(self.cmdline)
        sprun.assert_called_with(self.cmdline, check=True, errors='ignore',
                                 stdout=-1)

    @mock.patch('subprocess.run', autospec=True)
    def test_ignore_encoding_errors(self, sprun):
        """Test encoding errors are ignored by default"""
        codemetrics.internals.run(self.cmdline)
        args, kwargs = sprun.call_args
        self.assertIn('errors', kwargs)
        self.assertEqual(kwargs['errors'], 'ignore')

    @mock.patch('subprocess.run', autospec=True)
    def test_custom_encoding_errors(self, sprun):
        """Test encoding errors are ignored by default"""
        codemetrics.internals.run(self.cmdline, errors='jump')
        args, kwargs = sprun.call_args
        self.assertIn('errors', kwargs)
        self.assertEqual(kwargs['errors'], 'jump')

    @mock.patch('subprocess.run', autospec=True)
    def test_output_is_not_split(self, sprun):
        """Test that the output is not split"""
        expected = 'a\nb\nc\n'
        sprun.return_value.stdout = expected
        actual = codemetrics.internals.run(self.cmdline, errors='jump')
        self.assertEqual(expected, actual)

    @mock.patch('subprocess.run', autospec=True)
    def test_error_shows_in_log(self, sprun):
        """Test can capture stderr from exception"""
        exception = subprocess.CalledProcessError(1, cmd=self.cmdline,
                                                  stderr='some error')
        sprun.side_effect = [exception]
        with self.assertRaises(subprocess.CalledProcessError) as cm:
            codemetrics.internals.run(self.cmdline)
        self.assertEqual('some error', cm.exception.stderr)
