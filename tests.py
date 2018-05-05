#!/usr/bin/env python
# encoding: utf-8


"""Tests for codemetrics."""


import unittest
import unittest.mock as mock
import subprocess
import logging
import textwrap
import io
import datetime as dt

import pandas as pd
import pandas.testing as pdt
import tqdm

import codemetrics as cm


class CommandTest(unittest.TestCase):
    """Given a console based tool."""

    def test_can_run(self):
        """wrapper call to the command return output."""
        output = cm._run('echo Hello world!'.split())
        self.assertEqual(output, ['Hello world!', ''])

    def test_failure_throws(self):
        """wrapper call will throw on error."""
        msg = "Command 'badcall' returned non-zero.*"
        with self.assertRaisesRegex(subprocess.CalledProcessError, msg):
            output = cm._run('badcall', stderr=subprocess.STDOUT, shell=True)

    def test_failure_throws_without_shell(self):
        """wrapper call will throw on error."""
        #msg = "cannot find the file" for Windows
        #msg = "No such file or directory" for Linux
        with self.assertRaises(FileNotFoundError):
            output = cm._run('badcall', stderr=subprocess.STDOUT)


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


class ProgressBarAdapterTest(unittest.TestCase):
    """Test ProgressBarAdapter"""

    def setUp(self):
        pass

    @mock.patch('codemetrics.get_now', autospec=True,
                return_value = dt.datetime(2018, 2, 13))
    @mock.patch('tqdm.tqdm', autospec=True)
    def test_initialization(self, tqdm_, get_now):
        after = dt.datetime(2018, 2, 1)
        with cm.ProgressBarAdapter(tqdm.tqdm(), after=after) as pbar:
            pbar.update(pbar.today - dt.timedelta(3))
            pbar.update(pbar.today - dt.timedelta(1))
        expected = [mock.call(9), mock.call(2), mock.call(1)]
        self.assertEqual(tqdm_().update.mock_calls, expected)


