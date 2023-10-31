import psutil
import pytest
from typing import Literal
from rich import print
import random

from pytest_store import store


def test_randint():
    numbers = [random.randint(5, 10) for _i in range(1, random.randint(2, 4))]
    store.set("numbers", numbers)
    assert len(numbers) < 3


def test_append_randint():
    numbers = [random.randint(0, 5) for _i in range(1, random.randint(1, 3))]
    store.append("numbers", numbers, prefix="randint")
    all_numbers: list = store.get("numbers", [], prefix="randint")
    store.set("numbers_append", all_numbers)
    assert len(all_numbers) < 5
