#!/usr/bin/env python
# encoding: utf-8


"""Metrics offer a bunch of function useful to analyze a code base."""


import subprocess
import logging
import xml.etree.ElementTree as ET
import datetime as dt

import pandas as pd


log = logging.getLogger()
log.addHandler(logging.NullHandler())


def get_now():
    """Get current time stamp as pd.TimeStamp.

    This is also useful to patch retrieval of the current date/time.

    """
    return pd.to_datetime(dt.datetime.now())


def _run(command, **kwargs):
    """Exceute command passed as argument and return output.

    If the command does not return 0, will throw subprocess.CalledProcessError.

    :return: output of the command as iter(str)

    """
    if 'shell' not in kwargs:
        kwargs['shell'] = True
    if 'universal_newlines' not in kwargs:
        kwargs['universal_newlines'] = True
    return subprocess.check_output(command, **kwargs).split('\n')


class _DfSpec:
    """Specifies what the SCM DataFrame should look like."""
    columns = ['revision', 'author', 'date', 'textmods', 'kind',
               'action', 'propmods', 'path', 'message']



class BaseReport:
    """Base classes for the reports."""

    def __init__(self, path, after=None):
        """Initialization.

        :param str path: local repository to work with
        :param datetime.datetime after: limit how far back to mine SCM log.

        """
        self.path = path
        self.after = after
        # Will holds the result report as a pandas.DataFrame.
        self.data = None

    def get_svn_log(self):
        """Call svn log --xml -v and return the output as a DataFrame.

        :param str path: path to execute svn log in.
        :return: pandas.DataFrame

        """
        def process_entry(log_entry):
            """Convert a single xml <logentry/> element to csv rows.

            :param str log_entry: <logentry/> element.
            :yield: one or more csv rows.

            """

            elem = ET.fromstring(log_entry)
            revision = elem.attrib['revision']
            values = {}
            for sub in ['author', 'date', 'msg']:
                try:
                    values[sub] = elem.find(f'./{sub}').text
                except (AttributeError, SyntaxError):
                    log.warning('failed to retrieve %s in %s', sub, log_entry)
                    values[sub] = None
            if values['msg']:
                values['msg'] = values['msg'].replace('\n', ' ')
            for path_elem in elem.findall('*/path'):
                other = {}
                for sub in ['text-mods', 'kind', 'action', 'prop-mods']:
                    try:
                        other[sub] = path_elem.attrib[sub]
                    except (AttributeError, SyntaxError, KeyError):
                        other[sub] = None
                try:
                    path = path_elem.text
                except (AttributeError, SyntaxError):
                    path = None
                row = (revision,
                       values['author'],
                       values['date'],
                       other['text-mods'],
                       other['kind'],
                       other['action'],
                       other['prop-mods'],
                       path,
                       values['msg'])
                yield row

        def process(xml):
            """Convert output of svn log --xml -v to a csv.

            :param iter(str) xml: iterable of string (one for each line)

            :return: iter(tuple) containing the parsed entries.

            """
            log_entry = ''
            for line in xml:
                if line.startswith('<logentry'):
                    log_entry += line
                    continue
                if not log_entry:
                    continue
                log_entry += line
                if not line.startswith('</logentry>'):
                    continue
                yield from process_entry(log_entry)
                log_entry = ''

        command = 'svn log --xml -v '
        if self.after:
            command += '-r {' + self.after.strftime('%Y-%m-%d') + '}:HEAD '
        xml = _run(command + self.path)
        records = [entry for entry in process(xml)]
        result = pd.DataFrame.from_records(records, columns=_DfSpec.columns)
        return result

    def get_log(self):
        """Forwards to get_svn_log."""
        return self.get_svn_log()


class AgeReport(BaseReport):
    """Reports files or components age in days."""

    def __init__(self, path, after=None):
        """See BaseReport.__init__ for options."""
        super().__init__(path, after=after)

    def generate(self):
        """Generate report from SCM data."""
        columns = ['path', 'kind']
        df1 = self.get_log()[columns + ['date']].copy()
        now = get_now()
        df1['age'] = (now - pd.to_datetime(df1['date']))
        df1 = df1[columns + ['age']].groupby(['path']).min().reset_index()
        df1['age'] /= pd.Timedelta(1, unit='D')
        self.data = df1
        return self.data
