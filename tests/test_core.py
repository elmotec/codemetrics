#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `codemetrics` package."""

import datetime as dt
import io
import textwrap
import unittest
import unittest.mock as mock
import re
import os.path

import numpy as np
import pandas as pd
from click.testing import CliRunner

import codemetrics as cm
from codemetrics import cli
from tests.utils import DataFrameTestCase


class TestCodemetrics(unittest.TestCase):
    """Tests for `codemetrics` package."""

    def test_command_line_interface(self):
        """Test the CLI."""
        runner = CliRunner()
        result = runner.invoke(cli.main)
        assert result.exit_code == 0
        # assert 'codemetrics.cli.main' in result.output
        help_result = runner.invoke(cli.main, ['--help'])
        assert help_result.exit_code == 0
        assert '--help  Show this message and exit.' in help_result.output


class SimpleRepositoryFixture(DataFrameTestCase):
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
        super().setUp()
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
        self.assertEqual(expected, actual)


class AgeReportTestCase(SimpleRepositoryFixture):
    """Extends the repository scaffolding with an age report."""

    def setUp(self):
        super().setUp()
        self.now = dt.datetime(2018, 2, 28, tzinfo=dt.timezone.utc)
        self.get_now_patcher = mock.patch('codemetrics.internals.get_now',
                                          autospec=True, return_value=self.now)
        self.get_now = self.get_now_patcher.start()

    def tearDown(self):
        self.get_now_patcher.stop()

    def test_ages(self):
        """The age report generates data based on the SCM log data"""
        actual = cm.get_ages(self.log)
        expected = pd.read_csv(io.StringIO(textwrap.dedent('''
        path,age
        requirements.txt,3.531817
        stats.py,1.563889
        ''')))
        self.assertEqual(expected, actual)

    def test_ages_enriched_with_kind(self):
        """Allow to use additional columns in age report."""
        actual = cm.get_ages(self.log, by=['path', 'kind'])[['path', 'kind', 'age']]
        expected = pd.read_csv(io.StringIO(textwrap.dedent('''
        path,kind,age
        requirements.txt,file,3.531817
        stats.py,file,1.563889
        ''')))
        self.assertEqual(expected, actual)

    def test_age_report_enriched_with_component(self):
        """Allow one to enrich the log before generating the age report."""
        log = self.log
        log['component'] = 'blah'
        actual = cm.get_ages(log, by=['path', 'component'])
        expected = pd.read_csv(io.StringIO(textwrap.dedent('''
        path,component,age
        requirements.txt,blah,3.531817
        stats.py,blah,1.563889
        ''')))
        self.assertEqual(expected, actual)

    def test_key_parameter(self):
        """Ignore files_df if nothing in it is relevant"""
        self.log['component'] = 'kernel'
        actual = cm.get_ages(self.log, by=['component', 'kind'])
        expected = pd.read_csv(io.StringIO(textwrap.dedent('''
        component,kind,age
        kernel,file,1.563889''')))
        self.assertEqual(expected, actual)


class HotSpotReportTestCase(SimpleRepositoryFixture):
    """Extends the repository scaffolding with a hot spot report."""

    def setUp(self):
        super().setUp()

    def test_hot_spot_report(self):
        """Generate a report to find hot spots."""
        after = dt.datetime(2018, 2, 26)
        log = self.log.loc[self.log['date'] >= after, :]
        actual = cm.get_hot_spots(log, self.loc)
        expected = pd.read_csv(io.StringIO(textwrap.dedent('''
        language,path,blank,comment,complexity,changes
        Python,stats.py,28,84,100,1.0
        Unknown,requirements.txt,0,0,3,0
        ''')))
        self.assertEqual(expected, actual)

    def test_hot_spot_with_custom_change_metric(self):
        """Generate report with a different change metric than revision."""
        self.log['day'] = dt.date(2018, 2,
                                  24)  # force all rows to the same date.
        actual = cm.get_hot_spots(self.log, self.loc, count_one_change_per=['day'])
        expected = pd.read_csv(io.StringIO(textwrap.dedent('''
        language,path,blank,comment,complexity,changes
        Python,stats.py,28,84,100,1
        Unknown,requirements.txt,0,0,3,1
        ''')))
        self.assertEqual(expected, actual)


class CoChangeTestCase(SimpleRepositoryFixture):
    """CoChangeReport test case."""

    def setUp(self):
        super().setUp()

    def test_co_change_report(self):
        """Simple CoChangeReport usage."""
        actual = cm.get_co_changes(log=SimpleRepositoryFixture.get_log_df())
        expected = pd.read_csv(io.StringIO(textwrap.dedent('''
        path,dependency,changes,cochanges,coupling
        requirements.txt,stats.py,1,1,1.0
        stats.py,requirements.txt,2,1,0.5
        ''')))
        self.assertEqual(expected, actual)

    def test_co_change_report_on_day(self):
        """Check handling of on with the date as a day in argument."""
        log = SimpleRepositoryFixture.get_log_df()
        # Same day to force results different from test_co_change_report.
        log['day'] = pd.to_datetime('2018-02-24')
        actual = cm.get_co_changes(log=log, on='day')
        expected = pd.read_csv(io.StringIO(textwrap.dedent('''
        path,dependency,changes,cochanges,coupling
        requirements.txt,stats.py,1,1,1.0
        stats.py,requirements.txt,1,1,1.0
        ''')))
        self.assertEqual(expected, actual)


