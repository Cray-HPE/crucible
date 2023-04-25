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
Module for managing bootable devices.
"""
# TODO: Rewrite wipe.sh in Python within this module.
import os

import click
from crucible.os import run_command
from crucible.logger import Logger

LOG = Logger(__file__)


def create(device: str, iso: str, cow: int) -> None:
    """
    Runs the bootable media flow.

    :param device: Path of device to make into bootable media.
    :param iso: ISO to make bootable media from.
    :param cow: Size (in MiB) of the copy-on-write partition
                (default: 50,000 MiB).
    """
    directory = os.path.dirname(__file__)
    bootable_script = os.path.join(
        directory,
        '..',
        'scripts',
        'write-livecd.sh',
        )
    click.echo(f'Writing [{iso}] to [{device}]')
    result = run_command(
        [
            bootable_script,
            device,
            iso,
            cow,
        ],
        in_shell=True,
    )
    # TODO: No progress output
    if result.return_code != 0:
        LOG.critical('Failed to create bootable.')
    click.echo('Finished preparing bootable.')
