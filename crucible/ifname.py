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
import os
import re

from yaml import safe_load
from glob import glob

from crucible.logger import Logger
from crucible.cli import run_command

LOG = Logger(__name__)


class NIC:
    old_name = ''
    _name = ''
    MAC = ''
    device_id = ''
    vendor_id = ''

    def __init__(self, name, MAC, device_id: '', vendor_id: '') -> None:
        self._name = name
        self.MAC = MAC
        self.device_id = device_id
        self.vendor_id = vendor_id

    def __eq__(self, other: object) -> bool:
        if isinstance(self, other.__class__):
            return self._name == getattr(other, 'name', None) \
                and self.MAC == getattr(other, 'MAC', None) \
                and self.device_id == getattr(other, 'device_id', None) \
                and self.vendor_id == getattr(other, 'vendor_id', None)
        return False

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, new_name: str) -> None:
        self.old_name = self._name
        self._name = new_name

    def __str__(self) -> str:
        return f'{self._name}:{self.MAC}'


def _map_nics() -> list[NIC]:
    """
    Returns a map of all the NICs that the kernel has recognized on the system.
    """
    nic_files = glob('/sys/bus/pci/drivers/*/0000:*/net/*')
    nics = []
    for nic_file in nic_files:
        nic = os.path.basename(nic_file)
        mac_cmd = run_command(['ethtool', '-P', nic], silence=True)
        mac = mac_cmd.stdout.split(' ')[-1]

        pci_id = ''
        nic_kernel_files = os.path.dirname(os.path.dirname(nic_file))
        nic_uevent_file = os.path.join(nic_kernel_files, 'uevent')
        with open(nic_uevent_file, 'r') as uevent:
            for line in uevent:
                if re.search(r'^PCI_ID', line):
                    LOG.info(f"Found PCI_ID in line: {line}")
                    pci_id = line.split('=')[-1]
                    break
        vendor_id, device_id = pci_id.split(':')
        nics.append(
            NIC(
                name=nic,
                MAC=mac,
                device_id=device_id,
                vendor_id=vendor_id,
            )
        )
    return nics


def _rename_nic(name: str, new_name: str) -> bool:
    """
    Renames the NIC to NIC.
    :param name:
    :param new_name:
    :return:
    """
    up = False
    result = run_command(['ip', 'link', 'show', ''])
    pass


def _udev_rule(nic: dict) -> str:
    """

    :param nic:
    :return:
    """
    pass


def _ifname_meta() -> dict:
    """
    Opens the ifname.yml datafile.
    :return: Loaded ifname.yml
    """
    ifname_yml_path = os.path.join(os.path.dirname(__file__), 'ifname.yml')
    with open(ifname_yml_path, 'r') as ifname_yml:
        return safe_load(ifname_yml.read())


def _get_new_names(nics: list[NIC]) -> list[NIC]:
    """
    Given a list of NIC objects, resolve new names using the official prefixes.
    Requires ifname.yml.
    :param nics: Dictionary from _map_nics()
    :returns: list of tuples, each tuple is the NIC's current and new name.
    """
    ifname = _ifname_meta()
    indexes = dict.fromkeys(ifname['prefixes'], 0)
    hsn_ids = [f'{v["vendor_id"]}:{v["device_id"]}'.lower() for v in
               ifname.get('hsn_ids')]
    mgmt_ids = [v["vendor_id"].lower() for v in ifname.get('mgmt_ids')]
    for nic in nics:
        pci_id = f'{nic.vendor_id}:{nic.device_id}'.lower()
        if pci_id in hsn_ids:
            nic.name = f'hsn{indexes["hsn"]}'
            indexes['hsn'] = indexes['hsn'] + 1
        elif nic.vendor_id.lower() in mgmt_ids:
            nic.name = f'mgmt{indexes["mgmt"]}'
            indexes['mgmt'] = indexes['mgmt'] + 1
        else:
            nic.name = f'lan{indexes["lan"]}'
            indexes['lan'] = indexes['lan'] + 1
    return nics


def rename(*args, **kwargs):
    nics = _map_nics()
    nics = _get_new_names(nics)
    print(nics)
