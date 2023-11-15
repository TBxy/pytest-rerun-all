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
except ImportError:
    pass

try:
    from icecream import ic
except ImportError:  # Graceful fallback if IceCream isn't installed.
    ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a)  # noqa

# from _pytest.config import notset, Notset
from _pytest.terminal import TerminalReporter
from _pytest.pathlib import bestrelpath


def pytest_addoption(parser):
    group = parser.getgroup("rerun all")
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


# config stash key
rerun_time_key = pytest.StashKey[float]()
rerun_delay_key = pytest.StashKey[float]()
rerun_iter_key = pytest.StashKey[int]()
rerun_fresh_key = pytest.StashKey[bool]()

# session stash key
start_time_key = pytest.StashKey[float]()
next_run_items_key = pytest.StashKey[list[pytest.Item]]()
add_next_key = pytest.StashKey[bool]()

# item stash key
rerun_count_key = pytest.StashKey[int]()
# added for pytest-store support
# store_testname_key = "store_testname"
store_testname_attr = "_store_testname"
# store_run_key = "store_run"
store_run_attr = "_store_run"


def _timedelata_seconds(text: str) -> Optional[float]:
    """retunr timedelate in seconds from a string, None if not possible"""
    parse_date = dateparser.parse(text, languages=["en"], settings={"PARSERS": ["relative-time"]})
    if parse_date is not None:
        return round((parse_date - datetime.datetime.today()).total_seconds(), 2)
    else:
        return None


def get_time_seconds(config: pytest.Config, name="rerun_time") -> float:
    """get seconds from string either from a argument or env variable"""
    _rerun_time_str = config.getvalue(name.lower())
    if not _rerun_time_str:
        _rerun_time_str = os.getenv(name.upper())
    if isinstance(_rerun_time_str, str):
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


def get_rerun_fresh(config: pytest.Config, name="rerun_fresh") -> bool:
    rerun_fresh = config.getvalue(name.lower())
    if not rerun_fresh:
        _rerun_fresh_str = os.getenv(name.upper(), None)
        if _rerun_fresh_str is not None:
            try:
                rerun_fresh = bool(_rerun_fresh_str.lower()[0] in ["o", "y", "1", "t"])
            except ValueError:
                raise UserWarning("Wrong value for RERUN_FRESH.")
    else:
        rerun_fresh = bool(rerun_fresh)
    return rerun_fresh


def pytest_configure(config):
    config.stash[rerun_time_key] = get_time_seconds(config, "rerun_time")
    config.stash[rerun_delay_key] = get_time_seconds(config, "rerun_delay")
    config.stash[rerun_iter_key] = get_rerun_iter(config)
    config.stash[rerun_fresh_key] = get_rerun_fresh(config)

    config.addinivalue_line("markers", "once: run this test only once")
    if config.stash[rerun_time_key]:
        TerminalReporter._get_progress_information_message = _get_progress  # type: ignore
        TerminalReporter.write_fspath_result = _write_fspath_result  # type: ignore


def _write_fspath_result(self: TerminalReporter, nodeid: str, res, **markup: bool) -> None:
    fspath = self.config.rootpath / nodeid.split("::")[0]
    if self.currentfspath is None or fspath != self.currentfspath:
        if self.currentfspath is not None and self._show_progress_info:
            self._write_progress_information_filling_space()
        self.currentfspath = fspath
        relfspath = bestrelpath(self.startpath, fspath)
        self._tw.line()
        self._tw.write(relfspath)
        self._tw.write(f" #{self._session.stash.get(rerun_count_key, 0)} ", light=True)
    self._tw.write(res, flush=True, **markup)


def _get_progress(self: TerminalReporter):
    """
    Report progress in number of tests, not percentage.
    Since we have thousands of tests, 1% is still several tests.
    """
    assert self._session
    min_runtime = self.config.stash.get(rerun_time_key, 0)
    counts = self.config.stash.get(rerun_iter_key, 0)
    # collected = self._session.testscollected
    if counts:
        progressbar = round((self._session.stash.get(rerun_count_key, 0) + 1) / float(counts) * 100)
    elif min_runtime and self._session.stash.get(start_time_key, 0):
        start_time = self._session.stash[start_time_key]
        current_runtime = time.time() - start_time
        progressbar = round(current_runtime / float(min_runtime) * 100)
        progressbar = progressbar if progressbar <= 100 else 100
        if progressbar >= 100:
            progressbar = 99
    else:
        progressbar = 0
    return f"[{progressbar:>3}%]"


