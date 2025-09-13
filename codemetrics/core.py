#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os.path
import typing

import lizard
import pandas as pd
import sklearn
import sklearn.cluster
import sklearn.feature_extraction.text

from . import internals, scm
from typing import Optional

__all__ = [
    "get_mass_changes",
    "get_ages",
    "get_hot_spots",
    "get_co_changes",
    "guess_components",
    "get_complexity",
]


def get_mass_changes(
    log: pd.DataFrame,
    min_path: Optional[int] = None,
    max_changes_per_path: Optional[float] = None,
) -> pd.DataFrame:
    """Extract mass changesets from the SCM log data frame.

    Calculate the number of files changed by each revision and extract that
    list according to the threshold.

    Args:
        log: SCM log data is expected to contain at least revision, added,
            removed, and path columns.
        min_path: threshold for the number of files changed to consider the
            revision a mass change.
        max_changes_per_path: threshold for the number of changed lines
            (added + removed) per file that changed.

    Returns:
        revisions that had more files changed than the threshold as a pd.DataFrame
        with columns revision, path, changes and changes_per_path.

    """
    data = log.reset_index().copy()[["revision", "path", "added", "removed"]]
    data["changes"] = data["added"] + data["removed"]
    data = (
        data[["revision", "path", "changes"]]
        .groupby("revision", as_index=False)
        .agg({"path": "count", "changes": "sum"})
        .assign(revision=lambda x: x["revision"].astype("string"))
    )
    data["changes_per_path"] = data["changes"] / data["path"]
    if min_path is not None:
        data = data[data["path"] >= min_path]
    if max_changes_per_path is not None:
        data = data[data["changes_per_path"] <= max_changes_per_path]
    return data


def get_ages(
    data: pd.DataFrame,
    by: Optional[typing.Sequence[str]] = None,
) -> pd.DataFrame:
    """Generate age of each file based on last change.

    Takes the output of a SCM log or just the date column and return get_ages.

    Args:
        data: log or date column of log.
        by: keys used to group data before calculating the age.
            See pandas.DataFrame.groupby. Defaults to ['path'].

    Returns:
        age of most recent modification as pandas.DataFrame.

    Example::

        get_ages = codemetrics.get_ages(log_df)

    """
    if by is None:
        by = ["path"]
    now = pd.to_datetime(internals.get_now(), utc=True)
    rv = data.groupby(by)["date"].max().reset_index()
    rv["age"] = now - pd.to_datetime(rv["date"], utc=True)
    rv["age"] /= pd.Timedelta(1, unit="D")
    return rv.drop(columns=["date"])


def get_hot_spots(log, loc, by=None, count_one_change_per=None):
    """Generate hot spots from SCM and loc data.

    Cross SCM log and lines of code as an approximation of complexity to
    determine paths that are complex and change often.

    Args:
        log: output log from SCM.
        loc: output from cloc.
        by: aggregation level can be path (default), another column.
        count_one_change_per: allows one to count one change by day or one
                              change per JIRA instead of one change by revision.

    Returns:
        pandas.DataFrame

    """

    if by is None:
        by = "path"
    if count_one_change_per is None:
        count_one_change_per = ["revision"]
    c_df = loc.copy()
    c_df = c_df.rename(columns={"code": "lines"})
    columns = count_one_change_per + [by]
    ch_df = log[columns].drop_duplicates()[by].value_counts().to_frame("changes")
    df = pd.merge(c_df, ch_df, right_index=True, left_on=by, how="outer").reset_index(
        drop=True
    )
    num_columns = df.select_dtypes(include=["number"]).columns
    df[num_columns] = df[num_columns].fillna(0)
    return df


def get_co_changes(log=None, by=None, on=None):
    """Generate co-changes report.

    Returns a DataFrame with the following columns:
    - primary: first path changed.
    - secondary: second path changed.
    - coupling: how often do the path change together.

    Args:
        log: output log from SCM.
        by: aggregation level. Defaults to path.
        on: Field name to join/merge on. Defaults to revision.

    Returns:
        pandas.DataFrame

    """
    if by is None:
        by = "path"
    if on is None:
        on = "revision"
    df = log[[on, by]].drop_duplicates()
    sj = (
        pd.merge(df, df, on=on)
        .rename(columns={by + "_x": by, by + "_y": "dependency"})
        .groupby([by, "dependency"])
        .count()
        .reset_index()
    )
    result = pd.merge(
        sj[sj[by] == sj["dependency"]][[by, on]], sj[sj[by] != sj["dependency"]], on=by
    ).rename(columns={on + "_x": "changes", on + "_y": "cochanges"})
    result["coupling"] = result["cochanges"] / result["changes"]
    return result[[by, "dependency", "changes", "cochanges", "coupling"]].sort_values(
        by="coupling", ascending=False
    )


