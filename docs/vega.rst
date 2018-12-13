================
Vega integration
================

Vega is ...

Example
-------

Based on the Vega documentation's `circle pack example`_

.. code-block:: json

    # Circle pack Vega example
    {
      "$schema": "https://vega.github.io/schema/vega/v4.json",
      "width": 600,
      "height": 600,
      "padding": 5,
      "autosize": "none",

      "data": [
        {
          "name": "tree",
          "url": "data/flare.json",
          "transform": [
            {
              "type": "stratify",
              "key": "id",
              "parentKey": "parent"
            },
            {
              "type": "pack",
              "field": "size",
              "sort": {"field": "value"},
              "size": [{"signal": "width"}, {"signal": "height"}]
            }
          ]
        }
      ],

      "scales": [
        {
          "name": "color",
          "type": "sequential",
          "domain": {"data": "tree", "field": "depth"},
          "range": {"scheme": "orangered"},
          "nice": true,
          "zero": false
        }
      ],

      "marks": [
        {
          "type": "symbol",
          "from": {"data": "tree"},
          "encode": {
            "enter": {
              "shape": {"value": "circle"},
              "fill": {"scale": "color", "field": "depth"},
              "tooltip": {"signal": "datum.name + (datum.size ? ', ' + datum.size + ' bytes' : '')"}
            },
            "update": {
              "x": {"field": "x"},
              "y": {"field": "y"},
              "size": {"signal": "4 * datum.r * datum.r"},
              "stroke": {"value": "white"},
              "strokeWidth": {"value": 0.5}
            },
            "hover": {
              "stroke": {"value": "red"},
              "strokeWidth": {"value": 2}
            }
          }
        }
      ],

      "encoding": {
        "color": {
          "field": "series",
          "type": "nominal",
          "scale": {"scheme": "blues"}
        }
      }
    }



Links
-----

.. _circle pack example: https://vega.github.io/editor/#/examples/vega/circle-packing
