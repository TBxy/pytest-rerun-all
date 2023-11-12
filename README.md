# pytest-rerun-all
Rerun whole testsuites for a certain time or amount

_Still under development._

## Arguments

`--rerun-time TIME` Rerun tests for 'TIME', argmuent as text (e.g 2 min, 3 hours, ...). Can also be set with the 'RERUN_TIME' environment variable.

## Examples

```shell
pytest --rerun-time "10s" examples  # run tests for 10 secons
pytest --rerun-count "10" examples  # run all tests 10 times
# run all tests 10 times and teardown all fixtures after each run
pytest --rerun-count "10" --rerun-teardown examples 
# run tests for 2 hours with 10 secons delay after each run
pytest --rerun-time "2 hours" --rerun-dealy "10s" examples 
```

## Installation

You can install `pytest-rerun-all` via [pip] from this repo:
<!--- [pip] from [PyPI]: -->

```shell
pip install git+git@github.com:TBxy/pytest-rerun-all.git@main
#pip install pytest-rerun-all # not supported yet
```

## Todos

* Fixture to exclude tests from running more than once (eg. `@pytest_rerun_all.only_once()`)
* If only one test is selected the first tests teardsdown all fixtures, afterwards it is correct.
* Docu
* Tests

## Contributing

Contributions are very welcome. 
Tests are not ready at the moment, use the example scripts.
<!-- Tests can be run with [tox], please ensure
the coverage at least stays the same before you submit a pull request. -->

## License

Distributed under the terms of the [MIT] license, `pytest-rerun-all` is free and open source software


## Issues

If you encounter any problems, please [file an issue] along with a detailed description.

[Cookiecutter]: https://github.com/audreyr/cookiecutter
[@hackebrot]: https://github.com/hackebrot
[MIT]: http://opensource.org/licenses/MIT
[cookiecutter-pytest-plugin]: https://github.com/pytest-dev/cookiecutter-pytest-plugin
[file an issue]: https://github.com/TBxy/pytest-rerun-all/issues
[pytest]: https://github.com/pytest-dev/pytest
[tox]: https://tox.readthedocs.io/en/latest/
[pip]: https://pypi.org/project/pip/
[PyPI]: https://pypi.org/project

----

This [pytest] plugin was generated with [Cookiecutter] along with [@hackebrot]'s [cookiecutter-pytest-plugin] template.

