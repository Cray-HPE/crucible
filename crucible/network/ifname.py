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
Interface naming module.
"""
import os
import re
import sys
from glob import glob

import itertools
import click
from jinja2 import Environment
from jinja2 import FileSystemLoader
from yaml import safe_load

from crucible.logger import Logger
from crucible.os import run_command
from crucible.os import supported_platforms

LOG = Logger(__name__)


class UdevError(Exception):

    """
    An exception for udev problems.
    """

    def __init__(self, message) -> None:
        self.message = message
        super().__init__(self.message)


class PrefixIndexes:
    """
    Defines allowed network names, and provides an index/counter for naming
    interfaces.
    """
    prefix_lan = 'lan'
    prefix_mgmt = 'mgmt'
    prefix_hsn = 'hsn'
    prefix_sun = 'sun'

    def __init__(self) -> None:
        """
        Sets the indexes to 0.
        """
        self._lan_idx = itertools.count()
        self._mgmt_idx = itertools.count()
        self._hsn_idx = itertools.count()
        self._sun_idx = itertools.count()

    @property
    def lan(self) -> str:
        """
        Prints an index number for the local area network interface(s).
        """
        return f'{self.prefix_lan}{next(self._lan_idx)}'

    @property
    def mgmt(self) -> str:
        """
        Prints an index number for the management network interface(s).
        """
        return f'{self.prefix_mgmt}{next(self._mgmt_idx)}'

    @property
    def hsn(self) -> str:
        """
        Prints an index number for the high-speed network interface(s).
        """
        return f'{self.prefix_hsn}{next(self._hsn_idx)}'

    @property
    def sun(self) -> str:
        """
        Prints an index number for the storage utility network interface(s).
        """
        return f'{self.prefix_sun}{next(self._sun_idx)}'


class NIC:
    """
    Abstraction for a network interface.
    """
    old_name = ''
    _name = ''
    _mac = ''
    device_id = ''
    vendor_id = ''

    def __init__(
            self,
            name: str,
            mac: str,
            device_id: str = '',
            vendor_id: str = '',
    ) -> None:
        """
        Initializes a NIC abstraction.

        :param name: The physical name of the NIC.
        :param mac: The physical hardware address for the NIC.
        :param device_id: The PCI device ID for the NIC.
        :param vendor_id: The PCI vendor ID for the NIC.
        """
        self._name = name.strip()
        self._mac = mac.strip()
        self.device_id = device_id.strip()
        self.vendor_id = vendor_id.strip()

    def __eq__(self, other: object) -> bool:
        """
        Comparison function for use against other objects.

        \f
        :param other: The object being compared to.
        """
        if isinstance(self, other.__class__):
            return self.name == getattr(other, 'name', None) \
                and self.mac == getattr(other, 'mac', None) \
                and self.device_id == getattr(other, 'device_id', None) \
                and self.vendor_id == getattr(other, 'vendor_id', None)
        return False

    @property
    def name(self) -> str:
        """
        Returns the name property.
        """
        return self._name

    @name.setter
    def name(self, new_name: str) -> None:
        """
        Setter for the name property.
        :param new_name:
        """
        self.old_name = self._name
        self._name = new_name

    @property
    def mac(self) -> str:
        """
        Returns the MAC address in uppercase.
        """
        return self._mac.upper()

    def __str__(self) -> str:
        """
        Object as a string.
        """
        return f'{self._name}:{self._mac.upper()}'


def map_nics() -> list[NIC]:
    """
    Returns a map of all the network interfaces that the kernel is aware of.
    """
    nics = []
    supported, platform = supported_platforms()
    if not supported:
        click.echo(f'Mapping NICs is not supported on {platform}')
        return nics
    nic_files = glob('/sys/bus/pci/drivers/*/0000:*/net/*')
    for nic_file in nic_files:
        nic = os.path.basename(nic_file)
        mac_cmd = run_command(['ethtool', '-P', nic], silence=True)
        mac = mac_cmd.stdout.rsplit(' ', maxsplit=1)[-1]

        pci_id = ''
        nic_kernel_files = os.path.dirname(os.path.dirname(nic_file))
        nic_uevent_file = os.path.join(nic_kernel_files, 'uevent')
        with open(nic_uevent_file, 'r', encoding='utf-8') as uevent:
            for line in uevent:
                if re.search(r'^PCI_ID', line):
                    LOG.info('Found PCI_ID in line: %s', line)
                    pci_id = line.split('=')[-1]
                    break
        vendor_id, device_id = pci_id.split(':')
        LOG.info(
            'Found NIC name: %s, MAC: %s, device ID: %s, vendor ID: %s',
            nic,
            mac,
            device_id,
            vendor_id,
        )
        nics.append(
            NIC(
                name=nic,
                mac=mac,
                device_id=device_id,
                vendor_id=vendor_id,
            )
        )
    return nics


def _rename(nics: list[NIC]) -> None:
    """
    Renames the NIC to NIC.
    :param nics: List of ``NIC`` objects to rename.
    """
    for nic in nics:
        click.echo(f'Renaming {nic.old_name} to {nic.name}')
        if nic.name == nic.old_name:
            LOG.info('%s was already renamed.', nic.old_name)
        LOG.info('Renaming %s to %s', nic.old_name, nic.name)
        was_up = False
        current_state = run_command(['ip', 'link', 'show', nic.old_name])
        if current_state.return_code == 0:
            if 'UP' in current_state.stdout:
                LOG.info(
                    '%s is UP and will be shutdown for renaming.',
                    nic.old_name
                )
                down_result = run_command(
                    [
                        'ip',
                        'link',
                        'set',
                        nic.old_name,
                        'down',
                    ]
                )
                if down_result.return_code == 0:
                    LOG.info('%s is now DOWN.', nic.old_name)
                    was_up = True
                else:
                    LOG.error(
                        '%s could not be shut down, rename will fail '
                        '- skipping.'
                    )
                    continue
        else:
            LOG.error('NIC [%s] does not exist!', nic.old_name)
        rename_result = run_command(
            [
                'ip',
                'link',
                'set',
                nic.old_name,
                'name',
                nic.name,
            ]
        )
        if rename_result.return_code == 0:
            if was_up:
                LOG.info('Attempting to UP %s', nic.name)
                down_result = run_command(
                    [
                        'ip',
                        'link',
                        'set',
                        nic.old_name,
                        'up',
                    ]
                )
                if down_result.return_code == 0:
                    LOG.info('%s is now UP.', nic.name)
                else:
                    LOG.warning('%s could not be UPed!', nic.name)
            LOG.info('Successfully renamed %s to %s', nic.old_name, nic.name)
        else:
            LOG.error(
                'Failed to rename %s to %s for reason (stdout: %s)'
                ' (stderr: %s)',
                nic.old_name,
                nic.name,
                rename_result.stdout,
                rename_result.stderr,
            )
    click.echo('Finished renaming NICs')


def _rendor_udev_rules(nics: list[NIC]) -> str:
    """
    Renders the udev rule template based on a list of NICs.
    :param nics: A list of NICs, or a single NIC
    """
    directory = os.path.dirname(__file__)
    template_directory = os.path.join(directory, 'templates')
    loader = FileSystemLoader(template_directory)
    env = Environment(loader=loader)
    template = env.get_template('ifname.udev.rules.j2')
    render = sorted(template.render(nics=nics).split('\n'))
    return '\n'.join(render)


def write_udev_rules(
        rules: str,
        install_location: str,
        merge: bool = False,
        overwrite: bool = False,
) -> None:
    """
    Writes the udev rule file.

    :param rules: udev rules to write
    :param install_location: String
    :param merge: String
    :param overwrite: String
    """
    open_mode = 'w'
    udev_rules = os.path.join(install_location, '80-ifname.rules')
    if os.path.exists(udev_rules) and not overwrite:
        LOG.warning('File [%s] already exists!', udev_rules)
        choice = click.prompt(
            f'An existing udev file exists at {udev_rules}; overwrite, '
            f'merge, or quit?',
            show_choices=True,
            type=click.Choice(
                ['o', 'm', 'q'],
                case_sensitive=False,
            )
        )
        if choice == 'm':
            merge = True
        elif choice == 'q':
            LOG.info('User chose to exit.')
            click.echo('Exiting ... ')
            sys.exit(0)
        if merge:
            LOG.info('Merging old and new rules; sorting uniquely.')
            with open(udev_rules, 'r', encoding='utf-8') as old_udev_rules:
                unique = set()
                old_rules = old_udev_rules.read().split('\n')
                for rule in old_rules:
                    unique.add(rule)
                for rule in rules.split('\n'):
                    unique.add(rule)
                unique = sorted(unique)
                rules = '\n'.join(unique)
        LOG.info('Writing udev rules to: %s', install_location)
    with open(udev_rules, open_mode, encoding='utf-8') as udev_file:
        udev_file.write(rules)
    click.echo(f'Wrote {udev_rules}.')


def _ifname_meta() -> dict:
    """
    Opens the ifname.yml datafile.
    """
    default_yaml_path = '/etc/crucible/ifname'
    if os.path.exists(f'{default_yaml_path}.yml'):
        ifname_yml_path = os.path.join(f'{default_yaml_path}.yml')
    elif os.path.exists(f'{default_yaml_path}.yaml'):
        ifname_yml_path = os.path.join(f'{default_yaml_path}.yaml')
    else:
        ifname_yml_path = os.path.join(os.path.dirname(__file__), 'ifname.yml')
    LOG.info('Using NIC database file: %s',ifname_yml_path)
    with open(ifname_yml_path, 'r', encoding='utf-8') as ifname_yml:
        return safe_load(ifname_yml.read())


def get_new_names(nics: list[NIC]) -> list[NIC]:
    """
    Given a list of ``NIC`` objects, resolve new names using the official
    prefixes.

    Requires ``ifname.yml``.

    :param nics: List of ``NIC``s to resolve new classifications for.
    """
    sorted_nics = sorted(nics, key=lambda x: x.mac)
    ifname = _ifname_meta()
    prefixes = PrefixIndexes()
    hsn_ids = [f'{v["vendor_id"]}:{v["device_id"]}'.lower() for v in
               ifname.get('hsn_ids')]
    mgmt_ids = [v["vendor_id"].lower() for v in ifname.get('mgmt_ids')]
    for nic in sorted_nics:
        pci_id = f'{nic.vendor_id}:{nic.device_id}'.lower().strip()
        if pci_id in hsn_ids:
            nic.name = prefixes.hsn
        elif nic.vendor_id.lower() in mgmt_ids:
            nic.name = prefixes.mgmt
        else:
            nic.name = prefixes.lan
    return pcie_redundancy_indexing(sorted_nics)


def pcie_redundancy_indexing(nics: list[NIC]) -> list[NIC]:
    """
    Reindex network interface names to promote PCIe fail-over redundancy
    where the network is distributed across two switches each connected to
    their own PCIe device on the host. This means if a PCIe device or
    a switch fail, the host may maintain connectivity through the other switch
    and PCIe device.

    .. note::
        This does not protect against the edge case where failure on opposite
        devices occur (e.g. switch0 fails at the same time card1 fails).
        However, this scenario is very unlikely.

    Single PCIe card (no PCIe redundancy):
      - ``card0port0`` is ``mgmt0``
      - ``card1port0`` is ``mgmt1``

      .. code-block:: text

                ________          __________
                | HOST |          | SWITCH |
                --------          ----------
                                  |    _
                ---               |   |_|
                |_                |    _
          port0 |_| <-------------|-->|_|
                |_                |    _
          port1 |_| <-------------|-->|_|
                |                 |    _
          card0 ^                 |   |_|
                                  |
    Dual PCIe cards (PCIe redundancy):
      - ``card0port0`` is ``mgmt0``
      - ``card1port0`` is ``mgmt1``

      .. code-block:: text

          ___________           ________           ___________
          | SWITCH 0 |          | HOST |           | SWITCH 1 |
          ------------          --------           ------------
          |  _   _   |                             |   _   _  |
          | |_| |_|  |          ---  ---           |  |_| |_| |
          |  _   _   |          |_   |_            |   _   _  |
          | |_| |_|<-|--port0-->|_|  |_| <--port0--|->|_| |_| |
          |  _   _   |          |_   |_            |   _   _  |
          | |_| |_|  |          |_|  |_|           |  |_| |_| |
          |  _   _   |          |    |             |   _   _  |
          | |_| |_|  |     card0^    ^card1        |  |_| |_| |


    :param nics: List of ``NIC`` devices to check for PCIe redundancy.
    """
    prefixes = PrefixIndexes()
    main_nics = [nic for nic in nics if prefixes.prefix_mgmt in nic.name]
    if len(main_nics) <= 0:
        LOG.info('No NICs.')
        return nics
    if len(main_nics) <= 2:
        LOG.info(
            'Server has only 2 or less network interfaces for the '
            'management network.'
        )
        return nics
    LOG.info(
        'Server has more than 2 network interfaces for the '
        'management network. These will be indexed for PCIe redundancy,'
        'assuming two ports per PCIe card'
    )
    for nic in main_nics[::2]:
        nic.name = prefixes.mgmt
    for nic in main_nics[1::2]:
        nic.name = prefixes.sun
    return nics


def run(
        skip_rename: bool,
        skip_udev: bool,
        merge: bool,
        overwrite: bool,
        install_location: str = '/etc/udev/rules.d/',
) -> None:
    """
    Renames interfaces on the machine and creates udev rules for them.

    :param skip_rename: When true, interfaces will not be renamed but only
        previewed.
    :param skip_udev: When true, udev rules will not be saved but only
        previewed.
    :param merge: When true, new udev rules will merge with any existing
        ones (uniquely).
    :param overwrite: When true, new udev rules will overwrite the old udev
        rules without prompting.
    :param install_location: Where to install udev rules to.
    :raises UdevError: When udev rules can not be resolved.
    """
    nics = map_nics()
    nics = get_new_names(nics)
    if not nics:
        raise UdevError('Nothing to do')
    if not skip_rename:
        click.echo('Renaming NICs ... ')
        _rename(nics)
    else:
        LOG.info('skip-rename was set, not renaming interfaces.')
    if not skip_udev:
        click.echo('Creating udev rules for persistence ... ')
        rules = _rendor_udev_rules(nics)
        write_udev_rules(
            rules,
            install_location=install_location,
            merge=merge,
            overwrite=overwrite,
        )
    else:
        udev = _rendor_udev_rules(nics)
        LOG.info('skip-udev was present; not writing udev rules')
        click.echo(f'udev rule preview:\n{udev}')
