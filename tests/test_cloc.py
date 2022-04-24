#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for loc (lines of code) module."""

import io
import pathlib as pl
import textwrap
import unittest
from unittest import mock

import pandas as pd

import codemetrics.cloc as loc
import codemetrics.scm as scm

from . import utils


class SimpleDirectory(unittest.TestCase):
    """Given a simple directory."""

    def setUp(self):
        """Mocks the internal run command."""
        utils.add_data_frame_equality_func(self)
        self.run_output = textwrap.dedent(
            """\
        language,filename,blank,comment,code,"http://cloc.sourceforge.net"
        Python,internals.py,55,50,130
        Python,tests.py,29,92,109
        Python,setup.py,4,2,30
        C#,.NETFramework,Version=v4.7.2.AssemblyAttributes.cs,0,1,3
        """
        )
        cmi = "codemetrics.internals."
        self.run_patcher = mock.patch(
            cmi + "run", autospec=True, return_value=self.run_output
        )
        self.check_patcher = mock.patch(cmi + "check_run_in_root", autospec=True)
        self.run_ = self.run_patcher.start()
        self.check_run_from_root = self.check_patcher.start()

    def tearDown(self):
        """Turn off patches"""
        mock.patch.stopall()

    def test_cloc_reads_files(self):
        """cloc is called and reads the output csv file."""
        actual = loc.get_cloc(scm.Project())
        self.run_.assert_called_with("cloc --csv --by-file .".split(), cwd=pl.Path("."))
        expected = pd.read_csv(
            io.StringIO(
                textwrap.dedent(
                    """\
            language,path,blank,comment,code
            Python,internals.py,55,50,130
            Python,tests.py,29,92,109
            Python,setup.py,4,2,30
            C#,".NETFramework,Version=v4.7.2.AssemblyAttributes.cs",0,1,3
            """
                )
            ),
            dtype={"path": "string", "language": "string"},
        )
        self.assertEqual(expected, actual)

    def test_cloc_not_found(self):
        """Clean error message when cloc is not found in the path."""
        self.run_.side_effect = [FileNotFoundError]
        with self.assertRaises(FileNotFoundError) as context:
            _ = loc.get_cloc(scm.Project())
        self.assertIn("cloc", str(context.exception))


class TestClocCall(unittest.TestCase):
    """Checking the calls made by get_cloc()"""

    @mock.patch("pathlib.Path.glob", autospec=True, return_value=[])
    def test_cloc_fails_if_not_in_root(self, path_glob):
        """Make sure that command line call checks it is run from the root."""
        with self.assertRaises(ValueError) as context:
            loc.get_cloc(scm.Project())
        path_glob.assert_called_with(mock.ANY, pattern=".svn")
        self.assertIn("git or svn root", str(context.exception))

    @mock.patch("codemetrics.internals.check_run_in_root", autospec=True)
    @mock.patch("codemetrics.internals.run", autospec=True)
    def test_cloc_called_with_path(self, run, _):
        """Make sure the path is passed as argument to cloc when passed to the function."""
        loc.get_cloc(scm.Project(), path="some-path")
        run.assert_called_with(
            ["cloc", "--csv", "--by-file", "some-path"], cwd=pl.Path(".")
        )
