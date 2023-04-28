#  MIT License
#
#  (C) Copyright 2023 Hewlett Packard Enterprise Development LP
#
#  Permission is hereby granted, free of charge, to any person obtaining a
#  copy of this software and associated documentation files (the "Software"),
#  to deal in the Software without restriction, including without limitation
#  the rights to use, copy, modify, merge, publish, distribute, sublicense,
#  and/or sell copies of the Software, and to permit persons to whom the
#  Software is furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included
#  in all copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
#  THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
#  OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
#  ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
#  OTHER DEALINGS IN THE SOFTWARE.

#
# MIT License
#
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
from pathlib import Path
import sys

import nox

# Get project root directory
if getattr(sys, "frozen", False) and hasattr(
        sys, "_MEIPASS"
):  # pragma: no cover
    project_root = sys._MEIPASS
else:
    prog = __file__
    project_root = Path(__file__).resolve().parent

COVERAGE_FAIL = 85
ERROR_ON_GENERATE = True
locations = "crucible"
nox.options.sessions = 'test', 'lint', 'cover'


@nox.session(python="3")
def test(session):
    """Default unit test session."""
    # Install all test dependencies, then install this package in-place.
    session.install('.[test]')
    session.install('.')

    # Run pytest against the tests.
    session.run(
        'pytest',
        '--quiet',
        '--cov=crucible',
        '--cov-append',
        '--cov-report=',
        f'--cov-fail-under={COVERAGE_FAIL}',
        '.',
        success_codes=[0, 5], )


@nox.session(python="3")
def lint(session):
    """Run flake8 linter and plugins."""
    session.install('.[lint]')
    session.install('.[test]')
    session.install('.')
    session.run(
        'pylint',
        '--disable',
        'missing-module-docstring',
        '--disable',
        'fixme',
        'crucible', )


@nox.session(python="3")
def cover(session):
    """Run the final coverage report."""
    session.install('.[test]')
    session.install('.')
    session.run(
        'coverage',
        'report',
        '--show-missing',
        f'--fail-under={COVERAGE_FAIL}',
        success_codes=[0, 5]
    )
    session.run("coverage", "erase")
