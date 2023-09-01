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
Module for handling ``sysconfig`` based network managers.
"""
import click

from crucible.network.manager import SystemNetwork

from crucible.os import run_command
from crucible.logger import Logger

LOG = Logger(__name__)


class NetworkManager(SystemNetwork):

    """
    Abstraction of NetworkManager.
    """

    name = "NetworkManager"
    install_location = f'/etc/{name}/system-connections'

    def __str__(self):
        """
        Name of the network manager.
        """
        return self.name

    def update_dns(self) -> None:
        """
        Updates the system's static DNS list.
        """
        raise NotImplementedError('DNS updates for nmcli are not yet implemented.')

    def update_search(self) -> None:
        """
        Updates the system's static DNS list.
        """
        raise NotImplementedError('Search updates for nmcli are not yet implemented.')

    def reload_interface(self) -> None:
        """
        Loads new network interface configuration.
        """
        result = run_command(['nmcli', 'connection', 'reload', self.interface.name])
        LOG.debug(vars(result))
        result = run_command(['nmcli', 'connection', 'up', self.interface.name])
        LOG.debug(vars(result))
        result = run_command(['ip', 'l', 'show', self.interface.name])
        if result.return_code != 0:
            LOG.error('Failed to reload %s', self.interface.name)
            LOG.warning(vars(result))
        else:
            LOG.debug(vars(result))

    def remove_config(self) -> None:
        """
        Removes a network interface configuration.
        """
        result = run_command(['nmcli', 'connection', 'delete', self.interface.name])
        LOG.debug(vars(result))
        self.reload_interface()

    def write_config(self) -> None:
        """
        Write a string to file, prompting the user to overwrite if the file
        already exists.
        """
        args = ['nmcli', 'connection', 'add', 'con-name']
        if self.interface.dhcp:
            ip_args = [
                'ipv4.method', 'auto',
                'ipv6.method', 'disabled',
                'ethernet.mtu', self.interface.mtu,
            ]
        elif self.interface.noip:
            ip_args = [
                'ipv4.method', 'disabled',
                'ipv6.method', 'disabled',
                'ethernet.mtu', self.interface.mtu,
            ]
        else:
            ip_args = [
                'ipv4.address', str(self.interface.ipaddr.ip),
                'ipv4.gateway', str(self.interface.gateway),
                'ipv4.dns', ' '.join(self._dns),
                'ipv4.method', 'manual',
                'ipv6.method', 'disabled',
                'ethernet.mtu', self.interface.mtu,
            ]
        if self.interface.vlan_id != 0:
            interface_args = args + [
                self.interface.name,
                'type', 'vlan',
                'ifname', self.interface.name,
                'dev', self.interface.members[0],
                'id', self.interface.vlan_id,
            ] + ip_args
            result = run_command(interface_args)
            LOG.debug(vars(result))
        elif self.interface.is_bond():
            bond_opts = [f'{key}={value}' for key, value in
                         self.interface.bond_opts.items()]
            interface_args = args + [
                self.interface.name,
                'type', 'bond',
                'ifname', self.interface.name,
                'bond.options', ','.join(bond_opts),
            ] + ip_args
            result = run_command(interface_args)
            LOG.debug(vars(result))
            for member in self.interface.members:
                interface_args = args + [
                    member,
                    'type', 'ethernet',
                    'ifname', member,
                    'master', self.interface.name,
                    'ethernet.mtu', self.interface.mtu,
                ]
                result = run_command(interface_args)
                LOG.debug(vars(result))
        else:
            interface_args = args + [
                self.interface.name,
                'type', 'ethernet',
                'ifname', self.interface.name,
            ] + ip_args
            result = run_command(interface_args)
            LOG.debug(vars(result))
        if result.return_code != 0:
            click.echo(f'Failed to configure: {self.interface.name}')
            LOG.warning(vars(result))
        else:
            LOG.debug(vars(result))
            click.echo(f'Created connection for: {self.interface.name}')
        click.echo('See `nmcli connection` for status.')
