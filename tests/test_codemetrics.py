#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `codemetrics` package."""


from codemetrics import cli
import datetime as dt
import io
import textwrap
import unittest
import unittest.mock as mock
import pathlib

import pandas as pd
import pandas.testing as pdt
import tqdm
from click.testing import CliRunner

import codemetrics as cm
import codemetrics.pbar
import codemetrics.svn
import codemetrics.loc


class TestCodemetrics(unittest.TestCase):
    """Tests for `codemetrics` package."""

    def setUp(self):
        """Set up test fixtures, if any."""

    def tearDown(self):
        """Tear down test fixtures, if any."""

    def test_000_something(self):
        """Test something."""
        pass

    def test_command_line_interface(self):
        """Test the CLI."""
        runner = CliRunner()
        result = runner.invoke(cli.main)
        assert result.exit_code == 0
        #assert 'codemetrics.cli.main' in result.output
        help_result = runner.invoke(cli.main, ['--help'])
        assert help_result.exit_code == 0
        assert '--help  Show this message and exit.' in help_result.output


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
        <author>elmotec</author>
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


class ProgressBarAdapterTest(unittest.TestCase):
    """Test ProgressBarAdapter"""

    def setUp(self):
        pass

    @mock.patch('codemetrics.get_now', autospec=True,
                return_value = dt.datetime(2018, 2, 13))
    @mock.patch('tqdm.tqdm', autospec=True)
    def test_initialization(self, tqdm_, get_now):
        after = dt.datetime(2018, 2, 1)
        with cm.pbar.ProgressBarAdapter(tqdm.tqdm(), after=after) as pb:
            pb.update(pb.today - dt.timedelta(3))
            pb.update(pb.today - dt.timedelta(1))
        expected = [mock.call(9), mock.call(2), mock.call(1)]
        self.assertEqual(tqdm_().update.mock_calls, expected)


