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

##############################################################################
# constant: metal_fsopts_xfs
#
# COMMA-DELIMITED-LIST of fsopts for XFS
METAL_FSOPTS_XFS=noatime,largeio,inode64,swalloc,allocsize=131072k

##############################################################################
# constant: metal_disk_small
#
# Define the size that is considered to fit the "small" disk form factor. These
# usually serve critical functions.
METAL_DISK_SMALL=375809638400

##############################################################################
# constant: metal_disk_large
#
# Define the size that is considered to fit the "large" disk form factor. These
# are commonly if not always used as ephemeral disks.
METAL_DISK_LARGE=1048576000000

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
>"${LOG}"

boot_drive_scheme=LABEL
boot_drive_authority=BOOTRAID
sqfs_drive_scheme=LABEL
sqfs_drive_authority=SQFSRAID
vm_drive_scheme=LABEL
vm_drive_authority=VMSTORE

# Lock this to our root image label so kdump works
metal_overlay="$(grep -E '\s/\s' /etc/fstab | awk '{print $1}')"
oval_drive_scheme=${metal_overlay%%=*}
oval_drive_authority=${metal_overlay#*=}

metal_disks=2
metal_sqfs_size_end=25
metal_md_level=mirror
metal_minimum_disk_size=16
while getopts "l:s:d:i:" o; do
    case "${o}" in
        d)
            metal_disks="${OPTARG}"
            ;;
        s)
            metal_sqfs_size_end="${OPTARG}"
            ;;
        l)
            metal_md_level="${OPTARG}"
            ;;
        i)
            metal_minimum_disk_size="${OPTARG}"
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

case $sqfs_drive_scheme in
    PATH | path | UUID | uuid | LABEL | label)
        printf '%-12s: %s\n' 'squashFS' "${sqfs_drive_scheme}=${sqfs_drive_authority}"
        ;;
    *)
        echo >&2 "Unsupported sqfs-drive-scheme [${sqfs_drive_scheme}] Supported schemes: PATH, UUID, and LABEL"
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
    local minimum_size=$(echo $2 | sed 's/,.*//')
    name="$(echo $disk | sed 's/,/ /g' | awk '{print $2}')"
    size="$(echo $disk | sed 's/,/ /g' | awk '{print $1}')"
    if ! lsblk --fs --json "/dev/${name}" | grep -q children ; then
        if [ "${size}" -ge "${minimum_size}" ]; then
            echo -n "$name"
        fi
    fi
}

##############################################################################
# function: _overlayFS_path_spec
#
# Return a dracut-dmsquash-live friendly name for an overlayFS to pair with a booting squashFS.
# example:
#
#   overlay-SQFSRAID-cfc752e2-ebb3-4fa3-92e9-929e599d3ad2
#
_overlayFS_path_spec() {
    # if no label is given, grab the default array's UUID and use the default label
    if [ -b /dev/disk/by-${sqfs_drive_scheme,,}/${sqfs_drive_authority} ]; then
        echo "overlay-${sqfs_drive_authority:-SQFSRAID}-$(blkid -s UUID -o value /dev/disk/by-${sqfs_drive_scheme,,}/${sqfs_drive_authority})"
    else
        echo "overlay-${sqfs_drive_authority:-SQFSRAID}-$(blkid -s UUID -o value /dev/md/SQFS)"
    fi
}


