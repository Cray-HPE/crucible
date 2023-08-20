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
Tests the ``crucible`` command line.
"""
# pylint: disable=attribute-defined-outside-init
from importlib import metadata

import mock
from click.testing import CliRunner

from crucible.cli import crucible


class TestCLI:

    """
    Test class for the ``crucible`` command line.
    """

    runner: CliRunner

    def setup_method(self) -> None:
        """
        Sets up unit tests.
        """
        self.runner = CliRunner(echo_stdin=True)

    def test_crucible(self) -> None:
        """
        Tests whether crucible without arguments returns without errors.
        """
        result = self.runner.invoke(crucible)
        assert result.exit_code == 0

    def test_help(self) -> None:
        """
        Tests that --help and -h prints the usage.
        """
        result = self.runner.invoke(crucible, '--help')
        assert result.exit_code == 0
        result = self.runner.invoke(crucible, '-h')
        assert result.exit_code == 0

    def test_version(self) -> None:
        """
        Tests that --version or -v prints the version.
        """
        version = metadata.version('crucible')
        result = self.runner.invoke(crucible, '--version')
        assert version in result.stdout
        assert result.exit_code == 0

    def test_install_no_disks(self) -> None:
        """
        Tests that the ``install`` command fails if no disks are given.
        """
        result = self.runner.invoke(
            crucible,
            [
                'install',
                '--num-disks=0',
            ],
        )
        assert result.exit_code == 1

    def test_install_bad_raid_level(self) -> None:
        """
        Tests that the ``install`` command fails if an unaccepted RAID level
        is given.
        """
        result = self.runner.invoke(
            crucible,
            [
                'install',
                '--raid-level=foo',
            ],
        )
        assert result.exit_code == 1

    def test_install_stripe_single_disk(self) -> None:
        """
        Tests that the ``install`` command fails if a striped RAID is given
        only one disk.
        """
        result = self.runner.invoke(
            crucible,
            [
                'install',
                '--num-disks=1',
                '--raid-level=stripe',
            ],
        )
        assert result.exit_code != 0

    @mock.patch('crucible.install.run_command', spec=True, return_code=0)
    def test_install_mirror_single_disk(self, mock_run) -> None:
        """
        Tests that the ``install`` command does not fail if a mirrored RAID
        is only given one disk.
        """
        result = self.runner.invoke(
            crucible,
            [
                'install',
                '--num-disks=1',
                '--raid-level=mirror',
            ],
        )
        assert result.exit_code == 0
        assert mock_run.called

    @mock.patch('crucible.install.run_command', spec=True, return_code=0)
    def test_install_small_sqfs_storage(self, mock_run) -> None:
        """
        Tests that a warning is emitted if a small squashFS storage size is
        given.
        """
        result = self.runner.invoke(
            crucible,
            [
                'install',
                '--sqfs-storage-size=3',
            ],
        )
        assert result.exit_code == 0
        assert mock_run.called

    def test_install_no_sqfs_storage(self) -> None:
        """
        Tests that the ``install`` command fails if the squashFS storage
        is too small.
        """
        result = self.runner.invoke(
            crucible,
            [
                'install',
                '--sqfs-storage-size=0',
            ],
        )
        assert result.exit_code != 0

    @mock.patch('crucible.install.run_command', spec=True, return_code=0)
    def test_install_stripe(self, mock_run) -> None:
        """
        Tests that the ``install`` command does not fail if a stripe is given.
        :param mock_run:
        """
        result = self.runner.invoke(
            crucible,
            [
                'install',
                '--raid-level=stripe'
            ],
        )
        assert result.exit_code == 0
        assert mock_run.called

    @mock.patch('crucible.vms.run_command', spec=True)
    def test_vm_start(self, mock_run) -> None:
        """
        Tests that the ``vm`` command does not fail when is given.
        :param mock_run:
        """
        result = self.runner.invoke(
            crucible,
            [
                'vm',
                'start',
            ],
        )
        assert result.exit_code == 0
        assert mock_run.called

    @mock.patch('crucible.vms.run_command', spec=True)
    def test_vm_reset(self, mock_run) -> None:
        """
        Tests that the ``vm`` command does not fail when is given.
        :param mock_run:
        """
        result = self.runner.invoke(
            crucible,
            [
                'vm',
                'reset',
            ],
        )
        assert result.exit_code == 0
        assert mock_run.called


class TestCLIStorage:
    """
    Test class for the ``storage`` command group.
    """

    def setup_method(self) -> None:
        """
        Sets up unit tests.
        """
        self.runner = CliRunner(echo_stdin=True)

    @mock.patch('crucible.storage.disk.run_command', spec=True)
    def test_bootable(self, mock_run) -> None:
        """
        Assert that the ``bootable`` command starts.
        """
        result = self.runner.invoke(
            crucible,
            [
                'storage',
                'bootable',
            ],
        )
        assert result.exit_code == 2
        mock_run.return_code = 0
        result = self.runner.invoke(
            crucible,
            [
                'storage',
                'bootable',
                '/dev/thing1',
                '/root/my.iso',
            ],
        )
        assert result.exit_code == 0
        result = self.runner.invoke(
            crucible,
            [
                'storage',
                'bootable',
                '/dev/thing1',
                '/root/my.iso',
                '--cow',
                50000,
            ],
        )
        assert result.exit_code == 0

    @mock.patch('crucible.storage.disk.run_command', spec=True)
    def test_wipe(self, _) -> None:
        """
        Assert that the ``wipe`` command starts.
        """
        result = self.runner.invoke(
            crucible,
            [
                'storage',
                'wipe',
            ],
            input='n'
        )
        assert result.exit_code == 1

        result = self.runner.invoke(
            crucible,
            [
                'storage',
                'wipe',
            ],
            input='y'
        )
        assert result.exit_code == 0


class TestCLINetwork:
    """
    Test class for the ``network`` command group.
    """

    def setup_method(self) -> None:
        """
        Sets up unit tests.
        """
        self.runner = CliRunner(echo_stdin=True)

    @mock.patch('crucible.cli.config.interface', spec=True)
    def test_network_interface(self, _) -> None:
        """
        Assert that ``interface`` command starts.
        """
        result = self.runner.invoke(
            crucible,
            [
                'network',
                'interface',
            ]
        )
        assert result.exit_code == 2
        result = self.runner.invoke(
            crucible,
            [
                'network',
                'interface',
                '--dhcp',
                'mgmt0',
            ]
        )
        assert result.exit_code == 0
        result = self.runner.invoke(
            crucible,
            [
                'network',
                'interface',
                '--noip',
                'bond0',
            ]
        )
        assert result.exit_code == 0
        result = self.runner.invoke(
            crucible,
            [
                'network',
                'interface',
                'mgmt0',
                '192.168.1.0/24',
            ]
        )
        assert result.exit_code == 0

    @mock.patch('crucible.cli.config.system', spec=True)
    def test_network_system(self, _) -> None:
        """
        Assert that ``config`` command starts.
        """
        result = self.runner.invoke(
            crucible,
            [
                'network',
                'system',
                '--dns',
                '8.8.8.8',
            ]
        )
        assert result.exit_code == 0
        result = self.runner.invoke(
            crucible,
            [
                'network',
                'system',
                '--dns',
                '8.8.8.8,8.8.4.4',
            ]
        )
        assert result.exit_code == 0

    @mock.patch('crucible.cli.ifname.run', spec=True)
    def test_network_ifname(self, _) -> None:
        """
        Assert that ``ifname`` command starts.
        """
        result = self.runner.invoke(
            crucible,
            [
                'network',
                'udev',
            ]
        )
        assert result.exit_code == 0
