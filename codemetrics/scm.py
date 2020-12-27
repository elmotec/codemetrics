#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Factor things common to git and svn."""

import abc
import collections
import dataclasses
import datetime as dt
import pathlib as pl
import re
import typing

import mypy_extensions as mpx
import pandas as pd
import tqdm

from . import pbar

DownloadResult = collections.namedtuple(
    "DownloadResult", ["revision", "path", "content"]
)

ChunkStats = collections.namedtuple(
    "ChunkStats", ["path", "chunk", "first", "last", "added", "removed"]
)


# Default download function will be set by cm.git or cm.svn on checkout.
DownloadFuncType = typing.Optional[
    typing.Callable[
        [
            pd.DataFrame,
            # See https://github.com/PyCQA/pyflakes/issues/558
            mpx.DefaultNamedArg(str, "client"),  # noqa: F821
            # See https://github.com/PyCQA/pyflakes/issues/558
            mpx.DefaultNamedArg(typing.Optional[pl.Path], "cwd"),  # noqa: F821
        ],
        DownloadResult,
    ]
]


@dataclasses.dataclass
class Context:
    """Stores context information about the SCM tree.

    At first the attributes are initialized to None until the first request to the SCM tool.
    The value used are cached for subsequent called so they don't have to be specified again.

    Attributes:
        download_func: function used to download information from the SCM tool.
        cwd: working directory to run the download_func from. It would typically point to the
            root of the directory under SCM.
        client: name of the cient executable.

    """

    download_func: typing.Optional[DownloadFuncType] = None
    cwd: typing.Optional[pl.Path] = None
    client: typing.Optional[str] = None


context: Context = Context()


def update_context(
    download_func: DownloadFuncType = None, cwd: pl.Path = None, client: str = None
) -> None:
    """Convenience function to update the context easily

    Args:
        same as Context attributes.

    If a parameter is None, the context will not be updated.

    """
    if download_func:
        context.download_func = download_func
    if cwd:
        context.cwd = cwd
    if client:
        context.client = client


class LogEntry:
    """Data structure to hold git or svn data entries."""

    __slots__ = [
        "revision",
        "author",
        "date",
        "path",
        "message",
        "kind",
        "action",
        "textmods",
        "propmods",
        "copyfromrev",
        "copyfrompath",
        "added",
        "removed",
    ]

    def __init__(
        self,
        revision: str,
        author: typing.Optional[str],
        date: dt.datetime,
        path: typing.Optional[str] = None,
        message: typing.Optional[str] = None,
        kind: typing.Optional[str] = None,
        action: typing.Optional[str] = None,
        textmods: bool = True,
        propmods: bool = False,
        copyfromrev: str = None,
        copyfrompath: str = None,
        added: int = None,
        removed: int = None,
    ):
        """Initializes LogEntry

        Args:
            revision: ID of the revision (given by SCM).
            author: name of the user who committed the change.
            date: time stamp when code was committed.
            path: file name that changed.
            message: message accompanying the commit.
            kind: file, directory or property change.
            action: (svn only) A, M, D for Added, Modified or Deleted.
            textmods: (svn only) whether the change is to a text file.
                Always True for git.
            propmods: (svn only) property change. Always False for git.
            copyfromrev: source revision when a copy occured.
            copyfrompath: source path when a copy occurred.
            added: number of lines added.
            removed: number of lines removed.

        """
        self.revision = revision
        self.author = author
        self.date = date
        self.path = path
        self.message = message
        self.kind = kind
        self.action = action
        self.textmods = textmods
        self.propmods = propmods
        self.copyfromrev = copyfromrev
        self.copyfrompath = copyfrompath
        self.added = added
        self.removed = removed

    @property
    def changed(self):
        """Sum of lines added and lines removed."""
        return self.added + self.removed

    def astuple(self):
        """Return the data as tuple."""
        return (getattr(self, slot) for slot in self.__slots__)


def normalize_log(df):
    """Set dtype and categorize columns in the log DataFrame.

    Specifically:
        - Converts date to tz-aware UTC.
        - Replace NaN in author and message with an empty string.
        - Make added, and removed numeric (float so we can handle averages).
        - Make textmods and propmods as bool (no NA).
        - Make kind, and action categories.

    """
    return df.assign(
        revision=lambda x: x["revision"].astype("string"),
        path=lambda x: x["path"].astype("string"),
        author=lambda x: x["author"].fillna("").astype("string"),
        date=lambda x: pd.to_datetime(x["date"], utc=True),
        message=lambda x: x["message"].fillna("").astype("string"),
        copyfromrev=lambda x: x["copyfromrev"].astype("string"),
        copyfrompath=lambda x: x["copyfrompath"].astype("string"),
        added=lambda x: pd.to_numeric(x["added"], downcast="float"),
        removed=lambda x: pd.to_numeric(x["removed"], downcast="float"),
        textmods=lambda x: x["textmods"].astype("bool"),
        propmods=lambda x: x["propmods"].astype("bool"),
        kind=lambda x: x["kind"].astype("category"),
        action=lambda x: x["action"].astype("category"),
    )


