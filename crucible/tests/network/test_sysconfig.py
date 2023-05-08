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
Tests for the ``crucible.network.ifname`` module.
"""
# pylint: disable=protected-access
import os

import mock
from mock import mock_open

from crucible.network import sysconfig


class TestSysconfig:
    """
    Tests for the sysconfig network manager type.
    """
    network_manager = None

    def setup_method(self) -> None:
        """
        Sets up the ``sysconfig`` tests.
        """
        self.network_manager = sysconfig.Sysconfig()

    def test_name(self) -> None:
        """
        Asserts sysconfig identifies as sysconfig.
        """
        assert str(self.network_manager) == self.network_manager.name


class TestWicked(TestSysconfig):
    """
    Tests for the wicked network manager.
    """

    mock_config_no_values = '''NETCONFIG_DNS_STATIC_SERVERS=""
NETCONFIG_DNS_STATIC_SEARCHLIST=""
'''
    mock_config_with_values = '''NETCONFIG_DNS_STATIC_SERVERS="9.9.9.9 149.112.112.112"
NETCONFIG_DNS_STATIC_SEARCHLIST="foo bar"
'''

    def setup_method(self) -> None:
        """
        Sets up the ``wicked`` tests.
        """
        self.network_manager = sysconfig.Wicked()

    @mock.patch('crucible.network.sysconfig.os.unlink', spec=True)
    def test_remove_config(self, mock_unlink) -> None:
        """
        Asserts that a config is removed, and that a call to reload interfaces
        was made.
        """
        self.network_manager.interface.name = 'em1'
        self.network_manager.remove_config()
        assert mock_unlink.call_count == 2
        assert mock_unlink.mock_calls[0].args[0] == os.path.join(
            self.network_manager.install_location,
            f'ifcfg-{self.network_manager.interface.name}'
        )
        assert mock_unlink.mock_calls[1].args[0] == os.path.join(
            self.network_manager.install_location,
            f'ifroute-{self.network_manager.interface.name}'
        )

    # FIXME: Check file content.
    # TODO: Check call to ``netconfig update -f``
    def test_update_dns(self) -> None:
        """
        Asserts that DNS servers are written to file, and system call to
        update ``/etc/resolv.conf`` was made.
        """
        self.network_manager.network_config.dns = '8.8.8.8,8.8.4.4'
        with mock.patch(
                'crucible.network.sysconfig.open',
                mock_open(read_data=self.mock_config_no_values)
        ) as mock_config:
            self.network_manager.update_dns()
            assert mock_config
        with mock.patch(
                'crucible.network.sysconfig.open',
                mock_open(read_data=self.mock_config_with_values)
        ) as mock_config:
            self.network_manager.update_dns()
            assert mock_config


    # FIXME: Check file content.
    # TODO: Check call to ``netconfig update -f``
    def test_update_search(self) -> None:
        """
        Asserts that search domains are written to file, and system call to
        update ``/etc/resolv.conf`` was made.
        """
        self.network_manager.network_config.search = 'baz bax'
        with mock.patch(
                'crucible.network.sysconfig.open',
                mock_open(read_data=self.mock_config_no_values)
        ) as mock_config:
            self.network_manager.update_search()
            assert mock_config
        with mock.patch(
                'crucible.network.sysconfig.open',
                mock_open(read_data=self.mock_config_with_values)
        ) as mock_config:
            self.network_manager.update_search()
            assert mock_config

    def test_write_config_dhcp(self) -> None:
        """
        Asserts that an ifcfg file with DHCP is written.
        """
        with mock.patch(
                'crucible.network.sysconfig.open', mock_open()
        ):
            self.network_manager.interface.name = 'mgmt0'
            self.network_manager.interface.dhcp = True
            self.network_manager.write_config('ifcfg')
            self.network_manager.write_config('ifroute')
            # TODO: Test written files.

    def test_write_config_static(self) -> None:
        """
        Asserts that an ifcfg file with DHCP is written.
        """
        with mock.patch(
                'crucible.network.sysconfig.open', mock_open()
        ):
            self.network_manager.interface.name = 'lan0'
            self.network_manager.interface.ipaddr = '192.168.1.2/24'
            self.network_manager.interface.is_default_route = True
            self.network_manager.write_config('ifcfg')
            self.network_manager.write_config('ifroute')
            # TODO: Test written files.

    def test_write_config_bond(self) -> None:
        """
        Asserts that an ifcfg file with bond is written.
        """
        with mock.patch(
                'crucible.network.sysconfig.open', mock_open()
        ):
            self.network_manager.interface.name = 'bond0'
            self.network_manager.interface.ipaddr = '192.168.1.2/24'
            self.network_manager.interface.members = ['mgmt0', 'mgmt1']
            self.network_manager.write_config('ifcfg')
            self.network_manager.write_config('ifroute')
            # TODO: Test written files.

    def test_write_config_bridge(self) -> None:
        """
        Asserts that an ifcfg file for a bridge is written.
        """
        with mock.patch(
                'crucible.network.sysconfig.open', mock_open()
        ):
            self.network_manager.interface.name = 'virbr0'
            self.network_manager.interface.ipaddr = '192.168.1.2/24'
            self.network_manager.interface.members = ['bond0']
            self.network_manager.write_config('ifcfg')
            self.network_manager.write_config('ifroute')
            # TODO: Test written files.

    def test_write_config_vlan(self) -> None:
        """
        Asserts that an ifcfg file for a VLAN is written.
        """
        with mock.patch(
                'crucible.network.sysconfig.open', mock_open()
        ):
            self.network_manager.interface.name = 'bond0.nmn0'
            self.network_manager.interface.ipaddr = '192.168.1.2/24'
            self.network_manager.interface.vlan_id = 2
            self.network_manager.interface.members = ['bond0']
            self.network_manager.write_config('ifcfg')
            self.network_manager.write_config('ifroute')
            # TODO: Test written files.
