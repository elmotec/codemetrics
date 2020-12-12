#!/usr/bin/env python
# encoding: utf-8

"""Test internals function."""

import datetime as dt
import subprocess
import tempfile
import unittest
from unittest import mock

import codemetrics.internals as internals


class DefaultDatesTest(unittest.TestCase):
    """Test internals helper function"""

    today = dt.datetime(2019, 2, 1, tzinfo=dt.timezone.utc)
    year_ago = dt.datetime(2018, 2, 1, tzinfo=dt.timezone.utc)

    @mock.patch("codemetrics.internals.get_now", autospec=True, return_value=today)
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

    cmdline = "do something".split()

    @mock.patch("subprocess.run", autospec=True)
    def test_default_call(self, run):
        """Test default arguments"""
        internals.run(self.cmdline)
        run.assert_called_with(
            self.cmdline, check=True, errors="ignore", stdout=-1, stderr=-1
        )

    @mock.patch("subprocess.run", autospec=True)
    def test_ignore_encoding_errors(self, sprun):
        """Test encoding errors are ignored by default"""
        internals.run(self.cmdline)
        args, kwargs = sprun.call_args
        self.assertIn("errors", kwargs)
        self.assertEqual(kwargs["errors"], "ignore")

    @mock.patch("subprocess.run", autospec=True)
    def test_custom_encoding_errors(self, sprun):
        """Test encoding errors are ignored by default"""
        internals.run(self.cmdline, errors="jump")
        args, kwargs = sprun.call_args
        self.assertIn("errors", kwargs)
        self.assertEqual(kwargs["errors"], "jump")

    @mock.patch("subprocess.run", autospec=True)
    def test_output_is_not_split(self, sprun):
        """Test that the output is not split"""
        expected = "a\nb\nc\n"
        sprun.return_value.stdout = expected
        actual = internals.run(self.cmdline, errors="jump")
        self.assertEqual(expected, actual)

    @mock.patch(
        "subprocess.run",
        side_effect=subprocess.CalledProcessError(1, "command", stderr="the error"),
    )
    def test_error_shows_in_exception(self, _):
        """internals.run raises ValueError and captures stderr from exception"""
        cmd = "valid-command"
        with self.assertRaises(ValueError) as context:
            internals.run([cmd])
        self.assertEqual(f"failed to execute {cmd}: the error", str(context.exception))

    @mock.patch("subprocess.run", side_effect=FileNotFoundError())
    def test_diagnostic_when_file_does_not_exist(self, _):
        """internals.run raises ValueError and captures stderr from exception"""
        with self.assertRaises(ValueError) as context:
            internals.run(["invalid-command"])
        self.assertEqual(
            "failed to execute invalid-command: file not found", str(context.exception)
        )

    @mock.patch("subprocess.run")
    @mock.patch("codemetrics.internals.log")
    def test_logging(self, log, _):
        """Check the command is logged to the logger"""
        internals.run(["some", "command"])
        log.info.assert_called_with("some command")

    @mock.patch("subprocess.run")
    def test_command_with_backslashes(self, run):
        """Check the command is handling backslashes"""
        internals.run(["some", "..\\folder\\to\\command"])
        run.assert_called_with(
            ["some", r"..\folder\to\command"],
            check=True,
            stdout=-1,
            stderr=-1,
            errors="ignore",
        )


class TestCheckRunInRoot(unittest.TestCase):
    """Test check_run_in_root function"""

    def test_basic_check_run_in_root_works_in_parent_directory(self):
        """Works when running in the parent directory because it is the project root."""
        internals.check_run_in_root("..")
        pass

    def test_basic_check_run_in_root_fails_in_tests_directory(self):
        """Fails when running in the current directory because it is not a project root."""
        with self.assertRaises(ValueError) as context:
            internals.check_run_in_root(".")
        self.assertIn("git or svn root", str(context.exception))

    def test_basic_check_run_in_root_fails_in_temp_directory(self):
        """Fails when running in the current directory because it is not a project root

        Also checks the error message.

        """
        tempdir = tempfile.gettempdir()
        with self.assertRaises(ValueError) as context:
            internals.check_run_in_root(tempdir)
        self.assertIn(f"{tempdir} does not appear to be", str(context.exception))
