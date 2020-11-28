#!python

"""Complementary tool to analyze legacy code."""

import sys

import click
import lizard

import codemetrics as cm

from .lizardtokencounts import LizardExtension, span


def get_func_info_from_stream(file_path, code, line_no):
    """Process entire file and return lizard.FileInfo for the function."""
    extensions = lizard.get_extensions([]) + [LizardExtension()]
    analyzer = lizard.FileAnalyzer(extensions)
    results = analyzer.analyze_source_code(file_path, code)
    for function in results.function_list:
        if function.start_line <= line_no <= function.end_line:
            return function
    # FIXME: How can I access global_pseudo_function here?
    return


def get_func_info(file_path, line_no):
    """Open the file and call get_info_from_stream."""
    if file_path == "-":
        return get_func_info_from_stream("stdin", sys.stdin, line_no)
    with open(file_path, "r") as fh:
        return get_func_info_from_stream(file_path, fh.read(), line_no)


@click.command()
@click.argument(
    "file_path", type=click.Path(dir_okay=False, exists=True, allow_dash=True)
)
@click.argument("line_no", type=int)
@click.version_option(cm.__version__ + " (distributed with codemetrics)")
def cm_func_stats(file_path, line_no):
    """Generate statistics on the function specified by FILE_PATH LINE_NO."""
    func_info = get_func_info(file_path, line_no)
    if not func_info:
        msg = f"no function found in {file_path} at line {line_no}"
        raise click.BadParameter(msg)
    sys.stdout.write(
        f"{file_path}({func_info.start_line}): "
        f"{func_info.location.strip()}, NLOC: {func_info.nloc}, "
        f"CCN: {func_info.cyclomatic_complexity}\n"
    )
    func_span = span(func_info)
    for token in func_info.token_counts:
        if token.count <= 1:
            continue
        rel_span = span(token) / func_span * 100.0
        sys.stdout.write(
            f"{file_path}({token.start_line}): "
            f"{token.word} occurs {token.count} time(s), "
            f"spans {span(token)} lines ({rel_span:.2f}%)\n"
        )
