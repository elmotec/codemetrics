#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `codemetrics.svn`"""

import datetime as dt
import io
import pathlib as pl
import subprocess
import textwrap
import unittest
from unittest import mock

import pandas as pd

import codemetrics as cm
import tests.test_scm as test_scm
import tests.utils as utils


def get_log(dates=None):
    if dates is None:
        dates = [dt.datetime(2018, 2, 24, 11, 14, 11, tzinfo=dt.timezone.utc)]
    retval = textwrap.dedent(
        """
    <?xml version="1.0" encoding="UTF-8"?>
    <log>"""
    )
    for date in dates:
        retval += textwrap.dedent(
            f"""
        <logentry revision="1018">
        <author>elmotec</author>
        <date>{date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")}</date>
        <paths>
        <path text-mods="true" kind="file" action="M"
           prop-mods="false">/project/trunk/stats.py</path>
        <path text-mods="true" kind="file" action="M"
           prop-mods="false">/project/trunk/requirements.txt</path>
        </paths>
        <msg>Very descriptive</msg>
        </logentry>"""
        )
    retval += textwrap.dedent(
        """
    </log>
    """
    )
    return retval


class SubversionLogCollectorInitializationTestCase(unittest.TestCase):
    """Test initialization of _SvnLogCollector.

    The collection of the url is very important because the log from svn
    comes as absolute path.

    """

    svn_log_info_output = textwrap.dedent(
        r"""
    Path: .
    Working Copy Root Path: C:\Users\elmotec\Documents\Python\project
    URL: https://subversion/svn/python/project/trunk
    Relative URL: ^/project/trunk
    Repository Root: https://subversion/svn/python
    Repository UUID: blah-blah-blah
    Revision: 12345
    Node Kind: directory
    Schedule: normal
    """
    )

    @mock.patch(
        "codemetrics.internals.run", autospec=True, return_value=svn_log_info_output
    )
    def test_relative_url_collection(self, run_):
        """Collection of the relative url."""
        log_collector = cm.svn._SvnLogCollector()
        actual = log_collector.relative_url
        run_.assert_called_with("svn info .".split(), cwd=None)
        self.assertEqual("/project/trunk", actual)


