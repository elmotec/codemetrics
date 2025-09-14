#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""_SvnLogCollector related functions."""

import datetime as dt
import pathlib as pl
import re
import subprocess
import typing

# noinspection PyPep8Naming,PyPep8Naming
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd
import tqdm

from . import internals, scm
from .internals import log
from typing import Optional

default_client = "svn"


def to_date(datestr: str):
    """Convert str to datetime.datetime.

    The date returned by _SvnLogCollector is UTC according to git-svn man
    page. Date tzinfo is set to UTC.

    added and removed columns are set to np.nan for now.

    """
    from dateutil import parser

    return parser.parse(datestr).replace(tzinfo=dt.timezone.utc)


def to_bool(bool_str: str):
    """Convert str to bool."""
    bool_str_lc = bool_str.lower()
    if bool_str_lc in ("true", "1", "t"):
        return True
    if bool_str_lc in ("false", "0", "f", ""):
        return False
    raise ValueError(f"cannot interpret {bool_str} as a bool")


class _SvnLogCollector(scm.ScmLogCollector):
    """_ScmLogCollector interface adapter for _SvnLogCollector."""

    _args = "log --xml -v".split()

    def __init__(
        self,
        cwd: Optional[pl.Path] = None,
        svn_client: Optional[str] = None,
        relative_url: Optional[str] = None,
    ) -> None:
        """Initialize.

        Args:
            cwd: root of the directory under SCM.
            svn_client: name of svn client.
            relative_url: Subversion relative url (e.g. /project/trunk/).

        """
        if not svn_client:
            svn_client = default_client
        super().__init__(cwd=cwd)
        self.svn_client = svn_client
        # FIXME: Can we get rid of _relative_url?
        self._relative_url = relative_url

    def update_urls(self) -> typing.Optional[str]:
        """Relative URL so we can generate local paths."""
        rel_url_re = re.compile(r"^Relative URL: \^(.*)/?$")
        if not self._relative_url:
            # noinspection PyPep8
            for line in internals.run(
                [self.svn_client, "info", "."], cwd=self.cwd
            ).split("\n"):
                match = rel_url_re.match(line)
                if match:
                    self._relative_url = match.group(1)
                    break
        return self._relative_url

    @property
    def relative_url(self) -> str:
        """Relative url of Subversion reposotory (e.g. /trunk/project).

        Note the carret (^) at the begining is stripped and there is no trailing
        slash at the end.

        """
        if self._relative_url is None:
            self.update_urls()
        assert self._relative_url is not None
        return self._relative_url

    @staticmethod
    def _extract(
        elem: ET.Element, sub: str, log_entry: str, on_error=None
    ) -> typing.Optional[str]:
        """Extract subelement from element."""
        try:
            subel = elem.find(f"./{sub}")
            if subel is not None:
                return subel.text
        except (AttributeError, SyntaxError) as err:
            log.warning("failed to retrieve %s in %s: %s", sub, log_entry, err)
            if on_error == "raise":
                raise
        return None

    def process_entry(self, log_entry: str):
        """Convert a single xml <logentry/> element to csv rows.

        Args:
            log_entry: <logentry/> element.

        Yields:
            One or more csv rows.

        """
        elem = ET.fromstring(log_entry)
        rev = elem.attrib["revision"]
        author = self._extract(elem, "author", log_entry)
        date = self._extract(elem, "date", log_entry, "raise")
        message = self._extract(elem, "msg", log_entry)
        if message is not None:
            message = message.replace("\n", " ")
        rel_url_slash = self.relative_url + "/"
        for path_elem in elem.findall("*/path"):
            other = {}
            for sub in [
                "text-mods",
                "kind",
                "action",
                "prop-mods",
                "copyfrom-rev",
                "copyfrom-path",
            ]:
                try:
                    other[sub] = path_elem.attrib[sub]
                except (AttributeError, SyntaxError, KeyError):
                    other[sub] = np.nan
            try:
                path_elem_text = path_elem.text
                assert path_elem_text is not None
                path = path_elem_text.replace(rel_url_slash, "")
            except (AttributeError, SyntaxError, ValueError) as err:
                msg = f"{err} processing rev {rev}"
                log.warning(msg)
                path = msg
            assert date is not None, "expected datetime got None"
            entry = scm.LogEntry(
                rev,
                author,
                to_date(date),
                path=path,
                message=message,
                textmods=to_bool(other["text-mods"]),
                kind=other["kind"],
                action=other["action"],
                propmods=to_bool(other["prop-mods"]),
                copyfromrev=other["copyfrom-rev"],
                copyfrompath=other["copyfrom-path"],
                added=np.nan,
                removed=np.nan,
            )
            yield entry

    def process_log_entries(self, xml):
        # See parent.
        log_entry = ""
        for line in xml:
            if line.startswith("<logentry"):
                log_entry += line
                continue
            if not log_entry:
                continue
            log_entry += line
            if not line.startswith("</logentry>"):
                continue
            yield from self.process_entry(log_entry)
            log_entry = ""

    def get_log(
        self,
        path: str = ".",
        after: Optional[dt.datetime] = None,
        before: Optional[dt.datetime] = None,
        progress_bar: Optional[tqdm.tqdm] = None,
    ) -> pd.DataFrame:
        """Entry point to retrieve _SvnLogCollector log.

        Call svn log --xml -v and return the output as a DataFrame.

        Args:
            path: local to get the log for.
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
        internals.check_run_in_root(path, self.cwd)
        after, before = internals.handle_default_dates(after, before)
        before_str = "HEAD"
        if before:
            before_str = "{" + f"{before:%Y-%m-%d}" + "}"
        after_str = "{" + f"{after:%Y-%m-%d}" + "}"
        # noinspection PyPep8
        command = (
            [self.svn_client]
            + _SvnLogCollector._args
            + ["-r", f"{after_str}:{before_str}", path]
        )
        results = internals.run(command, cwd=self.cwd).split("\n")
        return self.process_log_output_to_df(
            results, after=after, progress_bar=progress_bar
        )


class SvnDownloader(scm.ScmDownloader):
    """Download files from Subversion."""

    def __init__(
        self,
        command: typing.List[str],
        svn_client: Optional[str] = None,
        cwd: Optional[pl.Path] = None,
    ) -> None:
        """Initialize downloader.

        Args:
            svn_client: name of svn client.
        """
        if not svn_client:
            svn_client = default_client
        super().__init__(command, client=svn_client, cwd=cwd)

    def _download(
        self, revision: str, path: Optional[str] = None
    ) -> scm.DownloadResult:
        """Download specific file and revision from git.

        Args:
            revision: revision number of the change set.
            path (optional): specific path to look up in this revision.

        Return:
            Result of svn command (e.g. show, diff, ...)

        """
        command = self.command + [revision]
        if path:
            command += [path]
        content = internals.run(command, cwd=self.cwd)
        return scm.DownloadResult(revision, path, content)


def get_diff_stats(
    data: pd.DataFrame,
    svn_client: Optional[str] = None,
    chunks=None,
    cwd: Optional[pl.Path] = None,
) -> typing.Union[None, pd.DataFrame]:
    """Download diff chunks statistics from Subversion.

    Args:
        data: revision ID of the change set.
        svn_client: Subversion client executable. Defaults to svn.
        chunks: if True, return statistics by chunk. Otherwise, return just
            added, and removed column for each path. If chunk is None, defaults
            to true for data frame and false for series.
        cwd: root of the directory under SCM.

    Returns:
        Dataframe containing the statistics for each chunk.

    Example::

        import pandas as pd
        import codemetrics as cm
        log = cm.get_svn_log().set_index(['revision', 'path'])
        log.loc[:, ['added', 'removed']] = log.reset_index().\\
                                            groupby('revision').\\
                                            apply(cm.svn.get_diff_stats,
                                            chunks=False)

    """
    if not svn_client:
        svn_client = default_client
    data = data.reset_index()  # prevents messing with input frame.
    try:
        revision = data.iloc[0]["revision"]
    except Exception as err:
        log.warning("cannot find revision in group: %s\n%s", str(err), data)
        return None
    downloader = SvnDownloader(["diff", "--git", "-c"], svn_client=svn_client, cwd=cwd)
    try:
        downloaded = downloader.download(revision)
    except subprocess.CalledProcessError as err:
        message = f"cannot retrieve diff for {revision}: {err}: {err.stderr}"
        log.warning(message)
        return None
    df = scm.parse_diff_chunks(downloaded)
    if chunks is None:
        chunks = data.ndim == 2
    if not chunks:
        df = df[["path", "added", "removed"]].groupby(["path"]).sum()
    else:
        df = df.set_index(["path", "chunk"])
    return df


class SvnProject(scm.Project):
    """Project for Subversion SCM."""

    def __init__(self, cwd: pl.Path = pl.Path(), client: str = "svn"):
        """Initialize a Subversion project.

        Args:
            cwd: root of the SCM project.
            client: svn client.

        """
        super().__init__(cwd)
        self.client = client

    def download(self, data: pd.DataFrame) -> scm.DownloadResult:
        """Download results from Subversion.

        Args:
            data: pd.DataFrame containing at least revision and path.

        Returns:
             list of file contents.

        """
        downloader = SvnDownloader(["cat", "-r"], svn_client=self.client, cwd=self.cwd)
        df = data[["revision", "path"]]
        if isinstance(df, pd.Series):
            df = df.to_frame().T
        revision, path = next(df.itertuples(index=False))
        return downloader.download(revision, path)

    def get_log(
        self,
        path: str = ".",
        after: Optional[dt.datetime] = None,
        before: Optional[dt.datetime] = None,
        progress_bar: Optional[tqdm.tqdm] = None,
        # FIXME: Why do we need path _and_ relative_url
        relative_url: Optional[str] = None,
        _pdb=False,
    ) -> pd.DataFrame:
        """Entry point to retrieve svn log.

        Args:
            path: location to retrieve the log for.
            after: only get the log after time stamp. Defaults to one year ago.
            before: only get the log before time stamp. Defaults to now.
            progress_bar: tqdm.tqdm progress bar.
            relative_url: Subversion relative url (e.g. /project/trunk/).
            _pdb: drop in debugger on parsing errors.

        Returns:
            pandas.DataFrame with columns matching the fields of
            :class:`codemetrics.scm.LogEntry`.

        Example::

            last_year = datetime.datetime.now() - datetime.timedelta(365)
            log_df = cm.svn.get_svn_log(path='src', after=last_year)

        """
        collector = _SvnLogCollector(
            cwd=self.cwd, svn_client=self.client, relative_url=relative_url
        )
        return collector.get_log(
            path=path, after=after, before=before, progress_bar=progress_bar
        )
