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
Handles network interface configuration files.
"""
import re
import sys

import click

from crucible.logger import Logger
from crucible.network import manager
from crucible.network import sysconfig
from crucible.network import networkmanager
from crucible.os import run_command

LOG = Logger(__name__)


class NetworkError(Exception):

    """
    An exception for network problems.
    """

    def __init__(self, message) -> None:
        self.message = message
        super().__init__(self.message)


def interface(**kwargs) -> None:
    """
    Configure the given interface.

    """
    name = kwargs.get('interface', None)
    if name:
        LOG.info('Working on interface [%s] ... ', name)

    reload = True

    network_manager = resolve_network_manager(**kwargs)

    LOG.info('Detected network manager: %s', network_manager.name)

    if network_manager.interface.is_bond() or \
            network_manager.interface.is_bridge():
        if not network_manager.interface.members:
            click.echo(
                'Interface is a bond or bridge but no members were given.'
                )
            LOG.critical('No members were given for bond/bridge.')
            sys.exit(1)
    if kwargs.get('defer', False):
        click.echo('Deferring reloading of network handlers.')
        reload = False
    elif kwargs.get('remove'):
        click.echo(f'Removing interface: {name} ... ')
        network_manager.remove_config()
        click.echo('Done.')
        sys.exit(0)
    else:
        network_manager.write_config()
    if reload:
        click.echo('Loading interface configuration ...')
        network_manager.reload_interface()
        click.echo('Done.')


def system(**kwargs) -> None:
    """
    Configures the system with the given network options.
    :param kwargs: NetworkManager parameters.
    """
    network_manager = resolve_network_manager(**kwargs)

    LOG.info('Detected network manager: %s', network_manager.name)

    if network_manager.dns:
        click.echo(f'Writing DNS {network_manager.dns}')
        network_manager.update_dns()
    if network_manager.search:
        click.echo(f'Writing Search domains {network_manager.search}')
        network_manager.update_search()


def resolve_network_manager(**kwargs) -> [manager.SystemNetwork]:
    """
    Resolves the running network manager.
    """
    result = run_command(['systemctl', 'show', '-p', 'FragmentPath', 'network'])
    result.decode('utf-8')
    if re.search(r'NetworkManager', result.stdout):
        return networkmanager.NetworkManager(**kwargs)
    if re.search(r'wicked', result.stdout):
        return sysconfig.Wicked(**kwargs)
    raise NetworkError('Unknown network manager')
