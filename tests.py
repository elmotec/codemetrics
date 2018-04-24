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

import codemetrics as cm


class CommandTest(unittest.TestCase):
    """Given a console based tool."""

    def test_can_run(self):
        """wrapper call to the command return output."""
        output = cm._run('echo Hello world!')
        self.assertEqual(output, ['Hello world!', ''])

    def test_failure_throws(self):
        """wrapper call will throw on error."""
        with self.assertRaisesRegex(subprocess.CalledProcessError,
                                    "Command 'badcall' returned non-zero.*"):
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


class BaseReportTest(unittest.TestCase):
    """Given a BaseReport instance."""

    def setUp(self):
        add_data_frame_equality_func(self)
        self.report = cm.BaseReport('.')

    @mock.patch('codemetrics._run', side_effect=[
        ['Relative URL: ^/project/trunk'],
        textwrap.dedent('''
    <?xml version="1.0" encoding="UTF-8"?>
    <log>
    <logentry revision="1018">
    <author>jlecomte</author>
    <date>2018-02-24T11:14:11.371061Z</date>
    <paths>
    <path text-mods="true" kind="file" action="M"
       prop-mods="false">/project/trunk/stats.py</path>
    <path text-mods="true" kind="file" action="M"
       prop-mods="false">/project/trunk/requirements.txt</path>
    </paths>
    <msg>Added joblib to requirements.txt</msg>
    </logentry>
    </log>
    ''').split('\n')], autospec=True)
    def test_get_log(self, call):
        """Simple svn call returns pandas.DataFrame."""
        expected = pd.read_csv(io.StringIO(textwrap.dedent('''
        revision,author,date,textmods,kind,action,propmods,path,message
        1018,jlecomte,2018-02-24T11:14:11.371061Z,true,file,M,false,stats.py,Added joblib to requirements.txt
        1018,jlecomte,2018-02-24T11:14:11.371061Z,true,file,M,false,requirements.txt,Added joblib to requirements.txt
        ''')), dtype='object')
        df = self.report.get_log()
        call.assert_called_with('svn log --xml -v .')
        self.assertEqual(df, expected)

    @mock.patch('codemetrics._run', side_effect=[
        ['Relative URL: ^/project/trunk'],
        textwrap.dedent('''
    <?xml version="1.0" encoding="UTF-8"?>
    <log>
    <logentry revision="1018">
    <author>jlecomte</author>
    <date>2018-02-24T11:14:11.371061Z</date>
    <paths><path kind="file" action="M">/project/trunk/stats.py</path></paths>
    <msg/>
    </logentry>
    </log>
    ''').split('\n')], autospec=True)
    def test_get_log_no_msg(self, call):
        """Simple svn call returns pandas.DataFrame."""
        expected = pd.read_csv(io.StringIO(textwrap.dedent('''
        revision,author,date,textmods,kind,action,propmods,path,message
        1018,jlecomte,2018-02-24T11:14:11.371061Z,,file,M,,stats.py,
        ''')), dtype='object')
        df = self.report.get_log()
        call.assert_called_with('svn log --xml -v .')
        self.assertEqual(df, expected)

    @mock.patch('codemetrics._run', side_effect=[
        ['Relative URL: ^/project/trunk'],
        textwrap.dedent('''
    <?xml version="1.0" encoding="UTF-8"?>
    <log>
    <logentry revision="1018">
    <date>2018-02-24T11:14:11.371061Z</date>
    <paths><path kind="file" action="M">/project/trunk/stats.py</path></paths>
    <msg>not much</msg>
    </logentry>
    </log>
    ''').split('\n')], autospec=True)
    def test_get_log_no_author(self, call):
        """Simple svn call returns pandas.DataFrame."""
        expected = pd.read_csv(io.StringIO(textwrap.dedent('''
        revision,author,date,textmods,kind,action,propmods,path,message
        1018,,2018-02-24T11:14:11.371061Z,,file,M,,stats.py,not much
        ''')), dtype='object')
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
        language,filename,blank,comment,code
        Python,codemetrics.py,55,50,130
        Python,tests.py,29,92,109
        Python,setup.py,4,2,30
        ''')))
        self.assertEqual(actual, expected)


class RepositoryTestCase(unittest.TestCase):
    """Given a repository of a few records."""

    path = '.'
    log_df = pd.read_csv(io.StringIO(textwrap.dedent('''
    revision,author,date,textmods,kind,action,propmods,path,message
    1016,jlecomte,2018-02-26T10:28:00Z,true,file,M,false,.\\stats.py,modified again
    1018,jlecomte,2018-02-24T11:14:11Z,true,file,M,false,.\\stats.py,modified
    1018,jlecomte,2018-02-24T11:14:11Z,true,file,M,false,.\\requirements.txt,modified''')))
    cloc_df = pd.read_csv(io.StringIO(textwrap.dedent('''
    language,filename,blank,comment,code,"github.com/AlDanial/cloc"
    Python,.\\stats.py,28,84,100
    Unknown,.\\requirements.txt,0,0,3
    ''')))

    def setUp(self):
        add_data_frame_equality_func(self)

    @mock.patch('codemetrics.get_now', autospec=True,
                return_value=pd.to_datetime(dt.datetime(2018, 2, 28)))
    @mock.patch('codemetrics.BaseReport.get_log', autospec=True,
                return_value=log_df)
    def test_age_report_raw_data(self, get_log, now):
        """Generate age by file report."""
        report = cm.AgeReport(self.path)
        report.generate()
        get_log.assert_called()
        now.assert_called_with()
        report.raw_data = self.log_df

    @mock.patch('codemetrics.get_now', autospec=True,
                return_value=pd.to_datetime(dt.datetime(2018, 2, 28)))
    def test_age_report_with_custom_raw_data(self, now):
        """Generate age by file report using specified raw_data."""
        report = cm.AgeReport(self.path)
        actual = report.generate({'log': self.log_df})
        expected = pd.read_csv(io.StringIO(textwrap.dedent('''
        path,kind,age
        .\\requirements.txt,file,3.531817
        .\\stats.py,file,1.563889
        ''')))
        now.assert_called_with()
        self.assertEqual(actual, expected)

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
                return_value=pd.to_datetime(dt.datetime(2018, 2, 28)))
    def test_age_report_with_time_limit(self, now, run):
        """Generate age by file report with a time limit on how far to go."""
        report = cm.AgeReport(self.path, after=dt.datetime(2018, 2, 26))
        actual = report.generate()
        expected = pd.read_csv(io.StringIO(textwrap.dedent('''
        path,kind,age
        stats.py,file,1.563889
        ''')))
        run.assert_called_with('svn log --xml -v -r {2018-02-26}:HEAD .')
        now.assert_called_with()
        self.assertEqual(actual, expected)

    @mock.patch('codemetrics.BaseReport.get_log', autospec=True,
                return_value=log_df)
    @mock.patch('codemetrics.BaseReport.get_cloc', autospec=True,
                return_value=cloc_df)
    def test_hot_spot_report(self, get_cloc, get_log):
        """Generate a report to find hot spots."""
        report = cm.HotSpotReport(self.path, after=dt.datetime(2018, 2, 26))
        actual = report.generate()
        get_cloc.assert_called_with(report)
        get_log.assert_called_with(report)
        expected = pd.read_csv(io.StringIO(textwrap.dedent('''
        filename,complexity,changes
        .\\stats.py,100,2
        .\\requirements.txt,3,1
        ''')))
        self.assertEqual(actual, expected)


if __name__ == '__main__':
    unittest.main()
