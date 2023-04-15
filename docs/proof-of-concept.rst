Proof of Concept
================

.. :caution:
    **For all intents and purposes this application is a pre-alpha used for a proof of concept.**

---------

* The `Crucible <https://github.com/Cray-HPE/crucible>`_
* The `Hypervisor ISO <https://github.com/Cray-HPE/node-images/tree/hypervisor/boxes/hypervisor>`_

1. Launching the LiveCD
-----------------------

#. Install ``cruicble``, either from VCS using ``pip`` or from the downloaded RPM.

   * Without HTTP proxy

     .. code-block:: shell

           python3 -m pip install git+https://github.com/Cray-HPE/crucible.git@main
           crucible --version

   * With HTTP proxy

     .. code-block:: shell

           python3 -m pip --proxy=http://hpeproxy.its.hpecorp.net:443 install git+https://github.com/Cray-HPE/crucible.git@main
           crucible --version

#. Fetch the ISO (see link:poc-iso-download.adoc[ISO Download]).
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

#. (optionally) setup SSH now

   .. code-block:: shell

         crucible setup ifnames
         crucible setup ip 10.100.254.5/24 16.110.135.51,16.110.135.52

2. Installing to Disk
---------------------

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
         crucible setup ip 10.100.254.5/24 16.110.135.51,16.110.135.52

Once connectivity is established, further setup and launching can be done on the hypervisor.

3. Configure VMs
----------------

.. note::
   The following steps are in development.

#. Run the Hypervisor Ansible playbook to setup the machine for VMs.

   .. code-block:: shell

         source /opt/cray/ansible/bin/activate
         ansible-playbook /srv/cray/metal-provision/hypervisor.yml

4. Clone cloud-init data
------------------------

5. Copy SSH keys
----------------

6. Join Kubernetes
------------------
