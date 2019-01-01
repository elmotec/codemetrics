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

from tests.utils import add_data_frame_equality_func

import codemetrics as cm
import codemetrics.git as git
import codemetrics.cloc


def get_git_log(dates=None):
    if dates is None:
        dates = [dt.datetime(2018, 2, 1, 0, 0, 0, tzinfo=dt.timezone.utc)]
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
    return retval.split('\n')


class GitTestCase(unittest.TestCase):
    """Given a BaseReport instance."""

    @staticmethod
    def read_git_log(gitlog):
        """Interprets a string as a pandas.DataFrame returned by get_git_log.

        Leverages pandas.read_csv. Also fixes the type of 'date' column to be
        a datet/time in UTC tz.

        """
        df = pd.read_csv(io.StringIO(gitlog), dtype={
            'revision': 'object',
            'author': 'object',
            'textmods': 'object',
            'kind': 'object',
            'action': 'object',
            'propmods': 'object',
            'path': 'object',
            'message': 'object',
        }, parse_dates=['date'])
        df['date'] = pd.to_datetime(df['date'], utc=True)
        return df

    def setUp(self):
        """Prepare environment for the tests.

        - Adds hanlding of equality test for pandas.DataFrame.
        - Patches the function get_now for a specific date.

        """
        add_data_frame_equality_func(self)
        self.now = dt.datetime(2018, 12, 6, 21, 0, tzinfo=dt.timezone.utc)
        self.get_now_patcher = mock.patch('codemetrics.internals.get_now',
                                          autospec=True, return_value=self.now)
        self.get_now = self.get_now_patcher.start()
        self.get_check_patcher = mock.patch('codemetrics.internals._check_run_in_root',
                                            autospec=True)
        self.check_run_in_root = self.get_check_patcher.start()

    def tearDown(self):
        """Clean up."""
        mock.patch.stopall()

    @mock.patch('codemetrics.internals._run',
                side_effect=[get_git_log()], autospec=True)
    def test_get_log(self, call):
        """Simple git call returns pandas.DataFrame."""
        df = git.get_git_log(dt.datetime(2018, 12, 4, tzinfo=dt.timezone.utc))
        call.assert_called_with(f'git {git._GitLogCollector._args} --after 2018-12-04 .')
        expected = GitTestCase.read_git_log(textwrap.dedent('''
revision,author,date,textmods,kind,action,propmods,path,message,added,removed
2adcc03,elmotec,2018-12-05 23:44:38+00:00,,f,,,codemetrics/core.py,Fixed Windows specific paths,1,1
2adcc03,elmotec,2018-12-05 23:44:38+00:00,,f,,,requirements.txt,Fixed Windows specific paths,1,1
b9fe5a6,elmotec,2018-12-04 21:49:55+00:00,,f,,,codemetrics/core.py,Added guess_components,44,0
b9fe5a6,elmotec,2018-12-04 21:49:55+00:00,,f,,,codemetrics/svn.py,Added guess_components,1,8
b9fe5a6,elmotec,2018-12-04 21:49:55+00:00,,f,,,requirements.txt,Added guess_components,1,0
b9fe5a6,elmotec,2018-12-04 21:49:55+00:00,,f,,,tests/test_core.py,Added guess_components,110,18
'''))
        self.assertEqual(df, expected)

    @mock.patch('tqdm.tqdm', autospec=True)
    @mock.patch('codemetrics.internals._run', side_effect=[get_git_log()],
                autospec=True)
    def test_get_log_with_progress(self, call, tqdm_):
        """Simple git call returns pandas.DataFrame."""
        pb = tqdm.tqdm()
        after = dt.datetime(2018, 12, 3, tzinfo=dt.timezone.utc)
        _ = cm.git.get_git_log(after, progress_bar=pb)
        cmd = ('git log --pretty=format:"[%h] [%an] [%ad] [%s]" --date=iso ' +
               '--numstat --after 2018-12-03 .')
        call.assert_called_with(cmd)
        self.assertEqual(pb.total, 3)
        calls = [mock.call(1), mock.call(2)]
        pb.update.assert_has_calls(calls)
        pb.close.assert_called_once()

    @mock.patch('codemetrics.git._GitLogCollector.get_log', autospec=True)
    def test_get_git_log_default_start_date(self, get_log):
        """Test get_git_log without argument start a year ago."""
        collector = git._GitLogCollector()
        self.get_now.assert_called_with()
        expected = self.now - dt.timedelta(365)
        self.assertEqual(collector.after, expected)

    @mock.patch('codemetrics.internals._run', autospec=True,
                return_value=textwrap.dedent("""
                [xxxxxxx] [elmotec] [2018-12-05 23:44:38 -0000] [excel file]
                -       -       directory/output.xls
                """).split('\n'))
    def test_handling_of_binary_files(self, call):
        """Handles binary files which do not show added or removed lines."""
        df = git.get_git_log(dt.datetime(2018, 12, 4, tzinfo=dt.timezone.utc))
        call.assert_called_with(f'git {git._GitLogCollector._args} --after 2018-12-04 .')
        expected = GitTestCase.read_git_log(textwrap.dedent('''\
        revision,author,date,textmods,kind,action,propmods,path,message,added,removed
        xxxxxxx,elmotec,2018-12-05 23:44:38+00:00,,f,,,directory/output.xls,excel file,,
        '''))
        self.assertEqual(expected, df)

    @mock.patch('codemetrics.internals._run', autospec=True,
                return_value=textwrap.dedent("""
                [xxxxxxx] [elmotec] [2018-12-05 23:44:38 -0000] [bbb [ci skip] [skipci]]
                1       1       some/file
                """).split('\n'))
    def test_handling_of_brackets_in_log(self, call):
        """Handles brackets inside the commit log."""
        df = git.get_git_log(dt.datetime(2018, 12, 4, tzinfo=dt.timezone.utc))
        call.assert_called_with(f'git {git._GitLogCollector._args} --after 2018-12-04 .')
        expected = GitTestCase.read_git_log(textwrap.dedent('''\
        revision,author,date,textmods,kind,action,propmods,path,message,added,removed
        xxxxxxx,elmotec,2018-12-05 23:44:38+00:00,,f,,,some/file,bbb [ci skip] [skipci],1,1
        '''))
        self.assertEqual(expected, df)

    @mock.patch('codemetrics.internals._run', autospec=True,
                return_value=textwrap.dedent("""
                [xxxxxxx] [elmotec] [2018-12-05 23:44:38 -0000] [a]
                -       -       directory/{ => subdir}/file
                """).split('\n'))
    def test_handling_of_files_moved(self, call):
        """Handles files that were moved using the new location."""
        df = git.get_git_log(dt.datetime(2018, 12, 4, tzinfo=dt.timezone.utc))
        call.assert_called_with(f'git {git._GitLogCollector._args} --after 2018-12-04 .')
        expected = GitTestCase.read_git_log(textwrap.dedent('''\
        revision,author,date,textmods,kind,action,propmods,path,message,added,removed
        xxxxxxx,elmotec,2018-12-05 23:44:38+00:00,,f,,,directory/subdir/file,a,,
        '''))
        self.assertEqual(expected, df)

    @mock.patch('codemetrics.internals._run', autospec=True,
                return_value=textwrap.dedent("""
                [xxxxxxx] [elmotec] [2018-12-05 23:44:38 -0000] [a]
                1       1       dir/{b/a.py => a/b.py}
                """).split('\n'))
    def test_handling_of_directory_renamed(self, call):
        """Handles subdirectories that were renamed."""
        df = git.get_git_log(dt.datetime(2018, 12, 4, tzinfo=dt.timezone.utc))
        call.assert_called_with(f'git {git._GitLogCollector._args} --after 2018-12-04 .')
        expected = GitTestCase.read_git_log(textwrap.dedent('''\
        revision,author,date,textmods,kind,action,propmods,path,message,added,removed
        xxxxxxx,elmotec,2018-12-05 23:44:38+00:00,,f,,,dir/a/b.py,a,1,1
        '''))
        self.assertEqual(expected, df)

    @mock.patch('codemetrics.internals._run', autospec=True,
                return_value=textwrap.dedent("""
                [xxxxxxx] [elmotec] [2018-12-05 23:44:38 -0000] [a]
                21	    2   	dir/{category => }/test.py
                """).split('\n'))
    def test_handling_of_removed_directories(self, call):
        """Handles subdirectories that were renamed."""
        df = git.get_git_log(dt.datetime(2018, 12, 4, tzinfo=dt.timezone.utc))
        call.assert_called_with(f'git {git._GitLogCollector._args} --after 2018-12-04 .')
        expected = GitTestCase.read_git_log(textwrap.dedent('''\
        revision,author,date,textmods,kind,action,propmods,path,message,added,removed
        xxxxxxx,elmotec,2018-12-05 23:44:38+00:00,,f,,,dir/test.py,a,21,2
        '''))
        self.assertEqual(expected, df)



if __name__ == '__main__':
    unittest.main()
