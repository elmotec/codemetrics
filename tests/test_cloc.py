#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for loc (lines of code) module."""

import textwrap
import unittest
from unittest import mock
import io

import pandas as pd

import codemetrics.cloc as loc
from tests.utils import add_data_frame_equality_func


class SimpleDirectory(unittest.TestCase):
    """Given a simple directory."""

    def setUp(self):
        """Mocks the internal run command."""
        add_data_frame_equality_func(self)
        self.run_output = textwrap.dedent("""\
        language,filename,blank,comment,code,"http://cloc.sourceforge.net"
        Python,internals.py,55,50,130
        Python,tests.py,29,92,109
        Python,setup.py,4,2,30
        """)
        cmi = 'codemetrics.internals.'
        self.run_patcher = mock.patch(cmi + 'run', autospec=True,
                                      return_value=self.run_output)
        self.check_patcher = mock.patch(cmi + 'check_run_in_root',
                                        autospec=True)
        self.run_ = self.run_patcher.start()
        self.check_run_from_root = self.check_patcher.start()

    def tearDown(self):
        """Turn off patches"""
        mock.patch.stopall()

    def test_cloc_reads_files(self):
        """cloc is called and reads the output csv file."""
        actual = loc.get_cloc()
        self.run_.assert_called_with('cloc --csv --by-file .')
        usecols = 'language,filename,blank,comment,code'.split(',')
        expected = pd.read_csv(io.StringIO(self.run_output), usecols=usecols).\
            rename(columns={'filename': 'path'})
        self.assertEqual(expected, actual)

    def test_cloc_not_found(self):
        """Clean error message when cloc is not found in the path."""
        self.run_.side_effect = [FileNotFoundError]
        with self.assertRaises(FileNotFoundError) as context:
            _ = loc.get_cloc()
        self.assertIn('cloc', str(context.exception))

    @mock.patch('pathlib.Path.glob', autospect=True, return_value=[])
    def test_cloc_runs_from_root(self, path_glob):
        """Make sure that command line call checks it is run from the root."""
        self.check_patcher.stop()
        with self.assertRaises(ValueError) as context:
            loc.get_cloc()
        path_glob.assert_called()
        self.assertIn('git or svn root', str(context.exception))
