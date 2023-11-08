# -*- coding: utf-8 -*-

import os
from typing import Callable, Optional, Union

# import warnings
import pytest

import time
import copy

from _pytest.runner import runtestprotocol

try:
    from rich import print
except ImportError:  # Graceful fallback if IceCream isn't installed.
    pass

try:
    from icecream import ic
except ImportError:  # Graceful fallback if IceCream isn't installed.
    ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a)  # noqa

# from _pytest.config import notset, Notset
from _pytest.terminal import TerminalReporter

import pandas as pd


def pytest_addoption(parser):
    group = parser.getgroup("rerun")
    group._addoption(
        "--rerun-for",
        action="store",
        type=str,
        metavar="TIME",
        default=None,
        help="Rerun tests for 'TIME', argmuent as text (e.g 2 min, 3 hours, ...). Can also be set with the 'RERUN_FOR' environment variable.",
    )
    group._addoption(
        "--rerun-delay",
        action="store",
        metavar="TIME",
        type=str,
        help="Add time (e.g. 30 sec) delay between reruns.",
    )


def get_for_seconds(config, name="rerun_for") -> float:
    _rerun_for_str = os.getenv(name.upper())
    if not _rerun_for_str:
        _rerun_for_str = config.getvalue(name.lower())
    if _rerun_for_str:
        try:
            rerun_for = pd.Timedelta(int(_rerun_for_str), unit="sec").total_seconds()  # noqa: N806
        except ValueError:
            rerun_for = pd.Timedelta(_rerun_for_str).total_seconds()
        return rerun_for
    return 0


def pytest_configure(config):
    if get_for_seconds(config):
        TerminalReporter._get_progress_information_message = _get_progress  # type: ignore


start_time_key = pytest.StashKey[float]()
next_run_items_key = pytest.StashKey[list[pytest.Item]]()


def _get_progress(self: TerminalReporter):
    """
    Report progress in number of tests, not percentage.
    Since we have thousands of tests, 1% is still several tests.
    """
    min_runtime = get_for_seconds(self.config, "rerun_for")
    # collected = self._session.testscollected
    if min_runtime and self._session.stash.get(start_time_key, None):
        start_time = self._session.stash[start_time_key]
        current_runtime = time.time() - start_time
        progressbar = round(current_runtime / float(min_runtime) * 100)
        progressbar = progressbar if progressbar <= 100 else 100
        if progressbar >= 100:
            progressbar = 99
        return f"[{progressbar:>3}%]"
    else:
        return "[  0%]"


# def pytest_runtest_setup(item):

# def pytest_runtest_setup(item):


def _prepare_next_item(item: pytest.Item, _copy=True):
    if _copy:
        item = copy.copy(item)
    if not hasattr(item, "original_nodeid"):
        item.original_nodeid = item.nodeid
    else:
        item.original_nodeid = item.original_nodeid
    if not hasattr(item, "execution_count"):
        item.execution_count = 0
        if "]" not in item.nodeid:
            item._nodeid = f"{item.nodeid}[]"
        else:
            item._nodeid = item.nodeid.replace("]", "-]")
        item._nodeid = item.nodeid.replace("]", f"run{item.execution_count}]")
    else:
        item.execution_count += 1
        item._nodeid = item.nodeid.replace(f"run{item.execution_count-1}", f"run{item.execution_count}")
    item.store_run = item.execution_count
    return item


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_protocol(item, nextitem):
    # reruns = get_reruns_count(item)
    reports = runtestprotocol(item, nextitem=nextitem, log=False)
    for report in reports:  # 3 reports: setup, call, teardown
        if report.skipped:
            return
    rerun_for_seconds = get_for_seconds(item.session.config, "rerun_for")
    rerun_delay_seconds = get_for_seconds(item.session.config, "rerun_delay")
    if not rerun_for_seconds:
        return
    if not item.session.stash.get(start_time_key, None):
        item.session.stash[start_time_key] = time.time()
    if item.session.stash.get("add_next", None) is None:
        item.session.stash["add_next"] = False
    start_time = item.session.stash[start_time_key]
    item = _prepare_next_item(item)
    if item.session.stash.get(next_run_items_key, None) is None:
        item.session.stash[next_run_items_key] = []
    if item.session.stash["add_next"]:
        item.session.items.append(item)
        item.session.stash["add_next"] = False
    else:
        item.session.stash[next_run_items_key].append(item)
    # if nextitem is None and time.time() + rerun_delay_seconds < start_time + rerun_for_seconds:
    if nextitem == item.session.items[-1] and time.time() + rerun_delay_seconds < start_time + rerun_for_seconds:
        for _item in item.session.stash.get(next_run_items_key, []):
            item.session.items.append(_item)
        # item.session.stash["add_next"] = True
        if nextitem is not None:
            _nextitem = _prepare_next_item(nextitem)
            item.session.items.append(_nextitem)
        item.session.testscollected = len(item.session.items)
        item.session.stash[next_run_items_key] = []
        if rerun_delay_seconds:
            time.sleep(rerun_delay_seconds)

    ## item.ihook.pytest_runtest_logfinish(nodeid=item.nodeid, location=item.location) return


def pytest_collection_modifyitems(session: pytest.Session, config: pytest.Config, items: list[pytest.Item]) -> None:
    if get_for_seconds(config):
        for item in items:
            _prepare_next_item(item, _copy=False)
        if len(items) == 1:
            items.append(_prepare_next_item(item, _copy=True))
