#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Subversion related functions."""

import pathlib as pl
import xml.etree.ElementTree as ET
import datetime as dt

import pandas as pd
import dateutil as du

from . import pbar
from . import internals
from . import log, LogEntry


class SvnLogCollector:
    """Collect log from Subversion.

    :param datetime.datetime after: limits the log to entries after that date.

    If after is not tz-aware, the date will automatically be assumed to be UTC
    based.

    """

    def __init__(self, path=None, svn_program=None, after=None,
                 progress_bar=None):
        """Initialize.

        :param tqdm.tqdm progress_bar: implements tqdm.tqdm interface.

        """
        self.path = path or '.'
        self.svn_program = svn_program or 'svn'
        self.after = after
        self.progress_bar = progress_bar
        if self.progress_bar is not None and self.after is None:
            raise ValueError("progress_bar requires 'after' parameter")

    def get_relative_url(self):
        """Relative URL so we can generate local paths."""
        relative_url = None
        for line in internals._run(f'{self.svn_program} info {self.path}'):
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
        rev = elem.attrib['revision']
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
                log.warning(f'{err} processing rev {rev}')
                path = None
            def to_date(datestr):
                """Convert str to datetime.datetime.

                The date returned by Subversion is UTC according to git-svn man
                page (FIXME). So we force the timezone to UTC as well.

                """
                return du.parser.parse(datestr).replace(tzinfo=dt.timezone.utc)

            entry = LogEntry(rev, values['author'], to_date(values['date']),
                             other['text-mods'], other['kind'], other['action'],
                             other['prop-mods'], path, values['msg'])
            yield entry

    def process(self, xml, relative_url):
        """Convert output of svn log --xml -v to a csv.

        :param iter(str) xml: iterable of string (one for each line)
        :param str relative_url: relative url for path elements.

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
        xml = internals._run(command + self.path)
        records = []
        with pbar.ProgressBarAdapter(self.progress_bar,
                                     self.after) as progress_bar:
            for entry in self.process(xml, relative_url):
                records.append(entry)
                progress_bar.update(entry.date)
        columns = ['revision', 'author', 'date', 'textmods', 'kind',
                   'action', 'propmods', 'path', 'message']
        result = pd.DataFrame.from_records(records, columns=columns)
        result['date'] = pd.to_datetime(result['date'], utc=True)
        # FIXME categorize columns that should be categorized.
        return result


def get_svn_log(path=None, after=None, svn_program=None, progress_bar=None):
    """Entry point to retrieve Subversion log.

    :param str path: location of checked out subversion repository.
    :param datetime.datetime after: only get the log after a certain time stamp.
    :param str svn_program: svn client (defaults to svn).
    :param progress_bar: tqdm.tqdm progress bar.

    """
    collector = SvnLogCollector(path=path, after=after,
                                svn_program=svn_program,
                                progress_bar=progress_bar)
    return collector.get_log()
