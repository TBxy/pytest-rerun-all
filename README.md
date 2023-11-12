# pytest-rerun-all
Rerun whole testsuites for a certain time or amount

_Still under development._

## Arguments

**`--rerun-time <time>`**  
Rerun testsuite for the specified time, argument as text (e.g `"2 min"`, `"3 hours"`, ...), the default unit is seconds. 

**`--rerun-iter <int>`**  
Rerun testsuite for the specified iterations.

**`--rerun-delay <time>`**  
After each testsuite run wait for the specified time, argument as text (e.g `"2 min"`, `10`, ...), the default unit is seconds.

**`--rerun-fresh`**  
Start each testsuite run with _fresh_ fixtures (teardown all fixtures), per default no teardown is done if not needed.

> **NOTE:** All arguments can also be set as environment variables, e.g. `RERUN_TIME="1 hour"`.

## Examples

```shell
pytest --rerun-time "10 min" examples  # run tests for 10 secons
pytest --rerun-iter 10 examples  # run all tests 10 times
# run all tests 10 times and teardown all fixtures after each run
pytest --rerun-iter 10 --rerun-teardown examples 
# run tests for 2 hours with 10 secons delay after each run
pytest --rerun-time "2 hours" --rerun-dealy "10s" examples 
# run tests for 120 seconds with a fresh restart for each testsuite run
RERUN_FRESH=1 pytest --rerun-time 120 examples 
```

## Installation

You can install `pytest-rerun-all` via [pip] from [PyPI] or this [repo]:

```shell
pip install pytest-rerun-all
pip install git+git@github.com:TBxy/pytest-rerun-all.git@main # latest version
```

## Todos

* Fixture to exclude tests from running more than once (e.g. `@pytest_rerun_all.only_once()`)
* Issue with only one selected test (teardown on frist run)
* Output for each new run
* Summary per test with number of fails and pass (maybe only for failed tests ...)
* Write tests
* Github Actions

## Contributing

Contributions are very welcome. 
Tests are not ready at the moment, use the example scripts.
<!-- Tests can be run with [tox], please ensure
the coverage at least stays the same before you submit a pull request. -->

## License

Distributed under the terms of the [MIT] license, `pytest-rerun-all` is free and open source software


## Issues

If you encounter any problems, please [file an issue] along with a detailed description.

[repo]: https://github.com/TBxy/pytest-rerun-all
[Cookiecutter]: https://github.com/audreyr/cookiecutter
[@hackebrot]: https://github.com/hackebrot
[MIT]: http://opensource.org/licenses/MIT
[cookiecutter-pytest-plugin]: https://github.com/pytest-dev/cookiecutter-pytest-plugin
[file an issue]: https://github.com/TBxy/pytest-rerun-all/issues
[pytest]: https://github.com/pytest-dev/pytest
[tox]: https://tox.readthedocs.io/en/latest/
[pip]: https://pypi.org/project/pip/
[PyPI]: https://pypi.org/project/pytest-rerun-all

----

This [pytest] plugin was generated with [Cookiecutter] along with [@hackebrot]'s [cookiecutter-pytest-plugin] template.

