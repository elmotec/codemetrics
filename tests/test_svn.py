#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `codemetrics.svn`"""

import datetime as dt
import io
import textwrap
import unittest
from unittest import mock
import subprocess

import pandas as pd

import codemetrics as cm
import tests.utils as utils


def get_log(dates=None):
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
        <msg>Very descriptive</msg>
        </logentry>''')
    retval += textwrap.dedent('''
    </log>
    ''')
    return retval


class SubversionLogCollectorInitializationTestCase(unittest.TestCase):
    """Test initialization of _SvnLogCollector.

    The collection of the url is very important because the log from svn
    comes as absolute path.

    """

    svn_log_info_output = textwrap.dedent(r'''
    Path: .
    Working Copy Root Path: C:\Users\elmotec\Documents\Python\project
    URL: https://subversion/svn/python/project/trunk
    Relative URL: ^/project/trunk
    Repository Root: https://subversion/svn/python
    Repository UUID: blah-blah-blah
    Revision: 12345
    Node Kind: directory
    Schedule: normal
    ''')

    @mock.patch('codemetrics.internals.run', autospec=True,
                return_value=svn_log_info_output)
    def test_relative_url_collection(self, run_):
        """Collection of the relative url."""
        svn = cm.svn._SvnLogCollector()
        actual = svn.relative_url
        run_.assert_called_with('svn info .')
        self.assertEqual('/project/trunk', actual)


class SubversionGetLogTestCase(unittest.TestCase):
    """Given a BaseReport instance."""

    def setUp(self):
        utils.add_data_frame_equality_func(self)
        self.after = dt.datetime(2018, 2, 24, tzinfo=dt.timezone.utc)
        self.get_check_patcher = mock.patch(
            'codemetrics.internals.check_run_in_root',
            autospec=True)
        self.check_run_in_root = self.get_check_patcher.start()
        self.svn = cm.svn._SvnLogCollector(relative_url='/project/trunk')

    def tearDown(self):
        mock.patch.stopall()

    @mock.patch('pathlib.Path.glob', autospec=True,
                side_effect=[['first.py', 'second.py']])
    def test_get_files(self, glob):
        """get_files return the list of files."""
        actual = cm.internals.get_files(pattern='*.py')
        glob.assert_called_with(mock.ANY, '*.py')
        actual = actual.sort_values(by='path').reset_index(drop=True)
        expected = pd.read_csv(io.StringIO(textwrap.dedent('''
        path
        first.py
        second.py
        ''')))
        self.assertEqual(actual, expected)

    @mock.patch('codemetrics.internals.run',
                side_effect=[get_log()], autospec=True)
    def test_get_log(self, run_):
        """Simple svn run_ returns pandas.DataFrame."""
        actual = self.svn.get_log(after=self.after)
        run_.assert_called_with('svn log --xml -v -r {2018-02-24}:HEAD .')
        expected = utils.csvlog_to_dataframe(textwrap.dedent('''
        revision,author,date,path,message,kind,action,textmods,propmods
        1018,elmotec,2018-02-24T11:14:11.000000Z,stats.py,Very descriptive,file,M,true,false
        1018,elmotec,2018-02-24T11:14:11.000000Z,requirements.txt,Very descriptive,file,M,true,false'''))
        self.assertEqual(expected, actual)

    @mock.patch('codemetrics.internals.get_now', autospec=True,
                return_value=dt.datetime(2018, 2, 28, tzinfo=dt.timezone.utc))
    @mock.patch('tqdm.tqdm', autospec=True)
    @mock.patch('codemetrics.internals.run', side_effect=[
        get_log(dates=[dt.date(2018, 2, 25),
                       dt.date(2018, 2, 27),
                       dt.date(2018, 2, 28)])], autospec=True)
    def test_get_log_with_progress(self, _, new_tqdm, run_):
        """Simple svn call returns pandas.DataFrame."""
        pb = new_tqdm()
        _ = self.svn.get_log(after=self.after, progress_bar=pb)
        self.assertEqual(pb.total, 4)
        calls = [mock.call(1), mock.call(2)]
        run_.assert_called()
        pb.update.assert_has_calls(calls)
        pb.close.assert_called_once()

    @mock.patch('codemetrics.internals.run', side_effect=[textwrap.dedent('''
    <?xml version="1.0" encoding="UTF-8"?>
    <log>
    <logentry revision="1018">
    <author>elmotec</author>
    <date>2018-02-24T11:14:11.000000Z</date>
    <paths><path text-mods="true" kind="file" action="M"
        prop-mods="false">stats.py</path></paths>
    <msg/>
    </logentry>
    </log>''')], autospec=True)
    def test_get_log_no_msg(self, _):
        """Simple svn call returns pandas.DataFrame."""
        df = self.svn.get_log(after=self.after)
        expected = utils.csvlog_to_dataframe(textwrap.dedent('''
        revision,author,date,path,message,kind,action,textmods,propmods
        1018,elmotec,2018-02-24T11:14:11.000000Z,stats.py,,file,M,true,false'''))
        self.assertEqual(expected, df)

    @mock.patch('codemetrics.internals.run', side_effect=[textwrap.dedent('''
    <?xml version="1.0" encoding="UTF-8"?>
    <log>
    <logentry revision="1018">
    <date>2018-02-24T11:14:11.000000Z</date>
    <paths><path text-mods="true" kind="file" action="M"
        prop-mods="false">stats.py</path></paths>
    <msg>i am invisible!</msg>
    </logentry>
    </log>
    ''')], autospec=True)
    def test_get_log_no_author(self, call):
        """Simple svn call returns pandas.DataFrame."""
        expected = utils.csvlog_to_dataframe(textwrap.dedent('''
        revision,author,date,path,message,kind,action,textmods,propmods
        1018,,2018-02-24T11:14:11.000000Z,stats.py,i am invisible!,file,M,true,false'''))
        actual = self.svn.get_log(after=self.after)
        call.assert_called_with('svn log --xml -v -r {2018-02-24}:HEAD .')
        self.assertEqual(expected, actual)

    @mock.patch('codemetrics.internals.run', autospec=True)
    def test_program_name(self, run):
        """Test program_name taken into account."""
        self.svn.svn_client = 'svn-1.7'
        self.svn.get_log(after=self.after)
        run.assert_called_with('svn-1.7 log --xml -v -r {2018-02-24}:HEAD .')

    def test_assert_when_no_tzinfo(self):
        """Test we get a proper message when the start date is not tz-aware."""
        after_no_tzinfo = self.after.replace(tzinfo=None)
        with self.assertRaises(ValueError) as context:
            self.svn.get_log(after=after_no_tzinfo)
        self.assertIn('tzinfo-aware', str(context.exception))

    @mock.patch('codemetrics.internals.run', side_effect=[textwrap.dedent('''
    <?xml version="1.0" encoding="UTF-8"?>
    <log>
    <logentry revision="1018">
    <date>2018-02-24T11:14:11.000000Z</date>
    <paths>
    <path text-mods="false" kind="file" action="D" 
        prop-mods="false">stats.py</path>
    <path text-mods="false" kind="file" copyfrom-path="stats.py"
        copyfrom-rev="930" action="A" prop-mods="false">new_stats.py</path>
    </paths>
    <msg>renamed</msg>
    </logentry>
    </log>
    ''')], autospec=True)
    def test_get_log_renamed_file(self, call):
        """Simple svn call returns pandas.DataFrame."""
        expected = utils.csvlog_to_dataframe(textwrap.dedent('''
        revision,author,date,path,message,kind,action,textmods,propmods,copyfromrev,copyfrompath
        1018,,2018-02-24T11:14:11.000000Z,stats.py,renamed,file,D,false,false,,
        1018,,2018-02-24T11:14:11.000000Z,new_stats.py,renamed,file,A,false,false,930,stats.py
        '''))
        df = self.svn.get_log(after=self.after)
        call.assert_called_with('svn log --xml -v -r {2018-02-24}:HEAD .')
        self.assertEqual(expected, df)


class SubversionDownloadFilesTestCase(unittest.TestCase):
    """Test getting historical files with subversion."""

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
        super().setUp()
        self.svn = cm.svn._SvnDownloader('cat -r')
        self.sublog = pd.read_csv(io.StringIO(textwrap.dedent("""\
        revision,path
        1,file.py
        2,file.py
        """)))

    @mock.patch('codemetrics.internals.run', autospec=True,
                return_value=content1)
    def test_svn_arguments(self, _run):
        cm.svn.download_file(self.sublog.iloc[0])
        _run.assert_called_with(f'{self.svn.command} 1 file.py')

    @mock.patch('codemetrics.internals.run', autospec=True,
                return_value=content1)
    def test_single_revision_download(self, _run):
        actual = cm.svn.download_file(self.sublog.iloc[0])
        expected = cm.scm.DownloadResult(1, 'file.py', self.content1)
        self.assertEqual(expected, actual)

    @mock.patch('codemetrics.internals.run', autospec=True,
                side_effect=[content1, content2])
    def test_multiple_revision_download(self, _run):
        actual = self.sublog.apply(cm.svn.download_file, axis=1).tolist()
        expected = [
            cm.scm.DownloadResult(1, 'file.py', self.content1),
            cm.scm.DownloadResult(2, 'file.py', self.content2),
        ]
        self.assertEqual(expected, actual)


class SubversionGetDiffStatsTestCase(utils.DataFrameTestCase):
    """Given a subversion repository and file chunks."""

    diffs = textwrap.dedent(r'''
    Index: estimate/__init__.py
    ===================================================================
    diff --git a/estimate/estimate/__init__.py b/estimate/estimate/__init__.py
    --- a/estimate/estimate/__init__.py     (revision 1013)
    +++ b/estimate/estimate/__init__.py     (revision 1014)
    @@ -8,7 +8,7 @@
     import logging
     import warnings
    
    -__version__ = "0.44.2"
    +__version__ = "0.44.3"
     package_name = 'estimate'
    Index: estimate/mktdata.py
    ===================================================================
    diff --git a/estimate/estimate/mktdata.py b/estimate/estimate/mktdata.py
    --- a/estimate/estimate/mktdata.py      (revision 1013)
    +++ b/estimate/estimate/mktdata.py      (revision 1014)
    @@ -1042,7 +1042,7 @@
    
         def get_prices(self, securities=None, begin_date=None, end_date=None,
                        num_periods=None, ascending=True,
    -                   source=None, keep_source=False) -> pd.DataFrame:
    +                   source=None) -> pd.DataFrame:
             """"Retrieve prices as a pandas.DataFrame.
    
             Prices are normalized for txns and dividends so that the most recent
    @@ -1086,7 +1086,10 @@
                 return df
    
             def adjust_prices(df, _pdb=None):
    -            df.sort_values('as_of_date', ascending=False, inplace=True)
    +            df.sort_values(['as_of_date', 'source'], ascending=False,
    +                           inplace=True)
    +            df.drop_duplicates(['as_of_date'], keep='last',
    +                               inplace=True)
                 df['sfactor'] = (df['old_q'] / df['new_q']).shift(1)
                 df['sfactor'].iloc[0] = 1.0
                 df['sfactor'].fillna(method='ffill', axis=0, inplace=True)
    @@ -1190,23 +1193,14 @@
                                         Distribution.amount.label('amount'),
                                         HistoricalPrice.source.label('source'))
             df = pd.read_sql(query.selectable, self.context.session.bind)
    +        # convert source to categorical column.
    +        df['source'] = df['source'].astype('category', categories=sources,
    +                                           ordered=True)
             df = df.groupby(by=['symbol']).apply(adjust_prices)
             if len(df):
                 # First 2 column labels of the query.
                 index = [c._label for c in
                          itertools.islice(query.selectable.inner_columns, 0, 2)]
    -            if not keep_source:
    -                dfs = []
    -                # reversed so lower priority source at index 0
    -                for src in reversed(sources):
    -                    dfs.append(df[df['source'] == src].
    -                               drop(['source'], axis=1))
    -                if dfs:
    -                    df = dfs[0].set_index(index)
    -                    # each higher priority overwrites df in place.
    -                    for altdf in dfs[1:]:
    -                        df.update(altdf.set_index(index))
    -                    df.reset_index(inplace=True)
                 df = df.set_index(index)
             if ascending is not None:
                 df.sort_index(axis=0, ascending=ascending, inplace=True)
    Index: setup.py
    ===================================================================
    diff --git a/estimate/setup.py b/estimate/setup.py
    --- a/estimate/setup.py (revision 1013)
    +++ b/estimate/setup.py (revision 1014)
    @@ -22,7 +22,7 @@
     setup(
         name="estimate",
    -    version="0.44.2",
    +    version="0.44.3",
         author="elmotec",
         description=("Management tools."),
    ''')

    log = pd.read_csv(io.StringIO(textwrap.dedent('''\
    index,revision,path
    0,1014,estimate/__init__.py
    1,1014,estimate/mktdata.py
    3,1014,setup.py
    ''')), index_col='index')
    expected = pd.read_csv(io.StringIO(textwrap.dedent('''\
    revision,path,chunk,first,last,added,removed
    1014,estimate/__init__.py,0,8,15,1,2
    1014,estimate/mktdata.py,0,1042,1049,1,1
    1014,estimate/mktdata.py,1,1086,1096,4,1
    1014,estimate/mktdata.py,2,1193,1207,3,13
    1014,setup.py,0,22,29,1,1
    ''')), index_col=['revision', 'path', 'chunk'])

    @mock.patch('codemetrics.internals.run', autospec=True,
                return_value=diffs)
    def test_called_command_line(self, run_):
        """Can retrieve chunk statistics from Subversion"""
        cm.svn.get_diff_stats(self.log)
        run_.assert_called_once_with('svn diff --git -c 1014')

    @mock.patch('codemetrics.internals.run', autospec=True,
                return_value=diffs)
    def test_direct_call(self, _):
        """Direct call to cm.svn.get_diff_stats"""
        actual = cm.svn.get_diff_stats(self.log)
        expected = self.expected.reset_index(level='revision', drop=True)
        self.assertEqual(expected, actual)

    @mock.patch('codemetrics.internals.run', autospec=True,
                side_effect=[diffs, diffs])
    def test_get_chunk_stats_with_groupby_apply(self, _):
        """Can retrieve chunk statistics from Subversion"""
        actual = self.log.groupby(['revision']).\
            apply(cm.svn.get_diff_stats)
        expected = self.expected
        self.assertEqual(expected, actual)

    @mock.patch('codemetrics.internals.run', autospec=True,
                side_effect=[diffs, diffs])
    def test_get_stats_with_groupby_apply(self, _):
        """Can retrieve chunk statistics from Subversion"""
        actual = self.log.groupby(['revision']).\
            apply(cm.svn.get_diff_stats, chunks=False)
        expected = self.expected[['added', 'removed']].\
            groupby(['revision', 'path']).\
            sum()
        self.assertEqual(expected, actual)

    @mock.patch('codemetrics.internals.run', autospec=True)
    def test_error_handling(self, run_):
        """Can retrieve chunk statistics from Subversion"""
        exception = subprocess.CalledProcessError(1, cmd='svn',
                                                  stderr='some error')
        run_.side_effect = [exception] * 2
        with self.assertLogs(level='WARN') as context:
            with self.assertRaises(subprocess.CalledProcessError):
                cm.svn.get_diff_stats(self.log)
        expected = "WARNING:codemetrics:cannot retrieve diff for 1014: " \
                   "Command 'svn' returned non-zero exit status 1.: some error"
        self.assertEqual([expected], context.output)


if __name__ == '__main__':
    unittest.main()