class SubversionTestCase(unittest.TestCase):
    """Given a BaseReport instance."""

    def read_svn_log(svnlog):
        """Interprets a string as a pandas.DataFrame returned by get_svn_log.

        Leverages pandas.read_csv. Also fixes the type of 'date' column to be
        a datet/time in UTC tz.

        """
        df = pd.read_csv(io.StringIO(svnlog), dtype={
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
        add_data_frame_equality_func(self)

    @mock.patch('pathlib.Path.glob', autospec=True,
                side_effect=[['first.py', 'second.py']])
    def test_get_files(self, glob):
        """get_files return the list of files."""
        actual = cm.internals.get_files(pattern='*.py')
        glob.assert_called_with(pathlib.WindowsPath('.'), '*.py')
        actual = actual.sort_values(by='path').reset_index(drop=True)
        expected = pd.read_csv(io.StringIO(textwrap.dedent('''
        path
        first.py
        second.py
        ''')))
        self.assertEqual(actual, expected)

    @mock.patch('codemetrics.internals._run',
                side_effect=[['Relative URL: ^/project/trunk'],
                             get_svn_log()], autospec=True)
    def test_get_log(self, call):
        """Simple svn call returns pandas.DataFrame."""
        df = cm.svn.get_svn_log('.')
        call.assert_called_with('svn log --xml -v .')
        expected = SubversionTestCase.read_svn_log(textwrap.dedent('''
        revision,author,date,textmods,kind,action,propmods,path,message
        1018,elmotec,2018-02-24T11:14:11.000000Z,true,file,M,false,stats.py,Added joblib to requirements.txt
        1018,elmotec,2018-02-24T11:14:11.000000Z,true,file,M,false,requirements.txt,Added joblib to requirements.txt
        '''))
        self.assertEqual(df, expected)

    @mock.patch('codemetrics.internals._run',
                side_effect=[['Relative URL: ^/project/trunk'],
                             get_svn_log()], autospec=True)
    def test_fails_with_pbar_without_after(self, call):
        """Check error when passing a progress bar without after parameter."""
        with self.assertRaises(ValueError) as err:
            pbar = tqdm.tqdm()
            df = cm.svn.get_svn_log('.', progress_bar=pbar)
        self.assertIn('progress_bar requires', str(err.exception))

    @mock.patch('codemetrics.get_now', autospec=True,
                return_value = dt.datetime(2018, 2, 28))
    @mock.patch('tqdm.tqdm', autospec=True)
    @mock.patch('codemetrics.internals._run', side_effect=[
        ['Relative URL: ^/project/trunk'],
        get_svn_log(dates=[dt.date(2018, 2, 25),
                           dt.date(2018, 2, 27),
                           dt.date(2018, 2, 28)])], autospec=True)
    def test_get_log_with_progress(self, call, tqdm_, today_):
        """Simple svn call returns pandas.DataFrame."""
        pb = tqdm.tqdm()
        _ = cm.svn.get_svn_log(after=dt.datetime(2018, 2, 24), progress_bar=pb)
        call.assert_called_with('svn log --xml -v -r {2018-02-24}:HEAD .')
        self.assertEqual(pb.total, 4)
        calls = [mock.call(1), mock.call(2)]
        pb.update.assert_has_calls(calls)
        pb.close.assert_called_once()

    @mock.patch('codemetrics.internals._run', side_effect=[
        ['Relative URL: ^/project/trunk'],
        textwrap.dedent('''
    <?xml version="1.0" encoding="UTF-8"?>
    <log>
    <logentry revision="1018">
    <author>elmotec</author>
    <date>2018-02-24T11:14:11.000000Z</date>
    <paths><path kind="file" action="M">/project/trunk/stats.py</path></paths>
    <msg/>
    </logentry>
    </log>
    ''').split('\n')], autospec=True)
    def test_get_log_no_msg(self, call):
        """Simple svn call returns pandas.DataFrame."""
        df = cm.svn.get_svn_log()
        call.assert_called_with('svn log --xml -v .')
        expected = SubversionTestCase.read_svn_log(textwrap.dedent('''
        revision,author,date,textmods,kind,action,propmods,path,message
        1018,elmotec,2018-02-24T11:14:11.000000Z,None,file,M,None,stats.py,None
        '''))
        expected.replace({'None': None}, inplace=True)
        self.assertEqual(df, expected)

    @mock.patch('codemetrics.internals._run', side_effect=[
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
        expected = SubversionTestCase.read_svn_log(textwrap.dedent('''
        revision,author,date,textmods,kind,action,propmods,path,message
        1018,,2018-02-24T11:14:11.000000Z,,file,M,,stats.py,not much
        '''))
        df = cm.svn.get_svn_log()
        call.assert_called_with('svn log --xml -v .')
        self.assertEqual(df, expected)

    @mock.patch('codemetrics.internals._run', autospec=True)
    def test_program_name(self, run):
        """Test program_name taken into account."""
        cm.svn.get_svn_log(svn_program='svn-1.7')
        run.assert_called_with('svn-1.7 log --xml -v .')

    @mock.patch('codemetrics.internals._run', return_value=textwrap.dedent('''\
    language,filename,blank,comment,code,"github.com/AlDanial/cloc..."
    Python,internals.py,55,50,130
    Python,tests.py,29,92,109
    Python,setup.py,4,2,30
    ''').split('\n'), autospec=True)
    def test_get_cloc(self, run):
        """Test handling of get_cloc output."""
        actual = cm.loc.get_cloc()
        run.assert_called_with('cloc --csv --by-file .')
        expected = pd.read_csv(io.StringIO(textwrap.dedent('''
        language,path,blank,comment,code
        Python,internals.py,55,50,130
        Python,tests.py,29,92,109
        Python,setup.py,4,2,30
        ''')))
        self.assertEqual(actual, expected)


class SimpleRepositoryFixture(unittest.TestCase):
    """Given a repository of a few records."""

    @staticmethod
    def  get_log_df():
        return pd.read_csv(io.StringIO(textwrap.dedent('''
        revision,author,date,textmods,kind,action,propmods,path,message
        1016,elmotec,2018-02-26T10:28:00Z,true,file,M,false,stats.py,modified again
        1018,elmotec,2018-02-24T11:14:11Z,true,file,M,false,stats.py,modified
        1018,elmotec,2018-02-24T11:14:11Z,true,file,M,false,requirements.txt,modified''')),
                           parse_dates=['date'])

    @staticmethod
    def get_files_df():
        return pd.read_csv(io.StringIO(textwrap.dedent('''
        path
        stats.py
        requirements.txt
        ''')))

    @staticmethod
    def get_loc_df():
        return pd.read_csv(io.StringIO(textwrap.dedent('''
        language,path,blank,comment,code
        Python,stats.py,28,84,100
        Unknown,requirements.txt,0,0,3
        ''')))

    def setUp(self):
        add_data_frame_equality_func(self)
        self.log = self.get_log_df()
        self.loc = self.get_loc_df()
        self.files = self.get_files_df()


class RepositoryTestCase(SimpleRepositoryFixture):
    """Test non-report functionalities."""

    def test_get_mass_changes(self):
        """Retrieve mass changes easily."""
        log = SimpleRepositoryFixture.get_log_df()
        threshold = int(log[['revision', 'path']].groupby('revision').
                        count().quantile(.5))
        self.assertEqual(threshold, 1)
        actual = cm.get_mass_changesets(log, threshold)
        expected = pd.read_csv(io.StringIO(textwrap.dedent('''
        revision,path_count,message,author
        1018,2,modified,elmotec
        ''')))
        self.assertEqual(actual, expected)


class AgeReportTestCase(SimpleRepositoryFixture):
    """Extends the repository scaffholding with an age report."""

    def setUp(self):
        super().setUp()

    @mock.patch('codemetrics.get_now', autospec=True,
                return_value=pd.to_datetime(dt.datetime(2018, 2, 28), utc=True))
    def test_ages(self, now):
        """The age report generates data based on the SCM log data"""
        actual = cm.ages(self.log)[['path', 'kind', 'age']]
        expected = pd.read_csv(io.StringIO(textwrap.dedent('''
        path,kind,age
        requirements.txt,file,3.531817
        stats.py,file,1.563889
        ''')))
        self.assertEqual(actual, expected)

    @mock.patch('codemetrics.get_now', autospec=True,
                return_value=pd.to_datetime(dt.datetime(2018, 2, 28), utc=True))
    def test_age_report_enriched_with_component(self, get_now):
        """Allow one to enrich the log before generating the age report."""
        log = self.log
        log['component'] = 'blah'
        actual = cm.ages(log, keys=['path', 'component'])
        expected = pd.read_csv(io.StringIO(textwrap.dedent('''
        path,component,age
        requirements.txt,blah,3.531817
        stats.py,blah,1.563889
        ''')))
        self.assertEqual(actual, expected)

    @mock.patch('codemetrics.get_now', autospec=True,
                return_value=pd.to_datetime(dt.datetime(2018, 2, 28), utc=True))
    def test_key_parameter(self, get_now):
        """Ignore files_df if nothing in it is relevant"""
        self.log['component'] = 'kernel'
        actual = cm.ages(self.log, keys=['component', 'kind'])
        expected = pd.read_csv(io.StringIO(textwrap.dedent('''
        component,kind,age
        kernel,file,1.563889''')))
        self.assertEqual(actual, expected)



class HotSpotReportTestCase(SimpleRepositoryFixture):
    """Extends the repository scaffholding with a hot spot report."""

    def setUp(self):
        super().setUp()

    def test_hot_spot_report(self):
        """Generate a report to find hot spots."""
        after = dt.datetime(2018, 2, 26)
        log = self.log.loc[self.log['date'] >= after, :]
        actual = cm.hot_spots(log, self.loc)
        expected = pd.read_csv(io.StringIO(textwrap.dedent('''
        language,path,blank,comment,complexity,changes,complexity_score,changes_score,score
        Python,stats.py,28,84,100,1.0,1.0,1.0,2.0
        Unknown,requirements.txt,0,0,3,0,0.0,0.0,0.0
        ''')))
        expected[['complexity_score', 'changes_score', 'score']] = \
            expected[['complexity_score', 'changes_score', 'score']].astype('float64')
        self.assertEqual(actual, expected)

    def test_hot_spot_with_custom_change_metric(self):
        """Generate report with a different change metric than revision."""
        self.log['day'] = dt.date(2018, 2, 24)  # force all rows to the same date.
        actual = cm.hot_spots(self.log, self.loc, count_one_change_per=['day'])
        expected = pd.read_csv(io.StringIO(textwrap.dedent('''
        language,path,blank,comment,complexity,changes,complexity_score,changes_score,score
        Python,stats.py,28,84,100,1,1.0,0.0,1.0
        Unknown,requirements.txt,0,0,3,1,0.0,0.0,0.0
        ''')))
        self.assertEqual(actual, expected)


class CoChangeTestCase(SimpleRepositoryFixture):
    """CoChangeReport test case."""

    def setUp(self):
        super().setUp()

    def test_co_change_report(self):
        """Simple CoChangeReport usage."""
        actual = cm.co_changes(log=SimpleRepositoryFixture.get_log_df())
        expected = pd.read_csv(io.StringIO(textwrap.dedent('''
        primary,secondary,revision_cochanges,revision_changes,coupling
        requirements.txt,stats.py,1,1,1.0
        stats.py,requirements.txt,1,2,0.5
        ''')))
        self.assertEqual(actual, expected)

    def test_co_change_report_on_day(self):
        """Check handling of on with the date as a day in argument."""
        log = SimpleRepositoryFixture.get_log_df()
        # Same day to force results different from test_co_change_report.
        log['day'] = pd.to_datetime('2018-02-24')
        actual = cm.co_changes(log=log, on='day')
        expected = pd.read_csv(io.StringIO(textwrap.dedent('''
        primary,secondary,day_cochanges,day_changes,coupling
        requirements.txt,stats.py,1,1,1.0
        stats.py,requirements.txt,1,1,1.0
        ''')))
        self.assertEqual(actual, expected)


if __name__ == '__main__':
    unittest.main()