##############################################################################
## function: partition_os
#
# Partition the OS disk(s).
function partition_os {
    local disks
    IFS=" " read -r -a disks <<< "$@"

    local boot_raid_parts=()
    local sqfs_raid_parts=()
    local oval_raid_parts=()
    for disk in "${disks[@]}"; do

        parted --wipesignatures -m --align=opt --ignore-busy -s "/dev/$disk" -- mklabel gpt \
            mkpart esp fat32 2048s 500MB set 1 esp on \
            mkpart primary xfs 500MB "${metal_sqfs_size_end}GB" \
            mkpart primary xfs "${metal_sqfs_size_end}GB" 100%

        # NVME partitions have a "p" to delimit the partition number, add this in order to reference properly in the RAID creation.
        if [[ "$disk" =~ "nvme" ]]; then
            disk="${disk}p"
        fi

        boot_raid_parts+=( "/dev/${disk}1" )
        sqfs_raid_parts+=( "/dev/${disk}2" )
        oval_raid_parts+=( "/dev/${disk}3" )
    done

    # metadata=0.9 for boot files.
    mdadm_raid_devices="--raid-devices=$metal_disks"
    mdadm --create /dev/md/BOOT --run --verbose --assume-clean --metadata=0.9 --level="$metal_md_level" "$mdadm_raid_devices" "${boot_raid_parts[@]}" || metal_die -b "Failed to make filesystem on /dev/md/BOOT"
    mdadm --create /dev/md/SQFS --run --verbose --assume-clean --metadata=1.2 --level="$metal_md_level" "$mdadm_raid_devices" "${sqfs_raid_parts[@]}" || metal_die -b "Failed to make filesystem on /dev/md/SQFS"
    mdadm --create /dev/md/ROOT --assume-clean --run --verbose --metadata=1.2 --level="$metal_md_level" "$mdadm_raid_devices" "${oval_raid_parts[@]}" || metal_die -b "Failed to make filesystem on /dev/md/ROOT"

    mkfs.vfat -F32 -n "${boot_drive_authority}" /dev/md/BOOT
    mkfs.xfs -f -L "${sqfs_drive_authority}" /dev/md/SQFS
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
    mkfs.xfs -f -L ${vm_drive_authority} "/dev/${target}${nvme:+p}1" || echo >&2 "Failed to create ${vm_drive_authority}"
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
    # Offset the search by the number of disks used up by the main metal dracut module.
    vm=''
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
    local init_cmdline
    local disk_cmdline

    local mpoint="$(mktemp -d)"
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
        grub2-install --no-rs-codes --suse-force-signed --root-directory "${mpoint}" --removable "$disk"

        efibootmgr -c -D -d "$disk" -p 1 -L "CRAY UEFI OS $index" -l '\efi\boot\bootx64.efi' | grep -i cray

        index=$((index + 1))
    done

    disk_cmdline=(kernel
    "root=live:${sqfs_drive_scheme}=${sqfs_drive_authority}"
    "rd.live.overlay=${oval_drive_scheme}=${oval_drive_authority}"
    rd.live.overlay.overlayfs=1
    "rd.live.dir=${live_dir}"
    "rd.live.squashimg=${squashfs_file}"
    rd.luks=1
    rd.luks.crypttab=0
    rd.lvm.conf=0
    rd.lvm=1
    rd.auto=1
    rd.md=1
    rd.dm=0
    rd.neednet=0
    rd.peerdns=0
    rd.md.waitclean=1
    rd.multipath=0
    rd.md.conf=1
    mediacheck=0
    biosdevname=1
    crashkernel=360M
    psi=1
    console=tty0
    "console=ttyS0,115200"
    mitigations=auto
    iommu=pt
    intel_iommu=on
    pcie_ports=native
    split_lock_detect=off
    transparent_hugepage=never
    rd.shell
    )

    # Get the cloud-init datasource, if present.
    init_cmdline=$(cat /proc/cmdline)
    found_ds=0
    for cmd in $init_cmdline; do
        if [[ "$cmd" =~ ^ds=.* ]]; then
            ds="$cmd"
        fi
    done

    # TODO: only append for installs from the ISO, PXE boots will already have this on the command line.
    if [ -n "$ds" ]; then
        # Append our existing ds command,(i.e. ds=nocloud-net;s=http://$url will get the ; escaped)
        disk_cmdline+=( "${ds//;/\\;}" )
    else
        disk_cmdline+=( 'ds=nocloud\;s=/metal' )
    fi

    # Make our grub.cfg file.
    cat << EOF > "$mpoint/boot/grub2/grub.cfg"
set timeout=10
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
    linuxefi \$prefix/../${disk_cmdline[@]}
    echo    'Loading initial ramdisk ...'
    initrdefi \$prefix/../initrd.img.xz
}
EOF
    local artifact_error=0
    local base_dir=/squashfs # This must copy from /squashfs and not /boot, the initrd at /squashfs is non-hostonly

    mkdir -pv "${mpoint}/boot"

    # pull the loaded items from the mounted squashFS storage into the fallback bootloader
    . /srv/cray/scripts/common/dracut-lib.sh
    if [ -z ${KVER} ]; then
        echo >&2 'Failed to find KVER from /srv/cray/scripts/common/dracut-lib.sh'
        return 1
    fi
    if ! cp -pv "${base_dir}/${KVER}.kernel" "${mpoint}/boot/kernel" ; then
        echo >&2 "Kernel file NOT found in $base_dir!"
        artifact_error=1
    fi
    if ! cp -pv "${base_dir}/initrd.img.xz" "${mpoint}/boot/initrd.img.xz" ; then
        echo >&2 "initrd.img.xz file NOT found in $base_dir!"
        artifact_error=1
    fi

    umount "${mpoint}"
    rmdir "${mpoint}"
    if [ "$artifact_error" -ne 0 ]; then
        echo >&2 "Error detected. Aborting!"
        return 1
    fi
}

