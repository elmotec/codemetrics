#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `codemetrics` package."""

import datetime as dt
import io
import textwrap
import unittest
import unittest.mock as mock

import pandas as pd
from click.testing import CliRunner

import codemetrics as cm
from codemetrics import cli
from tests.utils import add_data_frame_equality_func


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
        # assert 'codemetrics.cli.main' in result.output
        help_result = runner.invoke(cli.main, ['--help'])
        assert help_result.exit_code == 0
        assert '--help  Show this message and exit.' in help_result.output


class SimpleRepositoryFixture(unittest.TestCase):
    """Given a repository of a few records."""

    @staticmethod
    def get_log_df():
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
    """Test non-report features."""

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
    """Extends the repository scaffolding with an age report."""

    def setUp(self):
        super().setUp()

    @mock.patch('codemetrics.internals.get_now', autospec=True,
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

    @mock.patch('codemetrics.internals.get_now', autospec=True,
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

    @mock.patch('codemetrics.internals.get_now', autospec=True,
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
    """Extends the repository scaffolding with a hot spot report."""

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
            expected[['complexity_score', 'changes_score', 'score']].astype(
                'float64')
        self.assertEqual(actual, expected)

    def test_hot_spot_with_custom_change_metric(self):
        """Generate report with a different change metric than revision."""
        self.log['day'] = dt.date(2018, 2,
                                  24)  # force all rows to the same date.
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
