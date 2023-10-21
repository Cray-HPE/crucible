#!/usr/bin/env bash
#
# MIT License
#
# (C) Copyright 2023 Hewlett Packard Enterprise Development LP
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
# Do not 'set -euo pipefail', this script will probably break.
# TODO: Rewrite script in Python or Go.

mount -L data
rm -f /tmp/fstab && touch /tmp/fstab

##############################################################################
# constant: METAL_FSOPTS_XFS
#
# COMMA-DELIMITED-LIST of fsopts for XFS
METAL_FSOPTS_XFS=defaults

##############################################################################
# constant: METAL_FSOPTS_TMPFS
#
# COMMA-DELIMITED-LIST of fsopts for XFS
METAL_FSOPTS_TMPFS=defaults,noatime,size=16G

##############################################################################
# constant: METAL_DISK_SMALL
#
# Define the size that is considered to fit the "small" disk form factor. These
# usually serve critical functions.
METAL_DISK_SMALL=375809638400

##############################################################################
# constant: METAL_DISK_LARGE
#
# Define the size that is considered to fit the "large" disk form factor. These
# are commonly if not always used as ephemeral disks.
METAL_DISK_LARGE=480103980000

##############################################################################
# constant: METAL_SUBSYSTEMS
#
# PIPE-DELIMITED-LIST of SUBSYSTEMS to acknowledge from `lsblk` queries; anything listed here is in
# the cross-hairs for wiping and formatting.
# NOTE: To find values for this, run `lsblk -b -l -d -o SIZE,NAME,TYPE,SUBSYSTEMS`
# MAINTAINER NOTE: DO NOT ADD USB or ANY REMOVABLE MEDIA TRANSPORT in order to mitigate accidents.
METAL_SUBSYSTEMS='scsi|nvme'

##############################################################################
# constant: METAL_SUBSYSTEMS_IGNORE
#
# PIPE-DELIMITED-LIST of Transports to acknowledge from `lsblk` queries; these subsystems are
# excluded from any operations performed by this dracut module.
# NOTE: To find values for this, run `lsblk -b -l -d -o SIZE,NAME,TYPE,SUBSYSTEMS`
METAL_SUBSYSTEMS_IGNORE='usb'

LOG="/var/log/crucible/$(basename $0).log"
true >"${LOG}"

boot_drive_scheme=LABEL
boot_drive_authority=BOOTRAID
oval_drive_scheme=LABEL
oval_drive_authority=ROOTRAID
vm_drive_scheme=LABEL
vm_drive_authority=VMSTORE
vm_index=0
vm_letter_counter=({a..z})
yc=0

metal_disks=2
metal_boot_size=5
metal_root_size=50
metal_md_level=mirror
metal_minimum_disk_size=16

function usage {
    cat << EOF
-d      Number of disks to use for the rootfs array (default: 2)
-l      RAID type (default: mirror)
-i      Ignore disks smaller than X Gigabytes (default 16)
-s      SSH public key to install.
EOF
}
SSH_KEY='/root/.ssh/id_rsa.pub'
while getopts "l:s:d:i:" o; do
    case "${o}" in
        d)
            metal_disks="${OPTARG}"
            ;;
        l)
            metal_md_level="${OPTARG}"
            ;;
        i)
            metal_minimum_disk_size="${OPTARG}"
            ;;
        s)
            SSH_KEY="${OPTARG}"
            ;;
        *)
            usage
            return 2
            ;;
    esac
done
shift $((OPTIND-1))

METAL_IGNORE_THRESHOLD=$((metal_minimum_disk_size*1024**3))

if [ -z "$live_dir" ]; then
    live_dir=$(grep -Po 'rd.live.dir=([\w\.]+)' /proc/cmdline | awk -F '=' '{print $NF}')
    if [ -z "$live_dir" ] ; then
        # Conventional default
        live_dir=LiveOS
    fi
fi

