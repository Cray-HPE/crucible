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
import sys

import os

import click

from crucible.logger import Logger
from crucible.network import manager
from crucible.network import sysconfig

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

    LOG.info('Detected network manager: %s', network_manager)

    if network_manager.interface.is_bond() or \
            network_manager.interface.is_bridge():
        if network_manager.interface.members is None:
            click.echo('Interface is a bond or bridge but no members were '
                       'given.')
            LOG.critical('No members were given for bond/bridge.')
            sys.exit(1)
    if kwargs.get('defer'):
        reload = False
    elif kwargs.get('remove'):
        network_manager.remove_config()
    else:
        network_manager.write_config('ifcfg')
        network_manager.write_config('ifroute')
    if reload:
        network_manager.reload_interface(name)


def system(**kwargs) -> None:
    """
    Configures the system with the given network options.
    :param kwargs: NetworkManager parameters.
    """
    try:
        network_manager = resolve_network_manager(**kwargs)
    except NetworkError as error:
        click.echo(f'Failed! {error}')
        LOG.critical(error.message)
    else:
        network_manager.update_dns()
        LOG.info('Detected network manager: %s', network_manager)


def resolve_network_manager(**kwargs) -> [manager.NetworkManager]:
    """
    Resolves the running network manager.
    """
    # There is probably a much better way to do this than checking directory
    # presence.
    if os.path.isdir('/etc/sysconfig/network'):
        return sysconfig.Wicked(**kwargs)
    raise NetworkError('Unknown network manager')
