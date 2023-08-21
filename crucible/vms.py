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
Module for launching VMs.
"""
import os

import click

from crucible.os import run_command
from crucible.logger import Logger


LOG = Logger(__name__)
directory = os.path.dirname(__file__)
vm_script = os.path.join(directory, '..', 'scripts', 'management-vm.sh')


def start(capacity: int, interface: str, ssh_key_path: str) -> None:
    """
    Starts the management VM.

    :param capacity: Capacity (in Gigabytes) for the management VM
                     storage (default 100).
    :param interface: The interface for external networking (default lan0)
    :param ssh_key_path: The path to the SSH key for the VM's root user
                         (default: /root/.ssh/id_rsa.pub)
    """

    args = [vm_script]
    if capacity:
        args.extend(['-c', capacity])
    if interface:
        args.extend(['-i', interface])
    if ssh_key_path:
        args.extend(['-s', ssh_key_path])
    click.echo('Starting management VM ... ')
    result = run_command(args, in_shell=True)
    if result.return_code != 0:
        LOG.critical('Failed to start the management VM! Check logs.')
    click.echo('Management VM started.')


def reset() -> None:
    """
    Resets, purges the management VM.
    """
    args = [vm_script, '-r']
    click.echo('Purging/resetting management VM ... ')
    result = run_command(args, in_shell=True)
    if result.return_code != 0:
        LOG.critical('Failed cleanup the management VM! Check logs.')
    click.echo('Management VM was purged.')
