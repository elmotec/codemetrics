#!/usr/bin/env python
# encoding: utf-8


"""Metrics offer a bunch of function useful to analyze a code base."""


import subprocess
import logging
import xml.etree.ElementTree as ET
import datetime as dt
import logging
import csv
import pathlib as pl

import pandas as pd


log = logging.getLogger(__name__)
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
    try:
        log.info(command)
        return subprocess.check_output(command, **kwargs).split('\n')
    except subprocess.CalledProcessError as err:
        log.warning(err)
        raise


class SvnLogCollector:
    """Collect log from Subversion."""

    def __init__(self, path, svn_program=None, after=None):
        """Initialize."""
        self.path = path
        self.svn_program = svn_program or 'svn'
        self.after = after

    def get_relative_url(self):
        """Relative URL so we can generate local paths."""
        relative_url = None
        for line in _run(f'{self.svn_program} info {self.path}'):
            if line.startswith('Relative URL'):
                relative_url = pl.Path(line.split(': ^')[1])
                break
        return relative_url

    def process_entry(self, log_entry, relative_url):
        """Convert a single xml <logentry/> element to csv rows.

        :param str log_entry: <logentry/> element.
        :param str relative_url: relative url for path elements.

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
                path = str(pl.Path(path_elem.text).relative_to(relative_url))
            except (AttributeError, SyntaxError, ValueError) as err:
                log.warning(f'{err} processing revision {revision}')
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

    def process(self, xml, relative_url):
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
            yield from self.process_entry(log_entry, relative_url)
            log_entry = ''

    def get_log(self):
        """Call svn log --xml -v and return the output as a DataFrame."""
        relative_url = self.get_relative_url()
        command = f'{self.svn_program} log --xml -v '
        if self.after:
            command += '-r {' + self.after.strftime('%Y-%m-%d') + '}:HEAD '
        xml = _run(command + self.path)
        records = [entry for entry in self.process(xml, relative_url)]
        columns = ['revision', 'author', 'date', 'textmods', 'kind',
                   'action', 'propmods', 'path', 'message']
        result = pd.DataFrame.from_records(records, columns=columns)
        return result


class BaseReport:
    """Base classes for the reports."""

    def __init__(self, path, after=None,
                 cloc_program=None, svn_program=None):
        """Initialization.

        :param str path: local repository to work with
        :param datetime.datetime after: limit how far back to mine SCM log.
        :param str cloc_program: name of cloc program (e.g. cloc.pl)
        :param str svn_program: name and location of svn client program.

        """
        self.path = path
        self.after = after
        self.cloc_program = cloc_program or 'cloc'
        self.svn_program = svn_program or 'svn'

    def get_log(self):
        """Forwards to get_svn_log."""
        collector = SvnLogCollector(self.path, after=self.after,
                                    svn_program=self.svn_program)
        return collector.get_log()

    def get_cloc(self):
        cmdline = f'{self.cloc_program} --csv --by-file {self.path}'
        records = []
        reader = csv.reader(_run(cmdline))
        for record in reader:
            if len(record) >= 5 and record[0]:
                if record[0] != 'language':
                    record[1] = str(pl.Path(record[1]))
                    record[2:5] = [int(val) for val in record[2:5]]
                records.append(record[:5])
        columns = 'language,filename,blank,comment,code'.split(',')
        return pd.DataFrame.from_records(records[1:], columns=columns)

    def collect(self, **kwargs):
        """Collect raw data from command line passed in kwargs."""
        data = {}
        for key, func in kwargs.items():
            data[key] = func(self)
        return data


class AgeReport(BaseReport):
    """Reports files or components age in days."""

    def __init__(self, path, **kwargs):
        """See `BaseReport.__init__`."""
        super().__init__(path, **kwargs)

    def collect(self):
        """Collect data needed for report."""
        return super().collect(log=BaseReport.get_log)

    def generate(self, data=None):
        """Generate report from SCM data.

        If data is not passed, calls self.get_log() to retrieve the raw
        log from SCM.

        :param pandas.DataFrame data: data overrides.

        """
        columns = ['path', 'kind']
        if data is None:
            data = self.collect()
        assert 'log' in data
        df = data['log'][columns + ['date']].copy()
        now = get_now()
        df['age'] = (now - pd.to_datetime(df['date']))
        df = df[columns + ['age']].groupby(['path']).min().reset_index()
        df['age'] /= pd.Timedelta(1, unit='D')
        return df


class HotSpotReport(BaseReport):
    """Identifies changing high complexity files."""

    def __init__(self, path, **kwargs):
        """See `BaseReport.__init__`."""
        super().__init__(path, **kwargs)

    def collect(self):
        """Collect data necessary to the generation of the report.

        :return: output of the SCM log and cloc identified by the keys log
                 and cloc respectively
        :rtype: dict(pandas.DataFrame)

        """
        return super().collect(log=BaseReport.get_log,
                               cloc=BaseReport.get_cloc)

    def generate(self, data=None):
        """Generate report from SCM data.

        If data is not passed, calls self.get_log() to retrieve the raw
        log from SCM.

        :param dict(pandas.DataFrame) data: data overrides.

        """
        if not data:
            data = self.collect()
        log = data['log']
        if 'cloc' in data:
            c_df = data['cloc'][['filename', 'code']]
            c_df = c_df.rename(columns={'code': 'complexity'})
        ch_df = log['path'].value_counts().to_frame('changes')
        return pd.merge(c_df, ch_df, right_index=True, left_on='filename',
                        how='outer')


