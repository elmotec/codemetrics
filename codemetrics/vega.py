#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os

import pandas as pd

from . import internals


def build_hierarchy(data: pd.DataFrame,
                    get_parent=os.path.dirname,
                    root: str='',
                    max_iter: int=100,
                    col_name: str=None) -> pd.DataFrame:
    """Build a hierarchy from a data set and a get_parent relationship.

    The output frame adds 2 columns in front: id and parent. Both are numerical
    where the parent id identifies the id of the parent as returned by the
    get_parent function.

    The id of the root element is set to 0 and the parent is set to np.nan.

    Args:
        data: data containing the leaves of the tree.
        get_parent: function returning the parent of an element.
        root: expected root of the hierarchy.
        max_iter: maximum number of iterations.
        col_name: name of the column to use as input (default to column 0).

    Returns:
        pandas.DataFrame with the columns id, parent and col_name.
        The parent value identifies the id of the parent in the hierarchy where
        the id 0 is the root. The columns other than col_name are discarded.

    """
    assert isinstance(data, pd.DataFrame), 'DataFrame expected'
    if not col_name:
        col_name = data.columns[0]
    parent = get_parent.__name__
    df = data[[col_name]]
    frames = []
    seen = {root}
    root_actually_seen = False
    count = 0
    for ii in range(max_iter):
        df[parent] = df[col_name].apply(get_parent)
        if root in df[parent].values:
            root_actually_seen = True
        df['id'] = range(count, count + len(df))
        count += len(df)
        frames.append(df)
        df = df.loc[~df[parent].isin(seen), [parent]].\
            drop_duplicates().\
            rename(columns={parent: col_name})
        seen.update(df[col_name])
        if len(df) == 0:
            frames.append(pd.DataFrame(data={'id': [count], col_name: [root],
                                             parent: [None]}))
            break
    if not root_actually_seen:
        msg = f'cannot find root {root} in input frame'
        internals.log.error(msg)
        raise ValueError(msg)
    df = pd.concat(frames, sort=False).drop_duplicates()
    df['id'] = len(df) - df['id'] - 1
    y_name = col_name + '_y'
    merged = pd.merge(df, df, left_on=col_name,
                  right_on=parent, how='right')[[y_name, 'id_y', 'id_x']].\
        rename(columns={y_name: col_name, 'id_y': 'id', 'id_x': 'parent'})
    return merged[['id', 'parent', col_name]].sort_values(by='id').\
        reset_index(drop=True)


def vis_hot_spots(df: pd.DataFrame,
                  changes_threshold: float=0.1,
                  height: int=300,
                  width: int=400) -> dict:
    """Convert get_hot_spots output to a json vega dict.

    Args:
        df: input data returned by :func:`codemetrics.get_hot_spots`
        changes_threshold: records whose ratio of changes to the maximum number
            of changes (biggest circle) is below changes_threshold will not be
            displayed. Defaults to 0.1.
        height: vertical size of the figure.
        width: horizontal size of the figure.

    Returns:
        Vega description suitable to be use with Altair.

    Example::

    >>> from altair.vega.v4 import Vega
    >>> hspots = cm.get_hot_spots(loc_df, log_df)
    >>> desc = cm.vega.vis_hot_spots(hspots)
    >>> Vega(desc)  # display the visualization inline in you notebook.

    See also:
        `Vega circle pack example`_

    .. _Vega circle pack example: https://vega.github.io/editor/#/examples/vega/circle-packing

    """
    max_changes = df['changes'].max()
    df = df.loc[df['changes'] > changes_threshold * max_changes,
                ['path', 'complexity', 'changes']]
    hierarchy = build_hierarchy(df[['path']], root='')
    hierarchy = pd.merge(hierarchy, df,
                         left_on='path', right_on='path', how='left').\
                         sort_values(by='id')
    hierarchy.loc[:, ['complexity', 'changes']] = \
        hierarchy[['complexity', 'changes']].fillna(0)
    json_values = hierarchy.to_json(orient='records')
    desc = {
      "$schema": "https://vega.github.io/schema/vega/v4.json",
      "width": width,
      "height": height,
      "padding": 5,
      "autosize": "none",
      "data": [
        {
          "name": "tree",
          #"values":  ...,
          "transform": [
            {
              "type": "stratify",
              "key": "id",
              "parentKey": "parent"
            },
            {
              "type": "pack",
              "field": "changes",
              "sort": {
                "field": "value",
                "order": "descending"  
              },
              "size": [
                {
                  "signal": "width"
                },
                {
                  "signal": "height"
                }
              ]
            }
          ]
        }
      ],
      "scales": [
        {
          "name": "color",
          "type": "linear",
          "domain": {"data": "tree", "field": "complexity"},
          "range": {
            "scheme": "yelloworangered" 
            },
          "domainMin": 0
        }
      ],
      "marks": [
        {
          "type": "symbol",
          "from": {
            "data": "tree"
          },
          "encode": {
            "enter": {
              "shape": {
                "value": "circle"
              },
              "fill": {
                "scale": "color",
                "field": "complexity"
              },
              "tooltip": {
                "signal": "datum.path + (datum.changes ? ', ' + datum.changes + ' changes' : '') + (datum.complexity ? ', ' + datum.complexity + ' complexity': '')"
               }
            },
            "update": {
              "x": {
                "field": "x"
              },
              "y": {
                "field": "y"
              },
              "size": {
                "signal": "4 * datum.r * datum.r"
              },
              "stroke": {
                "value": "white"
              },
              "strokeWidth": {
                "value": 0.5
              }
            },
            "hover": {
              "stroke": {
                "value": "black"
              },
              "strokeWidth": {
                "value": 2
              }
            }
          }
        }
      ]
    }
    desc["data"][0]["values"] = json.loads(json_values)
    return desc
