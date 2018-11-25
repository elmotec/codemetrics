#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Progress bar."""

import codemetrics as cm
import tqdm


class ProgressBarAdapter:
    """Adapts interface of tqdm.tqdm in the context of SCM log retrieval.

    Also acts as a context manager.
    """

    def __init__(self, pbar=None, after=None):
        """Creates adapter

        If after is specified, calls reset(after).

        """

        self.pbar = pbar
        if self.pbar is not None:
            self.pbar.unit = 'day'
        self.today = cm.get_now().date()
        self.count = 0
        self.after = None
        if after is not None:
            self.after = after.date()
            self.reset(self.after)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        if self.pbar is not None:
            self.pbar.update(self.pbar.total - self.count)
            self.pbar.close()

    def reset(self, after):
        """Reset the progress bar total iterations from after."""
        if after is None or self.pbar is None:
            return
        self.pbar.total = (self.today - after).days

    def update(self, entry_date):
        """Update the progress bar."""
        if self.pbar is None:
            return
        if hasattr(entry_date, 'hour'):
            entry_date = entry_date.date()
        count = (entry_date - self.after).days
        diff = count - self.count
        if diff > 0:
            self.pbar.update(diff)
            self.count = count


