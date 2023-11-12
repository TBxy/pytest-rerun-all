# -*- coding: utf-8 -*-

import datetime
import os
from typing import Callable, Optional, Union
import dateparser

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
    group = parser.getgroup("rerun testsuite")
    group._addoption(
        "--rerun-time",
        action="store",
        type=str,
        metavar="TIME",
        default=None,
        help="Rerun testsuite for the specified time, argument as text (e.g 2 min, 3 hours, ...), the default unit is seconds. (Env: RERUN_TIME)",
    )
    group._addoption(
        "--rerun-iter",
        action="store",
        type=int,
        metavar="INT",
        default=None,
        help="Rerun testsuite for the specified iterations. (Env: RERUN_ITER)",
    )
    group._addoption(
        "--rerun-delay",
        action="store",
        metavar="TIME",
        type=str,
        help="After each testsuite run wait for the specified time, argument as text (e.g 2 min, 10, ...), the default unit is seconds. (Env: RERUN_DELAY)",
    )
    group._addoption(
        "--rerun-fresh",
        action="store_true",
        help='Start each testsuite run with "fresh" fixtures (teardown all fixtures), per default no teardown is done if not needed. (Env: RERUN_FRESH)',
    )


def _timedelata_seconds(text: str) -> Optional[float]:
    parse_date = dateparser.parse(text, languages=["en"], settings={"PARSERS": ["relative-time"]})
    if parse_date is not None:
        return round((parse_date - datetime.datetime.today()).total_seconds(), 2)
    else:
        return None


def get_time_seconds(config: pytest.Config, name="rerun_time") -> float:
    _rerun_time_str = config.getvalue(name.lower())
    if not _rerun_time_str:
        _rerun_time_str = os.getenv(name.upper())
    if _rerun_time_str:
        rerun_time = _timedelata_seconds(_rerun_time_str)
        if rerun_time is None:  # no unit
            _rerun_time_str = f"{_rerun_time_str} sec"
            rerun_time = _timedelata_seconds(_rerun_time_str)
        if rerun_time is not None and rerun_time < 0:
            rerun_time = _timedelata_seconds(f"in {_rerun_time_str}")
        if rerun_time is None:  # no unit
            raise UserWarning(f"Could not parse time '{_rerun_time_str}'.")
        return rerun_time
    return 0


def get_rerun_iter(config: pytest.Config, name="rerun_iter") -> int:
    _rerun_iter_str = config.getvalue(name.lower())
    if not _rerun_iter_str:
        _rerun_iter_str = os.getenv(name.upper())
    if _rerun_iter_str:
        try:
            rerun_iter = int(_rerun_iter_str)
        except ValueError:
            raise UserWarning("Wrong value for --rerun-iter.")
        return rerun_iter
    return 0


def get_rerun_fresh(config: pytest.Config, name="rerun_fresh") -> int:
    rerun_fresh = config.getvalue(name.lower())
    if not rerun_fresh:
        _rerun_fresh_str = os.getenv(name.upper())
    else:
        try:
            rerun_fresh = bool(int(_rerun_fresh_str))
        except ValueError:
            raise UserWarning("Wrong value for RERUN_FRESH.")
    return rerun_fresh


def pytest_configure(config):
    if get_time_seconds(config):
        TerminalReporter._get_progress_information_message = _get_progress  # type: ignore


start_time_key = pytest.StashKey[float]()
exec_count_key = pytest.StashKey[int]()
next_run_items_key = pytest.StashKey[list[pytest.Item]]()
add_next_key = pytest.StashKey[bool]()


def _get_progress(self: TerminalReporter):
    """
    Report progress in number of tests, not percentage.
    Since we have thousands of tests, 1% is still several tests.
    """
    min_runtime = get_time_seconds(self.config, "rerun_time")
    counts = get_rerun_iter(self.config)
    # collected = self._session.testscollected
    if counts:
        progressbar = round((self._session.stash.get(exec_count_key, 0) + 1) / float(counts) * 100)
    elif min_runtime and self._session.stash.get(start_time_key, None):
        start_time = self._session.stash[start_time_key]
        current_runtime = time.time() - start_time
        progressbar = round(current_runtime / float(min_runtime) * 100)
        progressbar = progressbar if progressbar <= 100 else 100
        if progressbar >= 100:
            progressbar = 99
    else:
        progressbar = 0
    return f"[{progressbar:>3}%]"


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


def _time_not_up(item: pytest.Item):
    rerun_time_seconds = get_time_seconds(item.session.config, "rerun_time")
    if not rerun_time_seconds:
        return True
    rerun_delay_seconds = get_time_seconds(item.session.config, "rerun_delay")
    start_time = item.session.stash[start_time_key]
    return time.time() + rerun_delay_seconds < start_time + rerun_time_seconds


def _last_item(item: pytest.Item, nextitem: Optional[pytest.Item]):
    if get_rerun_fresh(item.session.config):
        return nextitem is None
    else:
        return nextitem == item.session.items[-1]


def _count_not_up(item: pytest.Item):
    rerun_iter = get_rerun_iter(item.session.config)
    if not rerun_iter:
        return True
    return item.execution_count < rerun_iter


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_protocol(item: pytest.Item, nextitem: Optional[pytest.Item]):
    # reruns = get_reruns_count(item)
    reports = runtestprotocol(item, nextitem=nextitem, log=False)
    for report in reports:  # 3 reports: setup, call, teardown
        if report.skipped:
            return
    rerun_time_seconds = get_time_seconds(item.session.config, "rerun_time")
    rerun_delay_seconds = get_time_seconds(item.session.config, "rerun_delay")
    rerun_iter = get_rerun_iter(item.session.config, "rerun_iter")
    if not rerun_time_seconds and not rerun_iter:
        return
    item.session.stash[exec_count_key] = item.execution_count
    if not item.session.stash.get(start_time_key, None):
        item.session.stash[start_time_key] = time.time()
    if item.session.stash.get(add_next_key, None) is None:
        item.session.stash[add_next_key] = True
    start_time = item.session.stash[start_time_key]
    if item.session.stash.get(next_run_items_key, None) is None:
        item.session.stash[next_run_items_key] = []

    if nextitem is None and item.execution_count == 0 and not get_rerun_fresh(item.session.config):
        item = _prepare_next_item(item)
        nextitem = item
        item.session.items.append(item)
        item.session.stash[add_next_key] = False
    item = _prepare_next_item(item)
    if item.session.stash[add_next_key]:
        item.session.stash[next_run_items_key].append(item)
    else:
        item.session.stash[add_next_key] = True
    if _last_item(item, nextitem) and _time_not_up(item) and _count_not_up(item):
        if nextitem is not None:
            _nextitem = _prepare_next_item(nextitem)
            item.session.stash[next_run_items_key].append(_nextitem)
            item.session.stash[add_next_key] = False
        for _item in item.session.stash.get(next_run_items_key, []):
            item.session.items.append(_item)
        item.session.testscollected = len(item.session.items)
        item.session.stash[next_run_items_key] = []
        if rerun_delay_seconds:
            time.sleep(rerun_delay_seconds)

    ## item.ihook.pytest_runtest_logfinish(nodeid=item.nodeid, location=item.location) return


def pytest_collection_modifyitems(session: pytest.Session, config: pytest.Config, items: list[pytest.Item]) -> None:
    if get_time_seconds(config):
        for item in items:
            _prepare_next_item(item, _copy=False)