code_maat_dataset = pd.read_csv(io.StringIO(textwrap.dedent(r'''
path,component
.\.travis.yml,
.\project.clj,
.\src\code_maat\analysis\authors.clj,analysis.src
.\src\code_maat\analysis\churn.clj,analysis.src
.\src\code_maat\analysis\code_age.clj,analysis.src
.\src\code_maat\analysis\commit_messages.clj,analysis.src
.\src\code_maat\analysis\communication.clj,analysis.src
.\src\code_maat\analysis\coupling_algos.clj,analysis.src
.\src\code_maat\analysis\effort.clj,analysis.src
.\src\code_maat\analysis\entities.clj,analysis.src
.\src\code_maat\analysis\logical_coupling.clj,analysis.src
.\src\code_maat\analysis\math.clj,analysis.src
.\src\code_maat\analysis\sum_of_coupling.clj,analysis.src
.\src\code_maat\analysis\summary.clj,analysis.src
.\src\code_maat\analysis\workarounds.clj,analysis.src
.\src\code_maat\app\app.clj,app.src
.\src\code_maat\app\grouper.clj,app.src
.\src\code_maat\app\team_mapper.clj,app.src
.\src\code_maat\app\time_based_grouper.clj,app.src
.\src\code_maat\cmd_line.clj,analysis.src
.\src\code_maat\dataset\dataset.clj,dataset
.\src\code_maat\output\csv.clj,output
.\src\code_maat\output\filters.clj,output
.\src\code_maat\parsers\git.clj,parsers.src
.\src\code_maat\parsers\git2.clj,parsers.src
.\src\code_maat\parsers\hiccup_based_parser.clj,parsers.src
.\src\code_maat\parsers\limitters.clj,parsers.src
.\src\code_maat\parsers\mercurial.clj,parsers.src
.\src\code_maat\parsers\perforce.clj,parsers.src
.\src\code_maat\parsers\svn.clj,parsers.src
.\src\code_maat\parsers\tfs.clj,parsers.src
.\src\code_maat\parsers\time_parser.clj,parsers.src
.\src\code_maat\parsers\xml.clj,parsers.src
.\test\code_maat\analysis\authors_test.clj,analysis.test
.\test\code_maat\analysis\churn_test.clj,analysis.test
.\test\code_maat\analysis\code_age_test.clj,analysis.test
.\test\code_maat\analysis\commit_messages_test.clj,analysis.test
.\test\code_maat\analysis\communication_test.clj,analysis.test
.\test\code_maat\analysis\coupling_algos_test.clj,analysis.test
.\test\code_maat\analysis\effort_test.clj,analysis.test
.\test\code_maat\analysis\entities_test.clj,analysis.test
.\test\code_maat\analysis\logical_coupling_test.clj,analysis.test
.\test\code_maat\analysis\math_test.clj,analysis.test
.\test\code_maat\analysis\sum_of_coupling_test.clj,analysis.test
.\test\code_maat\analysis\test_data.clj,analysis.test
.\test\code_maat\app\cmd_line_test.clj,app.test
.\test\code_maat\app\grouper_test.clj,app.test
.\test\code_maat\app\team_mapper_test.clj,app.test
.\test\code_maat\app\time_based_grouper_test.clj,app.test
.\test\code_maat\dataset\dataset_test.clj,dataset
.\test\code_maat\end_to_end\churn_scenario_test.clj,end_to_end.test
.\test\code_maat\end_to_end\empty.xml,end_to_end.test
.\test\code_maat\end_to_end\git_live_data_test.clj,end_to_end.test
.\test\code_maat\end_to_end\mercurial_live_data_test.clj,end_to_end.test
.\test\code_maat\end_to_end\perforce_live_data_test.clj,end_to_end.test
.\test\code_maat\end_to_end\scenario_tests.clj,end_to_end.test
.\test\code_maat\end_to_end\simple.xml,end_to_end.test
.\test\code_maat\end_to_end\svn_live_data_test.clj,end_to_end.test
.\test\code_maat\end_to_end\team_level_analyses_test.clj,end_to_end.test
.\test\code_maat\end_to_end\tfs_live_data_test.clj,end_to_end.test
.\test\code_maat\parsers\git_test.clj,parsers.test
.\test\code_maat\parsers\mercurial_test.clj,parsers.test
.\test\code_maat\parsers\perforce_test.clj,parsers.test
.\test\code_maat\parsers\svn_test.clj,parsers.test
.\test\code_maat\parsers\tfs_test.clj,parsers.test
.\test\code_maat\parsers\time_parser_test.clj,parsers.test
.\test\code_maat\tools\test_tools.clj,
'''))).fillna('')


class ComponentTestCase(SimpleRepositoryFixture):
    """Test guess_components function."""

    def setUp(self):
        """Given a list of paths."""
        super().setUp()
        self.paths = code_maat_dataset['path']
        # keeps random generated sequences consistent over runs.
        np.random.seed(0)

    def test_can_guess_components(self):
        """Cluster paths in components."""
        actual = cm.guess_components(self.paths, stop_words={'code_maat'},
                                     n_clusters=10)
        actual = actual.sort_values(by='path').reset_index(drop=True)
        expected = code_maat_dataset
        self.assertEqual(expected, actual)

    def test_guess_components_for_specific_n_clusters(self):
        """Cluster paths to a specific number of components"""
        n_clusters = 3
        comps = cm.guess_components(self.paths, stop_words={'code_maat'},
                                    n_clusters=n_clusters)
        actual = comps[['component']].drop_duplicates().reset_index(drop=True)
        expected = pd.DataFrame(data={'component': ['parsers', 'src.analysis', 'test']})
        self.assertEqual(expected, actual)


if __name__ == '__main__':
    unittest.main()



