#!python

"""Tests for cmdline.py."""

import textwrap
import unittest
import unittest.mock as mock

import pandas as pd
from click import testing

from codemetrics import cmdline


class TestCommandLine(unittest.TestCase):
    """Test command line base class."""

    def setUp(self) -> None:
        super().setUp()
        self.runner = testing.CliRunner()

    def invoke(self, *args, **kwargs) -> testing.Result:
        """Forwards call to runner."""
        # kwargs.update({'catch_exceptions': False})
        return self.runner.invoke(cmdline.cm_func_stats, *args, **kwargs)


class TestCommandLineWithoutFile(TestCommandLine):
    """Test usage without the need to read/write a file."""

    def test_no_arguments(self) -> None:
        """No arguments should display a redirection to -help and fail."""
        result = self.invoke([])
        self.assertTrue(0 < result.exit_code)
        self.assertTrue("-help" in result.output)

    @mock.patch("codemetrics.cmdline.get_func_info_from_stream", autospec=True)
    def test_process_function(self, get_func_info) -> None:
        """Process function at line specified in second argument."""
        _ = self.invoke("- 42".split())
        get_func_info.assert_called_with("stdin", mock.ANY, 42)


def write_is_prime(file_name):
    sample_cpp = textwrap.dedent(
        """\
    #include <iostream>
    using namespace std;

    bool IsPrime (int i)
    {
        if(n % i == 0)
        {
            return false;
        }
        return true;
    }

    int main()
    {
      int n, i;
      bool isPrime = true;
      cout << "Enter a positive integer: ";
      cin >> n;
      for(i = 2; i <= n / 2; ++i)
      {
          if (isPrime = IsPrime(i))
              break;
      }
      if (isPrime)
          cout << "This is a prime number";
      else
          cout << "This is not a prime number";
      return 0;
    }
    """
    )
    with open(file_name, "w") as fh:
        fh.write(sample_cpp)


class TestCommandLineOnCppFile(TestCommandLine):
    """Test command line on a sample C++ file."""

    def setUp(self):
        """Forwards to parent setUp()."""
        super().setUp()

    def invoke(self, *args, **kwargs) -> testing.Result:
        """Create a local sample c++ file and calls cli."""
        with self.runner.isolated_filesystem():
            write_is_prime("is_prime.cpp")
            return super().invoke(*args, **kwargs)

    def test_read_file_first_func(self):
        """File reads fine."""
        result = self.invoke("is_prime.cpp 6".split())
        self.assertEqual(0, result.exit_code)
        expected = textwrap.dedent(
            """\
        is_prime.cpp(4): IsPrime@4-11@is_prime.cpp, NLOC: 8, CCN: 2
        is_prime.cpp(4): i occurs 2 time(s), spans 3 lines (37.50%)
        """
        )
        self.assertEqual(expected, result.stdout)

    def test_read_file_second_func(self):
        """File reads fine."""
        result = self.invoke("is_prime.cpp 13".split())
        self.assertEqual(0, result.exit_code)
        expected = textwrap.dedent(
            """\
        is_prime.cpp(13): main@13-29@is_prime.cpp, NLOC: 17, CCN: 4
        is_prime.cpp(15): i occurs 5 time(s), spans 7 lines (41.18%)
        is_prime.cpp(17): cout occurs 3 time(s), spans 11 lines (64.71%)
        is_prime.cpp(16): isPrime occurs 3 time(s), spans 9 lines (52.94%)
        is_prime.cpp(15): n occurs 3 time(s), spans 5 lines (29.41%)
        is_prime.cpp(19): 2 occurs 2 time(s), spans 1 lines (5.88%)
        """
        )
        self.assertEqual(expected, result.stdout)

    def test_bad_line_no(self):
        """Bad line number raise an exception."""
        result = self.invoke("is_prime.cpp 12".split())
        self.assertNotEqual(0, result.exit_code)
        expected = "Error: Invalid value: no function found in is_prime.cpp at line 12"
        self.assertIn(expected, result.output)