def _prepare_next_item(item: pytest.Item, _copy=True):
    if _copy:
        item = copy.copy(item)
    if not getattr(item, store_testname_attr, ""):
        setattr(item, store_testname_attr, item.name.replace("test_", ""))
    if item.stash.get(rerun_count_key, None) is None:
        item.stash[rerun_count_key] = 0
        if "]" not in item.nodeid:
            item._nodeid = f"{item.nodeid}[]"
        else:
            item._nodeid = item.nodeid.replace("]", "-]")
        item._nodeid = item.nodeid.replace("]", f"run{item.stash[rerun_count_key]}]")
    else:
        item.stash[rerun_count_key] += 1
        item._nodeid = item.nodeid.replace(f"run{item.stash[rerun_count_key]-1}", f"run{item.stash[rerun_count_key]}")
    setattr(item, store_run_attr, item.stash[rerun_count_key])
    return item


def _time_not_up(item: pytest.Item):
    rerun_time_seconds = item.session.config.stash.get(rerun_time_key, 0)
    if not rerun_time_seconds:
        return True
    rerun_delay_seconds = item.session.config.stash.get(rerun_delay_key, 0)
    start_time = item.session.stash[start_time_key]
    return time.time() + rerun_delay_seconds < start_time + rerun_time_seconds


def _last_item(item: pytest.Item, nextitem: Optional[pytest.Item]):
    if item.session.config.stash.get(rerun_fresh_key, False):
        return nextitem is None
    else:
        return nextitem == item.session.items[-1]


def _count_not_up(item: pytest.Item):
    rerun_iter = item.session.config.stash.get(rerun_iter_key, 0)
    if not rerun_iter:
        return True
    return item.stash[rerun_count_key] < rerun_iter


def _use_rerun(session: pytest.Session) -> bool:
    rerun_time_seconds = session.config.stash.get(rerun_time_key, 0)
    rerun_iter = session.config.stash.get(rerun_iter_key, 0)
    if rerun_time_seconds or rerun_iter:
        return True
    return False


@pytest.hookimpl(tryfirst=True)
def pytest_runtestloop(session: pytest.Session):
    if not _use_rerun(session):
        return
    if not session.stash.get(start_time_key, None):
        session.stash[start_time_key] = time.time()
    if session.stash.get(add_next_key, None) is None:
        session.stash[add_next_key] = True
    if session.stash.get(next_run_items_key, None) is None:
        session.stash[next_run_items_key] = []


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_protocol(item: pytest.Item, nextitem: Optional[pytest.Item]):
    if not _use_rerun(item.session):
        return
    reports = runtestprotocol(item, nextitem=nextitem, log=False)
    for report in reports:  # 3 reports: setup, call, teardown
        if report.skipped:
            return
    rerun_delay_seconds = item.session.config.stash.get(rerun_delay_key, 0)
    item.session.stash[rerun_count_key] = item.stash[rerun_count_key]  # used for progress  bar

    if (
        nextitem is None
        and item.stash[rerun_count_key] == 0
        and not item.session.config.stash.get(rerun_fresh_key, False)
    ):
        item = _prepare_next_item(item)
        nextitem = item
        item.session.items.append(item)
        item.session.stash[add_next_key] = False
    if item.session.stash[add_next_key]:
        # print("")
        # print(f"ITEM name: {item._nodeid}")
        # print(f"  count:  {item.stash.get(rerun_count_key, -1)}")
        item = _prepare_next_item(item)
        # print(f"  count2: {item.stash.get(rerun_count_key, -1)}")
        item.session.stash[next_run_items_key].append(item)
    else:
        item.session.stash[add_next_key] = True
    if _last_item(item, nextitem) and _time_not_up(item) and _count_not_up(item):
        if nextitem is not None:
            # print("")
            # print(f"NEXTITEM name: {nextitem._nodeid}")
            # print(f"  count:  {nextitem.stash.get(rerun_count_key, -1)}")
            nextitem = _prepare_next_item(nextitem)
            # print(f"  count2: {nextitem.stash.get(rerun_count_key, -1)}")
            item.session.stash[next_run_items_key].append(nextitem)
            item.session.stash[add_next_key] = False
        for _item in item.session.stash.get(next_run_items_key, []):
            item.session.items.append(_item)
        item.session.testscollected = len(item.session.items)
        item.session.stash[next_run_items_key] = []
        if rerun_delay_seconds:
            time.sleep(rerun_delay_seconds)


def pytest_collection_modifyitems(session: pytest.Session, config: pytest.Config, items: list[pytest.Item]) -> None:
    if config.stash.get(rerun_time_key, 0):
        for item in items:
            _prepare_next_item(item, _copy=False)