class BaseReportTest(unittest.TestCase):
    """Given a BaseReport instance."""

    def get_svn_log(dates=None):
        if dates is None:
            dates = [dt.datetime(2018, 2, 24, 11, 14, 11,
                                 tzinfo=dt.timezone.utc)]
        retval = textwrap.dedent('''
        <?xml version="1.0" encoding="UTF-8"?>
        <log>''')
        for date in dates:
            retval += textwrap.dedent(f'''
            <logentry revision="1018">
            <author>jlecomte</author>
            <date>{date.strftime('%Y-%m-%dT%H:%M:%S.%fZ')}</date>
            <paths>
            <path text-mods="true" kind="file" action="M"
               prop-mods="false">/project/trunk/stats.py</path>
            <path text-mods="true" kind="file" action="M"
               prop-mods="false">/project/trunk/requirements.txt</path>
            </paths>
            <msg>Added joblib to requirements.txt</msg>
            </logentry>''')
        retval += textwrap.dedent('''
        </log>
        ''')
        return retval.split('\n')

    def read_svn_log(svnlog):
        """Interprets a string as a pandas.DataFrame returned by get_svn_log.

        Leverages pandas.read_csv. Also fixes the type of 'date' column to be
        a datet/time in UTC tz.

        """
        df = pd.read_csv(io.StringIO(svnlog), dtype='object')
        df['date'] = pd.to_datetime(df['date'], utc=True)
        return df

    def setUp(self):
        add_data_frame_equality_func(self)
        self.report = cm.BaseReport('.')

    def test_get_files(self):
        """get_files return the list of files."""
        actual = self.report.get_files('*.py').\
                 sort_values(by='path').reset_index(drop=True)
        expected = pd.read_csv(io.StringIO(textwrap.dedent('''
        path
        codemetrics.py
        setup.py
        tests.py
        ''')))
        self.assertEqual(actual, expected)

    @mock.patch('codemetrics._run', side_effect=[
        ['Relative URL: ^/project/trunk'],
        get_svn_log()], autospec=True)
    def test_get_log(self, call):
        """Simple svn call returns pandas.DataFrame."""
        df = self.report.get_log()
        call.assert_called_with('svn log --xml -v .')
        expected = BaseReportTest.read_svn_log(textwrap.dedent('''
        revision,author,date,textmods,kind,action,propmods,path,message
        1018,jlecomte,2018-02-24T11:14:11.000000Z,true,file,M,false,stats.py,Added joblib to requirements.txt
        1018,jlecomte,2018-02-24T11:14:11.000000Z,true,file,M,false,requirements.txt,Added joblib to requirements.txt
        '''))
        self.assertEqual(df, expected)

    @mock.patch('codemetrics.get_now', autospec=True,
                return_value = dt.datetime(2018, 2, 28))
    @mock.patch('tqdm.tqdm', autospec=True)
    @mock.patch('codemetrics._run', side_effect=[
        ['Relative URL: ^/project/trunk'],
        get_svn_log(dates=[dt.date(2018, 2, 25),
                           dt.date(2018, 2, 27),
                           dt.date(2018, 2, 28)])], autospec=True)
    def test_get_log_with_progress(self, call, tqdm_, today_):
        """Simple svn call returns pandas.DataFrame."""
        self.report.after = dt.datetime(2018, 2, 24)
        self.report.progress_bar = tqdm.tqdm()
        _ = self.report.get_log()
        call.assert_called_with('svn log --xml -v -r {2018-02-24}:HEAD .')
        self.assertEqual(self.report.progress_bar.total, 4)
        calls = [mock.call(1), mock.call(2)]
        self.report.progress_bar.update.assert_has_calls(calls)
        self.report.progress_bar.close.assert_called_once()

    @mock.patch('codemetrics._run', side_effect=[
        ['Relative URL: ^/project/trunk'],
        textwrap.dedent('''
    <?xml version="1.0" encoding="UTF-8"?>
    <log>
    <logentry revision="1018">
    <author>jlecomte</author>
    <date>2018-02-24T11:14:11.000000Z</date>
    <paths><path kind="file" action="M">/project/trunk/stats.py</path></paths>
    <msg/>
    </logentry>
    </log>
    ''').split('\n')], autospec=True)
    def test_get_log_no_msg(self, call):
        """Simple svn call returns pandas.DataFrame."""
        expected = BaseReportTest.read_svn_log(textwrap.dedent('''
        revision,author,date,textmods,kind,action,propmods,path,message
        1018,jlecomte,2018-02-24T11:14:11.000000Z,,file,M,,stats.py,
        '''))
        df = self.report.get_log()
        call.assert_called_with('svn log --xml -v .')
        self.assertEqual(df, expected)

    @mock.patch('codemetrics._run', side_effect=[
        ['Relative URL: ^/project/trunk'],
        textwrap.dedent('''
    <?xml version="1.0" encoding="UTF-8"?>
    <log>
    <logentry revision="1018">
    <date>2018-02-24T11:14:11.000000Z</date>
    <paths><path kind="file" action="M">/project/trunk/stats.py</path></paths>
    <msg>not much</msg>
    </logentry>
    </log>
    ''').split('\n')], autospec=True)
    def test_get_log_no_author(self, call):
        """Simple svn call returns pandas.DataFrame."""
        expected = BaseReportTest.read_svn_log(textwrap.dedent('''
        revision,author,date,textmods,kind,action,propmods,path,message
        1018,,2018-02-24T11:14:11.000000Z,,file,M,,stats.py,not much
        '''))
        df = self.report.get_log()
        call.assert_called_with('svn log --xml -v .')
        self.assertEqual(df, expected)

    @mock.patch('codemetrics._run', autospec=True)
    def test_program_name(self, run):
        """Test program_name taken into account."""
        self.report.svn_program='svn-1.7'
        self.report.get_log()
        run.assert_called_with('svn-1.7 log --xml -v .')

    @mock.patch('codemetrics._run', return_value=textwrap.dedent('''\
    language,filename,blank,comment,code,"github.com/AlDanial/cloc..."
    Python,codemetrics.py,55,50,130
    Python,tests.py,29,92,109
    Python,setup.py,4,2,30
    ''').split('\n'), autospec=True)
    def test_get_cloc(self, run):
        """Test handling of get_cloc output."""
        actual = self.report.get_cloc()
        run.assert_called_with('cloc --csv --by-file .')
        expected = pd.read_csv(io.StringIO(textwrap.dedent('''
        language,path,blank,comment,code
        Python,codemetrics.py,55,50,130
        Python,tests.py,29,92,109
        Python,setup.py,4,2,30
        ''')))
        self.assertEqual(actual, expected)


class RepositoryTestCase(unittest.TestCase):
    """Given a repository of a few records."""

    def get_log_df():
        return pd.read_csv(io.StringIO(textwrap.dedent('''
        revision,author,date,textmods,kind,action,propmods,path,message
        1016,jlecomte,2018-02-26T10:28:00Z,true,file,M,false,stats.py,modified again
        1018,jlecomte,2018-02-24T11:14:11Z,true,file,M,false,stats.py,modified
        1018,jlecomte,2018-02-24T11:14:11Z,true,file,M,false,requirements.txt,modified''')))

    def get_files_df():
        return pd.read_csv(io.StringIO(textwrap.dedent('''
        path
        stats.py
        requirements.txt
        ''')))

    def get_cloc_df():
        return pd.read_csv(io.StringIO(textwrap.dedent('''
        language,path,blank,comment,code,"github.com/AlDanial/cloc"
        Python,stats.py,28,84,100
        Unknown,requirements.txt,0,0,3
        ''')))

    def setUp(self):
        add_data_frame_equality_func(self)
        self.path = '.'