class GetSvnLogTestCase(unittest.TestCase, test_scm.GetLogTestCase):
    """Given a BaseReport instance."""

    def setUp(self):
        """Calls parent GetLogTestCase.setUp."""
        test_scm.GetLogTestCase.setUp(self, cm.svn.SvnProject("<root>"))

    def tearDown(self):
        mock.patch.stopall()

    @mock.patch(
        "pathlib.Path.glob", autospec=True, side_effect=[["start_line.py", "second.py"]]
    )
    def test_get_files(self, glob):
        """get_files return the list of files."""
        actual = cm.internals.get_files(pattern="*.py")
        glob.assert_called_with(mock.ANY, "*.py")
        actual = actual.sort_values(by="path").reset_index(drop=True)
        expected = pd.read_csv(
            io.StringIO(
                textwrap.dedent(
                    """
        path
        second.py
        start_line.py
        """
                )
            )
        )
        self.assertEqual(actual, expected)

    @mock.patch("codemetrics.internals.run", side_effect=[get_log()], autospec=True)
    def test_get_log(self, run_):
        """Simple svn run_ returns pandas.DataFrame."""
        actual = cm.get_log(
            self.project, after=self.after, relative_url="/project/trunk"
        )
        run_.assert_called_with(
            "svn log --xml -v -r {2018-12-03}:HEAD .".split(), cwd="<root>"
        )
        expected = utils.csvlog_to_dataframe(
            textwrap.dedent(
                """
        revision,author,date,path,message,kind,action,textmods,propmods
        1018,elmotec,2018-02-24T11:14:11.000000Z,stats.py,Very descriptive,file,M,true,false
        1018,elmotec,2018-02-24T11:14:11.000000Z,requirements.txt,Very descriptive,file,M,true,false"""
            )
        )
        self.assertEqual(expected, actual)

    @mock.patch("tqdm.tqdm", autospec=True)
    @mock.patch(
        "codemetrics.internals.run",
        side_effect=[
            get_log(
                dates=[dt.date(2018, 12, 4), dt.date(2018, 12, 4), dt.date(2018, 12, 6)]
            )
        ],
        autospec=True,
    )
    def test_get_log_with_progress(self, _, new_tqdm):
        """The progress bar if set is called as appropriate."""
        progress_bar = new_tqdm()
        _ = self.project.get_log(
            after=self.after, progress_bar=progress_bar, relative_url="/project/trunk"
        )
        self.assertEqual(progress_bar.total, 3)
        calls = [mock.call(1), mock.call(2)]
        progress_bar.update.assert_has_calls(calls)
        progress_bar.close.assert_called_once()

    @mock.patch(
        "codemetrics.internals.run",
        side_effect=[
            textwrap.dedent(
                """
    <?xml version="1.0" encoding="UTF-8"?>
    <log>
    <logentry revision="1018">
    <author>elmotec</author>
    <date>2018-02-24T11:14:11.000000Z</date>
    <paths><path text-mods="true" kind="file" action="M"
        prop-mods="false">stats.py</path></paths>
    <msg/>
    </logentry>
    </log>"""
            )
        ],
        autospec=True,
    )
    def test_get_log_no_msg(self, _):
        """Simple svn call returns pandas.DataFrame."""
        df = self.project.get_log(after=self.after, relative_url="/project/trunk")
        expected = utils.csvlog_to_dataframe(
            textwrap.dedent(
                """
        revision,author,date,path,message,kind,action,textmods,propmods
        1018,elmotec,2018-02-24T11:14:11.000000Z,stats.py,,file,M,true,false"""
            )
        )
        self.assertEqual(expected, df)

    @mock.patch(
        "codemetrics.internals.run",
        side_effect=[
            textwrap.dedent(
                """
    <?xml version="1.0" encoding="UTF-8"?>
    <log>
    <logentry revision="1018">
    <date>2018-02-24T11:14:11.000000Z</date>
    <paths><path text-mods="true" kind="file" action="M"
        prop-mods="false">stats.py</path></paths>
    <msg>i am invisible!</msg>
    </logentry>
    </log>
    """
            )
        ],
        autospec=True,
    )
    def test_get_log_no_author(self, call):
        """Simple svn call returns pandas.DataFrame."""
        expected = utils.csvlog_to_dataframe(
            textwrap.dedent(
                """
        revision,author,date,path,message,kind,action,textmods,propmods
        1018,,2018-02-24T11:14:11.000000Z,stats.py,i am invisible!,file,M,true,false"""
            )
        )
        actual = self.project.get_log(after=self.after, relative_url="/project/trunk")
        call.assert_called_with(
            "svn log --xml -v -r {2018-12-03}:HEAD .".split(), cwd="<root>"
        )
        self.assertEqual(expected, actual)

    @mock.patch("codemetrics.internals.run", autospec=True)
    def test_program_name(self, run):
        """Test program_name taken into account."""
        self.project.client = "svn-1.7"
        self.project.get_log(after=self.after, relative_url="/project/trunk")
        run.assert_called_with(
            "svn-1.7 log --xml -v -r {2018-12-03}:HEAD .".split(), cwd="<root>"
        )

    def test_assert_when_no_tzinfo(self):
        """Test we get a proper message when the start date is not tz-aware."""
        after_no_tzinfo = self.after.replace(tzinfo=None)
        with self.assertRaises(ValueError) as context:
            self.project.get_log(after=after_no_tzinfo)
        self.assertIn("tzinfo-aware", str(context.exception))

    @mock.patch(
        "codemetrics.internals.run",
        side_effect=[
            textwrap.dedent(
                """
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
    """
            )
        ],
        autospec=True,
    )
    def test_get_log_renamed_file(self, call):
        """Simple svn call returns pandas.DataFrame."""
        expected = utils.csvlog_to_dataframe(
            textwrap.dedent(
                """
        revision,author,date,path,message,kind,action,textmods,propmods,copyfromrev,copyfrompath
        1018,,2018-02-24T11:14:11.000000Z,stats.py,renamed,file,D,false,false,,
        1018,,2018-02-24T11:14:11.000000Z,new_stats.py,renamed,file,A,false,false,930,stats.py
        """
            )
        )
        actual = self.project.get_log(after=self.after, relative_url="/project/trunk")
        call.assert_called_with(
            "svn log --xml -v -r {2018-12-03}:HEAD .".split(), cwd="<root>"
        )
        self.assertEqual(expected.T, actual.T)


