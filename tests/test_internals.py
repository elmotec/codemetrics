#!/usr/bin/env python
# encoding: utf-8

"""Test internals function."""

import datetime as dt
import unittest
from unittest import mock
import subprocess

import pandas as pd

import codemetrics.internals as internals


class DefaultDatesTest(unittest.TestCase):
    """Test internals helper function"""

    today = dt.datetime(2019, 2, 1, tzinfo=dt.timezone.utc)
    year_ago = dt.datetime(2018, 2, 1, tzinfo=dt.timezone.utc)

    @mock.patch('codemetrics.internals.get_now', autospec=True,
                return_value=today)
    def test_nothing_specified(self, get_now):
        """Test get_log without argument start a year ago."""
        after, before = internals.handle_default_dates(None, None)
        get_now.assert_called_with()
        self.assertEqual(self.year_ago, after)
        self.assertIsNone(before)

    def test_just_today(self):
        """Test get_log without argument start a year ago."""
        after, before = internals.handle_default_dates(self.today, None)
        self.assertEqual(self.today, after)
        self.assertIsNone(before)


class SubprocessRunTest(unittest.TestCase):
    """Test wrapper around subprocess run"""

    cmdline = 'do something'

    @mock.patch('subprocess.run', autospec=True)
    def test_default_call(self, sprun):
        """Test default arguments"""
        internals.run(self.cmdline)
        sprun.assert_called_with(self.cmdline, check=True, errors='ignore',
                                 stdout=-1, stderr=-1)

    @mock.patch('subprocess.run', autospec=True)
    def test_ignore_encoding_errors(self, sprun):
        """Test encoding errors are ignored by default"""
        internals.run(self.cmdline)
        args, kwargs = sprun.call_args
        self.assertIn('errors', kwargs)
        self.assertEqual(kwargs['errors'], 'ignore')

    @mock.patch('subprocess.run', autospec=True)
    def test_custom_encoding_errors(self, sprun):
        """Test encoding errors are ignored by default"""
        internals.run(self.cmdline, errors='jump')
        args, kwargs = sprun.call_args
        self.assertIn('errors', kwargs)
        self.assertEqual(kwargs['errors'], 'jump')

    @mock.patch('subprocess.run', autospec=True)
    def test_output_is_not_split(self, sprun):
        """Test that the output is not split"""
        expected = 'a\nb\nc\n'
        sprun.return_value.stdout = expected
        actual = internals.run(self.cmdline, errors='jump')
        self.assertEqual(expected, actual)

    def test_error_shows_in_exception(self):
        """Test can capture stderr from exception"""
        msg = "this is the error"
        cmd = f'''python -c "import sys; sys.stderr.write('{msg}'); sys.exit(1)'''
        with self.assertRaises(ValueError) as context:
            internals.run(cmd)
        self.assertIn(f'failed to execute {cmd}: {msg}', str(context.exception))

    def test_diagnostic_when_file_does_not_exist(self):
        """Diagnostic when the file is not found should also be accessible."""
        with self.assertRaises(ValueError) as context:
            internals.run('invalid-command')
        self.assertIn('failed to execute invalid-command: file not found',
                      str(context.exception))


class ExtractValuesTestCase(unittest.TestCase):
    """Test internals.extract_values behaviour."""

    def test_dataframe(self):
        data = pd.DataFrame(data={'revision': ['1'] * 2,
                                  'path': ['file.py'] * 2})
        revision, path = internals.extract_values(data, ['revision', 'path'])
        self.assertEqual('1', revision)
        self.assertEqual('file.py', path)

    def test_series(self):
        data = pd.Series(data={'revision': '1', 'path': 'file.py'})
        revision, path = internals.extract_values(data, ['revision', 'path'])
        self.assertEqual('1', revision)
        self.assertEqual('file.py', path)

    def test_list_of_labels_of_size_one(self):
        data = pd.DataFrame(data={'revision': ['1'] * 2,
                                  'path': ['file.py'] * 2})
        revision = internals.extract_values(data, ['revision'])
        self.assertEqual('1', revision)

    def test_label_as_scalar(self):
        data = pd.DataFrame(data={'revision': ['1'] * 2,
                                  'path': ['file.py'] * 2})
        revision = internals.extract_values(data, 'revision')
        self.assertEqual('1', revision)
