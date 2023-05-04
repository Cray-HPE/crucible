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

#
#  MIT License
#
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

#
#  MIT License
#
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

#
#  MIT License
#
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

#
#  MIT License
#
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
from dataclasses import dataclass
import os

import re
import mock
from mock import mock_open

from crucible.network import ifname

mock_nics = {
    'em1': {
        'file': '/sys/bus/pci/drivers/i40e/0000:3d:00.0/net/em1',
        'PCI_ID': '8086:37D2',
        'mac': 'a4:bf:01:38:f1:40',
        'real_name': 'lan0'
    },
    'p801p1': {
        'file': '/sys/bus/pci/drivers/mlx5_core/0000:af:00.0/net/p801p1',
        'PCI_ID': '15B3:1013',
        'mac': 'b8:59:9f:fe:49:d5',
        'real_name': 'mgmt0'
    },
    'em2': {
        'file': '/sys/bus/pci/drivers/i40e/0000:3d:00.1/net/em2',
        'PCI_ID': '8086:37D2',
        'mac': 'a4:bf:01:38:f1:41',
        'real_name': 'lan1'
    },
    'p801p2': {
        'file': '/sys/bus/pci/drivers/mlx5_core/0000:af:00.1/net/p801p2',
        'PCI_ID': '15B3:1013',
        'mac': 'b8:59:9f:fe:49:d7',
        'real_name': 'sun0'
    },
    'p795p1': {
        'file': '/sys/bus/pci/drivers/mlx5_core/0000:bb:00.0/net/p795p1',
        'PCI_ID': '15B3:1013',
        'mac': 'b8:59:9f:fe:50:00',
        'real_name': 'mgmt1'
    },
    'p795p2': {
        'file': '/sys/bus/pci/drivers/mlx5_core/0000:bb:00.1/net/p795p2',
        'PCI_ID': '15B3:1013',
        'mac': 'b8:59:9f:fe:50:01',
        'real_name': 'sun1'
    },
    'p1p1': {
        'file': '/sys/bus/pci/drivers/cxi_core/0000:03:00.0/net/p1p1',
        'PCI_ID': '17DB:0501',
        'mac': '00:40:a6:86:d7:66',
        'real_name': 'hsn0'
    },
    'p1p2': {
        'file': '/sys/bus/pci/drivers/cxi_core/0000:86:00.0/net/p1p2',
        'PCI_ID': '17DB:0501',
        'mac': '00:40:a6:86:d7:b0',
        'real_name': 'hsn1'
    },
}


@dataclass
class MockCLI:
    """
    Mock ``crucible.os._CLI`` object.
    """
    stdout = ''
    stderr = ''
    return_code = None
    duration = None


def mock_ethtool(*args, **_) -> MockCLI:
    """
    Mock for ``ethtool``.
    :param args: Arguments passed to ``ethtool``.
    """
    nic = args[0][-1]
    mock_cli = MockCLI()
    mac = mock_nics[nic]['mac']
    mock_cli.stdout = f'Permanent address: {mac}'
    return mock_cli


def mock_open_pci_id(*args, **_) -> mock.mock:
    """
    Mock for ``open(<pci_ID file>)``
    :param args: Arguments passed to ``open``
    """
    parent = os.path.dirname(args[0])
    name = [k for k, v in mock_nics.items() if parent in v['file']].pop()
    pci_id = mock_nics[name]['PCI_ID']
    read_data = f'PCI_ID={pci_id}'
    return mock_open(read_data=read_data)()


@mock.patch('crucible.os._CLI', spec=True, side_effect=mock_ethtool)
@mock.patch('crucible.network.ifname.glob', return_value=mock_nics)
class TestIfname:
    """
    Tests for the ifname module.
    """

    nics = []

    def setup_method(self, _) -> None:
        """
        Setup for the ifname tests.
        :param _:
        """
        self.nics = []
        for key, value in mock_nics.items():
            vendor_id, device_id = value['PCI_ID'].split(':')
            nic = ifname.NIC(
                name=key,
                mac=value['mac'],
                device_id=device_id,
                vendor_id=vendor_id,
            )
            assert f'{nic}' == f'{nic.name}:{nic.mac}'
            assert nic != bool
            self.nics.append(nic)

    def test_get_nics(self, mock_glob, *_) -> None:
        """
        Tests whether we can read NICs that are recognized
        by the kernel.
        """
        mock_glob.return_value = [v['file'] for _, v in mock_nics.items()]
        actual = None
        with mock.patch(
                'crucible.network.ifname.open',
                side_effect=mock_open_pci_id
                ):
            actual = ifname.map_nics()
            assert actual == self.nics

    def test_get_renames(self, *_) -> None:
        """
        Tests whether we correctly resolve new names correctly for each NIC.
        """
        actual = ifname.get_new_names(self.nics)
        expected = []
        for value in mock_nics.values():
            vendor_id, device_id = value['PCI_ID'].split(':')
            nic = ifname.NIC(
                name=value['real_name'],
                mac=value['mac'],
                device_id=device_id,
                vendor_id=vendor_id,
            )
            expected.append(nic)
        assert actual == expected

    def test_write_udev_rules(self, *_) -> None:
        """
        Tests whether we correctly render the Jinja template for udev rules.
        """
        mapped = ifname.get_new_names(self.nics)
        actual = ifname._rendor_udev_rules(mapped)
        for nic in mapped:
            assert nic.mac in actual
            assert nic.name in actual

    def test_newlines(self, *_) -> None:
        """
        Tests whether newlines are properly stripped which are frequently
        encountered on a live system.
        """
        new_lines_lexicon = r'\n'
        new_lines_regex = re.compile(new_lines_lexicon)
        new_lines = []
        for value in mock_nics.values():
            vendor_id, device_id = value['PCI_ID'].split(':')
            nic = ifname.NIC(
                name=f'{value["real_name"]}\n',
                mac=f'{value["mac"]}\n',
                device_id=f'{device_id}\n',
                vendor_id=f'{vendor_id}\n',
            )
            new_lines.append(nic)
        actual = ifname.get_new_names(new_lines)
        for nic in actual:
            assert not new_lines_regex.match(nic.name)
            assert not new_lines_regex.match(nic.mac)
            assert not new_lines_regex.match(nic.device_id)
            assert not new_lines_regex.match(nic.vendor_id)
