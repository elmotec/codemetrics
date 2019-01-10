#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import textwrap
import io
import sys

import pandas as pd

from codemetrics import vega
from tests.utils import DataFrameTestCase


class BuildHierarchyTest(DataFrameTestCase):
    """Tests function for build_hierarchy function."""

    def setUp(self):
        """Set up the test case."""
        super().setUp()
        self.input_df = pd.read_csv(io.StringIO(textwrap.dedent(r'''
        path,complexity,changes
        pandas\tests\io\data\banklist.html,4832,2.0
        doc\source\_static\banklist.html,4831,1.0
        pandas\tests\io\test_pytables.py,3961,27.0
        pandas\tests\test_window.py,2970,19.0
        pandas\io\pytables.py,2960,36.0''')))

    def test_input_does_not_change(self):
        """Make sure the input does not get modified."""
        backup = self.input_df.copy()
        _ = vega.build_hierarchy(self.input_df)
        self.assertEqual(self.input_df, backup)

    @unittest.skipUnless(sys.platform.startswith('win'), 'requires Windows')
    def test_path_hierarchy(self):
        """Main case where we build a hierarchy of paths"""
        actual = vega.build_hierarchy(self.input_df[['path']])
        expected = pd.read_csv(io.StringIO(textwrap.dedent(r'''
        id,parent,path
        0,,
        1,0,doc
        2,0,pandas
        3,1,doc\source
        4,2,pandas\io
        5,2,pandas\tests
        6,5,pandas\tests\io
        7,3,doc\source\_static
        8,6,pandas\tests\io\data
        9,4,pandas\io\pytables.py
        10,5,pandas\tests\test_window.py
        11,6,pandas\tests\io\test_pytables.py
        12,7,doc\source\_static\banklist.html
        13,8,pandas\tests\io\data\banklist.html''')),
            dtype={'id': 'int64', 'parent': 'float', 'path': 'object'})
        expected.loc[expected['path'].isnull(), 'path'] = ''
        self.assertEqual(expected, actual)

    def test_unix_path_hierarchy(self):
        """Main case where we build a hierarchy of paths"""
        actual = vega.build_hierarchy(self.input_df['path'].\
                                         str.replace('\\', '/').\
                                         str.replace('^\./','').\
                                         to_frame('path'),
                                         root='')
        expected = pd.read_csv(io.StringIO(textwrap.dedent(r'''
        id,parent,path
        0,,
        1,0,doc
        2,0,pandas
        3,1,doc/source
        4,2,pandas/io
        5,2,pandas/tests
        6,5,pandas/tests/io
        7,3,doc/source/_static
        8,6,pandas/tests/io/data
        9,4,pandas/io/pytables.py
        10,5,pandas/tests/test_window.py
        11,6,pandas/tests/io/test_pytables.py
        12,7,doc/source/_static/banklist.html
        13,8,pandas/tests/io/data/banklist.html''')),
            dtype={'id': 'int64', 'parent': 'float', 'path': 'object'})
        expected.loc[expected['path'].isnull(), 'path'] = ''
        self.assertEqual(expected, actual)

    def test_root_not_found(self):
        """Get a decent diagnostic when the root is not found."""
        with self.assertRaises(ValueError) as err:
            actual = vega.build_hierarchy(self.input_df, root='X')


class TestHotSpots(DataFrameTestCase):

    def setUp(self):
        """Set up the test case."""
        super().setUp()
        self.df = pd.read_csv(io.StringIO(textwrap.dedent(r'''
        path,complexity,changes
        pandas/tests/io/data/banklist.html,4832,2.0
        doc/source/_static/banklist.html,4831,1.0
        pandas/tests/io/test_pytables.py,3961,27.0
        pandas/tests/test_window.py,2970,19.0
        pandas/io/pytables.py,2960,36.0''')))

    def test_vis_hot_spots(self):
        """Test conversion of get_hot_spots data frame to vega visualization."""
        actual = vega.vis_hot_spots(self.df)
        # Check it out on https://vega.github.io/editor/#/custom/vega
        expected = {
          "$schema": "https://vega.github.io/schema/vega/v4.json",
          "width": 400,
          "height": 300,
          "padding": 5,
          "autosize": "none",
          "data": [
            {
              "name": "tree",
              "values": [
                {
                  "id": 0,
                  "parent": None,
                  "path": "",
                  "complexity": 0.0,
                  "changes": 0.0
                },
                {
                  "id": 1,
                  "parent": 0.0,
                  "path": "pandas",
                  "complexity": 0.0,
                  "changes": 0.0
                },
                {
                  "id": 2,
                  "parent": 1.0,
                  "path": "pandas/io",
                  "complexity": 0.0,
                  "changes": 0.0
                },
                {
                  "id": 3,
                  "parent": 1.0,
                  "path": "pandas/tests",
                  "complexity": 0.0,
                  "changes": 0.0
                },
                {
                  "id": 4,
                  "parent": 3.0,
                  "path": "pandas/tests/io",
                  "complexity": 0.0,
                  "changes": 0.0
                },
                {
                  "id": 5,
                  "parent": 2.0,
                  "path": "pandas/io/pytables.py",
                  "complexity": 2960.0,
                  "changes": 36.0
                },
                {
                  "id": 6,
                  "parent": 3.0,
                  "path": "pandas/tests/test_window.py",
                  "complexity": 2970.0,
                  "changes": 19.0
                },
                {
                  "id": 7,
                  "parent": 4.0,
                  "path": "pandas/tests/io/test_pytables.py",
                  "complexity": 3961.0,
                  "changes": 27.0
                }
              ],
              "transform": [
                {
                  "type": "stratify",
                  "key": "id",
                  "parentKey": "parent"
                },
                {
                  "type": "pack",
                  "field": "changes",
                  "sort": {
                    "field": "value",
                    "order": "descending"
                  },
                  "size": [
                    {
                      "signal": "width"
                    },
                    {
                      "signal": "height"
                    }
                  ]
                }
              ]
            }
          ],
          "scales": [
            {
              "name": "color",
              "type": "linear",
              "domain": {
                "data": "tree",
                "field": "complexity"
              },
              "range": {
                "scheme": "yelloworangered"
              },
              "domainMin": 0
            }
          ],
          "marks": [
            {
              "type": "symbol",
              "from": {
                "data": "tree"
              },
              "encode": {
                "enter": {
                  "shape": {
                    "value": "circle"
                  },
                  "fill": {
                    "scale": "color",
                    "field": "complexity"
                  },
                  "tooltip": {
                    "signal": "datum.path + (datum.changes ? ', ' + datum.changes + ' changes' : '') + (datum.complexity ? ', ' + datum.complexity + ' complexity': '')"
                  }
                },
                "update": {
                  "x": {
                    "field": "x"
                  },
                  "y": {
                    "field": "y"
                  },
                  "size": {
                    "signal": "4 * datum.r * datum.r"
                  },
                  "stroke": {
                    "value": "white"
                  },
                  "strokeWidth": {
                    "value": 0.5
                  }
                },
                "hover": {
                  "stroke": {
                    "value": "black"
                  },
                  "strokeWidth": {
                    "value": 2
                  }
                }
              }
            }
          ]
        }
        self.assertEqual(actual, expected)
