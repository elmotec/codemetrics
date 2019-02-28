#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Top-level module for codemetrics package."""

# noinspection SpellCheckingInspection
__author__ = """Elmotec"""
__email__ = 'elmotec@gmx.com'
__version__ = '0.8.2'

from .core import *
from .git import *
from .svn import *
from .cloc import *


__doc__ = """"
codemetrics
===========

Code metrics is a simple Python module that leverage your source control 
management (SCM) tool and pandas to generate insight on your code base.

"""
