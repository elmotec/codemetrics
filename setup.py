#!/usr/bin/env python
# encoding: utf-8

"""Packaging script."""

import os
from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))
readme = open(os.path.join(here, 'README.rst')).read()

setup(
    name="codemetrics",
    description='SCM mining utility classes',
    long_description=readme,
    long_description_content_type='text/rst',
    version="0.5",
    author="Jérôme Lecomte",
    author_email="elmotec@gmx.com",
    license="MIT",
    keywords="code metrics mining scm subversion svn Adam Tornhill utilities",
    url="http://github.com/elmotec/codemetrics",
    py_modules=['codemetrics'],
    entry_points={'console_scripts': ['codemetrics=codemetrics:main']},
    test_suite='tests',
    setup_requires=['pandas'],
    tests_require=['tqdm'],
    python_requires='>=3.6',
    classifiers=["Development Status :: 4 - Beta",
                 "License :: OSI Approved :: MIT License",
                 "Environment :: Console",
                 "Natural Language :: English",
                 "Programming Language :: Python :: 3.6",
                 "Topic :: Software Development",
                 "Topic :: Utilities",
                 "Topic :: Software Development :: Version Control",
                 "Intended Audience :: Developers",
                ],
)
