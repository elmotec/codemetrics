#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `codemetrics.pbar`"""

import datetime as dt
import unittest
from unittest import mock
import tqdm
import codemetrics as cm


class ProgressBarAdapterTest(unittest.TestCase):
    """Test ProgressBarAdapter"""

    def setUp(self):
        pass

    @mock.patch('codemetrics.internals.get_now', autospec=True,
                return_value=dt.datetime(2018, 2, 13))
    @mock.patch('tqdm.tqdm', autospec=True)
    def test_initialization(self, tqdm_, get_now):
        after = dt.datetime(2018, 2, 1)
        with cm.pbar.ProgressBarAdapter(tqdm.tqdm(), after=after) as pb:
            pb.update(pb.today - dt.timedelta(3))
            pb.update(pb.today - dt.timedelta(1))
        expected = [mock.call(9), mock.call(2), mock.call(1)]
        self.assertEqual(tqdm_().update.mock_calls, expected)
