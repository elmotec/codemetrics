#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Top-level module for codemetrics package."""

# noinspection SpellCheckingInspection
__author__ = """Jérôme Lecomte"""
__email__ = 'elmotec@gmx.com'
__version__ = '0.6.1'

from .core import *
from .git import *
from .svn import *
from .loc import *


__doc__ = """"
codemetrics
===========

Code metrics is a simple Python module that leverage your source control 
management (SCM) tool to generate insight on your code base.

"""
