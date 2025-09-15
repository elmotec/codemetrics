#!/usr/bin/env python
# -*- coding: utf-8 -*-
# flake8: noqa

"""Top-level module for codemetrics package."""

# noinspection SpellCheckingInspection
__author__ = """Elmotec"""
__email__ = "elmotec@gmx.com"
__version__ = "1.0.0"

from .cloc import get_cloc
from .core import (
    get_ages,
    get_co_changes,
    get_complexity,
    get_hot_spots,
    get_mass_changes,
    guess_components,
)
from .git import GitProject
from .internals import log
from .scm import get_log
from .svn import SvnProject

__doc__ = """"
codemetrics
===========

Code metrics is a simple Python module that leverage your source control
management (SCM) tool and pandas to generate insight on your code base.

"""
