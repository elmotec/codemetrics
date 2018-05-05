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
import collections

import pandas as pd
import numpy as np
import dateutil as du


log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


def get_now():
    """Get current time stamp as pd.TimeStamp.

    This is also useful to patch retrieval of the current date/time.

    """
    return pd.to_datetime(dt.datetime.now(dt.timezone.utc), utc=True)


def _run(command, errors=None, **kwargs):
    """Exceute command passed as argument and return output.

    If the command does not return 0, will throw subprocess.CalledProcessError.

    :param list(str) command: command to execute.
    :param str errors: error policy during bytes decoding. Defaults to ignore.
    :param dict **kwargs: additional kwargs are passed to subprocess.run().
    :return: output of the command as iter(str)

    """
    if errors is None:
        errors = 'ignore'
    try:
        log.info(command)
        proc = subprocess.run(command, check=True,
                              stdout=subprocess.PIPE, errors=errors,
                              **kwargs)
        return proc.stdout.split('\n')
    except subprocess.CalledProcessError as err:
        log.warning(err)
        raise


def filter_mass_changes(log, quantile=None):
    """Filters out mass change from the SCM log.

    Calculate the number of files change by revision and the threshold on the
    distribution. Split the log in 2 sets.

    :param pandas.DataFrame log: SCM log data.
    :param float quantile: quantile that determine the threshold of files per
                           revisions that drives the filter.

    :rtype: (pandas.DataFrame, pandas.DataFrame)
    :return: revisions that had less files than the threeshold of files and
             log of revision that are more.

    """
    if quantile is None:
        quantile = .975
    by_rev = log[['revision', 'path']].groupby('revision').count().reset_index()
    threshold = by_rev['path'].quantile(quantile)
    ignore = by_rev[by_rev['path'] > threshold]['revision'].unique()
    ignore_mask = log['revision'].isin(ignore)
    return log[~ignore_mask], log[ignore_mask]



class ProgressBarAdapter:
    """Adapts interface of tqdm.tqdm in the context of SCM log retrieval.

    Also acts as a context manager.
    """

    def __init__(self, pbar=None, after=None):
        """Creates adapter

        If after is specified, calls reset(after).

        """

        self.pbar = pbar
        if self.pbar is not None:
            self.pbar.unit = 'day'
        self.today = get_now().date()
        self.count = 0
        self.after = None
        if after is not None:
            self.after = after.date()
            self.reset(self.after)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        if self.pbar is not None:
            self.pbar.update(self.pbar.total - self.count)
            self.pbar.close()

    def reset(self, after):
        """Reset the progress bar total iterations from after."""
        if after is None or self.pbar is None:
            return
        self.pbar.total = (self.today - after).days

    def update(self, entry_date):
        """Update the progress bar."""
        if self.pbar is None:
            return
        if hasattr(entry_date, 'hour'):
            entry_date = entry_date.date()
        count = (entry_date - self.after).days
        diff = count - self.count
        if diff > 0:
            self.pbar.update(diff)
            self.count = count


LogEntry = collections.namedtuple('LogEntry',
    'revision author date textmods kind action propmods path msg'.split())


class SvnLogCollector:
    """Collect log from Subversion.

    :param datetime.datetime after: limits the log to entries after that date.

    If after is not tz-aware, the date will automatically be assumed to be UTC
    based.

    """

    def __init__(self, path, svn_program=None, after=None,
                 progress_bar=None):
        """Initialize.

        :param tqdm.tqdm progress_bar: implements tqdm.tqdm interface.

        """
        self.path = path
        self.svn_program = svn_program or 'svn'
        self.after = after
        self.progress_bar = None
        if progress_bar is not None:
            self.progress_bar = progress_bar

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
                """Convert str to datetime.datetime."""
                return du.parser.parse(datestr)

            entry = LogEntry(rev, values['author'], to_date(values['date']),
                             other['text-mods'], other['kind'], other['action'],
                             other['prop-mods'], path, values['msg'])
            yield entry

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
        records = []
        with ProgressBarAdapter(self.progress_bar, self.after) as progress_bar:
            for entry in self.process(xml, relative_url):
                records.append(entry)
                progress_bar.update(entry.date)
        columns = ['revision', 'author', 'date', 'textmods', 'kind',
                   'action', 'propmods', 'path', 'message']
        result = pd.DataFrame.from_records(records, columns=columns)
        return result


