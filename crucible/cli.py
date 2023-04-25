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
The crucible.
"""

import click
from click_option_group import optgroup
from click_option_group import MutuallyExclusiveOptionGroup

from crucible.install import install_to_disk
from crucible.network import ifcfg
from crucible.network import ifname
from crucible.storage.bootable import create
from crucible.storage.wipe import purge
from crucible.logger import Logger

CONTEXT_SETTINGS = {'help_option_names': ['-h', '--help']}
LOG = Logger(__name__)


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option()
def crucible() -> None:
    """
    The crucible, paving the way for new machines.

    \f
    """
    LOG.info('Invoked.')


@crucible.group()
def setup() -> None:
    """
    Functions for configuring the running server.

    \f
    """
    LOG.info('Invoked setup group.')


@setup.command()
@click.option(
    '--skip-udev',
    is_flag=True,
    help='Skip touching existing udev rules (if any).'
)
@click.option(
    '--skip-rename',
    is_flag=True,
    help='Skip renaming interfaces.'
)
@click.option(
    '--install-location',
    metavar='<directory path>',
    default='/etc/udev/rules.d',
    is_flag=False,
    help='Path to install udev rules to (default: /etc/udev/rules.d)'
)
@optgroup.group(
    'Write options',
    cls=MutuallyExclusiveOptionGroup,
    help='Specify one of these in order to bypass the prompt if existing '
         'rules already exist.'
)
@optgroup.option(
    '--overwrite',
    is_flag=True,
    help='Overwrite existing udev rules (if any).',
)
@optgroup.option(
    '--merge',
    is_flag=True,
    help='Merge new udev rules with existing rules (if any).'
)
def ifnames(**kwargs) -> None:
    """
    Renames NICs by classifying them using their PCI ID, and creating
    corresponding udev rules.

    \f
    :param kwargs:
    """
    LOG.info('Calling setup ifnames with: %s', kwargs)
    ifname.run(**kwargs)


@setup.command()
@click.option(
    '--dhcp',
    is_flag=True,
    is_eager=True,
    default=False,
    expose_value=False,
    help='Set the NIC up using DHCP.'
)
@click.argument('interface')
@click.argument('ipaddr', required=False)
@click.argument('dns', required=False)
@click.argument('gateway', required=False)
def ip(**kwargs) -> None:
    # pylint: disable=invalid-name
    """
    Sets up IP connectivity for a given interface.

    If no IP is given, the BOOTPROTO will be assumed as ``None``.
    \b
    INTERFACE to configure.
    IPADDR a static IP in CIDR notation to assign to the device (A.B.C.D/E).
    DNS comma delimited list of one or more IP addresses to use for DNS.
    GATEWAY the IP address of the router (default: first IP of the IP block).
    \f
    """
    LOG.info('Calling setup ifcfg with: %s', kwargs)
    ifcfg.run(**kwargs)


@crucible.group()
def storage() -> None:
    """
    Functions for configuring storage devices.

    \f
    """
    LOG.info('Invoked storage group.')


@storage.command()
@click.argument('device')
@click.argument('iso')
@click.option(
    '--cow',
    default='50000',
    type=str,
    is_flag=False,
    metavar='<size of overlayFS>',
    help='Size (in MiB) of the copy-on-write partition (default: 50,000 MiB).',
)
def bootable(**kwargs) -> None:
    """
    Makes a bootable device using the given ISO.

    \b
    DEVICE is the path to a device-mapper name (e.g. /dev/sda)
    ISO is the path to a ``.iso`` file to be written to the target DEVICE.
    \f
    """
    LOG.info('Calling storage bootable with: %s', kwargs)
    create(**kwargs)


@storage.command()
def wipe() -> None:
    """
    Wipes the local server and prepares it for new partition tables.

    This will prompt for confirmation before wiping, and it will always ignore
    USB devices as well as the device that root is currently running off of.

    \f
    """
    LOG.info('Calling storage wipe')
    click.confirm(
        'Are you sure you want to wipe all disks' +
        '(excluding USB and the booted root)?',
        abort=True
    )
    purge()


@crucible.command()
@click.option(
    '--num-disks',
    default=2,
    type=int,
    is_flag=False,
    metavar='<int>',
    help='Number of disks to use in the OS disk array (default: 2).',
)
@click.option(
    '--sqfs-storage-size',
    default=25,
    type=int,
    is_flag=False,
    metavar='<size GiB>',
    help='Size of the squashFS storage partition (default: 25GiB).',
)
@click.option(
    '--raid-level',
    default='mirror',
    type=str,
    is_flag=False,
    metavar='<mirror|stripe>',
    help='Level of redundancy (default: mirror).',
)
def install(**kwargs) -> None:
    """
    Install a running LIVE image to disk.

    \b
    Partition and formats disks:
     - Sets up a GRUB2 bootloader
     - Copies the LIVE image to disk
     - An OverlayFS for persistence
     - A partition for VM storage
    \f
    """
    LOG.info('Calling install with: %s', kwargs)
    install_to_disk(**kwargs)
