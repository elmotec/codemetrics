#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `codemetrics.git`"""

import datetime as dt
import textwrap
import unittest
from unittest import mock

import numpy as np
import pandas as pd
import tqdm

import codemetrics as cm
import codemetrics.git as git
import tests.test_scm as test_scm
import tests.utils as utils


class PathElemParser(unittest.TestCase):
    def setUp(self):
        """Initialize git collector."""
        self.git = git._GitLogCollector()

    def test_parse_path_elem(self):
        """Parsing of path element."""
        pe = "21        2   	dir/test.py"
        added, removed, relpath, copyfrompath = self.git.parse_path_elem(pe)
        self.assertEqual(21, added)
        self.assertEqual(2, removed)
        self.assertEqual("dir/test.py", relpath)
        self.assertIsNone(copyfrompath)

    def test_parse_renamed_path(self):
        """Parsing of path element."""
        pe = "1       1       dir/{b/a.py => a/b.py}"
        added, removed, relpath, copyfrompath = self.git.parse_path_elem(pe)
        self.assertEqual(1, added)
        self.assertEqual(1, removed)
        self.assertEqual("dir/a/b.py", relpath)
        self.assertEqual("dir/b/a.py", copyfrompath)

    def test_parse_renamed_path_empty_right(self):
        """Parsing of path element."""
        pe = "21        2   	dir/{category => }/test.py"
        added, removed, relpath, copyfrompath = self.git.parse_path_elem(pe)
        self.assertEqual(21, added)
        self.assertEqual(2, removed)
        self.assertEqual("dir/test.py", relpath)
        self.assertEqual("dir/category/test.py", copyfrompath)

    def test_parse_renamed_path_empty_left(self):
        """Parsing of path element."""
        pe = "-       -       dir/{ => subdir}/file.py"
        added, removed, relpath, copyfrompath = self.git.parse_path_elem(pe)
        self.assertTrue(np.isnan(added))
        self.assertTrue(np.isnan(removed))
        self.assertEqual("dir/subdir/file.py", relpath)
        self.assertEqual("dir/file.py", copyfrompath)


def get_log():
    retval = textwrap.dedent(
        """
    [2adcc03] [elmotec] [2018-12-05 23:44:38 -0000] [Fixed Windows specific paths]
    1       1       codemetrics/core.py
    1       1       requirements.txt

    [b9fe5a6] [elmotec] [2018-12-04 21:49:55 -0000] [Added guess_components]
    44      0       codemetrics/core.py
    1       8       codemetrics/svn.py
    1       0       requirements.txt
    110     18      tests/test_core.py
    """
    )
    return retval


