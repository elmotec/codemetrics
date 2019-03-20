#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `codemetrics.scm`"""

import unittest
import datetime as dt
import textwrap
import types
import unittest.mock as mock

import pandas as pd

import codemetrics.scm as scm
import tests.utils as utils


class TestLogEntriesToDataFrame(unittest.TestCase):
    """Given a set of scm.LogEntries"""

    def setUp(self):
        utils.add_data_frame_equality_func(self)
        self.log_entries = [
            scm.LogEntry(revision='abc',
                         author='Agatha',
                         date=dt.datetime(2019, 1, 13),
                         path='dir/file.txt',
                         message='',
                         kind='file',
                         textmods=True,
                         propmods=False,
                         action='M'),
            scm.LogEntry(revision='abd',
                         author='Agatha',
                         date=dt.datetime(2019, 2, 1),
                         path='dir/file.txt',
                         message='',
                         kind='file',
                         textmods=True,
                         propmods=False,
                         action='M'),
        ]

    def test_dataframe_conversion(self):
        """Check conversion to DataFrame."""
        actual = scm._to_dataframe(self.log_entries)
        expected = utils.csvlog_to_dataframe(textwrap.dedent('''\
        revision,author,date,path,message,kind,action
        abc,Agatha,2019-01-13T00:00:00.000000Z,dir/file.txt,,file,M
        abd,Agatha,2019-02-01T00:00:00.000000Z,dir/file.txt,,file,M'''))
        self.assertEqual(expected, actual)


class ScmDownloadTestCase:
    """Test interface of download functions.

    Common test case for all SCM download functions. Inherit from it *and*
    from unittest.TestCase.

    See https://stackoverflow.com/questions/1323455/ for design rationale.

    """

    @mock.patch('codemetrics.internals.run', autospec=True,
                return_value='dummy content')
    def test_download_return_single_result(self, _):
        """Makes sure the download function returns a DownloadResult."""
        actual = self.download(pd.DataFrame({'revision': ['abcd'],
                                             'path': ['/some/file']}))
        expected = scm.DownloadResult('abcd', '/some/file', 'dummy content')
        self.assertEqual(expected, actual)