class TestCodemetricsCli(unittest.TestCase):
    """Test the codemetrics report command line interface."""

    def setUp(self) -> None:
        super().setUp()
        self.runner = testing.CliRunner()
        self.log = pd.DataFrame(
            {
                "revision": ["1016", "1018", "1018"],
                "author": ["elmotec", "elmotec", "elmotec"],
                "date": pd.to_datetime(
                    [
                        "2018-02-26T10:28:00Z",
                        "2018-02-24T11:14:11Z",
                        "2018-02-24T11:14:11Z",
                    ]
                ),
                "path": ["stats.py", "stats.py", "requirements.txt"],
                "added": [1, 3, 5],
                "removed": [2, 4, 6],
            }
        )
        self.loc = pd.DataFrame(
            {
                "language": ["Python", "Text"],
                "path": ["stats.py", "requirements.txt"],
                "blank": [28, 0],
                "comment": [84, 0],
                "code": [100, 3],
            }
        )

    def invoke(self, args):
        """Invoke the codemetrics command."""
        return self.runner.invoke(cmdline.codemetrics, args)

    def test_help_lists_reports(self):
        """Help displays the new report commands."""
        result = self.invoke(["--help"])
        self.assertEqual(0, result.exit_code)
        self.assertIn("hot-spots", result.output)
        self.assertIn("co-changes", result.output)

    def test_no_arguments_shows_help(self):
        """No arguments should show the command help."""
        result = self.invoke([])
        self.assertEqual(0, result.exit_code)
        self.assertIn("Usage:", result.output)
        self.assertIn("mass-changes", result.output)

    @mock.patch("codemetrics.cmdline.cm.GitProject", autospec=True)
    def test_log_csv(self, git_project):
        """The log command retrieves and prints SCM history."""
        project = git_project.return_value
        project.get_log.return_value = self.log

        result = self.invoke(
            [
                "--repo",
                "repo-root",
                "--path",
                "src",
                "--after",
                "2018-02-01",
                "log",
                "--format",
                "csv",
                "--limit",
                "1",
            ]
        )

        self.assertEqual(0, result.exit_code)
        git_project.assert_called_once_with(cwd=mock.ANY, client="git")
        project.get_log.assert_called_once()
        self.assertTrue(
            result.output.startswith("revision,author,date,path,added,removed\n")
        )
        self.assertIn("1016,elmotec,2018-02-26", result.output)

    @mock.patch("codemetrics.cmdline.cm.get_cloc", autospec=True)
    @mock.patch("codemetrics.cmdline.cm.GitProject", autospec=True)
    def test_loc_table(self, git_project, get_cloc):
        """The loc command retrieves cloc data."""
        get_cloc.return_value = self.loc

        result = self.invoke(["loc", "--cloc-program", "cloc-2"])

        self.assertEqual(0, result.exit_code)
        get_cloc.assert_called_once_with(
            git_project.return_value, path=".", cloc_program="cloc-2"
        )
        self.assertIn("language", result.output)
        self.assertIn("stats.py", result.output)

    @mock.patch("codemetrics.cmdline.cm.get_cloc", autospec=True)
    @mock.patch("codemetrics.cmdline.cm.GitProject", autospec=True)
    def test_hot_spots(self, git_project, get_cloc):
        """The hot-spots command combines log and loc data."""
        project = git_project.return_value
        project.get_log.return_value = self.log
        get_cloc.return_value = self.loc

        result = self.invoke(["hot-spots", "--format", "csv"])

        self.assertEqual(0, result.exit_code)
        self.assertIn("language,path,blank,comment,lines,changes", result.output)
        self.assertIn("stats.py", result.output)

    @mock.patch("codemetrics.cmdline.cm.GitProject", autospec=True)
    def test_mass_changes_json(self, git_project):
        """The mass-changes command filters revisions."""
        git_project.return_value.get_log.return_value = self.log

        result = self.invoke(["mass-changes", "--min-path", "2", "--format", "json"])

        self.assertEqual(0, result.exit_code)
        self.assertIn('"revision":"1018"', result.output)
        self.assertIn('"changes":18', result.output)

    @mock.patch("codemetrics.cmdline.cm.GitProject", autospec=True)
    def test_co_changes(self, git_project):
        """The co-changes command prints logical coupling."""
        git_project.return_value.get_log.return_value = self.log

        result = self.invoke(["co-changes", "--format", "csv"])

        self.assertEqual(0, result.exit_code)
        self.assertIn("path,dependency,changes,cochanges,coupling", result.output)
        self.assertIn("requirements.txt,stats.py,1,1,1.0", result.output)


if __name__ == "__main__":
    unittest.main()
