#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `codemetrics.svn`"""

import datetime as dt
import io
import textwrap
import unittest
from unittest import mock

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


class DownloadSvnFilesTestCase(unittest.TestCase):
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
        self.svn = cm.svn._SvnFileDownloader()

    @mock.patch('codemetrics.internals.run', autospec=True,
                return_value=content1)
    def test_single_revision_download(self, _run):
        sublog = pd.read_csv(io.StringIO(textwrap.dedent("""\
        revision,path
        1,file.py
        """)))
        results = list(cm.svn.download_files(sublog))
        _run.assert_called_with(f'{self.svn.command} 1 file.py')
        self.assertEqual(1, len(results))
        actual = results[0]
        expected = cm.scm.FileDownloadResult('file.py', 1, self.content1)
        self.assertEqual(expected, actual)

    @mock.patch('codemetrics.internals.run', autospec=True,
                side_effect=[content1, content2])
    def test_multiple_revision_download(self, _run):
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
