.. highlight:: shell

============
Installation
============


Stable release
--------------

To install codemetrics, run this command in your terminal:

.. code-block:: console

    $ uv venv
    $ uv pip install codemetrics

This is the preferred method to install codemetrics, as it will always install the most recent stable release.

Install `uv <https://docs.astral.sh/uv/getting-started/installation/>`_ first.


From sources
------------

The sources for codemetrics can be downloaded from the `Github repo`_.

You can either clone the public repository:

.. code-block:: console

    $ git clone git://github.com/elmotec/codemetrics

Or download the `tarball`_:

.. code-block:: console

    $ curl  -OL https://github.com/elmotec/codemetrics/tarball/main

Once you have a copy of the source, you can install it with:

.. code-block:: console

    $ cd codemetrics
    $ uv sync --locked
    $ uv run --locked cm_func_stats --help


.. _Github repo: https://github.com/elmotec/codemetrics
.. _tarball: https://github.com/elmotec/codemetrics/tarball/main