class AgeReportTestCase(RepositoryTestCase):
    """Extends the repository scaffholding with an age report."""

    def setUp(self):
        super().setUp()
        self.report = cm.AgeReport(self.path)

    @mock.patch('codemetrics.BaseReport.get_log', autospec=True,
                return_value=RepositoryTestCase.get_log_df())
    def test_age_report_uses_get_log(self, get_log):
        """The age report uses get_log by default to get the raw SCM data."""
        self.report.generate()
        get_log.assert_called_with(self.report)

    @mock.patch('codemetrics.BaseReport.get_log', autospec=True,
                return_value=RepositoryTestCase.get_log_df())
    @mock.patch('codemetrics.BaseReport.get_files', autospec=True,
                return_value=RepositoryTestCase.get_files_df())
    def test_age_report_uses_get_files(self, get_files, get_logs):
        """The age report uses get_files by default to get the list of files."""
        self.report.generate()
        get_files.assert_called_with(self.report)

    @mock.patch('codemetrics.get_now', autospec=True,
                return_value=pd.to_datetime(dt.datetime(2018, 2, 28), utc=True))
    def test_age_report_with_custom_raw_data(self, now):
        """The age report generates data based on the SCM log data"""
        actual = self.report.generate(RepositoryTestCase.get_log_df())
        expected = pd.read_csv(io.StringIO(textwrap.dedent('''
        path,kind,age
        requirements.txt,file,3.531817
        ''')))
        self.assertEqual(actual, expected)

    @mock.patch('codemetrics.get_now', autospec=True,
                return_value=pd.to_datetime(dt.datetime(2018, 2, 28), utc=True))
    def test_age_report_skip_deleted_files(self, get_now):
        """missing file today should not be part of the age report."""
        files_df = pd.read_csv(io.StringIO(textwrap.dedent('''
        path
        requirements.txt
        ''')))
        actual = self.report.generate(RepositoryTestCase.get_log_df(), files_df)
        expected = pd.read_csv(io.StringIO(textwrap.dedent('''
        path,kind,age
        requirements.txt,file,3.531817
        ''')))
        self.assertEqual(actual, expected)

    @mock.patch('codemetrics.BaseReport.get_files', autospec=True,
                return_value=RepositoryTestCase.get_files_df())
    @mock.patch('codemetrics._run', side_effect=[
        ['Relative URL: ^/project/trunk'],
        textwrap.dedent('''
    <?xml version="1.0" encoding="UTF-8"?>
    <log>
    <logentry revision="1018">
    <date>2018-02-26T10:28:00Z</date>
    <paths><path kind="file" action="M">/project/trunk/stats.py</path></paths>
    <msg>not much</msg>
    </logentry>
    </log>
    ''').split('\n')], autospec=True)
    @mock.patch('codemetrics.get_now', autospec=True,
                return_value=pd.to_datetime(dt.datetime(2018, 2, 28), utc=True))
    def test_age_report_with_time_limit(self, now, run, get_files):
        """Generate age by file report with a time limit on how far to go."""
        self.report.after = dt.datetime(2018, 2, 26)
        actual = self.report.generate()
        expected = pd.read_csv(io.StringIO(textwrap.dedent('''
        path,kind,age
        stats.py,file,1.563889
        ''')))
        run.assert_called_with('svn log --xml -v -r {2018-02-26}:HEAD .')
        now.assert_called_with()
        get_files.assert_called_with(self.report)
        self.assertEqual(actual, expected)

    @mock.patch('codemetrics.get_now', autospec=True,
                return_value=pd.to_datetime(dt.datetime(2018, 2, 28), utc=True))
    @mock.patch('codemetrics.BaseReport.get_files', autospec=True,
                return_value=RepositoryTestCase.get_files_df())
    @mock.patch('codemetrics.BaseReport.get_log', autospec=True,
                return_value=RepositoryTestCase.get_log_df())
    def test_age_report_enriched_with_component(self, get_log, get_files,
                                                get_now):
        """Allow one to enrich the log before generating the age report."""
        log = self.report.collect()
        log['component'] = 'blah'
        actual = self.report.generate(log)
        expected = pd.read_csv(io.StringIO(textwrap.dedent('''
        path,kind,component,age
        requirements.txt,file,blah,3.531817
        stats.py,file,blah,1.563889
        ''')))
        self.assertEqual(actual, expected)


class HotSpotReportTestCase(RepositoryTestCase):
    """Extends the repository scaffholding with a hot spot report."""

    def setUp(self):
        super().setUp()
        self.report = cm.HotSpotReport(self.path)

    @mock.patch('codemetrics.BaseReport.get_log', autospec=True,
                return_value=RepositoryTestCase.get_log_df())
    @mock.patch('codemetrics.BaseReport.get_cloc', autospec=True,
                return_value=RepositoryTestCase.get_cloc_df())
    def test_hot_spot_report(self, get_cloc, get_log):
        """Generate a report to find hot spots."""
        self.report.after = dt.datetime(2018, 2, 26)
        actual = self.report.generate()
        get_cloc.assert_called_with(self.report)
        get_log.assert_called_with(self.report)
        expected = pd.read_csv(io.StringIO(textwrap.dedent('''
        path,complexity,changes,score
        stats.py,100,2,2.0
        requirements.txt,3,1,0.0
        ''')))
        self.assertEqual(actual, expected)


if __name__ == '__main__':
    unittest.main()
