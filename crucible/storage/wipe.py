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
Module handling wiping/resetting local disks.
"""
# TODO: Rewrite wipe.sh in Python within this module.
import os

import click
from crucible.os import run_command
from crucible.logger import Logger

LOG = Logger(__file__)


def purge() -> None:
    """
    Runs the wipe flow.

    """
    click.echo('Wiping disks ... ')
    directory = os.path.dirname(__file__)
    wipe_script = os.path.join(directory, '..', 'scripts', 'wipe.sh')
    result = run_command([wipe_script, '-y'], in_shell=True)
    if result.return_code != 0:
        LOG.critical('Failed to wipe disks! Verify ``lsblk`` output.')
