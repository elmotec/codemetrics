#!python

"""Tests for cmdline.py."""

import textwrap
import unittest
import unittest.mock as mock

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


if __name__ == "__main__":
    unittest.main()