##############################################################################
## function: setup_squashfs
# Adds the squashFS to the local disk.
function setup_squashfs {
    local error=0
    local mpoint="$(mktemp -d)"
    mkdir -pv "${mpoint}"
    if ! mount -n -t xfs -L "${sqfs_drive_authority}" "$mpoint"; then
        if ! mount -n -t ext4 -L "${sqfs_drive_authority}" "$mpoint"; then
            echo >&2 "Failed to mount ${sqfs_drive_authority} as xfs or ext4"
            rm -rf "${mpoint}"
            return 1
        fi
    fi
    mkdir -v -p "${mpoint}/${live_dir}"
    if ! cp -pv "/run/initramfs/live/${live_dir}/${squashfs_file}" "${mpoint}/${live_dir}"; then
        echo >&2 'Failed to load squash image onto disk'
        error=1
    fi
    umount "${mpoint}"
    rmdir "${mpoint}"
    if [ "$error" -ne 0 ]; then
        return 1
    fi
}

##############################################################################
## function: setup_overlayfs
# Make our dmsquash-live-root overlayFS.
# Also adds the fstab and udev files to the overlay, as well as kdump dependencies.
function setup_overlayfs {
    local error=0
    local mpoint="$(mktemp -d)"
    mkdir -pv "${mpoint}"
    if ! mount -n -t xfs -L "${oval_drive_authority}" "$mpoint"; then
        if ! mount -n -t ext4 -L "${oval_drive_authority}" "$mpoint"; then
            echo >&2 "Failed to mount ${oval_drive_authority} as xfs or ext4"
            error=1
        fi
    fi
    if [ "$error" -ne 0 ]; then
        rm -rf "$mpoint"
        return 1
    fi

    # Create OverlayFS directories for dmsquash-live
    metal_overlayfs_id="$(_overlayFS_path_spec)"
    mkdir -v -m 0755 -p \
        "${mpoint}/${live_dir}/${metal_overlayfs_id}" \
        "${mpoint}/${live_dir}/${metal_overlayfs_id}/../ovlwork"

    # fstab
    mkdir -v -p "${mpoint}/${live_dir}/${metal_overlayfs_id}/etc"
    mkdir -v -p "${mpoint}/${live_dir}/${metal_overlayfs_id}/etc/udev/rules.d"
    mkdir -v -p "${mpoint}/${live_dir}/${metal_overlayfs_id}/metal/recovery"
    mkdir -v -p "${mpoint}/${live_dir}/${metal_overlayfs_id}/vms"
    {
        printf "% -18s\t% -18s\t%s\t%s %d %d\n" "${boot_drive_scheme}=${boot_drive_authority}" /metal/recovery vfat defaults 0 0 > /tmp/fstab.metal
        printf '% -18s\t% -18s\t%s\t%s %d %d\n' "${vm_drive_scheme}=${vm_drive_authority}" /vms xfs "$METAL_FSOPTS_XFS" 0 0 >> /tmp/fstab.metal
    } >"${mpoint}/${live_dir}/${metal_overlayfs_id}/etc/fstab.metal"

    # udev
    # TODO: These rules should already exist at this point.
    mkdir -p "${mpoint}/${live_dir}/${metal_overlayfs_id}/etc/udev/rules.d"
    #ifnames.sh" -s -i "${mpoint}/${live_dir}/${metal_overlayfs_id}/etc/udev/rules.d"
    cp -pv /etc/udev/rules.d/80-ifname.rules "${mpoint}/${live_dir}/${metal_overlayfs_id}/etc/udev/rules.d"

    # Disable cloud-init
    mkdir -p "${mpoint}/${live_dir}/${metal_overlayfs_id}/etc/cloud/"
    touch "${mpoint}/${live_dir}/${metal_overlayfs_id}/etc/cloud/cloud-init.disabled"

    # cloud-init testing seed
    echo -e "instance-id: iid-local01" > "${mpoint}/${live_dir}/${metal_overlayfs_id}/metal/meta-data"
    echo -e "#cloud-config\nrun_cmd: [touch, /rusty_test]\n" > "${mpoint}/${live_dir}/${metal_overlayfs_id}/metal/user-data"

    # mdadm
    cat << EOF > "${mpoint}/${live_dir}/${metal_overlayfs_id}/etc/mdadm.conf"
HOMEHOST <none>
EOF

    # 1. Create an admin user, set a blank password and expire it at the same time
    # 2. Copy shadow and passwd to the new root
    # 3. Set root to /sbin/nologin, and remove its password (do not carry the liveCD root password over to the disk)
#     cp /etc/shadow "${mpoint}/etc/"
#     cp /etc/passwd "${mpoint}/etc/"

    # purge the root password
#     seconds_per_day=$(( 60*60*24 ))
#     days_since_1970=$(( $(date +%s) / seconds_per_day ))
#     sed -i "/^root:/c\root:\*:$days_since_1970::::::" "${mpoint}/etc/shadow"
#     sed -i -E 's@^(root:.*:.*:.*:.*:.*:).*@\1\/sbin\/nologin@' "${mpoint}/etc/passwd"

    # Automount the VMSTORE.
    cp /etc/fstab "${mpoint}/etc/fstab"
    sed -i -E 's:(^LABEL=VMSTORE[[:space:]]+/vms[[:space:]]+[/a-z]+[[:space:]]+)noauto,:\1:' "${mpoint}/etc/fstab"

    # kdump
    local kernel_savedir
    local kernel_image
    local kernel_ver
    local system_map
    kernel_savedir="$(grep -oP 'KDUMP_SAVEDIR="file:///\K\S+[^"]' /run/rootfsbase/etc/sysconfig/kdump)"
    mkdir -pv "${mpoint}/${live_dir}/${metal_overlayfs_id}/var/crash"
    ln -snf "./${live_dir}/${metal_overlayfs_id}/var/crash" "${mpoint}/${kernel_savedir}"
    mkdir -pv "${mpoint}/${live_dir}/${metal_overlayfs_id}/boot"
    ln -snf "./${live_dir}/${metal_overlayfs_id}/boot" "${mpoint}/boot"

    cat << 'EOF' > "${mpoint}/README.txt"
This directory contains two supporting directories for KDUMP
- boot/ is a symbolic link that enables KDUMP to resolve the kernel and system symbol maps.
- $crash_dir/ is a directory that KDUMP will dump into, this directory is bind mounted to /var/crash on the booted system.
EOF
    # kdump will produce incomplete dumps without the kernel image and/or system map present.
    kernel_ver="$(readlink /run/rootfsbase/boot/vmlinuz | grep -oP 'vmlinuz-\K\S+')"
    kernel_image="/run/rootfsbase/boot/vmlinux-${kernel_ver}.gz"
    if ! cp -pv "$kernel_image" "${mpoint}/boot/"; then
        echo >&2 "Failed to copy kernel image [$kernel_image] to overlay at [$mpoint/boot/]"
        error=1
    fi
    system_map=/run/rootfsbase/boot/System.map-${kernel_ver}
    if ! cp -pv "${system_map}" "${mpoint}/boot/"; then
        echo >&2 "Failed to copy system map [$system_map] to overlay at [$mpoint/boot/]"
        error=1
    fi

    mkdir -p /data
    mount -L data /data
    mkdir -p /vms
    mount -L VMSTORE /vms
    mkdir -p /vms/assets
    rsync -rltDv /data/ /vms/assets/
    umount /vms /data

    umount "${mpoint}"
    rmdir "${mpoint}"
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

echo 'Adding squashFS to disk ... '
setup_squashfs || exit 1

echo 'Creating overlayFS ...'
setup_overlayfs

echo 'Setting up bootloader ... '
setup_bootloader || exit 1

echo 'Setting boot order ... '
set_boot_order

echo 'Install completed, please reboot.'
