#!/usr/bin/env python
# encoding: utf-8

"""Packaging script."""

import os
from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))
readme = open(os.path.join(here, 'README.md')).read()

setup(
    name="codemetrics",
    version="0.1",
    author="Jérôme Lecomte",
    author_email="elmotec@gmx.com",
    description='SCM mining utility classes',
    license="MIT",
    keywords="TBD",
    url="http://github.com/elmotec/codemetrics",
    py_modules=['codemetrics'],
    entry_points={'console_scripts': ['codemetrics=codemetrics:main']},
    long_description=readme,
    test_suite='tests',
    setup_requires=[],
    tests_require=['pandas'],
    classifiers=["Development Status :: 5 - Production/Stable",
                 "License :: OSI Approved :: MIT License",
                 "Environment :: Console",
                 "Natural Language :: English",
                 "Programming Language :: Python :: 3.6",
                 "Topic :: Software Development",
                 "Topic :: Utilities",
                 "Intended Audience :: Developers",
                ],
)
