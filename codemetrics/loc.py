#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""cloc related functions."""

import csv
import pathlib as pl

import pandas as pd

from . import internals


def get_cloc(path=None, cloc_program=None):
    """Retrieve lines of code (LOC)

    TODO

    """
    if path is None:
        path = '.'
    if cloc_program is None:
        cloc_program = 'cloc'
    cmdline = f'{cloc_program} --csv --by-file {path}'
    records = []
    reader = csv.reader(internals._run(cmdline))
    for record in reader:
        if len(record) >= 5 and record[0]:
            if record[0] != 'language':
                record[1] = str(pl.Path(record[1]))
                record[2:5] = [int(val) for val in record[2:5]]
            records.append(record[:5])
    columns = 'language,path,blank,comment,code'.split(',')
    return pd.DataFrame.from_records(records[1:], columns=columns)

