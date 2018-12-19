#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for loc (lines of code) module."""

import textwrap
import unittest
from unittest import mock
import io

import pandas as pd

import codemetrics.loc as loc
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
        self.run_patcher = mock.patch('codemetrics.internals._run',
                                      autospec=True,
                                      return_value=self.run_output.split('\n'))
        self.run_ = self.run_patcher.start()

    def tearDown(self):
        """Turn off patches"""
        self.run_patcher.stop()

    def test_cloc_reads_files(self):
        """cloc is called and reads the output csv file."""
        actual = loc.get_cloc()
        self.run_.assert_called_with('cloc --csv --by-file .')
        usecols = 'language,filename,blank,comment,code'.split(',')
        expected = pd.read_csv(io.StringIO(self.run_output), usecols=usecols)
        expected.rename(columns={'filename': 'path'})
        self.assertEqual(expected, actual)

    def test_cloc_not_found(self):
        """Clean error message when cloc is not found in the path."""
        self.run_.side_effect = [FileNotFoundError]
        with self.assertRaises(FileNotFoundError) as context:
            _ = loc.get_cloc()
        self.assertIn('cloc', str(context.exception))