class BaseReport:
    """Base classes for the reports."""

    def __init__(self, path, after=None,
                 cloc_program=None, svn_program=None,
                 progress_bar=None):
        """Initialization.

        :param str path: local repository to work with
        :param datetime.datetime after: limit how far back to mine SCM log.
        :param str cloc_program: name of cloc program (e.g. cloc.pl)
        :param str svn_program: name and location of svn client program.
        :param ProgressBar progress_bar: derived from tqdm.tqdm.

        """
        self.path = path
        self.after = after
        self.cloc_program = cloc_program or 'cloc'
        self.svn_program = svn_program or 'svn'
        self.progress_bar = progress_bar

    def get_log(self):
        """Forwards to get_svn_log."""
        collector = SvnLogCollector(self.path, after=self.after,
                                    svn_program=self.svn_program,
                                    progress_bar=self.progress_bar)
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
        columns = 'language,path,blank,comment,code'.split(',')
        return pd.DataFrame.from_records(records[1:], columns=columns)

    def get_files(self, pattern=None):
        """Retrieve the list of the files currently in the directory."""
        if pattern is None:
            pattern = '**/*'
        fnames = pl.Path(self.path).glob(pattern)
        files = [(str(fname),) for fname in fnames]
        return pd.DataFrame.from_records(files, columns=['path'])

    def compute_score(self, input_df):
        """Compute score on the input dataframe for ranking.

        :param pandas.DataFrame input_df: data frame containing input.

        Scale each column accoding to min/max policy and compute a score
        between 0 and 1 based on the product of each column scaled value.

        :rtype: pandas.DataFrame

        """
        df = input_df.astype('float').copy()
        df -= df.min(axis=0)
        df /= df.max(axis=0)
        df = df ** 2
        return df.sum(axis=1)


class AgeReport(BaseReport):
    """Reports files or components age in days."""

    def __init__(self, path, **kwargs):
        """See `BaseReport.__init__`."""
        super().__init__(path, **kwargs)

    def collect(self, **kwargs):
        """Collect SCM log needed for the report.

        :param dict kwargs: passed as if to self.get_log().
        :rtype: pandas.DataFrame

        """
        return self.get_log(**kwargs)

    def generate(self, log_df=None, files_df=None, keys=None, **kwargs):
        """Generate report from SCM data.

        If data is not passed, calls:
        - self.get_log_df() to retrieve the raw log_df from SCM.
        - self.get_files_df() to retrieve the files currently in path.

        The keys are used to group the data by that key before calculating the
        minimum age (last change).

        :param pandas.DataFrame log_df: log output from SCM.
        :param pandas.DataFrame files_df: files found in path or cloc output.
        :param iter(str) keys: Default to file name and kind.
        :param dict kwargs: passed as if to self.collect() if log_df missing.

        """
        if log_df is None:
            log_df = self.get_log(**kwargs)
        if files_df is None:
            files_df = self.get_files(**kwargs)
        if keys is None:
            excluded = {'revision', 'author', 'date', 'textmods',
                        'action', 'propmods', 'message'}
            keys = [col for col in log_df.columns if col not in excluded]
        df = log_df.copy()
        now = get_now()
        df['age'] = (now - pd.to_datetime(df['date'], utc=True))
        df = df[keys + ['age']].groupby(['path']).min().reset_index()
        df['age'] /= pd.Timedelta(1, unit='D')
        df = pd.merge(df, files_df)
        return df


class HotSpotReport(BaseReport):
    """Identifies changing high complexity files."""

    def __init__(self, path, **kwargs):
        """See `BaseReport.__init__`."""
        super().__init__(path, **kwargs)

    def collect(self):
        """Collect data necessary to the generation of the report.

        :return: output of the SCM log and output of cloc.
        :rtype: 2 pandas.DataFrame

        """
        return BaseReport.get_log(), BaseReport.get_cloc()

    def generate(self, log=None, cloc=None):
        """Generate report from SCM data.

        If log or cloc is not passed, calls self.get_log() and self.get_cloc()
        to retrieve the raw log from SCM.

        :param pandas.DataFrame log: output log from SCM.
        :param pandas.DataFrame cloc: output from cloc.

        :rtype: pandas.DataFrame

        """
        if log is None:
            log = self.get_log()
        if cloc is None:
            cloc = self.get_cloc()
        c_df = cloc[['path', 'code']].copy()
        c_df = c_df.rename(columns={'code': 'complexity'})
        ch_df = log['path'].value_counts().to_frame('changes')
        df = pd.merge(c_df, ch_df, right_index=True, left_on='path',
                      how='outer')
        df['score'] = self.compute_score(df[['complexity', 'changes']])
        return df

