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
Module for handling command line calls.

.. note::
   The ``_CLI`` object is private, the intended usage is to use
   ``run_command``.

"""
from contextlib import contextmanager
from time import time
from subprocess import PIPE
from subprocess import Popen
import os
import platform

from crucible.logger import Logger

LOG = Logger(__file__)


class _CLI:
    """
    An object to abstract the return result from ``run_command``.
    """

    _stdout = b''
    _stderr = b''
    _return_code = None
    _duration = None

    def __init__(self, args: [str, list], shell: bool = False) -> None:
        """
        Create a ``Popen`` object.

        If shell==True then the arguments will be converted to a string if
        a list was passed.
        The conversion is recommended by Popen's documentation:
            https://docs.python.org/3/library/subprocess.html.

        :param args: The arguments (as a list or string) to run with Popen.
        :param shell: Whether to run Popen in a shell (default: False)
        """
        if shell and isinstance(args, list):
            self.args = ' '.join(args)
        else:
            self.args = args
        self.shell = shell
        self._run()

    def _run(self) -> None:
        """
        Invoke the loaded command with ``Popen``.

        Run the arguments and set the object's class variables with the
        results.
        """
        start_time = time()
        try:
            with Popen(
                    self.args,
                    stdout=PIPE,
                    stderr=PIPE,
                    shell=self.shell,
            ) as command:
                stdout, stderr = command.communicate()
        except IOError as error:
            self._stderr = error.strerror
            self._return_code = error.errno
            LOG.error('Could not find command for given args: %s', self.args)
        else:
            try:
                self._stdout = stdout
                self._stderr = stderr
                self._return_code = command.returncode
            except UnicodeDecodeError as error:
                self._stderr = error
                self._return_code = 1
                LOG.error('Could not decode stdout or stderr recieved from given args: %s. \
stdout: %s, stderr %s', self.args, stdout, stderr)
        self._duration = time() - start_time
        if self._return_code and self._duration:
            LOG.info(
                '%s ran for %f (sec) with return code %i',
                self.args,
                self._duration,
                self._return_code
            )

    @property
    def stdout(self) -> [str, bytes]:
        """
        ``stdout`` from the command.
        """
        return self._stdout

    @property
    def stderr(self) -> [str, bytes]:
        """
        ``stderr`` from the command.
        """
        return self._stderr

    @property
    def return_code(self) -> int:
        """
        Return code from the command.
        """
        return self._return_code

    @property
    def duration(self) -> float:
        """
        The duration of the running command.
        """
        return self._duration

    def decode(self, charset: str) -> None:
        """
        Decode ``self.stdout`` and ``self.stderr``.

        Decodes ``self._stdout`` and ``self._stderr`` with the given ``charset``.
        :param charset: The character set to decode with.
        """
        if not isinstance(self._stdout, str):
            try:
                self._stdout = self._stdout.decode(charset)
            except ValueError as error:
                LOG.error("Command output was requested to be decoded as"
                          " %s but failed: %s", charset, error)
                raise error
        if not isinstance(self._stderr, str):
            try:
                self._stderr = self._stderr.decode(charset)
            except ValueError as error:
                LOG.error("Command output was requested to be decoded as"
                          " %s but failed: %s", charset, error)
                raise error


@contextmanager
def chdir(directory: str, create: bool = False) -> None:
    """
    Change directories and run a command.

    Change into a given directory and returns to the original directory on
    exit.

    .. note::
       This does not wrap the yield in a 'try', everything done within
       the else is the user's responsibility.

    .. code-block:: python

        from libcsm.os import chdir

        print('doing things in /dir/foo')
        with chdir('/some/other/dir'):
            # doing things in /some/other/dir
        print('doing more things in /dir/foo')

    :param directory: Where you want to go.
    :param create: Whether you want the entire tree created or not.
    """
    original = os.getcwd()
    if not os.path.exists(directory) and create:
        os.makedirs(directory)
    try:
        os.chdir(directory)
    except OSError:
        LOG.warning('Invalid directory [%s]', directory)
    else:
        yield
    finally:
        os.chdir(original)


def run_command(
        args: [list, str],
        in_shell: bool = False,
        silence: bool = False,
        charset: str = None,
) -> _CLI:
    """
    Run a given command or list of commands by instantiating a ``CLI`` object.

    .. code-block:: python

        from libcsm.os import run_command

        result = run_command(['my', 'args'])
        print(vars(result))

    :param args: List of arguments to run, can also be a string. If a string,
    :param in_shell: Whether to use a shell when invoking the command.
    :param silence: Tells this not to output the command to console.
    :param charset: Returns the command ``stdout`` and ``stderr`` as a
                    string instead of bytes, and decoded with the given
                    ``charset``.
    """
    args_string = [str(x) for x in args]
    if not silence:
        LOG.info(
            'Running sub-command: %s (in shell: %s)',
            ' '.join(args_string),
            in_shell
        )
    result = _CLI(args_string, shell=in_shell)
    if charset:
        result.decode(charset)
    return result


def supported_platforms() -> (bool, str):
    """
    Returns whether the running platform is officially supported.
    This does not cause the program to exit, on the contrary it serves as a
    helper for other functions to handle behavior.
    """
    system = platform.system()
    if system != 'Linux':
        LOG.warning('The detected platform [%s] is not officially supported.',
                    system)
        return False, system
    return True, system
