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

import click

from crucible.logger import Logger
from crucible.ifname import rename

LOG = Logger(__name__)


@click.group()
@click.option('--verbose', is_flag=True, help='Will print verbose messages.')
@click.version_option()
def crucible(verbose: bool) -> None:
    pass


@crucible.command()
@click.pass_context
@click.option(
    '--overwrite', is_flag=True, help='Overwrite existing udev rules (if any).'
)
@click.option(
    '--merge',
    is_flag=True,
    help='Merge new udev rules with existing rules (if any).'
)
@click.option(
    '--skip-udev',
    is_flag=True,
    help='Skip touching existing udev rules (if any).'
)
@click.option('--skip-rename', is_flag=True, help='Skip renaming interfaces.')
def nics(ctx, **kwargs) -> None:
    rename(**kwargs)
    pass


@crucible.command()
@click.pass_context
def wipe(ctx) -> None:
    pass


@crucible.command()
@click.pass_context
def partition(ctx) -> None:
    ctx.invoke(wipe)
