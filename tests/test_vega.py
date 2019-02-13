#!/usr/bin/env python
# -*- coding: utf-8 -*-

import io
import sys
import textwrap
import unittest

import pandas as pd

from codemetrics import vega
from tests.utils import DataFrameTestCase


class BuildHierarchyTest(DataFrameTestCase):
    """Tests function for build_hierarchy function."""

    def setUp(self):
        """Set up the test case."""
        super().setUp()
        self.input_df = pd.read_csv(io.StringIO(textwrap.dedent(r'''
        path,lines,changes
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
                               dtype={'id': 'int64', 'parent': 'float',
                                      'path': 'object'})
        expected.loc[expected['path'].isnull(), 'path'] = ''
        self.assertEqual(expected, actual)

    def test_unix_path_hierarchy(self):
        """Main case where we build a hierarchy of paths"""
        actual = vega.build_hierarchy(self.input_df['path'].
                                      str.replace(r'\\', '/').
                                      str.replace(r'^\./', '').
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
                               dtype={'id': 'int64', 'parent': 'float',
                                      'path': 'object'})
        expected.loc[expected['path'].isnull(), 'path'] = ''
        self.assertEqual(expected, actual)

    def test_root_not_found(self):
        """Get a decent diagnostic when the root is not found."""
        with self.assertRaises(ValueError) as context:
            vega.build_hierarchy(self.input_df, root='X')
        self.assertIn('cannot find root', str(context.exception))


class TestHotSpots(DataFrameTestCase):

    def setUp(self):
        """Set up the test case."""
        super().setUp()
        self.df = pd.read_csv(io.StringIO(textwrap.dedent(r'''
        path,lines,changes
        pandas/tests/io/data/banklist.html,4832,2.0
        doc/source/_static/banklist.html,4831,1.0
        pandas/tests/io/test_pytables.py,3961,27.0
        pandas/tests/test_window.py,2970,19.0
        pandas/io/pytables.py,2960,36.0''')))

    def test_vis_hot_spots(self):
        """Test conversion of get_hot_spots data frame to vega visualization."""
        actual = vega.vis_hot_spots(
            self.df.sort_values(by='changes', ascending=False).head(3))
        # Check it out on https://vega.github.io/editor/#/custom/vega
        expected = {'$schema': 'https://vega.github.io/schema/vega/v4.json',
                    'autosize': 'none',
                    'data': [{'name': 'tree',
                              'transform': [{'key': 'id',
                                             'parentKey': 'parent',
                                             'type': 'stratify'},
                                            {'field': 'size',
                                             'size': [{'signal': 'width'},
                                                      {'signal': 'height'}],
                                             'sort': {'field': 'value',
                                                      'order': 'descending'},
                                             'type': 'pack'}],
                              'values': [{'intensity': 0.0,
                                          'id': 0,
                                          'size': 0.0,
                                          'parent': None,
                                          'path': ''},
                                         {'intensity': 0.0,
                                          'id': 1,
                                          'size': 0.0,
                                          'parent': 0.0,
                                          'path': 'pandas'},
                                         {'intensity': 0.0,
                                          'id': 2,
                                          'size': 0.0,
                                          'parent': 1.0,
                                          'path': 'pandas/tests'},
                                         {'intensity': 0.0,
                                          'id': 3,
                                          'size': 0.0,
                                          'parent': 2.0,
                                          'path': 'pandas/tests/io'},
                                         {'intensity': 0.0,
                                          'id': 4,
                                          'size': 0.0,
                                          'parent': 1.0,
                                          'path': 'pandas/io'},
                                         {'intensity': 19.0,
                                          'id': 5,
                                          'size': 2970.0,
                                          'parent': 2.0,
                                          'path': 'pandas/tests/test_window.py'},
                                         {'intensity': 27.0,
                                          'id': 6,
                                          'size': 3961.0,
                                          'parent': 3.0,
                                          'path': 'pandas/tests/io/test_pytables.py'},
                                         {'intensity': 36.0,
                                          'id': 7,
                                          'size': 2960.0,
                                          'parent': 4.0,
                                          'path': 'pandas/io/pytables.py'}]}],
                    'height': 300,
                    'marks': [{'encode': {'enter': {
                        'fill': {'field': 'intensity', 'scale': 'color'},
                        'shape': {'value': 'circle'},
                        'tooltip': {'signal': 'datum.path + '
                                              "(datum.intensity ? ', "
                                              "' + datum.intensity + "
                                              "' changes' : '') + "
                                              "(datum.size ? ', ' + "
                                              "datum.size + ' lines' "
                                              ": '')"}},
                        'hover': {
                            'stroke': {'value': 'black'},
                            'strokeWidth': {'value': 2}},
                        'update': {'size': {
                            'signal': '4 * datum.r * datum.r'},
                            'stroke': {
                                'value': 'white'},
                            'strokeWidth': {
                                'value': 0.5},
                            'x': {'field': 'x'},
                            'y': {'field': 'y'}}},
                        'from': {'data': 'tree'},
                        'type': 'symbol'}],
                    'padding': 5,
                    'scales': [
                        {'domain': {'data': 'tree', 'field': 'intensity'},
                         'domainMin': 0,
                         'name': 'color',
                         'range': {'scheme': 'yelloworangered'},
                         'type': 'linear'}],
                    'width': 400}
        self.assertEqual(expected, actual)

    def test_empty_frame_generates_error(self):
        """Test that an empty frame generate an error."""
        with self.assertRaises(ValueError) as context:
            _ = vega.vis_hot_spots(self.df.head(0))
            self.assertIn('empty', str(context.exception))