if [ -z "$squashfs_file" ]; then
    squashfs_file=$(grep -Po 'rd.live.squashimg=([\w\.]+)' /proc/cmdline | awk -F '=' '{print $NF}')
    if [ -z "$squashfs_file" ] ; then
        # Conventional default
        squashfs_file=squashfs.img
    fi
fi

memory_squashfs_file="/run/initramfs/live/${live_dir}/${squashfs_file}"

case $boot_drive_scheme in
    PATH | path | UUID | uuid | LABEL | label)
        printf '%-12s: %s\n' 'bootloader' "${boot_drive_scheme}=${boot_drive_authority}"
        ;;
    '')
        # no-op; drive disabled
        :
        ;;
    *)
        echo >&2 "Unsupported boot-drive-scheme [${boot_drive_scheme}] Supported schemes: PATH, UUID, and LABEL (upper and lower cases)"
        exit 1
        ;;
esac

case "$oval_drive_scheme" in
    PATH | path | UUID | uuid | LABEL | label)
        printf '%-12s: %s\n' 'overlay' "${oval_drive_scheme}=${oval_drive_authority}"
        ;;
    '')
        # no-op; disabled
        :
        ;;
    *)
        echo >&2 "Unsupported oval-drive-scheme [${oval_drive_scheme}] Supported schemes: PATH, UUID, and LABEL"
        exit 1
        ;;
esac

case "$vm_drive_scheme" in
    PATH | path | UUID | uuid | LABEL | label)
        printf '%-12s: %s\n' 'vm storage' "${vm_drive_scheme}=${vm_drive_authority}"
        ;;
    '')
        # no-op; disabled
        :
        ;;
    *)
        echo >&2 "Unsupported oval-drive-scheme [${vm_drive_scheme}] Supported schemes: PATH, UUID, and LABEL"
        exit 1
        ;;
esac

