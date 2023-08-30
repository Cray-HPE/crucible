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
vm_script = os.path.join(directory, 'scripts', 'management-vm.sh')


def start(system_name: str = None, **kwargs) -> None:
    """
    Starts the management VM.

    :param system_name: The name of the system, a more recognizable handle.
    :keyword capacity: Capacity (in Gigabytes) for the management VM
                     storage (default 100).
    :keyword interface: The interface for external networking (default lan0)
    :keyword ssh_key_path: The path to the SSH key for the VM's root user
                         (default: /root/.ssh/)
    :keyword ip_address: The CIDR to assign to the external interface in the management VM
    :keyword dns: A comma delimited list of DNS servers to assign to the management VM
    """

    args = [vm_script]
    capacity = kwargs.get('capacity')
    dns = kwargs.get('dns')
    interface = kwargs.get('interface')
    ip_address = kwargs.get('ip_address')
    ssh_key_path = kwargs.get('ssh_key_path')
    if capacity:
        args.extend(['-c', capacity])
    if interface:
        args.extend(['-i', interface])
    if ssh_key_path:
        args.extend(['-s', ssh_key_path])
    if ip_address:
        args.extend(['-I', ip_address])
    if dns:
        args.extend(['-d', dns])
    if system_name:
        args.extend(['-S', system_name])
    click.echo('Starting management VM ... ')
    result = run_command(args, in_shell=True)
    LOG.info(vars(result))
    if result.return_code != 0:
        click.echo('Failed to start the management VM! Check logs.')
    else:
        click.echo('Management VM started.')


def reset() -> None:
    """
    Resets, purges the management VM.
    """
    args = [vm_script, '-r']
    click.echo('Purging/resetting management VM ... ')
    result = run_command(args, in_shell=True)
    if result.return_code != 0:
        click.echo('Failed cleanup the management VM! Check logs and'
                   'then run the `reset` subcommand before trying again.')
    else:
        click.echo('Management VM was purged.')
