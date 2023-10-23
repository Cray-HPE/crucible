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
Base object for network managers, their configuration, and an interface.
"""
# pylint: disable=duplicate-code,too-many-instance-attributes

import re
import dataclasses
import os

import netaddr
import jinja2
from j2ipaddr import filters

from crucible.logger import Logger

jinja2.filters.FILTERS.update(filters.load_all())

LOG = Logger(__name__)


class InterfaceError(Exception):

    """
    An exception for interface problems.
    """

    def __init__(self, message) -> None:
        self.message = message
        super().__init__(self.message)


default_bond_opts = {
    'mode': '802.3ad',
    'miimon': 100,
    'lacp_rate': 'fast',
    'xmit_hash_policy': 'layer2+3',
}


class IPAddr:
    """
    Object for IP information.
    """
    _ipaddr = None

    def __init__(self, interface: str = '', cidr: str = '', **kwargs) -> None:
        """
        Initializes
        :param name: Name of the interface to be worked on.
        :param cidr: CIDR to assign to the interface.
        :param kwargs:
        """
        self.name = interface
        self.dhcp = kwargs.get('dhcp', False)
        self.noip = kwargs.get('noip', False)
        self.ipaddr = cidr

    @property
    def ipaddr(self) -> netaddr.IPNetwork:
        """
        An IP address in CIDR notation.
        """
        return self._ipaddr

    @ipaddr.setter
    def ipaddr(self, new_ipaddr: str) -> None:
        """
        Sets an IP address, if valid, otherwise sets 0.0.0.0/0.
        :param new_ipaddr: The new IP in CIDR notation.
        """
        if new_ipaddr is None:
            return
        try:
            self._ipaddr = netaddr.IPNetwork(new_ipaddr)
        except netaddr.core.AddrFormatError as error:
            LOG.info(error)
            self._ipaddr = netaddr.IPNetwork('0.0.0.0/0')
        finally:
            self.gateway = self._ipaddr[1]

    def is_bridge(self) -> bool:
        """
        Whether this is a bridge or not.
        """
        if re.search(r'br\d+$', self.name):
            return True
        return False

    def is_bond(self) -> bool:
        """
        Whether this is a bond or not.
        """
        if re.match(r'^bond', self.name):
            return True
        return False


@dataclasses.dataclass
class Interface(IPAddr):

    """
    Object for a system network interface.
    """

    def __init__(self, **kwargs) -> None:
        """
        :raises InterfaceError: When the interface is illegal.
        """
        super().__init__(**kwargs)
        self.members = kwargs.get('members', '').split(',')
        self.bond_opts = kwargs.get('bond_opts', default_bond_opts)
        self.vlan_id = kwargs.get('vlan_id', 0)
        self.mtu = kwargs.get('mtu', 9000)
        self.is_default_route = kwargs.get('default', False)

    @property
    def vlan_id(self) -> int:
        """
        The currently assigned VLAN ID.
        """
        return self._vlan_id

    @vlan_id.setter
    def vlan_id(self, new_vlan_id: int) -> None:
        """
        Sets a new VLAN ID.
        :param new_vlan_id: New VLAN ID to set.
        """
        if new_vlan_id < 0 or new_vlan_id > 4094:
            raise InterfaceError(
                'Invalid VLAN ID! Must be between 0 and 4094.'
            )
        self._vlan_id = new_vlan_id

    @vlan_id.deleter
    def vlan_id(self) -> None:
        """
        Unsets the VLAN ID.
        """
        self._vlan_id = 0


class SystemNetwork:

    """
    Base class for a network manager object.
    """

    name = ''
    install_location = ''
    _dns = []
    _search = []

    def __init__(self, **kwargs) -> None:
        """
        Initializes a NetworkManager.
        :param kwargs:
        """
        self.interface = Interface(**kwargs)
        self.dns = kwargs.get('dns', '')
        self.search = kwargs.get('search', '')

    @property
    def dns(self) -> list:
        """
        Prints this objects DNS servers
        """
        return self._dns

    @dns.setter
    def dns(self, new_dns: [list, str]) -> None:
        """
        Sets the DNS property.
        :param new_dns: Static DNS server IP(s)
        """
        if new_dns is not None:
            if isinstance(new_dns, list):
                self._dns = new_dns
            else:
                self._dns = new_dns.split(',')

    @property
    def search(self) -> list:
        """
        Prints this objects search domains.
        """
        return self._search

    @search.setter
    def search(self, new_search: [list, str]) -> None:
        """
        Sets the search property.
        :param new_search: Search domain(s).
        """
        if new_search is not None:
            if isinstance(new_search, list):
                self._search = new_search
            else:
                self._search = new_search.split(',')

    def _render_template(self, template_name: str) -> str:
        """
        Renders a template file from ``templates/``
        """

        directory = os.path.dirname(__file__)
        template_directory = os.path.join(directory, 'templates', self.name)
        loader = jinja2.FileSystemLoader(template_directory)
        env = jinja2.Environment(loader=loader, keep_trailing_newline=True)
        template = env.get_template(f'{template_name}.j2')
        return template.render(interface=self.interface)

    def reload_interface(self) -> None:
        """
        Reloads/loads an interface.
        """

    def remove_config(self) -> None:
        """
        Removes an interface configuration.
        """

    def update_dns(self) -> None:
        """
        Updates the system's static DNS list.
        """

    def update_search(self) -> None:
        """
        Updates the system's static DNS list.
        """

    def write_config(self) -> None:
        """
        Writes a configuration to a file.
        """
