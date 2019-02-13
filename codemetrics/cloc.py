#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""cloc related functions."""

import csv
import pathlib as pl

import pandas as pd

from . import internals


__all__ = ['get_cloc']


def get_cloc(path='.', cloc_program='cloc'):
    """Retrieve lines of code (LOC) using cloc.pl

    For more information about cloc.pl, see http://cloc.sourceforge.net/.

    Args:
        path: path from which to gather statistics.
        cloc_program: name of the program.

    Returns:
        pandas.DataFrame.

    """
    internals.check_run_in_root(path)
    cmdline = f'{cloc_program} --csv --by-file {path}'
    records = []
    try:
        output = internals.run(cmdline).split('\n')
    except FileNotFoundError as err:
        msg = f'{err}. Is {cloc_program} available? Please pass ' \
              'cloc_program=<cloc location> to get_cloc'
        raise FileNotFoundError(msg)
    reader = csv.reader(output)
    for record in reader:
        if len(record) >= 5 and record[0]:
            if record[0].strip() != 'language':
                record[1] = str(pl.Path(record[1]))
                record[2:5] = [int(val) for val in record[2:5]]
            records.append(record[:5])
    columns = records[0]
    cloc = pd.DataFrame.from_records(records[1:], columns=columns).\
        rename(columns={'filename': 'path'})
    cloc.loc[:, 'path'] = cloc['path'].str.replace('\\', '/')
    return cloc
