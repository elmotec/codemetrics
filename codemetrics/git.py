#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Git related functions."""

import datetime as dt
import pathlib as pl
import re
import typing

import numpy as np
import pandas as pd
import tqdm

from . import internals, scm
from .internals import log

default_client = "git"


class _GitLogCollector(scm.ScmLogCollector):
    """Collect log from Git."""

    _args = [
        "log",
        '--pretty=format:"[%h] [%an] [%ad] [%s]"',
        "--date=iso",
        "--numstat",
    ]

    def __init__(self, git_client=default_client, cwd: pl.Path = None, _pdb=False):
        """Initialize.

        Compiles regular expressions to be used during parsing of log.

        Args:
            cwd: root of the directory under SCM.
            git_client: name of git client.
            _pdb: drop in debugger when output cannot be parsed.

        """
        super().__init__(cwd=cwd)
        self._pdb = _pdb
        self.git_client = git_client
        self.log_re = re.compile(
            r"([-\d]+)\s+([-\d]+)\s+(.*)"
        )
        self.log_moved_re = re.compile(
            r"([-\d]+)\s+([-\d]+)\s+(.*) => (.*)"
        )
        self.log_curly_re = re.compile(
            r"([-\d]+)\s+([-\d]+)\s+(.*)\{(.*) => (.*)\}(.*)"
        )

    def parse_path_elem(self, path_elem: str):
        """Parses git output to identify lines added, removed and path.

        Also handles renamed path.

        Args:
            path_elem: path element line.

        Returns:
            Quadruplet of added, removed, rel_path, copy_from_path where
            copy_from_path may be None.

        """
        copy_from_path: typing.Optional[str] = None
        match_log = self.log_re.match(path_elem)
        match_log_moved = self.log_moved_re.match(path_elem)
        match_log_curly = self.log_curly_re.match(path_elem)
        if match_log_curly:
            added, removed, base, from_mid, rel_mid, end = match_log_curly.groups()
            rel_path = (base + rel_mid + end).replace("//", "/")
            copy_from_path = (base + from_mid + end).replace("//", "/")
        elif match_log_moved:
            added, removed, copy_from_path, rel_path = match_log_moved.groups()
        elif match_log:
            added, removed, rel_path = match_log.groups()
        else:
            raise ValueError(f"{path_elem} not understood")
        added_as_int = int(added) if added != "-" else np.nan
        removed_as_int = int(removed) if removed != "-" else np.nan
        return added_as_int, removed_as_int, rel_path, copy_from_path

    def process_entry(
        self, log_entry: typing.List[str]
    ) -> typing.Generator[scm.LogEntry, None, None]:
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
            rev, author, date_str, *remainder = log_entry[0][1:-1].split("] [")
        except ValueError:
            log.warning("failed to parse %s", log_entry[0])
            raise
        msg = "] [".join(remainder)
        date = dt.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S %z")
        if len(log_entry) < 2:
            entry = scm.LogEntry(
                rev,
                author=author,
                date=date,
                path=None,
                message=msg,
                kind="X",
                added=0,
                removed=0,
                copyfrompath=None,
            )
            yield entry
            return
        for path_elem in log_entry[1:]:
            path_elem = path_elem.strip()
            if not path_elem:
                break
            # git log shows special characters in paths to indicate moves.
            try:
                added, removed, relpath, copyfrompath = self.parse_path_elem(path_elem)
            except ValueError as err:
                log.error(f"failed to parse {path_elem}: {err}")
                continue
            # - indicate binary files.
            entry = scm.LogEntry(
                rev,
                author=author,
                date=date,
                path=relpath,
                message=msg,
                kind="f",
                added=added,
                removed=removed,
                copyfrompath=copyfrompath,
            )
            yield entry
        return

    def process_log_entries(
        self, text: typing.List[str]
    ) -> typing.Generator[scm.LogEntry, None, None]:
        """See :member:`_ScmLogCollector.process_log_entries`."""
        log_entry: typing.List[str] = []
        for line in text:
            # Unquote output. Not sure if anything is escaped though...
            if len(line) > 2 and line[0] == '"' and line[-1] == '"':
                line = line[1:-1]
            if line.startswith("["):
                if log_entry:
                    yield from self.process_entry(log_entry)
                    log_entry = []
                log_entry.append(line)
                continue
            if not log_entry:
                continue
            log_entry.append(line)
            if line != "":
                continue
        if log_entry:
            yield from self.process_entry(log_entry)
        return

    def get_log(
        self,
        path: str = ".",
        after: dt.datetime = None,
        before: dt.datetime = None,
        progress_bar: tqdm.tqdm = None,
    ) -> pd.DataFrame:
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
        internals.check_run_in_root(path, self.cwd)
        after, before = internals.handle_default_dates(after, before)
        if progress_bar is not None and after is None:
            raise ValueError("progress_bar requires 'after' parameter")
        command = [self.git_client] + self._args
        if after:
            command += ["--after", f"{after:%Y-%m-%d}"]
        if before:
            command += ["--before", f"{before:%Y-%m-%d}"]
        command.append(path)
        if self._pdb:
            import pdb

            pdb.set_trace()
        results = internals.run(command, cwd=self.cwd).split("\n")
        return self.process_log_output_to_df(
            results, after=after, progress_bar=progress_bar
        )


