#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `codemetrics.git`"""

import datetime as dt
import textwrap
import io
import unittest
from unittest import mock

import tqdm
import pandas as pd
import numpy as np

import tests.utils as utils

import codemetrics as cm
import codemetrics.git as git


class PathElemParser(unittest.TestCase):

    def setUp(self):
        """Initialize git collector."""
        self.git = git._GitLogCollector()

    def test_parse_path_elem(self):
        """Parsing of path element."""
        pe = '21	    2   	dir/test.py'
        added, removed, relpath, copyfrompath = self.git.parse_path_elem(pe)
        self.assertEqual(21, added)
        self.assertEqual(2, removed)
        self.assertEqual('dir/test.py', relpath)
        self.assertIsNone(copyfrompath)

    def test_parse_renamed_path(self):
        """Parsing of path element."""
        pe = '1       1       dir/{b/a.py => a/b.py}'
        added, removed, relpath, copyfrompath = self.git.parse_path_elem(pe)
        self.assertEqual(1, added)
        self.assertEqual(1, removed)
        self.assertEqual('dir/a/b.py', relpath)
        self.assertEqual('dir/b/a.py', copyfrompath)

    def test_parse_renamed_path_empty_right(self):
        """Parsing of path element."""
        pe = '21	    2   	dir/{category => }/test.py'
        added, removed, relpath, copyfrompath = self.git.parse_path_elem(pe)
        self.assertEqual(21, added)
        self.assertEqual(2, removed)
        self.assertEqual('dir/test.py', relpath)
        self.assertEqual('dir/category/test.py', copyfrompath)

    def test_parse_renamed_path_empty_left(self):
        """Parsing of path element."""
        pe = '-       -       dir/{ => subdir}/file.py'
        added, removed, relpath, copyfrompath = self.git.parse_path_elem(pe)
        self.assertTrue(np.isnan(added))
        self.assertTrue(np.isnan(removed))
        self.assertEqual('dir/subdir/file.py', relpath)
        self.assertEqual('dir/file.py', copyfrompath)


def get_log():
    retval = textwrap.dedent('''
    [2adcc03] [elmotec] [2018-12-05 23:44:38 -0000] [Fixed Windows specific paths]
    1       1       codemetrics/core.py
    1       1       requirements.txt
    
    [b9fe5a6] [elmotec] [2018-12-04 21:49:55 -0000] [Added guess_components]
    44      0       codemetrics/core.py
    1       8       codemetrics/svn.py
    1       0       requirements.txt
    110     18      tests/test_core.py
    ''')
    return retval