class GetGitLogTestCase(unittest.TestCase, test_scm.GetLogTestCase):
    """Given a BaseReport instance."""

    def setUp(self):
        """Prepare environment for the tests."""
        test_scm.GetLogTestCase.setUp(self, cm.get_git_log, cm.git, cwd="<root>")

    def tearDown(self):
        """Clean up."""
        mock.patch.stopall()

    @mock.patch("codemetrics.internals.run", side_effect=[get_log()], autospec=True)
    def test_git_arguments(self, run):
        """Check that git is called with the expected parameters."""
        git.get_git_log("file", after=self.after, cwd="<root>")
        run.assert_called_with(
            ["git"]
            + git._GitLogCollector._args
            + ["--after", f"{self.after:%Y-%m-%d}", "file"],
            cwd="<root>",
        )

    # noinspection PyUnresolvedReferences,PyUnresolvedReferences,PyUnresolvedReferences
    @mock.patch("tqdm.tqdm", autospec=True, create=True)
    @mock.patch("codemetrics.internals.run", side_effect=[get_log()], autospec=True)
    def test_get_log_with_progress(self, _run, _):
        """Simple git call returns pandas.DataFrame."""
        pb = tqdm.tqdm()
        _ = git.get_git_log("file", after=self.after, cwd="<root>", progress_bar=pb)
        expected_cmd = [
            "git",
            "log",
            '--pretty=format:"[%h] [%an] [%ad] [%s]"',
            "--date=iso",
            "--numstat",
            "--after",
            "2018-12-03",
            "file",
        ]
        _run.assert_called_with(expected_cmd, cwd="<root>")
        self.assertEqual(pb.total, 3)
        pb.update.assert_has_calls([mock.call(1), mock.call(2)])
        pb.close.assert_called_once()

    @mock.patch("codemetrics.internals.run", side_effect=[get_log()], autospec=True)
    def test_get_log(self, _):
        """Simple git call returns pandas.DataFrame."""
        actual = git.get_git_log(".", after=self.after)
        expected = utils.csvlog_to_dataframe(
            textwrap.dedent(
                """

revision,author,date,path,message,kind,action,copyfromrev,copyfrompath,added,removed
2adcc03,elmotec,2018-12-05 23:44:38+00:00,codemetrics/core.py,Fixed Windows specific paths,f,,,,1,1
2adcc03,elmotec,2018-12-05 23:44:38+00:00,requirements.txt,Fixed Windows specific paths,f,,,,1,1
b9fe5a6,elmotec,2018-12-04 21:49:55+00:00,codemetrics/core.py,Added guess_components,f,,,,44,0
b9fe5a6,elmotec,2018-12-04 21:49:55+00:00,codemetrics/svn.py,Added guess_components,f,,,,1,8
b9fe5a6,elmotec,2018-12-04 21:49:55+00:00,requirements.txt,Added guess_components,f,,,,1,0
b9fe5a6,elmotec,2018-12-04 21:49:55+00:00,tests/test_core.py,Added guess_components,f,,,,110,18"""
            )
        )
        self.assertEqual(expected, actual)

    @mock.patch(
        "codemetrics.internals.run",
        autospec=True,
        return_value=textwrap.dedent(
            """
                [xxxxxxx] [elmotec] [2018-12-05 23:44:38 -0000] [excel file]
                -       -       directory/output.xls
                """
        ),
    )
    def test_handling_of_binary_files(self, _):
        """Handles binary files which do not show added or removed lines."""
        df = git.get_git_log(".", after=self.after)
        expected = utils.csvlog_to_dataframe(
            textwrap.dedent(
                """\
        revision,author,date,path,message,kind,action
        xxxxxxx,elmotec,2018-12-05 23:44:38+00:00,directory/output.xls,excel file,f,"""
            )
        )
        self.assertEqual(expected, df)

    @mock.patch(
        "codemetrics.internals.run",
        autospec=True,
        return_value=textwrap.dedent(
            """
                [xxxxxxx] [elmotec] [2018-12-05 23:44:38 -0000] [bbb [internals skip] [skipci]]
                1       1       some/file
                """
        ),
    )
    def test_handling_of_brackets_in_log(self, _):
        """Handles brackets inside the commit log."""
        df = git.get_git_log(".", after=self.after)
        expected = utils.csvlog_to_dataframe(
            textwrap.dedent(
                """\
        revision,author,date,path,message,kind,action,copyfromrev,copyfrompath,added,removed
        xxxxxxx,elmotec,2018-12-05 23:44:38+00:00,some/file,bbb [internals skip] [skipci],f,,,,1,1"""
            )
        )
        self.assertEqual(expected, df)

    @mock.patch(
        "codemetrics.internals.run",
        autospec=True,
        return_value=textwrap.dedent(
            """
                [a897aad] [elmotec] [2019-01-25 07:05:25 -0500] [Merge nothing]
                [1987486] [elmotec] [2019-01-25 07:04:31 -0500] [Change]
                3       4       .gitignore
                """
        ),
    )
    def test_empty_diff(self, _):
        """Handles log segment with no diffs."""
        actual = git.get_git_log(".", after=self.after)
        expected = utils.csvlog_to_dataframe(
            textwrap.dedent(
                """\
        revision,author,date,path,message,kind,added,removed
        a897aad,elmotec,2019-01-25 12:05:25,,Merge nothing,X,0,0
        1987486,elmotec,2019-01-25 12:04:31,.gitignore,Change,f,3,4
        """
            )
        )
        self.assertEqual(expected, actual)

    def test_handle_double_quotes_in_cmd_output(self):
        """Handles binary files which do not show added or removed lines."""
        cmd_output = [
            '"[dfa9d6f08] [Joris] [2020-11-28 15:27:20 +0100] [TST: rewrite]"',
            "145\t250\ttest_convert_dtypes.py",
            "",
        ]
        collector = cm.git._GitLogCollector()
        df = collector.process_log_output_to_df(
            cmd_output, after=dt.datetime(2020, 11, 1, tzinfo=dt.timezone.utc)
        )
        expected = utils.csvlog_to_dataframe(
            textwrap.dedent(
                """\
        revision,author,date,path,message,kind,added,removed
        dfa9d6f08,Joris,2020-11-28 15:27:20 +0100,test_convert_dtypes.py,TST: rewrite,f,145,250
        """
            )
        )
        self.assertEqual(expected.T, df.T)


class GitDownloadTestCase(unittest.TestCase, test_scm.ScmDownloadTestCase):
    """Test getting historical files with git."""

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
        super().setUp()
        self.download = git.download
        self.git = cm.git._GitFileDownloader()

    @mock.patch("codemetrics.internals.run", autospec=True, return_value=content1)
    def test_single_revision_download(self, _run):
        """Retrieval of one file and one revision."""
        sublog = pd.DataFrame(data={"revision": ["abc"], "path": ["file.py"]})
        actual = cm.git.download(sublog)
        _run.assert_called_with(self.git.command + ["abc:file.py"], cwd=None)
        expected = cm.scm.DownloadResult("abc", "file.py", self.content1)
        self.assertEqual(expected, actual)

    @mock.patch("codemetrics.internals.run", autospec=True, side_effect=[content1])
    def test_single_revision_download_via_apply(self, _run):
        """Retrieval of single revisions via apply."""
        sublog = pd.DataFrame(data={"revision": ["r1"], "path": ["file.py"]})
        actual = sublog.apply(cm.svn.download, axis=1).tolist()
        expected = [cm.scm.DownloadResult("r1", "file.py", self.content1)]
        self.assertEqual(expected, actual)

    @mock.patch(
        "codemetrics.internals.run", autospec=True, side_effect=[content1, content2]
    )
    def test_multiple_revision_download_return_multiple_downloads(self, _run):
        """Retrieval of multiple revisions returns multiple downloads."""
        sublog = pd.DataFrame(data={"revision": ["r1", "r2"], "path": ["file.py"] * 2})
        actual = sublog.apply(cm.svn.download, axis=1).tolist()
        expected = [
            cm.scm.DownloadResult("r1", "file.py", self.content1),
            cm.scm.DownloadResult("r2", "file.py", self.content2),
        ]
        self.assertEqual(expected, actual)


if __name__ == "__main__":
    unittest.main()
