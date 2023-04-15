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
Handles network interface configuration files.
"""

from crucible.logger import Logger

LOG = Logger(__file__)


def run(
        interface: str,
        dhcp: bool = False,
        ipaddr: str = None,
        dns: str = None,
        gateway: str = None
) -> None:
    """
    Configure the given interface.

    :param interface: Name of interface as reported by the kernel.
    :param dhcp: Enable DHCP.
    :param ipaddr: Static IP address to use (CIDR notation: A.B.C.D/E).
    :param dns: DNS server(s) to use (comma delimited).
    :param gateway: Gateway IP to use.
    """
    LOG.info('Configuring interface [%s] ... ', interface)
    LOG.info('- DHCP: %s', dhcp)
    if ipaddr:
        LOG.info('- IP  : %s', ipaddr)
        if not gateway:
            gateway = 'first-ip-placeholder'
        LOG.info('- GW  : %s', gateway)
    if dns:
        LOG.info('- DNS : %s', dns)
