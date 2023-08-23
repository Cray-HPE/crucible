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
import re
import os
import sys

import click

from crucible.network.manager import SystemNetwork

from crucible.os import run_command
from crucible.logger import Logger

LOG = Logger(__name__)


class Sysconfig(SystemNetwork):

    """
    Main object for all ``sysconfig`` derived network managers.
    """

    name = 'sysconfig'
    install_location = f'/etc/{name}/network'

    def __str__(self):
        """
        Name of the network manager.
        """
        return self.name

    @staticmethod
    def _update_resolv() -> None:
        """
        Forces an update to ``/etc/resolv.conf``.
        """
        run_command(['netconfig', 'update', '-f'])

    def update_dns(self) -> None:
        """
        Updates the DNS of the running system.
        """
        config_path = os.path.join(self.install_location, 'config')
        dns_regex = re.compile(r'(^NETCONFIG_DNS_STATIC_SERVERS=)["\'].*["\']')
        with open(config_path, 'r', encoding='utf-8') as config:
            content = config.readlines()
        new_content = []
        new_dns = " ".join(self._dns)
        for line in content:
            try:
                new_content.append(dns_regex.sub(fr'\g<1>"{new_dns}"', line))
            except re.error:
                new_content.append(line)
        with open(config_path, 'w', encoding='utf-8') as config:
            config.writelines(new_content)
        self._update_resolv()

    def update_search(self) -> None:
        """
        Updates the search domains of the running system.
        """
        config_path = os.path.join(self.install_location, 'config')
        search_regex = re.compile(
            r'(^NETCONFIG_DNS_STATIC_SEARCHLIST=)["\'].*["\']'
        )
        with open(config_path, 'r', encoding='utf-8') as config:
            content = config.readlines()
        new_content = []
        new_search = " ".join(self._search)
        for line in content:
            try:
                new_content.append(
                    search_regex.sub(fr'\g<1>"{new_search}"', line)
                )
            except re.error:
                new_content.append(line)
        with open(config_path, 'w', encoding='utf-8') as config:
            config.writelines(new_content)
        self._update_resolv()


class Wicked(Sysconfig):

    """
    Abstraction of the SUSE Wicked network manager.
    """

    @staticmethod
    def _reload_nanny() -> None:
        """
        Reloads wickedd-nanny, which will jump-start the adoption of new
        interface configurations. This also shakes loose stale configurations
        by reloading the network interface handlers. This does not restart
        the network daemon.
        """
        run_command(['systemctl', 'restart', 'wickedd-nanny'])

    def reload_interface(self, force: bool = False) -> None:
        """
        Loads new network interface configuration.
        :param force: Whether to also reload wickedd-nanny.
        """
        run_command(['wicked', 'ifreload', self.interface.name])
        result = run_command(['ip', 'l', 'show', self.interface.name])
        if result.return_code != 0 or force:
            self._reload_nanny()

    def remove_config(self) -> None:
        """
        Removes a network interface configuration.
        """
        ifcfg_file = os.path.join(
            self.install_location, f'ifcfg-{self.interface.name}', )
        ifroute_file = os.path.join(
            self.install_location, f'ifroute-{self.interface.name}', )
        try:
            os.unlink(ifcfg_file)
        except OSError:
            LOG.info('%s not found, nothing to remove.', ifcfg_file)
        try:
            os.unlink(ifroute_file)
        except OSError:
            LOG.info('%s not found, nothing to remove.', ifroute_file)
        self.reload_interface(self.interface.name)

    def write_config(self) -> None:
        """
        Write a string to file, prompting the user to overwrite if the file
        already exists.
        """
        for config in ['ifcfg', 'ifroute']:
            open_mode = 'w'
            config_path = os.path.join(
                self.install_location, f'{config}-{self.interface.name}'
            )
            if os.path.exists(config_path):
                LOG.warning('File [%s] already exists!', config_path)
                choice = click.prompt(
                    f'An existing config file exists at {config_path}; '
                    f'overwrite or quit?',
                    show_choices=True,
                    type=click.Choice(['o', 'q'], case_sensitive=False)
                )
                if choice == 'q':
                    LOG.info('User chose to exit.')
                    click.echo('Exiting ... ')
                    sys.exit(0)
                LOG.info('Writing %s-%s', config, self.interface.name)
            content = self._render_template(config)
            with open(config_path, open_mode, encoding='utf-8') as config_file:
                config_file.write(content)
            click.echo(f'Wrote {config_path}')
