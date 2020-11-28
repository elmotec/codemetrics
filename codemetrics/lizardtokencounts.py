#!python

"""
Lizard extension to count occurences and span of tokens within a function.

:seealso:
https://www.fluentcpp.com/2018/10/23/word-counting-span/
https://github.com/terryyin/lizard/tree/master/lizard_ext

Note the style of this module is consistent with the lizard project as we may
move it there if it adds value.

"""

import functools

from lizard_ext.keywords import IGNORED_WORDS


def span(line_obj):
    """Calculate number of lines between the start_line and end_line."""
    assert line_obj.end_line is not None
    assert line_obj.start_line is not None
    return line_obj.end_line - line_obj.start_line + 1


@functools.total_ordering
class TokenCount(object):
    """Holds information about token statistics."""

    __slots__ = ["word", "count", "end_line", "start_line"]

    def __init__(self, word, count=None, end_line=None, start_line=None):
        self.count = count or 0
        self.end_line = end_line or 0
        self.start_line = start_line or self.end_line
        self.word = word

    def __repr__(self):
        return (
            f"{__class__.__name__}('{self.word}', "
            f"count={self.count}, end_line={self.end_line}, start_line={self.start_line})"
        )

    def inc_count(self, line_no):
        """Increment count and update the end_line line seen."""
        self.end_line = line_no
        self.count += 1
        return self

    def __eq__(self, other):
        return (self.count, self.end_line, self.start_line, self.word) == (
            other.count,
            other.end_line,
            other.start_line,
            other.word,
        )

    def __lt__(self, other):
        return (self.count, self.end_line, self.start_line, self.word) < (
            other.count,
            other.end_line,
            other.start_line,
            other.word,
        )


class LizardExtension(object):
    """Extension to collect word count and span."""

    @staticmethod
    def __call__(tokens, reader):
        """
        The function will be used in multiple threading tasks.
        So don't store any data with an extension object.
        """
        ignored_words = IGNORED_WORDS
        ignored_first_char = ('"', "'", "#")
        ignored_words.add(" ")
        occurences = {}
        for token in tokens:
            if token in ignored_words or token[0] in ignored_first_char:
                yield token
                continue
            current_line = reader.context.current_line
            # if reader.context._nesting_stack.current_nesting_level < 1:
            #     current_function = reader.context.global_pseudo_function
            # else:
            current_function = reader.context.current_function
            if current_function not in occurences:
                occurences[current_function] = {}
            if token not in occurences[current_function]:
                occurences[current_function][token] = TokenCount(
                    token, start_line=current_line
                )
            occurences[current_function][token].inc_count(current_line)
            yield token
        for function in reader.context.fileinfo.function_list:
            if function not in occurences:
                function.token_counts = []
                continue
            func_occurences = occurences[function]
            result = sorted(func_occurences.values(), reverse=True)
            function.token_counts = result
        return

    def cross_file_process(self, fileinfos):
        """
        Combine the statistics from each file.
        Because the statistics came from multiple thread tasks. This function
        needs to be called to collect the combined result.
        """
        for fileinfo in fileinfos:
            if hasattr(fileinfo, "token_counts"):
                for k, val in fileinfo.wordCount.items():
                    self.result[k] = self.result.get(k, 0) + val
            yield fileinfo
