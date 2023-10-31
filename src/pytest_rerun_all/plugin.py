# -*- coding: utf-8 -*-

import os
from typing import Callable, Optional, Union
#import warnings
import pytest

import time

from _pytest.runner import runtestprotocol

try:
    from rich import print
except ImportError:  # Graceful fallback if IceCream isn't installed.
    pass

try:
    from icecream import ic
except ImportError:  # Graceful fallback if IceCream isn't installed.
    ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a)  # noqa

#from _pytest.config import notset, Notset
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


def get_for_seconds(config, name="rerun_for") -> Union[None, float]:
    _rerun_for_str = os.getenv(name.upper())
    if not _rerun_for_str:
        _rerun_for_str = config.getvalue(name.lower())
    if _rerun_for_str:
        try:
            rerun_for = pd.Timedelta(int(_rerun_for_str), unit="sec").total_seconds()  # noqa: N806
        except ValueError:
            rerun_for = pd.Timedelta(_rerun_for_str).total_seconds()
        return rerun_for
    return None


def pytest_configure(config):
    if get_for_seconds(config):
        TerminalReporter._get_progress_information_message = _get_progress  # type: ignore

def _get_progress(self):
    """
    Report progress in number of tests, not percentage.
    Since we have thousands of tests, 1% is still several tests.
    """
    min_runtime = get_for_seconds(self.config, "rerun_for")
    # collected = self._session.testscollected
    if min_runtime and "start_time" in self.config.stash:
        start_time = self.config.stash["start_time"]
        current_runtime = time.time() - start_time
        progressbar = round(current_runtime / float(min_runtime) * 100)
        progressbar = progressbar if progressbar <= 100 else 100
        # if progressbar == "100% " and self.tests_taken < self.tests_count:
        #    progressbar = "99% "
        return f"[{progressbar}%]"
    else:
        return "[0%]"


#def pytest_runtest_setup(item):

# def pytest_runtest_setup(item):
def pytest_runtest_protocol(item, nextitem):
    global first_test, times_up
    # reruns = get_reruns_count(item)
    reports = runtestprotocol(item, nextitem=nextitem, log=False)
    for report in reports:  # 3 reports: setup, call, teardown
        if report.skipped:
            return
    rerun_for_seconds = get_for_seconds(item.session.config, "rerun_for")
    rerun_delay_seconds = get_for_seconds(item.session.config, "rerun_delay")
    print(f"Rerun for seconds: '{rerun_for_seconds}' seconds")
    if not rerun_for_seconds:
        return
    if "first_test_started" not in item.stash:
        item.stash["first_test_started"] = True
        item.session.config.stash["start_time"] = time.time()
        item.first_test = True
    else:
        item.first_test = False
        if rerun_delay_seconds:
            time.sleep(rerun_delay_seconds)
    start_time = item.session.config.stash["start_time"]
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
    # item.ihook.pytest_runtest_logfinish(nodeid=item.nodeid, location=item.location)
    if time.time() > start_time + rerun_for_seconds:
        if item.first_test:
            first_test = "done"
            item.stash.set("test_done", True)
            return
        if item.stash.get("test_done", False):
            item.session.items.append(item)
    else:
        item.session.items.append(item)
    return


