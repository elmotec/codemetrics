#!python

"""Tests for lizardwordcountspan extension."""

import io
import textwrap
import unittest

import lizard

from codemetrics.lizardtokencounts import LizardExtension, TokenCount


def get_token_counts(file_path, code, target_line_no):
    """Process lines in argument."""
    extensions = lizard.get_extensions([]) + [LizardExtension()]
    analyzer = lizard.FileAnalyzer(extensions)
    results = analyzer.analyze_source_code(file_path, code)
    for function in results.function_list:
        if function.start_line <= target_line_no <= function.end_line:
            return function.token_counts
    # FIXME: How can I access global_pseudo_function here?
    return []


class TestWordCountSpan(unittest.TestCase):
    """Test of TokenCount data structure."""

    def test_repr(self):
        self.assertEqual(
            repr(TokenCount("test", 1, 1)),
            "TokenCount('test', count=1, end_line=1, start_line=1)",
        )

    def test_comparison(self):
        self.assertLess(TokenCount("test", count=3), TokenCount("test", count=5))


class TestTokenCounts(unittest.TestCase):
    """Test ability to retrieve info about specific function."""

    def setUp(self) -> None:
        super().setUp()
        self.input = io.StringIO(
            textwrap.dedent(
                """\
        void foo() { innerfoo(); }

        void bar(int v) {
           v = v + 1;
           if (v % 2)
              return v + 1;
           return v;
        };
        myfunc(2);
        """
            )
        ).read()

    def test_fluentcpp_sample(self) -> None:
        """Test fluentcpp sample."""
        input = io.StringIO(
            textwrap.dedent(
                """\
        void test_fluentcpp() {
            int i = 42;
            f(i);
            f(i+1)
            std::cout << "hello";
            ++i;
        }
        """
            )
        ).read()
        results = get_token_counts("example.cpp", input, 1)
        expected = [
            TokenCount("i", 4, 6, 2),
            TokenCount("f", 2, 4, 3),
            TokenCount("std", 1, 5),
            TokenCount("cout", 1, 5),
            TokenCount("1", 1, 4),
            TokenCount("int", 1, 2),
            TokenCount("42", 1, 2),
        ]
        self.assertEqual(expected, results)

    def test_function_foo(self) -> None:
        """Test sample with function."""
        results = get_token_counts("example.cpp", self.input, 1)
        expected = [TokenCount("innerfoo", count=1, end_line=1)]
        self.assertEqual(expected, results)

    def test_function_bar(self) -> None:
        """Test sample with function."""
        results = get_token_counts("example.cpp", self.input, 3)
        expected = [
            TokenCount("v", count=6, end_line=7, start_line=3),
            TokenCount("1", count=2, end_line=6, start_line=4),
            TokenCount("2", count=1, end_line=5, start_line=5),
            TokenCount("%", count=1, end_line=5, start_line=5),
            TokenCount("int", count=1, end_line=3, start_line=3),
        ]
        self.assertEqual(expected, results)

    def test_line_between_function(self) -> None:
        """Test sample with function."""
        results = get_token_counts("example.cpp", self.input, 2)
        self.assertEqual([], results)
