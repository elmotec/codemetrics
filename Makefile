.PHONY: clean clean-test clean-pyc clean-build docs help upgrade
.DEFAULT_GOAL := help

define BROWSER_PYSCRIPT
import os, webbrowser, sys

try:
	from urllib import pathname2url
except:
	from urllib.request import pathname2url

webbrowser.open("file://" + pathname2url(os.path.abspath(sys.argv[1])))
endef
export BROWSER_PYSCRIPT

define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
	match = re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-20s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT

BROWSER := uv run --locked python -c "$$BROWSER_PYSCRIPT"

help:
	@uv run --locked python -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

clean: clean-build clean-pyc clean-test ## remove all build, test, coverage and Python artifacts

clean-build: ## remove build artifacts
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

clean-pyc: ## remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test: ## remove test and coverage artifacts
	rm -fr .tox/
	rm -f .coverage
	rm -fr htmlcov/
	rm -fr .pytest_cache

lint: ## check style with flake8
	uv run --locked flake8 codemetrics tests

test: ## run tests quickly with the default Python
	uv run --locked python -m unittest discover -s tests -t .

test-all: ## run tests on every supported Python version
	@for version in 3.11 3.12 3.13 3.14 3.15; do \
		uv run --locked --python $$version python -m unittest discover -s tests -t . || exit $$?; \
	done

coverage: ## check code coverage quickly with the default Python
	uv run --locked coverage run --source codemetrics -m pytest tests
	uv run --locked coverage report -m
	uv run --locked coverage html
	$(BROWSER) htmlcov/index.html

docs: ## build Sphinx HTML documentation, including API docs
	$(MAKE) -C docs clean
	$(MAKE) -C docs html
	$(BROWSER) docs/_build/html/index.html

servedocs: docs ## compile the docs watching for changes
	uv run --locked --group docs watchmedo shell-command -p '*.rst' -c '$(MAKE) -C docs html' -R -D .

release: dist ## package and upload a release
	uv publish

dist: clean ## builds source and wheel package
	uv build
	ls -l dist

install: ## sync the project and development dependencies
	uv sync --locked

upgrade: ## upgrade locked dependencies and pre-commit hooks
	uv lock --upgrade
	uv run --locked pre-commit autoupdate
