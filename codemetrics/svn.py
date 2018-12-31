#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Subversion related functions."""

import pathlib as pl
import xml.etree.ElementTree as ET
import datetime as dt

import dateutil as du
import tqdm
import numpy as np

from . import scm
from . import internals
from .internals import log


class _SvnLogCollector(scm._ScmLogCollector):
    """Collect log from Subversion."""

    _args = 'log --xml -v'

    def __init__(self, svn_program='svn', **kwargs):
        """Initialize.

        Args:
            svn_program: name of svn client.
            **kwargs: passed to :class:`scm._ScmLogCollector`
`
        """
        super().__init__(**kwargs)
        self.svn_program = svn_program or 'svn'
        self._relative_url = None

    @property
    def relative_url(self):
        """Relative URL so we can generate local paths."""
        if self._relative_url is None:
            for line in internals._run(f'{self.svn_program} info {self.path}'):
                if line.startswith('Relative URL'):
                    self._relative_url = pl.Path(line.split(': ^')[1])
                    break
        return self._relative_url

    def process_entry(self, log_entry):
        """Convert a single xml <logentry/> element to csv rows.

        Args:
            log_entry: <logentry/> element.

        Yields:
            One or more csv rows.

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
                path = str(pl.Path(path_elem.text).relative_to(self.relative_url))
            except (AttributeError, SyntaxError, ValueError) as err:
                log.warning(f'{err} processing rev {rev}')
                path = None

            def to_date(datestr):
                """Convert str to datetime.datetime.

                The date returned by Subversion is UTC according to git-svn man
                page. Date tzinfo is set to UTC.

                added and removed columns are set to np.nan for now.

                """
                return du.parser.parse(datestr).replace(tzinfo=dt.timezone.utc)

            entry = scm.LogEntry(rev, values['author'], to_date(values['date']),
                                 other['text-mods'], other['kind'],
                                 other['action'], other['prop-mods'], path,
                                 values['msg'], np.nan, np.nan)
            yield entry

    def get_log_entries(self, xml):
        # See parent.
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
            yield from self.process_entry(log_entry)
            log_entry = ''

    def get_log(self):
        """Call svn log --xml -v and return the output as a DataFrame."""
        relative_url = self.relative_url
        if self.before is None:
            before = 'HEAD'
        else:
            before = '{' + f'{self.before:%Y-%m-%d}' + '}'
        after = '{' + f'{self.after:%Y-%m-%d}' + '}'
        command = f'{self.svn_program} {_SvnLogCollector._args} -r {after}:{before}'
        command_with_path = f'{command} {self.path}'
        results = internals._run(command_with_path)
        return self.process_output_to_df(results)


def get_svn_log(
    after: dt.datetime=None,
    before: dt.datetime=None,
    path: str='.',
    svn_program: str='svn',
    progress_bar: tqdm.tqdm=None):
    """Entry point to retrieve Subversion log.

    Args:
        after: only get the log after time stamp
               (defaults to one year ago).
        before: only get the log before time stamp
                (defaults to now).
        path: location of checked out subversion repository root.
        svn_program: svn client (defaults to svn).
        progress_bar: tqdm.tqdm progress bar.

    Returns:
        pandas.DataFrame with columns matching the fields of
        :class:`codemetrics.scm.LogEntry`.

    Example::

        >>> last_year = datetime.datetime.now() - datetime.timedelta(365)
        >>> log_df = cm.svn.get_svn_log(path='src', after=last_year)

    """
    internals._check_run_in_root(path)
    collector = _SvnLogCollector(after=after, before=before, path=path,
                                 svn_program=svn_program,
                                 progress_bar=progress_bar)
    return collector.get_log()
