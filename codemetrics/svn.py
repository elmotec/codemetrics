#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""_SvnLogCollector related functions."""

import pathlib as pl
import xml.etree.ElementTree as ET
import datetime as dt
import typing
import re

import dateutil as du
import tqdm
import numpy as np
import pandas as pd

from . import scm
from . import internals
from .internals import log


def to_date(datestr: str):
    """Convert str to datetime.datetime.

    The date returned by _SvnLogCollector is UTC according to git-svn man
    page. Date tzinfo is set to UTC.

    added and removed columns are set to np.nan for now.

    """
    return du.parser.parse(datestr).replace(tzinfo=dt.timezone.utc)


def to_bool(bool_str: str):
    """Convert str to bool."""
    bool_str_lc = bool_str.lower()
    if bool_str_lc in ('true', '1', 't'):
        return True
    if bool_str_lc in ('false', '0', 'f', ''):
        return False
    raise ValueError(f'cannot interpret {bool_str} as a bool')


class _SvnLogCollector(scm._ScmLogCollector):
    """_ScmLogCollector interface adapter for _SvnLogCollector."""

    _args = 'log --xml -v'

    def __init__(self,
                 svn_client: str='svn',
                 path: str='.',
                 relative_url: str=None,
                 wc_root: str=None,
                 **kwargs):
        """Initialize.

        Args:
            svn_client: name of svn client.
            path: top of the checked out directory.
            relative_url: Subversion relative url (e.g. /project/trunk/).
            **kwargs: passed to :class:`scm._ScmLogCollector`
`
        """
        super().__init__(**kwargs)
        self.svn_client = svn_client or 'svn'
        self.path = path
        self._relative_url = relative_url

    def update_urls(self):
        """Relative URL so we can generate local paths."""
        rel_url_re = re.compile(r'^Relative URL: \^(.*)/?$')
        wc_root_re = re.compile(r'^Working Copy Root Path: (.*)$')
        if not self._relative_url or not self._wc_root:
            for line in internals.run(f'{self.svn_client} info {self.path}').split('\n'):
                match = rel_url_re.match(line)
                if match:
                    self._relative_url = match.group(1)
                    break
        return self._relative_url

    @property
    def relative_url(self):
        """Relative url of Subversion reposotory (e.g. /trunk/project).

        Note the carret (^) at the begining is stripped and there is no trailing
        slash at the end.

        """
        if self._relative_url is None:
            self.update_urls()
        return self._relative_url

    def process_entry(self,
                      log_entry: str):
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
        rel_url_slash = self.relative_url + '/'
        for path_elem in elem.findall('*/path'):
            other = {}
            for sub in ['text-mods', 'kind', 'action', 'prop-mods',
                        'copyfrom-rev', 'copyfrom-path']:
                try:
                    other[sub] = path_elem.attrib[sub]
                except (AttributeError, SyntaxError, KeyError):
                    other[sub] = np.nan
            try:
                path = path_elem.text.replace(rel_url_slash, '')
            except (AttributeError, SyntaxError, ValueError) as err:
                log.warning(f'{err} processing rev {rev}')
                path = None
            entry = scm.LogEntry(rev, values['author'], to_date(values['date']),
                                 path=path, message=values['msg'],
                                 textmods=to_bool(other['text-mods']),
                                 kind=other['kind'], action=other['action'],
                                 propmods=to_bool(other['prop-mods']),
                                 copyfromrev=other['copyfrom-rev'],
                                 copyfrompath=other['copyfrom-path'],
                                 added=np.nan, removed=np.nan)
            yield entry

    def process_log_entries(self, xml):
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

    def get_log(self,
                path: str='.',
                after: dt.datetime=None,
                before: dt.datetime=None,
                progress_bar: tqdm.tqdm=None) -> pd.DataFrame:
        """Entry point to retrieve _SvnLogCollector log.

        Call svn log --xml -v and return the output as a DataFrame.
        
        Args:
            path: location of checked out subversion repository root.
            after: only get the log after time stamp. Defaults to one year ago.
            before: only get the log before time stamp. Defaults to now.
            progress_bar: tqdm.tqdm progress bar.

        Returns:
            pandas.DataFrame with columns matching the fields of
            codemetrics.scm.LogEntry.

        Example::

            last_year = datetime.datetime.now() - datetime.timedelta(365)
            log_df = cm.git.get_git_log(path='src', after=last_year)

        """
        internals.check_run_in_root(path)
        after, before = internals.handle_default_dates(after, before)
        relative_url = self.relative_url
        before_str = 'HEAD'
        if before:
            before_str = '{' + f'{before:%Y-%m-%d}' + '}'
        after_str = '{' + f'{after:%Y-%m-%d}' + '}'
        command = \
            f'{self.svn_client} {_SvnLogCollector._args} ' \
            f'-r {after_str}:{before_str}'
        command_with_path = f'{command} {path}'
        results = internals.run(command_with_path).split('\n')
        return self.process_log_output_to_df(results, after=after,
                                             progress_bar=progress_bar)


def get_svn_log(
    path: str='.',
    after: dt.datetime=None,
    before: dt.datetime=None,
    progress_bar: tqdm.tqdm=None,
    svn_client: str = 'svn') -> pd.DataFrame:
    """Entry point to retrieve svn log.

    Args:
        path: location of checked out subversion repository root.
        after: only get the log after time stamp. Defaults to one year ago.
        before: only get the log before time stamp. Defaults to now.
        progress_bar: tqdm.tqdm progress bar.
        svn_client: Subversion client executable. Defaults to svn.

    Returns:
        pandas.DataFrame with columns matching the fields of
        :class:`codemetrics.scm.LogEntry`.

    Example::

        >>> last_year = datetime.datetime.now() - datetime.timedelta(365)
        >>> log_df = cm.svn.get_svn_log(path='src', after=last_year)

    """
    collector = _SvnLogCollector(svn_client=svn_client)
    return collector.get_log(path=path, after=after, before=before,
                             progress_bar=progress_bar)


def _download_file(base_command, filename, revision) -> scm.FileDownloadResult:
    """Download specific file and revision from svn."""
    command = f'{base_command} {revision} {filename}'
    content = internals.run(command)
    yield scm.FileDownloadResult(filename, revision, content)


class _SvnFileDownloader:
    """Download files from Subversion."""

    def __init__(self, svn_client: str='svn'):
        """Initialize downloader.

        Args:
            svn_client: name of svn client.
        """
        self.svn_client = svn_client
        self.command = f'{svn_client} cat -r'

    def download_files(self,
                       df: pd.DataFrame) -> typing.Sequence[scm.FileDownloadResult]:
        """Downloads files from Subversion.

        Args:
            df: dataframe containing at least a (path, revision) columns to
                identify the files to download.
            svn_client: Subversion client executable. Defaults to svn.

        Returns:
             list of file locations.

        """
        for _, (filename, revision) in df[['path', 'revision']].iterrows():
            yield from _download_file(self.command, filename, revision)
        return


def download_files(df: pd.DataFrame,
                   svn_client: str = 'svn') -> typing.Sequence[scm.FileDownloadResult]:
    """Downloads files from Subversion.

    Args:
        df: dataframe containing at least a (path, revision) columns to
            identify the files to download.
        svn_client: Subversion client executable. Defaults to svn.

    Returns:
         list of file locations.

    """
    downloader = _SvnFileDownloader(svn_client=svn_client)
    return downloader.download_files(df)