class GitTestCase(unittest.TestCase):
    """Given a BaseReport instance."""

    def setUp(self):
        """Prepare environment for the tests.

        - Adds hanlding of equality test for pandas.DataFrame.
        - Patches the function get_now for a specific date.

        """
        utils.add_data_frame_equality_func(self)
        self.now = dt.datetime(2018, 12, 6, 21, 0, tzinfo=dt.timezone.utc)
        self.get_now_patcher = mock.patch('codemetrics.internals.get_now',
                                          autospec=True, return_value=self.now)
        self.get_now = self.get_now_patcher.start()
        self.get_check_patcher = mock.patch('codemetrics.internals.check_run_in_root',
                                            autospec=True)
        self.check_run_in_root = self.get_check_patcher.start()
        self.after = dt.datetime(2018, 12, 3, tzinfo=dt.timezone.utc)

    def tearDown(self):
        """Clean up."""
        mock.patch.stopall()

    @mock.patch('codemetrics.internals.run',
                side_effect=[get_log()], autospec=True)
    def test_get_log(self, call):
        """Simple git call returns pandas.DataFrame."""
        actual = git.get_git_log('.', after=self.after)
        call.assert_called_with(
            f'git {git._GitLogCollector._args} --after {self.after:%Y-%m-%d} .')
        expected = utils.csvlog_to_dataframe(textwrap.dedent('''
revision,author,date,path,message,kind,action,copyfromrev,copyfrompath,added,removed
2adcc03,elmotec,2018-12-05 23:44:38+00:00,codemetrics/core.py,Fixed Windows specific paths,f,,,,1,1
2adcc03,elmotec,2018-12-05 23:44:38+00:00,requirements.txt,Fixed Windows specific paths,f,,,,1,1
b9fe5a6,elmotec,2018-12-04 21:49:55+00:00,codemetrics/core.py,Added guess_components,f,,,,44,0
b9fe5a6,elmotec,2018-12-04 21:49:55+00:00,codemetrics/svn.py,Added guess_components,f,,,,1,8
b9fe5a6,elmotec,2018-12-04 21:49:55+00:00,requirements.txt,Added guess_components,f,,,,1,0
b9fe5a6,elmotec,2018-12-04 21:49:55+00:00,tests/test_core.py,Added guess_components,f,,,,110,18'''))
        self.assertEqual(expected, actual)

    @mock.patch('tqdm.tqdm', autospec=True, create=True)
    @mock.patch('codemetrics.internals.run', side_effect=[get_log()],
                autospec=True)
    def test_get_log_with_progress(self, _run, _):
        """Simple git call returns pandas.DataFrame."""
        pb = tqdm.tqdm()
        _ = git.get_git_log('.', after=self.after, progress_bar=pb)
        cmd = ('git log --pretty=format:"[%h] [%an] [%ad] [%s]" --date=iso '
               '--numstat --after 2018-12-03 .')
        _run.assert_called_with(cmd)
        self.assertEqual(pb.total, 3)
        calls = [mock.call(1), mock.call(2)]
        pb.update.assert_has_calls(calls)
        pb.close.assert_called_once()

    @mock.patch('codemetrics.internals.run', autospec=True,
                return_value=textwrap.dedent("""
                [xxxxxxx] [elmotec] [2018-12-05 23:44:38 -0000] [excel file]
                -       -       directory/output.xls
                """))
    def test_handling_of_binary_files(self, call):
        """Handles binary files which do not show added or removed lines."""
        df = git.get_git_log('.', after=self.after)
        call.assert_called_with(
            f'git {git._GitLogCollector._args} --after 2018-12-03 .')
        expected = utils.csvlog_to_dataframe(textwrap.dedent('''\
        revision,author,date,path,message,kind,action
        xxxxxxx,elmotec,2018-12-05 23:44:38+00:00,directory/output.xls,excel file,f,'''))
        self.assertEqual(expected, df)

    @mock.patch('codemetrics.internals.run', autospec=True,
                return_value=textwrap.dedent("""
                [xxxxxxx] [elmotec] [2018-12-05 23:44:38 -0000] [bbb [ci skip] [skipci]]
                1       1       some/file
                """))
    def test_handling_of_brackets_in_log(self, call):
        """Handles brackets inside the commit log."""
        df = git.get_git_log('.', after=self.after)
        call.assert_called_with(
            f'git {git._GitLogCollector._args} --after {self.after:%Y-%m-%d} .')
        expected = utils.csvlog_to_dataframe(textwrap.dedent('''\
        revision,author,date,path,message,kind,action,copyfromrev,copyfrompath,added,removed
        xxxxxxx,elmotec,2018-12-05 23:44:38+00:00,some/file,bbb [ci skip] [skipci],f,,,,1,1'''))
        self.assertEqual(expected, df)


class DownloadGitFilesTestCase(unittest.TestCase):
    """Test getting historical files with git."""

    content1 = textwrap.dedent('''
    def main():
        print('ahah!')
    ''')
    content2 = textwrap.dedent('''
    def main():
        print('ahah!')

    if __name__ == '__main__':
        main()
    ''')

    def setUp(self):
        self.git = cm.git._GitFileDownloader()

    @mock.patch('codemetrics.internals.run', autospec=True,
                return_value=content1)
    def test_single_revision_download(self, _run):
        """Retrieval of one file and one revision."""
        sublog = pd.read_csv(io.StringIO(textwrap.dedent("""\
        revision,path
        1,file.py
        """)))
        results = list(cm.git.download_files(sublog))
        _run.assert_called_with(f'{self.git.command} 1:file.py')
        self.assertEqual(1, len(results))
        actual = results[0]
        expected = cm.scm.FileDownloadResult('file.py', 1, self.content1)
        self.assertEqual(expected, actual)

    @mock.patch('codemetrics.internals.run', autospec=True,
                side_effect=[content1, content2])
    def test_multiple_revision_download(self, _run):
        """Retrieval of multiple revisions."""
        sublog = pd.read_csv(io.StringIO(textwrap.dedent("""\
        revision,path
        1,file.py
        2,file.py
        """)))
        actual = list(cm.svn.download_files(sublog))
        expected = [
            cm.scm.FileDownloadResult('file.py', 1, self.content1),
            cm.scm.FileDownloadResult('file.py', 2, self.content2),
        ]
        self.assertEqual(expected, actual)


if __name__ == '__main__':
    unittest.main()
