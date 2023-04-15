#
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
"""
Tests for the ``cmd`` module.
"""
from os import getcwd

from crucible.os import run_command
from crucible.os import chdir


class TestCLI:
    """
    Test class for the ``cli`` module.
    """

    def test_run_command(self) -> None:
        """
        Assert that we can run a command and that if it isn't found an
        error is raised.
        """
        command = ['ls', '-l']
        shell_command = 'ls -l'
        bad_command = 'foo!!!'
        no_shell_result = run_command(shell_command)
        shell_result = run_command(shell_command, in_shell=True)
        bad_result = run_command(bad_command)
        command_result = run_command(command)
        for result in [no_shell_result, shell_result, bad_result,
                       command_result]:
            assert result.duration > 0.0
            assert isinstance(result.return_code, int)
            assert result.stdout or result.stderr

    def test_chdir(self) -> None:
        """
        Assert that our context manager will change directories and
        change back to our original directory.
        """
        original = getcwd()
        with chdir('/'):
            assert getcwd() == '/'
        assert getcwd() == original
