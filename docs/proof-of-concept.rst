Proof of Concept
================

.. :caution:
    **For all intents and purposes this application is a pre-alpha used for a proof of concept.**

Requirements:
^^^^^^^^^^^^^

* The `Crucible <https://github.com/Cray-HPE/crucible>`_
* The `Hypervisor ISO <https://github.com/Cray-HPE/node-images/tree/hypervisor/boxes/hypervisor>`_

1. Launching the LiveCD
^^^^^^^^^^^^^^^^^^^^^^^

#. Install ``crucible``, either from VCS using ``pip`` or from the downloaded RPM.

   * Without HTTP proxy

     .. code-block:: shell

           python3 -m pip install git+https://github.com/Cray-HPE/crucible.git@main
           crucible --version

   * With HTTP proxy

     .. code-block:: shell

           python3 -m pip --proxy=http://hpeproxy.its.hpecorp.net:443 install git+https://github.com/Cray-HPE/crucible.git@main
           crucible --version

#. Fetch the ISO (see :ref:`ISO Download <download:Downloading the Hypervisor Image>`).
#. Write the ISO to a block device.

   .. code-block:: shell

         crucible storage bootable /path/to/disk /path/to/ISO [<size of overlayFS>]

#. Reboot.


   .. attention::
      **Connect to a serial console before rebooting!**

   .. note::

      The ``bootable`` command will set the ``BootOrder`` to "USB first," but it is advised to be ready to intervene via a console as milage may vary by server vendor.

      The following code block can help "seal the deal," however it is always advised to watch the console and intervene if the BIOS chooses to ignore our boot order requests.

      .. code-block:: shell

            ipmitool chassis bootdev bios options=efiboot
            ipmitool chassis power cycle

#. At the first login screen, set your password

   .. hint::
      The initial password is blank.

#. (optionally) setup network interface names and SSH now.

   .. code-block:: shell

         crucible setup ifnames

         # TODO: Manually apply LAN configuration; command does not work yet.
         # crucible setup ip 10.100.254.5/24 16.110.135.51,16.110.135.52

2. Installing to Disk
^^^^^^^^^^^^^^^^^^^^^

#. Prepare the system by wiping the disks.

   .. danger::
      **This will destroy volume groups, RAIDs, and partition tables** on everything except for:

      * Any/all USB devices are safe.
      * The device mounted at `/run/initramfs/live` is also safe.

   .. code-block:: shell

         crucible wipe -y


#. Install the hypervisor image to disk. This command will partition and format a few partitions; a bootloader, a root file system (overlayFS), and a large partition for VM guests.

   .. code-block:: shell

         crucible install

   .. note::

     **This proof of concept does not offer much in terms of disk configuration.**

     However, the ``install`` command does allow limited customization of the OS disk(s).

     By default, three disks are used:

     * A mirror consisting of two disks will be formatted with 3 partitions:

       * A ``500 MiB`` ``vfat`` bootloader
       * A ``25 GiB`` ``ext4`` partition for holding squashFS images
       * The remainder is ``xfs`` for the ``rootfs`` overlayFS

     * A single, standalone disk will be formatted as `xfs` for VM storage

     One can customize this setup to work with only two disks by changing the
     OS array to use only one disk by passing ``--num-disks=1`` (leaving the second disk for VM storage).

     Optionally, for more space one can sacrifice the redundancy by passing ``--raid-level stripe`` which will provide twice the amount of space to the ``rootfs`` by striping the OS disks together.

     At this time there is no way to configure the ``VMSTORE`` disk.

   .. tip::
     For the largest ``rootfs``, one can pass ``--raid-level stripe --sqfs-storage-size 5``.


#. Reboot.

   .. attention::
      **Connect to a serial console before rebooting!**

   .. note::
      The ``install`` command will set the ``BootOrder`` to "disk first," but it is advised to be ready to intervene via a console as milage may vary by server vendor.

      If the USB or PXE is attempted, either let the USB finish booting and try to run the code block below:

      .. code-block:: shell

            ipmitool chassis bootdev disk options=efiboot
            ipmitool chassis power cycle

      *or* use the following code block to boot into BIOS for manual one-time boot selection:

      .. code-block:: shell

            ipmitool chassis bootdev bios options=efiboot
            ipmitool chassis power cycle

#. At the first login, set your password.

   .. hint::
      The initial password is blank.

#. Setup network interface names and SSH

   .. code-block:: shell

      crucible setup ifnames


      # TODO: Manually apply LAN configuration; command does not work yet.
      #crucible setup ip --interface bond0:mgmt0,mgmt1
      #crucible setup ip --interface bond0.nmn0 --vlan 2 --dhcp

      # or for external:
      #crucible setup ip 10.100.254.5/24 16.110.135.51 ,16.110.135.52 nterface lan0

3. Configure the ``pit`` node
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. caution::

   From this point on, the steps change from "generalized" steps to hack steps for standing up VMs while using a PIT node as a DHCP and cloud-init server. The following steps will entail setting up some hardcoded values, whereas the steps before this are aimed at generalized installs.

#. Visit the ``pit`` node.

#. Install ``crucible`` onto the PIT node, or clone this repository into ``/usr/lib/crucible`` to align with the following commands.

#. Copy the startup files into place.

   #. Copy ``statics.vm.conf`` into ``/etc/dnsmasq.d/`` and merge ``vm-data.json` into ``data.json``

      .. code-block::

         cp -pv /usr/lib/crucible/poc-mocks/statics.vm.conf /etc/dnsmasq.d/
         mv /var/www/ephemeral/configs/data{,-pre-vm}.json
         jq -s '.[0] * .[1]' /var/www/ephemeral/configs/data-pre-vm.json /usr/lib/crucible/poc-mocks/vm-data.json > /var/www/ephemeral/configs/data.json

   #. Restart services

      .. code-block:: shell

         systemctl restart basecamp dnsmasq

   #. Fetch the latest Kubernetes ``box`` file.

      .. code-block::

         ARTIFACTORY_USER=
         ARTIFACTORY_TOKEN=

         curl --proxy http://hpeproxy.its.hpecorp.net:443 \
           -C - -o /var/www/ephemeral/data/kubernetes-x86_64.box \
           https://$ARTIFACTORY_USER:$ARTIFACTORY_TOKEN@artifactory.algol60.net/artifactory/csm-images/stable/kubernetes/\\[RELEASE\\]/kubernetes-\\[RELEASE\\]-${ARCH}.box

4. Prepare the VMs
^^^^^^^^^^^^^^^^^^

Return to the ``hypervisor`` node.

#. Grab SSH keys (these will be used for the VMs)

   .. code-block:: shell

      scp -r pit.nmn:/root/.ssh /root/

#. Mount our VM storage area, and fetch a box file.

   .. code-block:: shell

      mount -L VMSTORE
      rsync -rltDv pit.nmn:/var/www/ephemeral/data/kubernetes-x86_64.box /vms/
      cp /usr/lib/crucible/poc-mocks/Vagrantfile /vms/

5. Join Kubernetes
^^^^^^^^^^^^^^^^^^

#. Launch the VMs and join Kubernetes

   .. code-block:: shell

      vagrant up

   After some time, all of the Vagrant VMs should be SSHable and in the cluster.

#. Check the Kubernetes cluster

   .. code-block:: shell

      ssh ncn-m002 kubectl get nodes
