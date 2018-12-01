#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `codemetrics.svn`"""

import datetime as dt
import textwrap
import io
import unittest
from unittest import mock

import tqdm
import pandas as pd

from tests.utils import add_data_frame_equality_func

import codemetrics as cm
import codemetrics.svn
import codemetrics.loc


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


class SubversionTestCase(unittest.TestCase):
    """Given a BaseReport instance."""

    @staticmethod
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
        glob.assert_called_with(mock.ANY, '*.py')
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

    @mock.patch('codemetrics.internals.get_now', autospec=True,
                return_value=dt.datetime(2018, 2, 28))
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


if __name__ == '__main__':
    unittest.main()
