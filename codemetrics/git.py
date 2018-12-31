#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Git related functions."""

import datetime as dt
import re

import tqdm
import numpy as np

from . import internals
from . import scm
from .internals import log


class _GitLogCollector(scm._ScmLogCollector):
    """Collect log from Git."""

    _args = 'log --pretty=format:"[%h] [%an] [%ad] [%s]" --date=iso --numstat'

    def __init__(self, git_program='git', **kwargs):
        """Initialize.

        Compiles regular expressions to be used during parsing of log.

        Args:
            git_program: name of svn client.
            **kwargs: passed to parent :class:`_ScmLogCollector`

        """
        super().__init__(**kwargs)
        self.git_program = git_program
        self.log_moved_re = re.compile(r"\{(?:\S* )?=> (\S*)\}")

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
            hash, author, date_str, *remainder = log_entry[0][1:-1].split('] [')
        except ValueError as err:
            log.warning('failed to parse %s', log_entry[0])
            raise
        msg = '] ['.join(remainder)
        date = dt.datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S %z')
        for path_elem in log_entry[1:]:
            path_elem = path_elem.strip()
            if not path_elem:
                break
            # git log shows special characters in paths to indicate moves.
            substed_path_elem = self.log_moved_re.sub(r'\1', path_elem)
            substed_path_elem = substed_path_elem.replace('//', '/')
            try:
                added, removed, relpath = substed_path_elem.split()
            except ValueError:
                log.warning('failed to parse the following line:\n%s\n%s',
                            log_entry[0], path_elem)
                continue
            # - indicate binary files.
            added_as_int = int(added) if added != '-' else np.nan
            removed_as_int = int(removed) if removed != '-' else np.nan
            entry = scm.LogEntry(hash, author, date, None, 'f', None,
                                 None, relpath, msg, added_as_int,
                                 removed_as_int)
            yield entry

    def get_log_entries(self, text):
        """See :member:`_ScmLogCollector.get_log_entries`."""
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

    def get_log(self):
        """Call git log and return output as a DataFrame."""
        command = f'{self.git_program} {self._args}'
        if self.after:
            command += f' --after {self.after:%Y-%m-%d}'
        if self.before:
            command += f' --before {self.before:%Y-%m-%d}'
        command_with_path = f'{command} {self.path}'
        results = internals._run(command_with_path)
        return self.process_output_to_df(results)


def get_git_log(
    after: dt.datetime=None,
    before: dt.datetime=None,
    path: str='.',
    git_program: str='git',
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
        codemetrics.scm.LogEntry.

    Example::

        last_year = datetime.datetime.now() - datetime.timedelta(365)
        log_df = cm.git.get_git_log(path='src', after=last_year)

    """
    internals._check_run_in_root(path)
    collector = _GitLogCollector(after=after, before=before, path=path,
                                 git_program=git_program,
                                 progress_bar=progress_bar)
    return collector.get_log()
