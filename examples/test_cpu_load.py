import psutil
import pytest
from typing import Literal
from rich import print

import time

from pytest_store import store


def cpu_load(minutes: Literal[1, 5, 15] = 5):
    idx = int(minutes / 5) if minutes in [1, 5] else 2
    load = psutil.getloadavg()[idx]
    time.sleep(0.02)
    return int((load / psutil.cpu_count()) * 100)


@pytest.mark.parametrize("load,expected", ((1, 80), (5, 50), (15, 45)))
def test_cpu_load(load, expected):
    cpu_load_percent = cpu_load(load)
    # print(f"cpu load: {cpu_load_percent}%")
    print("set cpu load: ", cpu_load_percent)
    store.set(f"{load}min", cpu_load_percent)
    assert cpu_load_percent < expected


def test_mem_usage():
    mem_percent = psutil.virtual_memory()[2]
    time.sleep(0.01)
    # print(f"mem usage: {mem_percent}%")
    store.set("percent", mem_percent)
    # print("ID", store.item.nodeid)
    assert mem_percent < 90


def test_network():
    net = psutil.net_io_counters(pernic=False, nowrap=False)
    time.sleep(0.01)
    # print("network: ", net)
    store.set("errin", net.errin)
    store.set("errout", net.errout)
    assert net.errin == 0
    assert net.errout == 0
