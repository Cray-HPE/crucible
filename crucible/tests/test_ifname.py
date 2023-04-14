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
from dataclasses import dataclass
import os

import mock
from mock import mock_open

from crucible import ifname

mock_nics = {
    'em1': {
        'file': '/sys/bus/pci/drivers/i40e/0000:3d:00.0/net/em1',
        'PCI_ID': '8086:37D2',
        'MAC': 'a4:bf:01:38:f1:40',
        'real_name': 'lan0'
    },
    'p801p1': {
        'file': '/sys/bus/pci/drivers/mlx5_core/0000:af:00.0/net/p801p1',
        'PCI_ID': '15B3:1013',
        'MAC': 'b8:59:9f:fe:49:d5',
        'real_name': 'mgmt0'
    },
    'em2': {
        'file': '/sys/bus/pci/drivers/i40e/0000:3d:00.1/net/em2',
        'PCI_ID': '8086:37D2',
        'MAC': 'a4:bf:01:38:f1:41',
        'real_name': 'lan1'
    },
    'p801p2': {
        'file': '/sys/bus/pci/drivers/mlx5_core/0000:af:00.1/net/p801p2',
        'PCI_ID': '15B3:1013',
        'MAC': 'b8:59:9f:fe:49:d7',
        'real_name': 'mgmt1'
    },
    'p1p1': {
        'file': '/sys/bus/pci/drivers/cxi_core/0000:03:00.0/net/p1p1',
        'PCI_ID': '17DB:0501',
        'MAC': '00:40:a6:86:d7:66',
        'real_name': 'hsn0'
    },
    'p1p2': {
        'file': '/sys/bus/pci/drivers/cxi_core/0000:86:00.0/net/p1p2',
        'PCI_ID': '17DB:0501',
        'MAC': '00:40:a6:86:d7:b0',
        'real_name': 'hsn1'
    },
}


@dataclass
class MockCLI:
    stdout = ''
    stderr = ''
    rc = None
    duration = None


def mock_ethtool(*args, **kwargs) -> MockCLI:
    nic = args[0][-1]
    mock_cli = MockCLI()
    mac = mock_nics[nic]['MAC']
    mock_cli.stdout = f'Permanent address: {mac}'
    return mock_cli


def mock_open_pci_id(*args, **kwargs) -> mock.mock:
    parent = os.path.dirname(args[0])
    name = [k for k, v in mock_nics.items() if parent in v['file']].pop()
    pci_id = mock_nics[name]['PCI_ID']
    read_data = f'PCI_ID={pci_id}'
    return mock_open(read_data=read_data)()


@mock.patch('crucible.cli._CLI', spec=True, side_effect=mock_ethtool)
@mock.patch('crucible.ifname.glob', return_value=mock_nics)
class TestIfname:

    def test_get_nics(self, mock_glob, *_) -> None:
        """
        Verify our expected errors cause our custom error to be raised.
        """
        mock_glob.return_value = [v['file'] for _, v in mock_nics.items()]
        expected = []
        for k, v in mock_nics.items():
            vendor_id, device_id = v['PCI_ID'].split(':')
            nic = ifname.NIC(
                name=k,
                MAC=v['MAC'],
                device_id=device_id,
                vendor_id=vendor_id,
            )
            expected.append(nic)
        actual = None
        with mock.patch(f'crucible.ifname.open', side_effect=mock_open_pci_id):
            actual = ifname._map_nics()
            assert actual == expected

    def test_get_renames(self, *_) -> None:
        nics = []
        for k, v in mock_nics.items():
            vendor_id, device_id = v['PCI_ID'].split(':')
            nic = ifname.NIC(
                name=k,
                MAC=v['MAC'],
                device_id=device_id,
                vendor_id=vendor_id,
            )
            nics.append(nic)
        actual = ifname._get_new_names(nics)
        expected = []
        for k, v in mock_nics.items():
            vendor_id, device_id = v['PCI_ID'].split(':')
            nic = ifname.NIC(
                name=v['real_name'],
                MAC=v['MAC'],
                device_id=device_id,
                vendor_id=vendor_id,
            )
            expected.append(nic)
        assert actual == expected
