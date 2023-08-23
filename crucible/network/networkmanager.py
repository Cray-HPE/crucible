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
        run_command(['nmcli', 'connection', 'reload', self.interface.name])
        result = run_command(['ip', 'l', 'show', self.interface.name])
        if result.return_code != 0:
            LOG.error('Failed to reload %s', self.interface.name)

    def remove_config(self) -> None:
        """
        Removes a network interface configuration.
        """
        run_command(['rm', f'{self.install_location}/*-{self.interface.name}'])
        self.reload_interface()

    def write_config(self) -> None:
        """
        Write a string to file, prompting the user to overwrite if the file
        already exists.
        """
        if self.interface.vlan_id != 0:
            run_command(
                [
                    'nmcli', 'connection', 'add', 'type', 'vlan',
                    'ifname', self.interface.name,
                    'dev', self.interface.members[0],
                    'id', self.interface.vlan_id,
                ]
            )
        elif self.interface.is_bond():
            bond_opts = [f'{key}={value}' for key, value in
                         self.interface.bond_opts.items()]
            run_command(
                ['nmcli', 'connection', 'add', 'type', 'bond',
                 'ifname', self.interface.name,
                 'bond.options', ','.join(bond_opts)]
            )
            for member in self.interface.members:
                run_command(
                    ['nmcli', 'connection', 'add', 'type', 'ethernet',
                     'ifname', member,
                     'master', self.interface.name]
                )

        click.echo(f'Created connections for: {self.interface.name}')
        click.echo('See `nmcli connection` for status.')
