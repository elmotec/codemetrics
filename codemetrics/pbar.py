#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Progress bar."""

import datetime as dt

import tqdm

import codemetrics as cm


class ProgressBarAdapter:
    """Adapts interface of tqdm.tqdm in the context of SCM log retrieval.

    Also acts as a context manager.
    """

    def __init__(self,
                 progress_bar: tqdm.tqdm,
                 after: dt.datetime,
                 ascending:bool=None):
        """Creates adapter to update the progress bar based on days retrieved.

        We can't really know how far we are in processing the SCM log so we
        use dates as an approximation.

        If ascending is not specified, the value None is defaulted and the 
        class will try to figure it out on its own.
        
        Args:
            progress_bar: underlying progress bar.
            after: start of days to cover. Must be tz-aware.
            ascending: whether the SCM tool process log ascendingly or not.

        """

        self.progress_bar = progress_bar
        if self.progress_bar is not None:
            self.progress_bar.unit = 'day'
        self.now = cm.internals.get_now()
        self.count = 0
        assert after.tzinfo is not None, 'requires tz aware datetime'
        self.after = after
        self.reset(self.after)
        self.ascending = ascending

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        if self.progress_bar is not None:
            self.progress_bar.update(self.progress_bar.total - self.count)
            self.progress_bar.close()

    def reset(self, after):
        """Reset the progress bar total iterations from after."""
        if after is None or self.progress_bar is None:
            return
        self.progress_bar.total = (self.now - after).days

    def _is_order_ascending(self, first_date) -> bool:
        """Guess the logging order based on the first date retrieved."""
        # If we are closer to the start date than from the end, we ascend.
        return first_date - self.after < self.now - first_date

    def update(self, current_datetime: dt.datetime):
        """Update the progress bar with current date.
        
        Args:
            current_datetime: current date being processed.
        
        """
        if self.progress_bar is None:
            return
        if self.ascending is None:
            self.ascending = self._is_order_ascending(current_datetime)
        if self.ascending:
            new_count = (current_datetime - self.after).days
        else:
            new_count = (self.now - current_datetime).days
        diff = new_count - self.count
        if diff > 0:
            self.progress_bar.update(diff)
            self.count = new_count
        return