def to_frame(log_entries: typing.Sequence[LogEntry]) -> pd.DataFrame:
    """Convert log entries to a pandas DataFrame.

    Args:
        log_entries: records generated by the SCM log command.

    Returns:
        Data converted to a DataFrame with categories and type adjustments.

    """
    columns = LogEntry.__slots__
    result = pd.DataFrame.from_records(
        (log_entry.astuple() for log_entry in log_entries), columns=columns
    )
    return normalize_log(result)


class ScmLogCollector(abc.ABC):
    """Base class for svn and git.

    See `get_log` functions.

    """

    def __init__(self, cwd: pl.Path = None):
        """Initialize interface.

        Args:
            cwd: root of the directory under SCM.

        """
        self.cwd = cwd or None

    @abc.abstractmethod
    def process_log_entries(self, cmd_output):
        """Convert output of git log --xml -v to a csv.

        Args:
            cmd_output: iterable of string (one for each line).

        Yields:
            tuple of :class:`codemetrics.scm.LogEntry`.

        """
        pass

    def process_log_output_to_df(
        self,
        cmd_output: typing.Sequence[str],
        after: dt.datetime,
        progress_bar: tqdm.tqdm = None,
    ):
        """Factor creation of dataframe from output of command.

        Args:
            cmd_output: generator returning lines of output from the cmd line.
            after: date for the oldest change to retrieve. Usefull when
                progress_bar is specified. Ignored otherwise.
            progress_bar: progress bar if any. Defaults to self.progress_bar.

        Returns:
            pandas.DataFrame

        """
        assert not isinstance(cmd_output, str)
        log_entries = []
        with pbar.ProgressBarAdapter(progress_bar, after) as tqdm_pbar:
            for entry in self.process_log_entries(cmd_output):
                log_entries.append(entry)
                tqdm_pbar.update(entry.date)
        df = to_frame(log_entries)
        return df

    @abc.abstractmethod
    def get_log(self):
        """Call git log and return the log entries as a DataFrame.

        Returns:
            pandas.DataFrame.

        """
        pass


def parse_diff_as_tuples(
    download: DownloadResult,
) -> typing.Generator[ChunkStats, None, None]:
    """Parse download result looking for diff chunks.

    Args:
        download: Download result.

    Yield:
        statistics, one tuple for each chunk (begin, end, added, removed).

    """
    curr_chunk, curr_path, count = None, None, 0
    for line in download.content.split("\n"):
        fm_re = r"Index: (.*)"
        # fm_re = r'^\+\+\+ b/[^\s/]+/(.*\S)\s+\((revision \d+|nonexistent)\)'
        file_match = re.match(fm_re, line)
        if file_match is not None:
            if curr_chunk is not None:
                yield curr_chunk
            curr_chunk = None
            curr_path = file_match.group(1)
            count = 0
            continue
        chunk_match = re.match(r"^@@ -\d+,\d+ \+(\d+)(?:,(\d+))? @@", line)
        if chunk_match is not None:
            if curr_chunk is not None:
                yield curr_chunk
            begin = int(chunk_match.group(1))
            if chunk_match.group(2):
                length = int(chunk_match.group(2))
            else:
                length = 0
            assert curr_path is not None
            curr_chunk = ChunkStats(curr_path, count, begin, begin + length, 0, 0)
            count += 1
            continue
        if curr_chunk is None or not line:
            continue
        if line[0] == "-":
            curr_chunk = curr_chunk._replace(removed=curr_chunk.removed + 1)  # noqa
        elif line[0] == "+":
            curr_chunk = curr_chunk._replace(added=curr_chunk.added + 1)  # noqa
    if curr_chunk is not None:
        yield curr_chunk
    return


def parse_diff_chunks(download: DownloadResult) -> pd.DataFrame:
    """Concatenate chunks data returned by parse_diff_as_tuples into a frame"""
    tuples = list(parse_diff_as_tuples(download))
    df = pd.DataFrame.from_records(data=tuples, columns=ChunkStats._fields)
    return df


class ScmDownloader(abc.ABC):
    """Abstract class that defines a common interface for SCM downloaders."""

    def __init__(self, command: typing.List[str], client: str, cwd: pl.Path = None):
        """Aggregates the client and the command in one variable.

        Args:
            command: argument to pass to the command line SCM client.
            client: name of the SCM client.
            cwd: root of the directory under SCM.

        """
        self.command = [client] + command
        self.cwd = cwd or None

    def download(self, revision: str, path: str = None) -> DownloadResult:
        """Download content specific to a revision and path.

        Runs checks and forward the call to _download (template method).

        Args:
            revision: identify the commit ID
            path: file path. Can be left as None if all files in the commit
                are to be retrieved.

        """
        assert revision is None or isinstance(
            revision, str
        ), f"expected string, got {type(revision)}"
        assert path is None or isinstance(
            path, str
        ), f"expected a string, got {type(path)}"
        if path is None:
            path = "."
        dr = self._download(revision, path)
        return dr

    @abc.abstractmethod
    def _download(self, revision: str, path: str) -> DownloadResult:
        """Download content specific to a revision and path.

        Args:
            revision id: revision to download.
            path: some SCM (e.g. Subversion) requires a path but not all do.

        Return:
            May return more than one item (e.g. multiple chunks) as generator.

        """
        pass