class SubversionDownloadTestCase(unittest.TestCase):
    """Test getting historical files with subversion."""

    content1 = textwrap.dedent(
        """
    def main():
        print('ahah!')
    """
    )
    content2 = textwrap.dedent(
        """
    def main():
        print('ahah!')

    if __name__ == '__main__':
        main()
    """
    )

    def setUp(self):
        self.svn = cm.svn.SvnDownloader("cat -r".split())
        self.sublog = pd.DataFrame(
            data={"revision": ["1", "2"], "path": ["file.py"] * 2}
        )

    @mock.patch("codemetrics.internals.run", autospec=True, return_value=content1)
    def test_svn_arguments(self, _run):
        cm.svn.SvnProject().download(self.sublog.iloc[0])
        _run.assert_called_with(self.svn.command + ["1", "file.py"], cwd=pl.Path("."))

    @mock.patch("codemetrics.internals.run", autospec=True, return_value=content1)
    def test_single_revision_download(self, _run):
        actual = cm.svn.SvnProject().download(self.sublog.iloc[0])
        expected = cm.scm.DownloadResult("1", "file.py", self.content1)
        self.assertEqual(expected, actual)

    @mock.patch(
        "codemetrics.internals.run", autospec=True, side_effect=[content1, content2]
    )
    def test_multiple_revision_download(self, _run):
        actual = self.sublog.apply(cm.svn.SvnProject().download, axis=1).tolist()
        expected = [
            cm.scm.DownloadResult("1", "file.py", self.content1),
            cm.scm.DownloadResult("2", "file.py", self.content2),
        ]
        self.assertEqual(expected, actual)


