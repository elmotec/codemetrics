#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Top-level package for codemetrics."""

# noinspection SpellCheckingInspection
__author__ = """Jérôme Lecomte"""
__email__ = 'elmotec@gmx.com'
__version__ = '0.6.1'

import datetime as dt
import logging
import collections

import pandas as pd

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

LogEntry = collections.namedtuple('LogEntry',
                                  'revision author date textmods kind action propmods path msg'.split())


def get_now():
    """Get current time stamp as pd.TimeStamp.

    This is also useful to patch retrieval of the current date/time.

    """
    return pd.to_datetime(dt.datetime.now(dt.timezone.utc), utc=True)


def get_mass_changesets(log, min_changes):
    """Extract mass change sets from the SCM log dataframe.

    Calculate the number of files changed by each revision and extract that
    list according to the threshold.

    :param pandas.DataFrame log: SCM log data.
    :param int min_changes: threshold of changes above which a revision is
                            included in the output.

    :rtype: pandas.DataFrame
    :return: revisions that had more files changed than the threshold.

    """
    by_rev = log[['revision', 'path']].groupby('revision').count()
    by_rev.rename(columns={'path': 'path_count'}, inplace=True)
    by_rev.reset_index(inplace=True)
    massive = pd.merge(by_rev[by_rev['path_count'] > min_changes],
                       log[['revision', 'message', 'author']].drop_duplicates())
    return massive


def ages(log, files=None, keys=None, **kwargs):
    """Generate report from SCM data.

    Group the log by the keys passed as argument and generates the age of each
    group (last time the group was changed).

    If files is passed, join results to files.

    :param pandas.DataFrame log: log output from SCM.
    :param pandas.DataFrame files: files found in path or cloc output.
    :param iter(str) keys: Default to file name and kind.
    :param dict kwargs: passed as if to self.collect() if log_df missing.

    :return pandas.DataFrame: log frame joined to files with the age column.

    """
    if keys is None:
        excluded = {'revision', 'author', 'date', 'textmods',
                    'action', 'propmods', 'message'}
        keys = [col for col in log.columns if col not in excluded]
    df = log.copy()
    now = get_now()
    df['age'] = (now - pd.to_datetime(df['date'], utc=True))
    df = df[keys + ['age']].groupby(['path']).min().reset_index()
    df['age'] /= pd.Timedelta(1, unit='D')
    if files is not None:
        if not isinstance(files, pd.DataFrame):
            raise TypeError('files should be a pandas.DataFrame')
        df = pd.merge(df, files)
    return df


def hot_spots(log, loc, by=None, count_one_change_per=None):
    """Generate hot spots from SCM and loc data.

    Cross SCM log and loc as an approximation of complexity to determine paths
    that are complex and change often.

    :param pandas.DataFrame log: output log from SCM.
    :param pandas.DataFrame loc: output from cloc.
    :param str by: aggregation level can be path (default), another column.
    :param list(str) count_one_change_per: allows one to count one change
        by day or one change per JIRA instead of one change by revision.

    :rtype: pandas.DataFrame

    """

    def compute_score(input_df):
        """Compute score on the input dataframe for ranking.

        :param pandas.DataFrame input_df: data frame containing input.

        Scale each column accoding to min/max policy and compute a score
        between 0 and 1 based on the product of each column scaled value.

        :rtype: pandas.DataFrame

        """
        df = input_df.astype('float').copy()
        df.fillna(0.0, inplace=True)
        df -= df.min(axis=0)
        df /= df.max(axis=0)
        df.fillna(0.0, inplace=True)
        df = df ** 2
        return df

    if by is None:
        by = 'path'
    if count_one_change_per is None:
        count_one_change_per = ['revision']
    c_df = loc.copy()
    c_df = c_df.rename(columns={'code': 'complexity'})
    columns = count_one_change_per + [by]
    ch_df = log[columns].drop_duplicates()[by]. \
        value_counts().to_frame('changes')
    df = pd.merge(c_df, ch_df, right_index=True, left_on=by, how='outer'). \
        fillna(0.0)
    df[['complexity_score', 'changes_score']] = \
        compute_score(df[['complexity', 'changes']])
    df['score'] = df[['complexity_score', 'changes_score']].sum(axis=1)
    return df


def co_changes(log=None, by=None, on=None):
    """Generate co-changes report.

    Returns a pandas.DataFrame with the following columns:
    - primary: first path changed.
    - secondary: second path changed.
    - coupling: how often do the path change together.

    :param pandas.DataFrame log: output log from SCM.
    :param str by: aggregation level. Defaults to path.
    :param str on: Field name to join/merge on. Defaults to revision.

    :rtype: pandas.DataFrame

    """
    if by is None:
        by = 'path'
    if on is None:
        on = 'revision'
    df = log[[on, by]].drop_duplicates()
    sj = pd.merge(df, df, on=on)
    sj = sj.rename(columns={by + '_x': 'primary', by + '_y': 'secondary'})
    sj.drop_duplicates(inplace=True)  # FIXME: needs a test
    sj = sj.groupby(['primary', 'secondary']).count().reset_index()
    result = pd.merge(sj[sj['primary'] == sj['secondary']][['primary', on]],
                      sj[sj['primary'] != sj['secondary']],
                      on='primary', suffixes=['_changes', '_cochanges'])
    result['coupling'] = result[on + '_cochanges'] / result[on + '_changes']
    return result[['primary', 'secondary', on + '_cochanges',
                   on + '_changes', 'coupling']]. \
        sort_values(by='coupling', ascending=False)
