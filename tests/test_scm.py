#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `codemetrics.scm`"""

import datetime as dt
import textwrap
import typing
import unittest
import unittest.mock as mock

import pandas as pd

import codemetrics.scm as scm
import tests.utils as utils


class TestNormaliseLog(unittest.TestCase):
    """Given a scm.LogEntry data frame."""

    def test_date_to_utc(self):
        """TBD"""
        csv_data = textwrap.dedent(
            """
        ,revision,author,date,path,message,kind,action
        0,dfa9d6f08,Joris,2020-11-28 15:27:20+01:00,pandas/tests/series/methods/test_convert_dtypes.py,TST: rewrite
        1,91abd0aba,Joris,2020-11-27 21:12:01+01:00,doc/source/whatsnew/v1.1.5.rst,REGR: fix"""
        )
        actual = utils.csvlog_to_dataframe(csv_data)
        self.assertEqual("datetime64[ns, UTC]", actual["date"].dtype.name)


class TestLogEntriesToDataFrame(unittest.TestCase):
    """Given a set of scm.LogEntries"""

    def setUp(self):
        utils.add_data_frame_equality_func(self)
        self.log_entries = [
            scm.LogEntry(
                revision="abc",
                author="Agatha",
                date=dt.datetime(2019, 1, 13),
                path="dir/file.txt",
                message="",
                kind="file",
                textmods=True,
                propmods=False,
                action="M",
            ),
            scm.LogEntry(
                revision="abd",
                author="Agatha",
                date=dt.datetime(2019, 2, 1),
                path="dir/file.txt",
                message="",
                kind="file",
                textmods=True,
                propmods=False,
                action="M",
            ),
        ]

    @property
    def actual(self):
        """Factor computation of the actual dataframe."""
        return scm.to_frame(self.log_entries)

    @property
    def dtypes(self):
        """Factor computation of the actual dataframe dtypes."""
        return self.actual.dtypes

    def test_dataframe_conversion(self):
        """Check conversion to DataFrame."""
        expected = utils.csvlog_to_dataframe(
            textwrap.dedent(
                """\
        revision,author,date,path,message,kind,action
        abc,Agatha,2019-01-13T00:00:00.000000Z,dir/file.txt,,file,M
        abd,Agatha,2019-02-01T00:00:00.000000Z,dir/file.txt,,file,M"""
            )
        )
        self.assertEqual(expected, self.actual)

    def test_dataframe_revision_dtype(self):
        """Check dtype in DataFrame."""
        self.assertEqual("string", self.dtypes["revision"].name)

    def test_dataframe_author_dtype(self):
        """Check dtype in DataFrame."""
        self.assertEqual("string", self.dtypes["author"].name)

    def test_dataframe_date_dtype(self):
        """Check dtype in DataFrame."""
        self.assertEqual("datetime64[ns, UTC]", self.dtypes["date"].name)

    def test_dataframe_path_dtype(self):
        """Check dtype in DataFrame."""
        self.assertEqual("string", self.dtypes["path"].name)

    def test_dataframe_message_dtype(self):
        """Check dtype in DataFrame."""
        self.assertEqual("string", self.dtypes["message"].name)

    def test_dataframe_kind_dtype(self):
        """Check dtype in DataFrame."""
        self.assertEqual("category", self.dtypes["kind"].name)

    def test_dataframe_action_dtype(self):
        """Check dtype in DataFrame."""
        self.assertEqual("category", self.dtypes["action"].name)

    def test_dataframe_textmods_dtype(self):
        """Check dtype in DataFrame."""
        self.assertEqual("bool", self.dtypes["textmods"].name)

    def test_dataframe_propmods_dtype(self):
        """Check dtype in DataFrame."""
        self.assertEqual("bool", self.dtypes["propmods"].name)

    def test_dataframe_copyfromrev_dtype(self):
        """Check dtype in DataFrame."""
        self.assertEqual("string", self.dtypes["copyfromrev"].name)

    def test_dataframe_copyfrompath_dtype(self):
        """Check dtype in DataFrame."""
        self.assertEqual("string", self.dtypes["copyfrompath"].name)

    def test_dataframe_added_dtype(self):
        """Check dtype in DataFrame."""
        self.assertEqual("float32", self.dtypes["added"].name)

    def test_dataframe_removed_dtype(self):
        """Check dtype in DataFrame."""
        self.assertEqual("float32", self.dtypes["removed"].name)


class ScmDownloadTestCase:
    """Test interface of download functions.

    Common test case for all SCM download functions. Inherit from it *and*
    from unittest.TestCase.

    See also:
        GitDownloadTestCase, SubversionDownloadTestCase

    See https://stackoverflow.com/questions/1323455/ for design rationale.

    """

    @mock.patch(
        "codemetrics.internals.run", autospec=True, return_value="dummy content"
    )
    def test_download_return_single_result(self, _):
        """Makes sure the download function returns a DownloadResult."""
        actual = self.download(
            pd.DataFrame({"revision": ["abcd"], "path": ["/some/file"]})
        )
        expected = scm.DownloadResult("abcd", "/some/file", "dummy content")
        self.assertEqual(expected, actual)


class GetLogTestCase:
    """Test interface to get_log functions.

    Common test case for all SCM get_log functions. Inherit from it *and* from
    unittest.TestCase.

    see also:
        GetGitLogTestCase, SubversionTestCase

    """

    def setUp(self, get_log_func: typing.Callable, module) -> None:
        """Set up common to all log getting test cases.

        Adds hanlding of equality test for pandas.DataFrame and patches the
        functions get_now for a specific date and check_run_in_root.

        Args:
            get_log_func: function that will retrieve the log from SCM tool.

        """
        utils.add_data_frame_equality_func(self)
        self.get_log = get_log_func
        self.module = module
        self.now = dt.datetime(2018, 12, 6, 21, 0, tzinfo=dt.timezone.utc)
        self.get_now_patcher = mock.patch(
            "codemetrics.internals.get_now", autospec=True, return_value=self.now
        )
        self.get_now = self.get_now_patcher.start()
        self.get_check_patcher = mock.patch(
            "codemetrics.internals.check_run_in_root", autospec=True
        )
        self.check_run_in_root = self.get_check_patcher.start()
        self.after = dt.datetime(2018, 12, 3, tzinfo=dt.timezone.utc)

    def test_set_up_called(self):
        """Makes sure GetLogTestCase.setUp() is called."""
        self.assertIsNotNone(self.get_log)

    @mock.patch("codemetrics.internals.run", autospec=True)
    def test_get_log_updates_default_download_func(self, _):
        """The SCM used to get the log updates the default download."""
        self.get_log()
        self.assertEqual(self.module.download, scm.default_download_func)

    @mock.patch("codemetrics.internals.run", autospec=True)
    def test_get_log_with_path(self, run_):
        """get_log takes path into account."""
        _ = self.get_log(path="my-path", after=self.after)
        self.assertIn("my-path", str(run_.call_args[0][0]))