class SubversionGetDiffStatsTestCase(utils.DataFrameTestCase):
    """Given a subversion repository and file chunks."""

    diffs = textwrap.dedent(
        r'''
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
    +            df.drop_duplicates(['as_of_date'], keep='end_line',
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
    '''
    )

    log = pd.read_csv(
        io.StringIO(
            textwrap.dedent(
                """\
    index,revision,path
    0,1014,estimate/__init__.py
    1,1014,estimate/mktdata.py
    3,1014,setup.py
    """
            )
        ),
        index_col="index",
        dtype="str",
    )
    expected = pd.read_csv(
        io.StringIO(
            textwrap.dedent(
                """\
    revision,path,chunk,first,last,added,removed
    1014,estimate/__init__.py,0,8,15,1,1
    1014,estimate/mktdata.py,0,1042,1049,1,1
    1014,estimate/mktdata.py,1,1086,1096,4,1
    1014,estimate/mktdata.py,2,1193,1207,3,12
    1014,setup.py,0,22,29,1,1
    """
            )
        ),
        dtype={"revision": "str", "path": "str"},
    )

    @mock.patch("codemetrics.internals.run", autospec=True, return_value=diffs)
    def test_called_command_line(self, run_):
        """Can retrieve chunk statistics from Subversion"""
        cm.svn.get_diff_stats(self.log, cwd="<root>")
        run_.assert_called_once_with("svn diff --git -c 1014 .".split(), cwd="<root>")

    @mock.patch("codemetrics.internals.run", autospec=True, return_value=diffs)
    def test_direct_call(self, _):
        """Direct call to cm.svn.get_diff_stats"""
        actual = cm.svn.get_diff_stats(self.log)
        expected = self.expected.drop(columns=["revision"]).set_index(["path", "chunk"])
        self.assertEqual(expected, actual)

    @mock.patch("codemetrics.internals.run", autospec=True, return_value=diffs)
    def test_direct_call_with_indexed_data(self, _):
        """Direct call to cm.svn.get_diff_stats"""
        actual = cm.svn.get_diff_stats(self.log.set_index(["revision", "path"]))
        expected = self.expected.drop(columns=["revision"]).set_index(["path", "chunk"])
        self.assertEqual(expected, actual)

    @mock.patch("codemetrics.internals.run", autospec=True, side_effect=[diffs, diffs])
    def test_get_chunk_stats_with_groupby_apply(self, _):
        """Can retrieve chunk statistics from Subversion"""
        actual = self.log.groupby(["revision"]).apply(cm.svn.get_diff_stats)
        expected = self.expected.reset_index(drop=True).set_index(
            ["revision", "path", "chunk"]
        )
        self.assertEqual(expected, actual)

    @mock.patch("codemetrics.internals.run", autospec=True, side_effect=[diffs, diffs])
    def test_get_stats_with_groupby_apply(self, _):
        """Can retrieve chunk statistics from Subversion"""
        actual = self.log.groupby(["revision"]).apply(
            cm.svn.get_diff_stats, chunks=False
        )
        expected = (
            self.expected[["revision", "path", "added", "removed"]]
            .groupby(["revision", "path"])
            .sum()
        )
        self.assertEqual(expected, actual)

    @mock.patch("codemetrics.internals.run", autospec=True)
    def test_error_generates_warning(self, run_):
        """Can retrieve chunk statistics from Subversion"""
        exception = subprocess.CalledProcessError(1, cmd="svn", stderr="some error")
        run_.side_effect = [exception] * 2
        with self.assertLogs(level="WARN") as context:
            cm.svn.get_diff_stats(self.log)
        expected = (
            "WARNING:codemetrics:cannot retrieve diff for 1014: "
            "Command 'svn' returned non-zero exit status 1.: some error"
        )
        self.assertEqual([expected], context.output)

    @mock.patch("codemetrics.internals.run", autospec=True)
    def test_empty_diff(self, run):
        """Direct call when svn returns an empty data frame"""
        run.return_value = textwrap.dedent(
            """
        Index: connect_jupyter_on_desktop1.sh
        ===================================================================
        diff --git a/estimate/connect_jupyter_on_desktop1.sh b/estimate/connect_jupyter_on_desktop1.sh
        new file mode 100644
        --- a/estimate/connect_jupyter_on_desktop1.sh   (nonexistent)
        +++ b/estimate/connect_jupyter_on_desktop1.sh   (revision 899)
        """
        )
        actual = cm.svn.get_diff_stats(self.log)
        expected = pd.read_csv(
            io.StringIO(
                textwrap.dedent(
                    """
        path,chunk,first,last,added,removed
        """
                )
            ),
            index_col=["path", "chunk"],
        )
        self.assertEqual(expected, actual)

    @mock.patch("codemetrics.internals.run", autospec=True)
    def test_single_diff_line(self, run):
        """Direct call to cm.svn.get_diff_stats when svn returns single line"""
        run.return_value = textwrap.dedent(
            """
        Index: connect_jupyter_on_desktop1.sh
        ===================================================================
        diff --git a/estimate/connect_jupyter_on_desktop1.sh b/estimate/connect_jupyter_on_desktop1.sh
        new file mode 100644
        --- a/estimate/connect_jupyter_on_desktop1.sh   (nonexistent)
        +++ b/estimate/connect_jupyter_on_desktop1.sh   (revision 899)
        @@ -0,0 +1 @@
        +ssh -NL 8888:localhost:8888 elmotec@desktop1
        """
        )
        actual = cm.svn.get_diff_stats(self.log)
        expected = pd.read_csv(
            io.StringIO(
                textwrap.dedent(
                    """
        path,chunk,first,last,added,removed
        connect_jupyter_on_desktop1.sh,0,1,1,1,0
        """
                )
            ),
            index_col=["path", "chunk"],
        )
        self.assertEqual(expected, actual)

    @mock.patch("codemetrics.internals.run", autospec=True)
    def test_handle_files_with_spaces_in_name(self, run):
        """Files that have spaces in the name are handled correctly."""
        run.return_value = textwrap.dedent(
            """
        Index: contrib/file with spaces.py
        ===================================================================
        diff --git a/dir/contrib/file.py b/dir/contrib/file.py
        new file mode 100644
        --- a/estimate/contrib/file with spaces.py        (nonexistent)
        +++ b/estimate/contrib/file with spaces.py        (revision 756)
        @@ -0,0 +1,1 @@
        +#!/usr/bin/env python
        """
        )
        actual = cm.svn.get_diff_stats(self.log)
        expected = pd.read_csv(
            io.StringIO(
                textwrap.dedent(
                    """
        path,chunk,first,last,added,removed
        contrib/file with spaces.py,0,1,2,1,0
        """
                )
            ),
            index_col=["path", "chunk"],
        )
        self.assertEqual(expected, actual)

    @mock.patch("codemetrics.internals.run", autospec=True)
    def test_deleted_files(self, run):
        """Files that were deleted."""
        run.return_value = textwrap.dedent(
            """
        Index: alembic-prod.ini
        ===================================================================
        diff --git a/estimate/alembic-prod.ini b/estimate/alembic-prod.ini
        deleted file mode 100644
        --- a/estimate/alembic-prod.ini (revision 1035)
        +++ b/estimate/alembic-prod.ini (nonexistent)
        @@ -1,50 +0,0 @@
        -# A generic, single database configuration.
        -
        """
        )
        actual = cm.svn.get_diff_stats(self.log)
        expected = pd.read_csv(
            io.StringIO(
                textwrap.dedent(
                    """
        path,chunk,first,last,added,removed
        alembic-prod.ini,0,0,0,0,2
        """
                )
            ),
            index_col=["path", "chunk"],
        )
        self.assertEqual(expected, actual)

    @mock.patch("codemetrics.internals.run", autospec=True)
    def test_use_index_to_id_file_in_branches(self, run):
        """Handles a weird bug in Subversion

        Branch name is dropped with --git option in the diff command. So we
        must rely on the Index: line above. It seems simpler anyway.

        """
        run.return_value = textwrap.dedent(
            """
        Index: somedir/file.py
        ===================================================================
        diff --git a/project/branches/somedir/file.txt b/project/branches/somedir/file.txt
        --- a/project/branches/somedir/file.py       (revision 1234)
        +++ b/project/branches/somedir/file.py       (revision 1235)
        @@ -0,0 +1,1 @@
        +#!/usr/bin/env python
        """
        )
        actual = cm.svn.get_diff_stats(self.log)
        expected = pd.read_csv(
            io.StringIO(
                textwrap.dedent(
                    """
        path,chunk,first,last,added,removed
        somedir/file.py,0,1,2,1,0
        """
                )
            ),
            index_col=["path", "chunk"],
        )
        self.assertEqual(expected, actual)


class SubversionProjectTestCase(unittest.TestCase, test_scm.CommonProjectTestCase):
    """Test SvnProject."""

    Project = cm.svn.SvnProject

    def setUp(self):
        pass


if __name__ == "__main__":
    unittest.main()
