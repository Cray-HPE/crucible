

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
from contextlib import contextmanager
from time import time
from subprocess import PIPE
from subprocess import Popen
import os
from crucible.logger import Logger

LOG = Logger(__name__)


class _CLI:
    """
    An object to abstract the return result from run_command.
    """
    stdout = ''
    stderr = ''
    rc = None
    duration = None

    def __init__(self, args: [str, list], shell: bool = False) -> None:
        """
        If shell==True then the arguments will be converted to a string if
        a list was passed.
        The conversion is recommended by Popen's documentation:
            https://docs.python.org/3/library/subprocess.html
        :param args: The arguments (as a list or string) to run with Popen.
        :param shell: Whether or not to run Popen in a shell (default: False)
        """
        if shell and isinstance(args, list):
            self.args = ' '.join(args)
        else:
            self.args = args
        self.shell = shell
        self._run()

    def _run(self) -> None:
        """
        Run the arguments and set the object's class variables with the
        results.
        """
        start_time = time()
        try:
            command = Popen(
                self.args, stdout=PIPE, stderr=PIPE, shell=self.shell
            )
            stdout, stderr = command.communicate()
        except IOError as error:
            self.stderr = error.strerror
            self.rc = error.errno
            LOG.error('Could not find command for given args: %s', self.args)
        else:
            self.stdout = stdout.decode('utf8')
            self.stderr = stderr.decode('utf8')
            self.rc = command.returncode
        self.duration = time() - start_time
        if self.rc and self.duration:
            LOG.info(
                '%s ran for %f (sec) with return code %i',
                self.args,
                self.duration,
                self.rc
            )


@contextmanager
def chdir(directory: str, create: bool = False) -> None:
    """
    Changes into a given directory and returns to the original directory on
    exit.

    Note: This does not wrap the yield in a 'try', everything done within
    the else is the user's
    responsibility.
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
        silence: bool = False, ) -> _CLI:
    """
    Runs a command and returns a dict with the stdio, stderr, and rc as keys.
    :param args: List of arguments to run, can also be a string. If a string,
    :param in_shell: Whether or not the command must be ran in a shell.
    :param silence: Tells this not to output the command to console.
    :returns: A CLI object denoting the results.
    """
    if not silence:
        LOG.info(
            'Running sub-command: %s (in shell: %s)', ' '.join(args), in_shell
        )
    return _CLI(args, shell=in_shell)
