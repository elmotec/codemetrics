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


class SubversionTest(unittest.TestCase):
    """Given svn command in $PATH environment variable."""

    def setUp(self):
        add_data_frame_equality_func(self)
        self.report = cm.BaseReport('.')

    @mock.patch('codemetrics._run', return_value=textwrap.dedent('''
    <?xml version="1.0" encoding="UTF-8"?>
    <log>
    <logentry revision="1018">
    <author>jlecomte</author>
    <date>2018-02-24T11:14:11.371061Z</date>
    <paths>
    <path text-mods="true" kind="file" action="M"
       prop-mods="false">gstats.py</path>
    <path text-mods="true" kind="file" action="M"
       prop-mods="false">grequirements.txt</path>
    </paths>
    <msg>Added joblib to requirements.txt</msg>
    </logentry>
    </log>
    ''').split('\n'), spec=True)
    def test_get_log(self, call):
        """Simple svn call returns pandas.DataFrame."""
        expected = pd.read_csv(io.StringIO(textwrap.dedent('''
        revision,author,date,textmods,kind,action,propmods,path,message
        1018,jlecomte,2018-02-24T11:14:11.371061Z,true,file,M,false,gstats.py,Added joblib to requirements.txt
        1018,jlecomte,2018-02-24T11:14:11.371061Z,true,file,M,false,grequirements.txt,Added joblib to requirements.txt
        ''')), dtype='object')
        df = self.report.get_log()
        call.assert_called_with('svn log --xml -v .')
        self.assertEqual(df, expected)

    @mock.patch('codemetrics._run', return_value=textwrap.dedent('''
    <?xml version="1.0" encoding="UTF-8"?>
    <log>
    <logentry revision="1018">
    <author>jlecomte</author>
    <date>2018-02-24T11:14:11.371061Z</date>
    <paths> <path kind="file" action="M">gstats.py</path> </paths>
    <msg/>
    </logentry>
    </log>
    ''').split('\n'), spec=True)
    def test_get_log_no_msg(self, call):
        """Simple svn call returns pandas.DataFrame."""
        expected = pd.read_csv(io.StringIO(textwrap.dedent('''
        revision,author,date,textmods,kind,action,propmods,path,message
        1018,jlecomte,2018-02-24T11:14:11.371061Z,,file,M,,gstats.py,
        ''')), dtype='object')
        df = self.report.get_log()
        call.assert_called_with('svn log --xml -v .')
        self.assertEqual(df, expected)

    @mock.patch('codemetrics._run', return_value=textwrap.dedent('''
    <?xml version="1.0" encoding="UTF-8"?>
    <log>
    <logentry revision="1018">
    <date>2018-02-24T11:14:11.371061Z</date>
    <paths> <path kind="file" action="M">stats.py</path> </paths>
    <msg>not much</msg>
    </logentry>
    </log>
    ''').split('\n'), spec=True)
    def test_get_log_no_author(self, call):
        """Simple svn call returns pandas.DataFrame."""
        expected = pd.read_csv(io.StringIO(textwrap.dedent('''
        revision,author,date,textmods,kind,action,propmods,path,message
        1018,,2018-02-24T11:14:11.371061Z,,file,M,,stats.py,not much
        ''')), dtype='object')
        df = self.report.get_log()
        call.assert_called_with('svn log --xml -v .')
        self.assertEqual(df, expected)


class RepositoryTestCase(unittest.TestCase):
    """Given a repository of a few records."""

    path = '.'
    log_df = pd.read_csv(io.StringIO(textwrap.dedent('''
    revision,author,date,textmods,kind,action,propmods,path,message
    1016,jlecomte,2018-02-26T10:28:00Z,true,file,M,false,stats.py,modified again
    1018,jlecomte,2018-02-24T11:14:11Z,true,file,M,false,stats.py,modified
    1018,jlecomte,2018-02-24T11:14:11Z,true,file,M,false,requirements.txt,modified''')))

    def setUp(self):
        add_data_frame_equality_func(self)

    @mock.patch('codemetrics.get_now', spec=True,
                return_value=pd.to_datetime(dt.datetime(2018, 2, 28)))
    @mock.patch('codemetrics.BaseReport.get_log', spec=True, return_value=log_df)
    def test_age_report(self, get_log, now):
        """Generate age by file report."""
        report = cm.AgeReport(self.path)
        report.generate()
        expected = pd.read_csv(io.StringIO(textwrap.dedent('''
        path,kind,age
        requirements.txt,file,3.531817
        stats.py,file,1.563889
        ''')))
        get_log.assert_called()
        now.assert_called_with()
        self.assertEqual(report.data, expected)

    @mock.patch('codemetrics._run', return_value=textwrap.dedent('''
    <?xml version="1.0" encoding="UTF-8"?>
    <log>
    <logentry revision="1018">
    <date>2018-02-26T10:28:00Z</date>
    <paths> <path kind="file" action="M">stats.py</path> </paths>
    <msg>not much</msg>
    </logentry>
    </log>
    ''').split('\n'), spec=True)
    @mock.patch('codemetrics.get_now', spec=True,
                return_value=pd.to_datetime(dt.datetime(2018, 2, 28)))
    def test_age_report_with_time_limit(self, now, run):
        """Generate age by file report with a time limit on how far to go."""
        report = cm.AgeReport(self.path, after=dt.datetime(2018, 2, 26))
        report.generate()
        expected = pd.read_csv(io.StringIO(textwrap.dedent('''
        path,kind,age
        stats.py,file,1.563889
        ''')))
        run.assert_called_with('svn log --xml -v -r {2018-02-26}:HEAD .')
        now.assert_called_with()
        self.assertEqual(report.data, expected)


if __name__ == '__main__':
    unittest.main()
