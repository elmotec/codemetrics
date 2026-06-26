#!python

"""Command line tools for codemetrics."""

import datetime as dt
import io
import pathlib as pl
import sys

import click
import lizard
from dateutil import parser as date_parser

import codemetrics as cm

if __package__:
    from .lizardtokencounts import LizardExtension, span
else:
    from codemetrics.lizardtokencounts import LizardExtension, span


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


def _parse_datetime(ctx, param, value):
    """Parse command line date/datetime options."""
    if value is None:
        return None
    try:
        parsed = date_parser.parse(value)
    except (TypeError, ValueError) as err:
        raise click.BadParameter(str(err)) from err
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed


def _split_csv(ctx, param, value):
    """Parse comma separated command line values."""
    if value is None:
        return None
    values = [elem.strip() for elem in value.split(",")]
    return [elem for elem in values if elem]


def _project(ctx):
    """Build the SCM project configured on the command group."""
    params = ctx.obj
    cwd = pl.Path(params["repo"])
    client = params["client"]
    if params["scm"] == "git":
        return cm.GitProject(cwd=cwd, client=client or "git")
    if params["scm"] == "svn":
        return cm.SvnProject(cwd=cwd, client=client or "svn")
    raise click.ClickException(f"unsupported SCM: {params['scm']}")


def _get_log(ctx):
    """Retrieve the configured SCM log."""
    params = ctx.obj
    return _project(ctx).get_log(
        path=params["path"],
        after=params["after"],
        before=params["before"],
        relative_url=params["relative_url"],
    )


def _format_dataframe(data, output_format="table", limit=None):
    """Format a pandas dataframe for command line output."""
    if limit is not None:
        data = data.head(limit)
    if output_format == "csv":
        stream = io.StringIO()
        data.to_csv(stream, index=False)
        return stream.getvalue()
    if output_format == "json":
        return data.to_json(orient="records", date_format="iso") + "\n"
    return data.to_string(index=False) + "\n"


def _write_dataframe(data, output_format, limit):
    """Write dataframe output to stdout."""
    click.echo(_format_dataframe(data, output_format, limit), nl=False)


def _output_options(func):
    """Apply common output options to report commands."""
    func = click.option(
        "--limit",
        type=click.IntRange(min=1),
        help="Only display the first LIMIT rows.",
    )(func)
    func = click.option(
        "--format",
        "output_format",
        type=click.Choice(["table", "csv", "json"]),
        default="table",
        show_default=True,
        help="Output format.",
    )(func)
    return func


@click.group(invoke_without_command=True)
@click.option(
    "--scm",
    type=click.Choice(["git", "svn"]),
    default="git",
    show_default=True,
    help="SCM backend used to collect history.",
)
@click.option(
    "--repo",
    type=click.Path(file_okay=False),
    default=".",
    show_default=True,
    help="Repository root.",
)
@click.option(
    "--path",
    "path",
    default=".",
    show_default=True,
    help="Repository path to analyze.",
)
@click.option("--after", callback=_parse_datetime, help="Only include later changes.")
@click.option("--before", callback=_parse_datetime, help="Only include earlier changes.")
@click.option("--client", help="SCM client executable.")
@click.option("--relative-url", help="Subversion relative URL.")
@click.version_option(cm.__version__ + " (distributed with codemetrics)")
@click.pass_context
def codemetrics(ctx, scm, repo, path, after, before, client, relative_url):
    """Run codemetrics reports from a source checkout."""
    ctx.ensure_object(dict)
    ctx.obj.update(
        {
            "scm": scm,
            "repo": repo,
            "path": path,
            "after": after,
            "before": before,
            "client": client,
            "relative_url": relative_url,
        }
    )
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        ctx.exit(0)


@codemetrics.command("log")
@_output_options
@click.pass_context
def cli_log(ctx, output_format, limit):
    """Print SCM log data."""
    _write_dataframe(_get_log(ctx), output_format, limit)


@codemetrics.command("loc")
@click.option(
    "--cloc-program",
    default="cloc",
    show_default=True,
    help="cloc executable.",
)
@_output_options
@click.pass_context
def cli_loc(ctx, cloc_program, output_format, limit):
    """Print lines of code by file."""
    loc = cm.get_cloc(_project(ctx), path=ctx.obj["path"], cloc_program=cloc_program)
    _write_dataframe(loc, output_format, limit)


@codemetrics.command("ages")
@click.option(
    "--by",
    callback=_split_csv,
    help="Comma separated grouping columns. Defaults to path.",
)
@_output_options
@click.pass_context
def cli_ages(ctx, by, output_format, limit):
    """Print file age report."""
    _write_dataframe(cm.get_ages(_get_log(ctx), by=by), output_format, limit)


@codemetrics.command("mass-changes")
@click.option("--min-path", type=int, help="Minimum changed files per revision.")
@click.option(
    "--max-changes-per-path",
    type=float,
    help="Maximum changed lines per changed file.",
)
@_output_options
@click.pass_context
def cli_mass_changes(ctx, min_path, max_changes_per_path, output_format, limit):
    """Print revisions that changed many files."""
    report = cm.get_mass_changes(
        _get_log(ctx),
        min_path=min_path,
        max_changes_per_path=max_changes_per_path,
    )
    _write_dataframe(report, output_format, limit)


@codemetrics.command("hot-spots")
@click.option(
    "--by",
    default="path",
    show_default=True,
    help="Column used to join log and LOC data.",
)
@click.option(
    "--count-one-change-per",
    callback=_split_csv,
    help="Comma separated columns used to count one change.",
)
@click.option(
    "--cloc-program",
    default="cloc",
    show_default=True,
    help="cloc executable.",
)
@_output_options
@click.pass_context
def cli_hot_spots(ctx, by, count_one_change_per, cloc_program, output_format, limit):
    """Print files with high complexity and change frequency."""
    project = _project(ctx)
    log = project.get_log(
        path=ctx.obj["path"],
        after=ctx.obj["after"],
        before=ctx.obj["before"],
        relative_url=ctx.obj["relative_url"],
    )
    loc = cm.get_cloc(project, path=ctx.obj["path"], cloc_program=cloc_program)
    report = cm.get_hot_spots(
        log,
        loc,
        by=by,
        count_one_change_per=count_one_change_per,
    )
    _write_dataframe(report, output_format, limit)


@codemetrics.command("co-changes")
@click.option(
    "--by",
    default="path",
    show_default=True,
    help="Column used as the changed entity.",
)
@click.option(
    "--on",
    default="revision",
    show_default=True,
    help="Column used as the change set identifier.",
)
@_output_options
@click.pass_context
def cli_co_changes(ctx, by, on, output_format, limit):
    """Print files that tend to change together."""
    report = cm.get_co_changes(_get_log(ctx), by=by, on=on)
    _write_dataframe(report, output_format, limit)


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


if __name__ == "__main__":
    codemetrics()