class _GitFileDownloader(scm.ScmDownloader):
    """Download files from Subversion."""

    def __init__(self, git_client: str = None, cwd: pl.Path = None):
        """Initialize downloader.

        Args:
            git_client: name of git client.

        """
        if not git_client:
            git_client = default_client
        super().__init__(client=git_client, command=["show"], cwd=cwd)

    def _download(
        self, revision: str, path: typing.Optional[str]
    ) -> scm.DownloadResult:
        """Download specific file and revision from git."""
        command = self.command + [f"{revision}:{path}"]
        content = internals.run(command, cwd=self.cwd)
        return scm.DownloadResult(revision, path, content)


class GitProject(scm.Project):

    """Project for git SCM."""

    def __init__(self, cwd: pl.Path = pl.Path("."), client: str = "git"):
        """Initialize a Subversion project.

        Args:
            cwd: root of the SCM project. Defaults to current directory.
            client: git client. Defaults to git.

        """
        super().__init__(cwd)
        self.client = client

    def download(self, data: pd.DataFrame) -> scm.DownloadResult:
        """Download results from Git.

        Args:
            data: pd.DataFrame containing at least revision and path.

        Returns:
             list of file contents.

        """
        downloader = _GitFileDownloader(git_client=self.client, cwd=self.cwd)
        df = data[["revision", "path"]]
        if isinstance(df, pd.Series):
            df = df.to_frame().T
        revision, path = next(df.itertuples(index=False))
        return downloader.download(revision, path)

    def get_log(
        self,
        path: str = ".",
        after: dt.datetime = None,
        before: dt.datetime = None,
        progress_bar: tqdm.tqdm = None,
        # FIXME: Why do we need path _and_ relative_url
        relative_url: str = None,
        _pdb=False,
    ) -> pd.DataFrame:
        """Entry point to retrieve git log.

        Args:
            path: location of checked out file/directory to get the log for.
            after: only get the log after time stamp. Defaults to one year ago.
            before: only get the log before time stamp. Defaults to now.
            progress_bar: tqdm.tqdm progress bar.
            _pdb: drop in debugger on parsing errors.

        Returns:
            pandas.DataFrame with columns matching the fields of
            codemetrics.scm.LogEntry.

        Example::

            last_year = datetime.datetime.now() - datetime.timedelta(365)
            log_df = cm.git.get_git_log(path='src', after=last_year)

        """
        collector = _GitLogCollector(git_client=self.client, cwd=self.cwd, _pdb=_pdb)
        return collector.get_log(
            after=after, before=before, path=path, progress_bar=progress_bar
        )


def download(
    data: pd.DataFrame, client: str = None, cwd: pl.Path = None
) -> scm.DownloadResult:
    """Downloads files from Subversion.

    Args:
        data: dataframe containing at least a (path, revision) columns to
              identify the files to download.
        client: Git client executable. Defaults to git.
        cwd: working directory, typically the root of the directory under SCM.

    Returns:
         list of scm.DownloadResult.

    """
    if not client:
        client = default_client
    downloader = _GitFileDownloader(git_client=client, cwd=cwd)
    revision, path = next(data[["revision", "path"]].itertuples(index=False))
    return downloader.download(revision, path)
