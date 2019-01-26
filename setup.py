#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

import os
import setuptools

here = os.path.abspath(os.path.dirname(__file__))

with open('README.rst') as readme_file:
    readme = readme_file.read()
with open('HISTORY.rst') as history_file:
    history = history_file.read()


# Simple version to extract requirements from requirements files.
def get_requirements(filename):
    lines = list(val.strip() for val in open(filename))
    filtered = []
    for line in lines:
        line = line.strip().split('#')[0]
        if not line or line.startswith('-'):
            continue
        filtered.append(line)
    return filtered


requirements = get_requirements('requirements.txt')

setup_requirements = []

test_requirements = []

setuptools.setup(
    name="codemetrics",
    description='SCM mining utility classes',
    long_description=readme + '\n\n' + history,
    long_description_content_type='text/x-rst',
    version='0.7.0',
    author="Elmotec",
    author_email="elmotec@gmx.com",
    license="MIT",
    keywords="code metrics mining scm subversion svn Adam Tornhill utilities",
    url="http://github.com/elmotec/codemetrics",
    entry_points={'console_scripts': ['codemetrics=codemetrics:main']},
    install_requires=requirements,
    include_package_data=True,
    packages=setuptools.find_packages(include=['codemetrics']),
    setup_requires=setup_requirements,
    test_suite='tests',
    tests_require=test_requirements,
    python_requires='>=3.6',
    classifiers=["Development Status :: 4 - Beta",
                 "License :: OSI Approved :: MIT License",
                 "Environment :: Console",
                 "Natural Language :: English",
                 "Programming Language :: Python :: 3.6",
                 "Programming Language :: Python :: 3.7",
                 "Topic :: Software Development",
                 "Topic :: Utilities",
                 "Topic :: Software Development :: Version Control",
                 "Intended Audience :: Developers",
                 "Intended Audience :: Education",
                 ],
)