def guess_components(paths, stop_words=None, n_clusters=8):
    """Guess components from an iterable of paths.

    Args:
        paths: list of string containing file paths in the project.
        stop_words: stop words. Passed to TfidfVectorizer.
        n_clusters: number of clusters. Passed to MiniBatchKMeans.

    Returns:
        pandas.DataFrame

    See Also:
        sklearn.feature_extraction.text.TfidfVectorizer
        sklearn.cluster.MiniBatchKMeans

    """
    dirs = [os.path.dirname(p.replace("\\", "/")) for p in paths]
    vectorizer = sklearn.feature_extraction.text.TfidfVectorizer(stop_words=stop_words)
    transformed_dirs = vectorizer.fit_transform(dirs)
    algo = sklearn.cluster.MiniBatchKMeans
    clustering = algo(compute_labels=True, n_clusters=n_clusters)
    clustering.fit(transformed_dirs)

    def __cluster_name(center, threshold):
        df = pd.DataFrame(
            data={"feature": vectorizer.get_feature_names_out(), "weight": center}
        )
        df.sort_values(by=["weight", "feature"], ascending=False, inplace=True)
        if (df["weight"] <= threshold).all():
            return ""
        df = df[df["weight"] > threshold]
        return ".".join(df["feature"].tolist())

    cluster_names = [
        __cluster_name(center, 0.4) for center in clustering.cluster_centers_
    ]
    components = [cluster_names[lbl] for lbl in clustering.labels_]
    rv = pd.DataFrame(data={"path": paths, "component": components})
    rv.sort_values(by="component", inplace=True)
    return rv


# Exclude the parameters field for now.
_lizard_fields = [
    fld
    for fld in vars(lizard.FunctionInfo("", "")).keys()
    if fld not in ["filename", "parameters", "full_parameters"]
]
_complexity_fields = _lizard_fields + "file_tokens file_nloc".split()


def get_complexity(
    group: typing.Union[pd.DataFrame, pd.Series], project: scm.Project
) -> pd.DataFrame:
    """Generate complexity information for files and revisions in dataframe.

    For each pair of (path, revision) in the input dataframe, analyze the code
    with lizard and return the output.

    Args:
        group: contains at least path and revision values.
        project: scm.Project derived class used to retrieve files for specific revision in
        `codemetrics.scm.DownloadResult` objects.

    Returns:
        Dataframe containing output of function-level lizard.analyze_

    Example::

        import codemetrics as cm
        log = cm.get_git_log()
        log.groupby(['revision', 'path']).\
            apply(get_complexity, download_func=cm.git.download)

    .. _lizard.analyze: https://github.com/terryyin/lizard

    """
    df = pd.DataFrame(columns=_lizard_fields + ["file_tokens", "file_nloc"])
    downloaded = project.download(group)
    if downloaded is not None:
        path = downloaded.path
        content = downloaded.content
        info = lizard.analyze_file.analyze_source_code(path, content)
        if info.function_list:
            df = pd.DataFrame.from_records(
                [vars(d) for d in info.function_list], columns=_lizard_fields
            ).assign(
                file_tokens=info.token_count,
                file_nloc=info.nloc,
            )
    df = (
        df.rename_axis("function")
        .assign(
            cyclomatic_complexity=lambda x: x["cyclomatic_complexity"].astype("Int32"),
            nloc=lambda x: x["nloc"].astype("Int32"),
            token_count=lambda x: x["token_count"].astype("Int32"),
            start_line=lambda x: x["start_line"].astype("Int32"),
            end_line=lambda x: x["end_line"].astype("Int32"),
            top_nesting_level=lambda x: x["top_nesting_level"].astype("Int32"),
            length=lambda x: (x["end_line"] - x["start_line"] + 1).astype("Int32"),
            fan_in=lambda x: x["fan_in"].astype("Int32"),
            fan_out=lambda x: x["fan_out"].astype("Int32"),
            general_fan_out=lambda x: x["general_fan_out"].astype("Int32"),
        )
        .astype({"name": "string", "long_name": "string"})
    )
    return df