# Borrowed from: https://github.com/dracutdevs/dracut/blob/master/modules.d/99base/dracut-lib.sh#L61
trim() {
    local var="$*"
    var="${var#"${var%%[![:space:]]*}"}" # remove leading whitespace characters
    var="${var%"${var##*[![:space:]]}"}" # remove trailing whitespace characters
    printf "%s" "$var"
}

##############################################################################
# function: metal_scand
#
# Returns a sorted, space delimited list of disks. Each element in the list is
# a tuple representing a disk; the size of the disk (in bytes), and
# device-mapper name.
#
# usage:
#
#     metal_scand
#
# output:
#
#     10737418240,sdd 549755813888,sda 549755813888,sdb 1099511627776,sdc
#
function metal_scand() {
    echo -n "$(lsblk -b -l -d -o SIZE,NAME,TYPE,SUBSYSTEMS |\
        grep -E '('"$METAL_SUBSYSTEMS"')' |\
        grep -v -E '('"$METAL_SUBSYSTEMS_IGNORE"')' |\
        sort -h |\
        grep -vE 'p[0-9]+$' |\
        awk '{print ($1 > '$METAL_IGNORE_THRESHOLD') ? $1 "," $2 : ""}' |\
        tr '\n' ' ' |\
        sed 's/ *$//')"
}

##############################################################################
# function: metal_die
#
# Wait for dracut to settle and die with an error message
#
# Optionally provide -b to reset the system.
metal_die() {
    echo >&2 "FAILURE: $*"
    exit 1
}

##############################################################################
# function: metal_resolve_disk
#
# Given a disk tuple from metal_scand and a minimum size, print the disk if it's
# larger than or equal to the given size otherwise print nothing.
# Also verified whether the disk has children or not, if it does then it's not
# eligible. Since all disks are wiped to start with, if a disk has children when
# this function would be called then it's already spoken for.
#
# This is useful for iterating through a list of devices and ignoring ones that
# are insufficient.
#
# usage:
#
#   metal_resolve_disk size,name floor/minimum_size
#
metal_resolve_disk() {
    local disk=$1
    local minimum_size
    minimum_size=$(echo $2 | sed 's/,.*//')
    name="$(echo $disk | sed 's/,/ /g' | awk '{print $2}')"
    size="$(echo $disk | sed 's/,/ /g' | awk '{print $1}')"
    if ! lsblk --fs --json "/dev/${name}" | grep -q children ; then
        if [ "${size}" -ge "${minimum_size}" ]; then
            echo -n "$name"
        fi
    fi
}

##############################################################################
# function: _find_hypervisor_iso
#
# Prints off the path to the hypervisor ISO.
# example:
#
#   overlay-SQFSRAID-cfc752e2-ebb3-4fa3-92e9-929e599d3ad2
#
_find_hypervisor_iso() {
    local iso
    tar="$(find /data -name "fawkes*.tar.gz")"
    if [ -n "$tar" ]; then
        tar --wildcards -xzvf "$tar" "*/images/hypervisor/hypervisor-*.iso" -C /data
    fi
    iso="$(find /data -name "hypervisor*.iso")"
    echo "$iso"
}

##############################################################################
# function: _find_hypervisor_iso_overlayfs_spec
#
# Return a name that dracut-dmsquash-live will resolve for a persistent
# overlay
# example:
#
#   overlay-SQFSRAID-cfc752e2-ebb3-4fa3-92e9-929e599d3ad2
#   overlay-hypervisor-x86_64-2023-08-23-15-04-34-00
#
_find_hypervisor_iso_overlayfs_spec() {
    local iso
    local iso_label
    iso="$(_find_hypervisor_iso)"
    iso_label="$(isoinfo -j UTF-8 -d -i "$iso" | sed -n 's/Volume id: //p' | tr -d \\n)"
    echo "overlay-${iso_label}-$(blkid -s UUID -o value "$iso")"
}

##############################################################################
# function: _find_boot_disk_overlayfs_spec
#
# Return a name that dracut-dmsquash-live will resolve for a persistent
# overlay
# example:
#
#   overlay-SQFSRAID-cfc752e2-ebb3-4fa3-92e9-929e599d3ad2
#   overlay-hypervisor-x86_64-2023-08-23-15-04-34-00
#
_find_boot_disk_overlayfs_spec() {
    echo "overlay-${boot_drive_authority}-$(blkid -s UUID -o value "/dev/disk/by-${boot_drive_scheme,,}/${boot_drive_authority}")"
}

##############################################################################
## function: partition_os
#
# Partition the OS disk(s).
function partition_os {
    local disks
    IFS=" " read -r -a disks <<< "$@"
    local metal_boot_size_end
    local metal_root_size_end

    metal_boot_size_end="${metal_boot_size}"
    metal_root_size_end="$((metal_boot_size_end + metal_root_size))"

    local boot_raid_parts=()
    local oval_raid_parts=()
    for disk in "${disks[@]}"; do

        parted --wipesignatures -m --align=opt --ignore-busy -s "/dev/$disk" -- mklabel gpt \
            mkpart esp fat32 2048s "${metal_boot_size_end}GB" set 1 esp on \
            mkpart primary xfs "${metal_boot_size_end}GB" "${metal_root_size_end}GB" \
            mkpart primary xfs "${metal_root_size_end}GB" 100% \

        # NVME partitions have a "p" to delimit the partition number, add this in order to reference properly in the RAID creation.
        if [[ "$disk" =~ "nvme" ]]; then
            disk="${disk}p"
        fi

        boot_raid_parts+=( "/dev/${disk}1" )
        oval_raid_parts+=( "/dev/${disk}2" )

        mkfs.xfs -f -L "${vm_drive_authority}_${vm_letter_counter[yc]^^}" "/dev/${disk}${nvme:+p}3" || echo >&2 "Failed to create ${vm_drive_authority}_${vm_letter_counter[yc]^^}"
        printf '% -18s\t% -18s\t%s\t%s %d %d\n' "${vm_drive_scheme}=${vm_drive_authority}_${vm_letter_counter[yc]^^}" "/vms/store${vm_letter_counter[yc]^^}" xfs "$METAL_FSOPTS_XFS" 0 0 >> /tmp/fstab
        ((++yc))
    done

    # metadata=0.9 for boot files.
    mdadm_raid_devices="--raid-devices=$metal_disks"
    [ "$metal_disks" -eq 1 ] && mdadm_raid_devices="$mdadm_raid_devices --force"
    mdadm --create /dev/md/BOOT --run --verbose --assume-clean --metadata=0.9 --level="$metal_md_level" "$mdadm_raid_devices" "${boot_raid_parts[@]}" || metal_die -b "Failed to make filesystem on /dev/md/BOOT"
    mdadm --create /dev/md/ROOT --assume-clean --run --verbose --metadata=1.2 --level="$metal_md_level" "$mdadm_raid_devices" "${oval_raid_parts[@]}" || metal_die -b "Failed to make filesystem on /dev/md/ROOT"

    mkfs.vfat -F32 -n "${boot_drive_authority}" /dev/md/BOOT
    mkfs.xfs -f -L "${oval_drive_authority}" /dev/md/ROOT

}


##############################################################################
## function: partition_vm
# Partition the VM disk.
function partition_vm {
    local target="${1:-}" && shift
    [ -z "$target" ] && echo >&2 'No ephemeral disk.' && return 2

    parted --wipesignatures -m --align=opt --ignore-busy -s "/dev/${target}" -- mktable gpt \
        mkpart extended xfs 2048s 100%

    # NVME partitions have a "p" to delimit the partition number.
    if [[ "$target" =~ "nvme" ]]; then
        nvme=1
    fi

    partprobe "/dev/${target}"
    mkfs.xfs -f -L "${vm_drive_authority}_${vm_index}" "/dev/${target}${nvme:+p}1" || echo >&2 "Failed to create ${vm_drive_authority}_${vm_index}"
    printf '% -18s\t% -18s\t%s\t%s %d %d\n' "${vm_drive_scheme}=${vm_drive_authority}_${vm_index}" "/vms/store${vm_index}" xfs "$METAL_FSOPTS_XFS" 0 0 >> /tmp/fstab
    vm_index="$((vm_index + 1))"
    partprobe "/dev/${target}"
}


##############################################################################
## function: disks_os
# Find disks for our OS to use.
function disks_os {
    local md_disks=()
    local disks

    disks="$(metal_scand)"
    IFS=" " read -r -a pool <<< "$disks"
    for disk in "${pool[@]}"; do
        if [ "${#md_disks[@]}" -eq "${metal_disks}" ]; then
            break
        fi
        md_disk=$(metal_resolve_disk "$disk" "$METAL_DISK_SMALL")
        if [ -n "${md_disk}" ]; then
            md_disks+=("$md_disk")
        fi
    done

    if [ "${#md_disks[@]}" -lt "$metal_disks" ]; then
        echo >&2 "No disks were found for the OS that were [$METAL_DISK_SMALL] (in bytes) or larger, all were too small or had filesystems present!"
        return 1
    else
        echo >&2 "Found the following disk(s) for the main RAID array (qty. [$metal_disks]): [${md_disks[*]}]"
    fi

    partition_os "${md_disks[@]}"
}


##############################################################################
## function: disk_vm
# Find a disk for our VMs to use.
function disk_vm {
    local vm=''
    local disks

    disks="$(metal_scand)"
    IFS=" " read -r -a pool <<< "$disks"
    for disk in "${pool[@]}"; do
        if [ -n "${vm}" ]; then
            break
        fi
        vm=$(metal_resolve_disk "$disk" "$METAL_DISK_LARGE")
    done

    # If no disks were found, die.
    # When rd.luks is disabled, this hook-script expects to find a disk. Die if one isn't found.
    if [ -z "${vm}" ]; then
        echo >&2 "No disks were found for ephemeral use."
        return 1
    else
        echo >&2 "Found the following disk for ephemeral storage: $vm"
    fi

    partition_vm "${vm}"
}


##############################################################################
## function: setup_bootloader
# Create our boot loader.
function setup_bootloader {
    local name
    local index
    local disk_cmdline
    local mpoint
    local iso
    local iso_file
    local iso_label
    local arch=x86_64

    mpoint="$(mktemp -d)"
    mkdir -pv "${mpoint}"
    if ! mount -n -t vfat -L "${boot_drive_authority}" "$mpoint"; then
        echo >&2 "Failed to mount ${boot_drive_authority} as xfs or ext4"
        rm -rf "${mpoint}"
        return 1
    fi

    # Remove all existing entries; anything with CRAY (lower or uppercase). We
    # only want our boot-loader.
    for entry in $(efibootmgr | awk -F '[* ]' 'toupper($0) ~ /CRAY/ {print $1}'); do
         efibootmgr -q -b "${entry:4:8}" -B
    done

    # Install grub2.
    name=$(grep PRETTY_NAME /etc/*release* | cut -d '=' -f2 | tr -d '"')

    index=0
    mapfile -t boot_disks < <(mdadm --detail "$(blkid -L ${boot_drive_authority})" | grep /dev | grep -v md | awk '{print $NF}')
    for disk in "${boot_disks[@]}"; do

        # Add '--suse-enable-tpm' to grub2-install once we need TPM.
        grub2-install \
            --no-rs-codes \
            --suse-force-signed \
            --root-directory "${mpoint}" \
            --removable "$disk" \
            --themes=SLE \
            --locales="" \
            --fonts=""

        efibootmgr -c -D -d "$disk" -p 1 -L "CRAY UEFI OS $index" -l '\efi\boot\bootx64.efi' | grep -i cray

        index=$((index + 1))
    done

    disk_cmdline=(
    'kernel'
    "rd.live.overlay=${oval_drive_scheme}=${oval_drive_authority}"
    'rd.live.overlay.overlayfs=1'
    "rd.live.dir=${live_dir}"
    "rd.live.squashimg=${squashfs_file}"
    'rd.luks=1'
    'rd.luks.crypttab=0'
    'rd.lvm.conf=0'
    'rd.lvm=1'
    'rd.auto=1'
    'rd.md=1'
    'rd.dm=0'
    'rd.neednet=0'
    'rd.peerdns=0'
    'rd.md.waitclean=1'
    'rd.multipath=0'
    'rd.md.conf=1'
    'mediacheck=0'
    'biosdevname=1'
    'crashkernel=360M'
    'psi=1'
    'console=tty0'
    'console=ttyS0,115200'
    'mitigations=auto'
    'iommu=pt'
    'intel_iommu=on'
    'pcie_ports=native'
    'split_lock_detect=off'
    'transparent_hugepage=never'
    'rd.shell'
    )

    iso="$(_find_hypervisor_iso)"
    if [ -n "$iso" ]; then
        mkdir -pv "${mpoint}/${live_dir}/iso"
        cp "$iso" "${mpoint}/${live_dir}/iso"
        iso_file="/${live_dir}/iso/$(basename "$iso")"
        iso_label="$(isoinfo -j UTF-8 -d -i "$iso" | sed -n 's/Volume id: //p' | tr -d \\n)"
        disk_cmdline+=( "iso-scan/filename=$iso_file" )
        disk_cmdline+=( "root=live:LABEL=$iso_label" )
    # Make our grub.cfg file.
        cat << EOF > "${mpoint}/boot/grub2/grub.cfg"
set timeout=5
set default=0 # Set the default menu entry
menuentry "$name" --class gnu-linux --class gnu {
    set gfxpayload=keep
    # needed for compression
    insmod gzio
    # needed for partition manipulation
    insmod part_gpt
    # needed for block device handles
    insmod diskfilter
    # needed for RAID (this does not always load despite this entry)
    insmod mdraid1x
    # verbosely define accepted formats (ext2/3/4 & xfs)
    insmod ext2
    insmod xfs
    loopback loop $iso_file
    echo    'Loading kernel ...'
    linuxefi (loop)/boot/$arch/loader/${disk_cmdline[@]}
    echo    'Loading initial ramdisk ...'
    initrdefi (loop)/boot/$arch/loader/initrd.img.xz
}
EOF
    elif [ -f "$memory_squashfs_file" ]; then

        # If the hypervisor ISO isn't found, and we're on the fawkes-live CD, then abort!
        if [ -f /etc/fawkes-release ]; then
            echo 'A valid hypervisor ISO was not found!' >&2
            return 1
        fi

        mkdir -pv "${mpoint}/${live_dir}/"
        cp "$memory_squashfs_file" "${mpoint}/${live_dir}/"
        cp "/run/initramfs/live/boot/$arch/loader/kernel" "${mpoint}/${live_dir}/"
        cp "/run/initramfs/live/boot/$arch/loader/initrd.img.xz" "${mpoint}/${live_dir}/"
        disk_cmdline+=( "root=live:LABEL=${boot_drive_authority}" )
        cat << EOF > "${mpoint}/boot/grub2/grub.cfg"
set timeout=5
set default=0 # Set the default menu entry
menuentry "$name" --class gnu-linux --class gnu {
    set gfxpayload=keep
    # needed for compression
    insmod gzio
    # needed for partition manipulation
    insmod part_gpt
    # needed for block device handles
    insmod diskfilter
    # needed for RAID (this does not always load despite this entry)
    insmod mdraid1x
    # verbosely define accepted formats (ext2/3/4 & xfs)
    insmod ext2
    insmod xfs
    echo    'Loading kernel ...'
    linuxefi \$prefix/../../$live_dir/${disk_cmdline[@]}
    echo    'Loading initial ramdisk ...'
    initrdefi \$prefix/../../$live_dir/initrd.img.xz
}
EOF
    else
        echo >&2 'Error! No rootfs was found.'
        return 1
    fi

    umount "${mpoint}"
    rmdir "${mpoint}"
}

##############################################################################
## function: setup_overlayfs
# Make our dmsquash-live-root overlayFS.
# Also adds the fstab and udev files to the overlay, as well as kdump dependencies.
function setup_overlayfs {
    local error=0
    local mpoint
    local connections='/etc/NetworkManager/system-connections'

    mpoint="$(mktemp -d)"
    mkdir -pv "${mpoint}"
    if ! mount -n -t xfs -L "${oval_drive_authority}" "$mpoint"; then
        if ! mount -n -t ext4 -L "${oval_drive_authority}" "$mpoint"; then
            echo >&2 "Failed to mount ${oval_drive_authority} as xfs or ext4"
            error=1
        fi
    fi
    if [ "$error" -ne 0 ]; then
        rm -rf "$mpoint"
        error=1
    fi

    # Create OverlayFS directories for dmsquash-live
    iso="$(_find_hypervisor_iso)"
    if [ -n "$iso" ]; then
        overlayfs_spec="$(_find_hypervisor_iso_overlayfs_spec)"
    elif [ -f "$memory_squashfs_file" ]; then
        overlayfs_spec="$(_find_boot_disk_overlayfs_spec)"
    else
        echo >&2 'Error! No overlayFS spec was found for the rootfs partition.'
        error=1
    fi
    mkdir -v -p \
        "${mpoint}/${live_dir}/${overlayfs_spec}" \
        "${mpoint}/${live_dir}/${overlayfs_spec}/../ovlwork"
    chmod -R 0755 "${mpoint}/${live_dir}"

    # Create all dependent directories.
    mkdir -v -p "${mpoint}/${live_dir}/${overlayfs_spec}${connections}"
    mkdir -v -p "${mpoint}/${live_dir}/${overlayfs_spec}/boot"
    mkdir -v -p "${mpoint}/${live_dir}/${overlayfs_spec}/etc"
    mkdir -v -p "${mpoint}/${live_dir}/${overlayfs_spec}/etc/ssh"
    mkdir -v -p "${mpoint}/${live_dir}/${overlayfs_spec}/etc/udev/rules.d"
    mkdir -v -p "${mpoint}/${live_dir}/${overlayfs_spec}/metal/recovery"
    mkdir -v -p "${mpoint}/${live_dir}/${overlayfs_spec}/root/.ssh"
    mkdir -v -p "${mpoint}/${live_dir}/${overlayfs_spec}/var/crash"
    mkdir -v -p "${mpoint}/${live_dir}/${overlayfs_spec}/vms"
    chmod 700 "${mpoint}/${live_dir}/${overlayfs_spec}/root/.ssh"

    # fstab
    {
        printf '% -18s\t% -18s\t%s\t%s %d %d\n' "${boot_drive_scheme}=${boot_drive_authority}" /metal/recovery vfat defaults 0 0
        printf '% -18s\t% -18s\t%s\t%s %d %d\n' "${oval_drive_scheme}=${oval_drive_authority}" / xfs defaults 0 0
        printf '% -18s\t% -18s\t%s\t%s %d %d\n' tmpfs /tmp tmpfs "$METAL_FSOPTS_TMPFS" 0 0
    } > "${mpoint}/${live_dir}/${overlayfs_spec}/etc/fstab"
    cat /tmp/fstab >> "${mpoint}/${live_dir}/${overlayfs_spec}/etc/fstab"

    # udev
    if [ ! -f /etc/udev/rules.d/80-ifname.rules ]; then
        # Create udev rules without renaming the current boot session's interfaces, prevent pulling the rug out from the user if they're logged in through a NIC.
        crucible network udev --skip-rename
    fi
    cp -p -v /etc/udev/rules.d/80-ifname.rules "${mpoint}/${live_dir}/${overlayfs_spec}/etc/udev/rules.d"

    # networking
    rsync "${connections}/" "${mpoint}/${live_dir}/${overlayfs_spec}${connections}/"

    # mdadm
    cat << EOF > "${mpoint}/${live_dir}/${overlayfs_spec}/etc/mdadm.conf"
HOMEHOST <none>
EOF

    if [ -f "$SSH_KEY" ]; then
        install -m 600 "${mpoint}/${live_dir}/${overlayfs_spec}/root/.ssh/authorized_keys"
        cat "${SSH_KEY}" >> "${mpoint}/${live_dir}/${overlayfs_spec}/root/.ssh/authorized_keys"

        # Copy the key for the management-vm to find and import.
        cp -p -v "${SSH_KEY}" "${mpoint}/${live_dir}/${overlayfs_spec}/root/.ssh/"
    elif [ -d "$SSH_KEY" ]; then
        install -m 600 "${mpoint}/${live_dir}/${overlayfs_spec}/root/.ssh/authorized_keys"
        local ssh_keys

        # Remove trailing slash for niceness.
        ssh_keys="$(realpath -s "$SSH_KEY")"
        local key
        for key in "$ssh_keys"/*.pub; do
            # For safety, ensure a new line is always at end of file.
            sed '$a\' "${key}" >> "${mpoint}/${live_dir}/${overlayfs_spec}/root/.ssh/authorized_keys"

            # Copy the keys for the management-vm to find and import.
            cp -p -v "${key}" "${mpoint}/${live_dir}/${overlayfs_spec}/root/.ssh/"
        done
    fi
    local ssh_import_exit_code
    ssh_import_exit_code="$(systemctl show ssh-import-id.service --property ExecMainStatus --value)"
    if [ -f /etc/fawkes-release ]; then
        echo 'Installing from fawkes liveCD! Skipping gitea auto-import.'
    elif [ -f /etc/hypervisor-release ]; then
        if [ "$ssh_import_exit_code" -ne 0 ]; then
            echo >&2 'SSH key auto-import failed! See ssh-import-id.service for more information.'
            error=1
        fi
        if [ ! -f /root/.ssh/authorized_keys ]; then
            echo >&2 'No authorized_keys were defined for root, double-check the ssh-import-id.service.'
            error=1
        fi
        cat /root/.ssh/authorized_keys >> "${mpoint}/${live_dir}/${overlayfs_spec}/root/.ssh/authorized_keys"
        chmod 600 "${mpoint}/${live_dir}/${overlayfs_spec}/root/.ssh/authorized_keys"
    else
        echo >&2 'Unsupported install environment for ssh-key import! Not importing any ssh keys from gitea.'
    fi

    # Disable further processing of auto-importing keys.
    touch "${mpoint}/${live_dir}/${overlayfs_spec}/etc/ssh/ssh_import_id.disabled"

    # kdump
    local kernel_savedir
    local kernel_image
    local kernel_ver
    local system_map
    kernel_savedir="$(grep -oP 'KDUMP_SAVEDIR="file:///\K\S+[^"]' /run/rootfsbase/etc/sysconfig/kdump)"
    ln -snf "./${live_dir}/${overlayfs_spec}/var/crash" "${mpoint}/${kernel_savedir}"
    ln -snf "./${live_dir}/${overlayfs_spec}/boot" "${mpoint}/boot"

    cat << 'EOF' > "${mpoint}/README.txt"
This directory contains two supporting directories for KDUMP
- boot/ is a symbolic link that enables KDUMP to resolve the kernel and system symbol maps.
- $crash_dir/ is a directory that KDUMP will dump into, this directory is bind mounted to /var/crash on the booted system.
EOF
    # kdump will produce incomplete dumps without the kernel image and/or system map present.
    kernel_ver="$(readlink /run/rootfsbase/boot/vmlinuz | grep -oP 'vmlinuz-\K\S+')"
    kernel_image="/run/rootfsbase/boot/vmlinux-${kernel_ver}.gz"
    if ! cp -p -v "$kernel_image" "${mpoint}/boot/"; then
        echo >&2 "Failed to copy kernel image [$kernel_image] to overlay at [$mpoint/boot/]"
        error=1
    fi
    system_map=/run/rootfsbase/boot/System.map-${kernel_ver}
    if ! cp -p -v "${system_map}" "${mpoint}/boot/"; then
        echo >&2 "Failed to copy system map [$system_map] to overlay at [$mpoint/boot/]"
        error=1
    fi

    umount "${mpoint}"
    rmdir "${mpoint}"

    mkdir -p /vms/store0
    # Always mount the first VMSTORE index.
    mount -L VMSTORE_0 /vms/store0
    mkdir -p /vms/store0/assets
    rsync -rltDv /data/ /vms/store0/assets/
    umount /vms/store0

    if [ "$error" -ne 0 ]; then
        return 1
    fi
}


##############################################################################
## function: setup_boot_order
# Re-orders the boot order to set disks first.
function set_boot_order {
    local disks
    local boot_order
    local new_bootorder=''
    boot_order="$(efibootmgr | grep -i bootorder | awk '{print $NF}')"
    mapfile -t disks < <(efibootmgr | grep 'CRAY UEFI' | sed 's/^Boot//g' | awk '{print $1}' | tr -d '*')

    # Remove disks from the current boot order list, and add them to the front of the new boot order list.
    for disk in "${disks[@]}"; do
        boot_order=$(echo "$boot_order" | sed -E 's/'"$disk"',?//')
        new_bootorder="$disk,$new_bootorder"
    done

    # Append the scrubbed, old boot order to the end of the new boot order.
    new_bootorder="$(echo "${new_bootorder}${boot_order}" | sed 's/,$//')"

    # Set the boot order.
    efibootmgr -o "${new_bootorder}"
}

echo 'Partitioning OS disks ...'
disks_os

echo 'Partitioning VM disk ... '
disk_vm

echo 'Creating overlayFS ...'
setup_overlayfs

echo 'Installing bootloader and ISO artifact ... '
setup_bootloader || exit 1

echo 'Setting boot order ... '
set_boot_order

echo 'Install completed, please reboot.'
