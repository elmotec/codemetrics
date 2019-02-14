#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Git related functions."""

import datetime as dt
import typing
import re

import tqdm
import numpy as np
import pandas as pd

from . import internals
from . import scm
from .internals import log


class _GitLogCollector(scm._ScmLogCollector):
    """Collect log from Git."""

    _args = 'log --pretty=format:"[%h] [%an] [%ad] [%s]" --date=iso --numstat'

    def __init__(self, git_client='git', **kwargs):
        """Initialize.

        Compiles regular expressions to be used during parsing of log.

        Args:
            git_client: name of git client.
            **kwargs: passed to parent :class:`codemetrics.scm._ScmLogCollector`

        """
        super().__init__(**kwargs)
        self.git_client = git_client
        self.log_moved_re = \
            re.compile(r"([-\d]+)\s+([-\d]+)\s+(\S*)\{(\S*) => (\S*)\}(\S*)")

    def parse_path_elem(self, path_elem: str):
        """Parses git output to identify lines added, removed and path.

        Also handles renamed path.

        Args:
            path_elem: path element line.

        Returns:
            Quadruplet of added, removed, relpath, copyfrompath where
            copyfrompath may be None.

        """
        copyfrompath = None
        if '{' not in path_elem:
                if '=>' in path_elem:
                    added, removed, copyfrompath, _, relpath = \
                        path_elem.split()
                else:
                    added, removed, relpath = path_elem.split()
        else:
            match = self.log_moved_re.match(path_elem)
            if not match:
                raise ValueError(f'{path_elem} not understood')
            added = match.group(1)
            removed = match.group(2)
            relpath = match.group(3) + match.group(5) + match.group(6)
            relpath = relpath.replace('//', '/')
            copyfrompath = match.group(3) + match.group(4) + match.group(6)
            copyfrompath = copyfrompath.replace('//', '/')
        added_as_int = int(added) if added != '-' else np.nan
        removed_as_int = int(removed) if removed != '-' else np.nan
        return added_as_int, removed_as_int, relpath, copyfrompath

    def process_entry(self, log_entry):
        """Convert a single xml <logentry/> element to csv rows.

        If the log includes entries about binary files, the added/removed
        columns are set to numpy.nan special value. Only reference the new name
        when a path changes.

        Args:
            log_entry: Git log entry paragraph.

        Yields:
            One or more csv rows.

        """
        try:
            rev, author, date_str, *remainder = log_entry[0][1:-1].split('] [')
        except ValueError:
            log.warning('failed to parse %s', log_entry[0])
            raise
        msg = '] ['.join(remainder)
        date = dt.datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S %z')
        for path_elem in log_entry[1:]:
            copyfrompath = None
            path_elem = path_elem.strip()
            if not path_elem:
                break
            # git log shows special characters in paths to indicate moves.
            try:
                added, removed, relpath, copyfrompath = \
                    self.parse_path_elem(path_elem)
            except ValueError as err:
                log.error(f'failed to parse {path_elem}: {err}')
                continue
            # - indicate binary files.
            entry = scm.LogEntry(rev, author=author, date=date, path=relpath,
                                 message=msg, kind='f', added=added,
                                 removed=removed, copyfrompath=copyfrompath)
            yield entry

    def process_log_entries(self, text):
        """See :member:`_ScmLogCollector.process_log_entries`."""
        log_entry = []
        for line in text:
            if line.startswith('['):
                log_entry.append(line)
                continue
            if not log_entry:
                continue
            log_entry.append(line)
            if line != '':
                continue
            yield from self.process_entry(log_entry)
            log_entry = []

    def get_log(self,
                path: str = '.',
                after: dt.datetime = None,
                before: dt.datetime = None,
                progress_bar: tqdm.tqdm = None) -> pd.DataFrame:
        """Retrieve log from git.

        Args:
            path: location of checked out subversion repository root. Defaults to .
            after: only get the log after time stamp. Defaults to one year ago.
            before: only get the log before time stamp. Defaults to now.
            progress_bar: tqdm.tqdm progress bar.

        Returns:
            pandas.DataFrame with columns matching the fields of
            codemetrics.scm.LogEntry.

        """
        internals.check_run_in_root(path)
        after, before = internals.handle_default_dates(after, before)
        if progress_bar is not None and after is None:
            raise ValueError("progress_bar requires 'after' parameter")
        command = f'{self.git_client} {self._args}'
        if after:
            command += f' --after {after:%Y-%m-%d}'
        if before:
            command += f' --before {before:%Y-%m-%d}'
        command_with_path = f'{command} {path}'
        results = internals.run(command_with_path).split('\n')
        return self.process_log_output_to_df(results, after=after,
                                             progress_bar=progress_bar)


def get_git_log(path: str = '.',
                after: dt.datetime = None,
                before: dt.datetime = None,
                progress_bar: tqdm.tqdm = None,
                git_client: str = 'git') -> pd.DataFrame:
    """Entry point to retrieve git log.

    Args:
        path: location of checked out subversion repository root. Defaults to .
        after: only get the log after time stamp. Defaults to one year ago.
        before: only get the log before time stamp. Defaults to now.
        git_client: git client executable (defaults to git).
        progress_bar: tqdm.tqdm progress bar.

    Returns:
        pandas.DataFrame with columns matching the fields of
        codemetrics.scm.LogEntry.

    Example::

        last_year = datetime.datetime.now() - datetime.timedelta(365)
        log_df = cm.git.get_git_log(path='src', after=last_year)

    """
    collector = _GitLogCollector(git_client=git_client)
    return collector.get_log(after=after, before=before, path=path,
                             progress_bar=progress_bar)


def _download_file(base_command, filename, revision) -> scm.FileDownloadResult:
    """Download specific file and revision from git."""
    command = f'{base_command} {revision}:{filename}'
    content = internals.run(command)
    yield scm.FileDownloadResult(filename, revision, content)


class _GitFileDownloader:
    """Download files from Subversion."""

    def __init__(self, git_client: str = 'git'):
        """Initialize downloader.

        Args:
            git_client: name of git client.

        """
        self.command = f'{git_client} show '

    def download_files(self,
                       df: pd.DataFrame) -> typing.Sequence[scm.FileDownloadResult]:
        """Downloads files from Subversion.

        Args:
            df: dataframe containing at least a (path, revision) columns to
                identify the files to download.

        Returns:
             list of file locations.

        """
        for _, (filename, revision) in df[['path', 'revision']].iterrows():
            yield from _download_file(self.command, filename, revision)
        return


def download_files(df: pd.DataFrame,
                   git_client: str = 'git') -> typing.Sequence[scm.FileDownloadResult]:
    """Downloads files from Subversion.

    Args:
        df: dataframe containing at least a (path, revision) columns to
            identify the files to download.
        git_client: Subversion client executable. Defaults to git.

    Returns:
         list of scm.FileDownloadResult.

    """
    downloader = _GitFileDownloader(git_client=git_client)
    yield from downloader.download_files(df)
