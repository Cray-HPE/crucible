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
Module for installing a LIVE OS to disk.
"""
import os
import sys

import click
from crucible.os import run_command
from crucible.logger import Logger

LOG = Logger(__name__)


def install_to_disk(
        num_disks: int,
        sqfs_storage_size: int,
        raid_level: str,
) -> None:
    """
    Installs the running image to disk.

    :param num_disks: Number of disks to use for the OS array.
    :param sqfs_storage_size: Size of squashFS storage.
    :param raid_level: Stripe or Mirror
    """
    if raid_level not in ['stripe', 'mirror']:
        LOG.critical('Chosen RAID level was [%s] but '
                     'only type "mirror" and "stripe" are supported.',
                     raid_level)
        sys.exit(1)
    if sqfs_storage_size < 2:
        LOG.critical('SquashFS was set to less than the minimum of 2 GiB!')
        sys.exit(1)
    elif sqfs_storage_size < 5:
        LOG.warning('SquashFS storage is set to less than 5 GiB! '
                    'Mileage may vary.')
    if num_disks < 2 and raid_level == 'stripe':
        LOG.critical('Number of disks was set to [< 2] but RAID level "stripe"'
                     ' was chosen, this can not be done. Please choose '
                     '"mirror" instead, mirrors can start with 1 disk '
                     'and expand later much easier than a stripe.')
        sys.exit(1)
    elif num_disks < 1:
        LOG.critical('Number of disks chosen was [< 1], this is impossible '
                     'to use. Please choose an integer (0 < x).')
        sys.exit(1)
    directory = os.path.dirname(__file__)
    click.echo('Installing OS to disk ... ')
    install_script = os.path.join(directory, 'scripts', 'install.sh')
    result = run_command(
        [
            install_script,
            '-d', num_disks,
            '-s', sqfs_storage_size,
            '-l', raid_level,
        ],
    )
    if result.return_code != 0:
        LOG.critical('Install failed!')
        click.echo('Install to disk failed. Check logfile.')

        # FIXME: Not very clean printing this to crucible.log..
        LOG.critical(result.stdout)
        LOG.critical(result.stderr)
    else:
        LOG.info('Install succeeded!')
        click.echo('Install to disk succeeded.')
