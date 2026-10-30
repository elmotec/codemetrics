============
Contributing
============

Contributions are welcome, and they are greatly appreciated! Every little bit
helps, and credit will always be given.

You can contribute in many ways:

Types of Contributions
----------------------

Report Bugs
~~~~~~~~~~~

Report bugs at https://github.com/elmotec/codemetrics/issues.

If you are reporting a bug, please include:

* Your operating system name and version.
* Any details about your local setup that might be helpful in troubleshooting.
* Detailed steps to reproduce the bug.

Fix Bugs
~~~~~~~~

Look through the GitHub issues for bugs. Anything tagged with "bug" and "help
wanted" is open to whoever wants to implement it.

Implement Features
~~~~~~~~~~~~~~~~~~

Look through the GitHub issues for features. Anything tagged with "enhancement"
and "help wanted" is open to whoever wants to implement it.

Write Documentation
~~~~~~~~~~~~~~~~~~~

codemetrics could always use more documentation, whether as part of the
official codemetrics docs, in docstrings, or even on the web in blog posts,
articles, and such.

Submit Feedback
~~~~~~~~~~~~~~~

The best way to send feedback is to file an issue at https://github.com/elmotec/codemetrics/issues.

If you are proposing a feature:

* Explain in detail how it would work.
* Keep the scope as narrow as possible, to make it easier to implement.
* Remember that this is a volunteer-driven project, and that contributions
  are welcome :)

Get Started!
------------

Ready to contribute? Here's how to set up `codemetrics` for local development.

1. Fork the `codemetrics` repo on GitHub.
2. Clone your fork locally::

    $ git clone git@github.com:elmotec/codemetrics.git

3. Install `uv <https://docs.astral.sh/uv/getting-started/installation/>`_ and
   sync your local copy (uv creates ``.venv`` and installs the project in editable mode)::

    $ cd codemetrics/
    $ uv sync --locked

   Optional dependencies live in the ``docs`` and ``notebooks`` groups::

    $ uv sync --locked --all-groups

   Use ``uv add PACKAGE`` for runtime dependencies or ``uv add --dev PACKAGE``
   for development tools. Commit both ``pyproject.toml`` and ``uv.lock``.
   After editing dependency declarations manually, run ``uv lock``.
   Use ``uv lock --upgrade-package PACKAGE`` to update a pinned dependency.

4. Create a branch for local development::

    $ git checkout -b name-of-your-bugfix-or-feature

   Now you can make your changes locally.

5. When you're done making changes, check that your changes pass flake8 and the
   tests, including testing other Python versions::

    $ uv run --locked flake8 codemetrics tests
    $ uv run --locked python -m unittest discover -s tests -t .
    $ make test-all

6. Commit your changes and push your branch to GitHub::

    $ git add .
    $ git commit -m "Your detailed description of your changes."
    $ git push origin name-of-your-bugfix-or-feature

7. Submit a pull request through the GitHub website.

Pull Request Guidelines
-----------------------

Before you submit a pull request, check that it meets these guidelines:

1. The pull request should include tests.
2. If the pull request adds functionality, the docs should be updated. Put
   your new functionality into a function with a docstring, and add the
   feature to the list in README.rst.
3. The pull request should work for all supported versions of Python.  Check
   https://github.com/elmotec/codemetrics/actions
   and make sure that the tests pass for all versions.

Tips
----

To run a subset of tests::


    $ uv run --locked python -m unittest tests.test_codemetrics

Deploying
---------

A reminder for the maintainers on how to deploy.
Make sure all your changes are committed (including an entry in HISTORY.rst).
Then run::

    $ make test-all
    $ uv run --locked cz bump --dry-run

Review the version and changelog changes, then run ``uv run --locked cz bump``.
Refresh ``uv.lock`` with ``uv lock`` after bumping the project version and commit
it before pushing the release tag. Tags matching ``v*`` trigger the GitHub Actions
workflow, which builds with ``uv build`` and publishes through PyPI Trusted Publishing.
To build a distribution locally::

    $ uv build

For a manual release, ``uv publish`` uploads the distributions in ``dist/``.
