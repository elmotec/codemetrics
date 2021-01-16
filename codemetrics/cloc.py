#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""cloc related functions."""

import csv
import dataclasses
import pathlib as pl

import pandas as pd

from . import internals, scm

__all__ = ["get_cloc"]


@dataclasses.dataclass
class ClocEntry:
    language: str
    filename: str
    blank: int
    comment: int
    code: int


def get_cloc(
    project: scm.Project, path: str = ".", cloc_program: str = "cloc"
) -> pd.DataFrame:
    """Retrieve lines of code (LOC) using cloc.pl

    For more information about cloc.pl, see http://cloc.sourceforge.net/.

    Args:
        path: path from which to gather statistics.
        cloc_program: name of the program.
        cwd: current working directory, typically the root of the tree under SCM.

    Returns:
        Output of cloc with columns language, filename (posix), blank,
        comment and code counts.

    """
    internals.check_run_in_root(path, project.cwd)
    cmdline = [cloc_program, "--csv", "--by-file", path]
    cloc_entries = []
    try:
        output = internals.run(cmdline, cwd=project.cwd).split("\n")
    except FileNotFoundError as err:
        msg = (
            f"{err}. Is {cloc_program} available? Please pass "
            "cloc_program=<cloc location> to get_cloc"
        )
        raise FileNotFoundError(msg)
    reader = csv.reader(output)
    for record in reader:
        if len(record) < 5 or not record[0]:
            continue
        if record[0].strip() == "language":
            continue
        # If the record contains more than 5 columns, concat the extra columns in the filename.
        last_filename_col = len(record) - 3
        filename = pl.Path(",".join(record[1:last_filename_col])).as_posix()
        cloc_entry = ClocEntry(
            language=record[0],
            filename=filename,
            blank=int(record[-3]),
            comment=int(record[-2]),
            code=int(record[-1]),
        )
        cloc_entries.append(cloc_entry)
    columns = [f.name for f in dataclasses.fields(ClocEntry)]
    cloc = (
        pd.DataFrame.from_records(
            (dataclasses.astuple(ce) for ce in cloc_entries),
            columns=columns,
        )
        .rename(
            columns={"filename": "path"},
        )
        .astype({"path": "string", "language": "string"})
    )
    return cloc
