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
# TODO: Rewrite script in Python
trap disclaimer ERR
DRY_RUN=1

function usage {
    cat << EOF
usage:

-f          : Disable the dry-run, and act on destructive behavior.
-i [size]   : Exclude disks that are of size (in Gigabytes) or smaller (default: 16)

EOF
}

function disclaimer {
    echo >&2 'This script assumes targeted volume groups are unmounted.'
}

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

metal_minimum_disk_size=16
while getopts "yi:" o; do
    case "${o}" in
        y)
            DRY_RUN=0
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

if [ "${DRY_RUN}" -ne 0 ]; then
    echo >&2 'This is a dry-run and no changes will be made to the system'
    echo >&2 "Run $0 with -y to exit dry-run."
fi

root_partition="$(findmnt -o TARGET,SOURCE -rn /run/initramfs/live | awk '{print $NF}')"
if [ -n "$root_partition" ]; then
    root_disk="$(lsblk -n -o PKNAME "$root_partition" | head -n 1)"
    if [ -z "$root_disk" ] && [[ "$root_partition" =~ /dev/md.* ]]; then
        root_disk="$root_partition"
    fi
else
    root_disk=''
fi

doomed_disks="$(lsblk -b -d -l -o NAME,SUBSYSTEMS,SIZE | grep -E '('"$METAL_SUBSYSTEMS"')' | grep -v -E '('"$METAL_SUBSYSTEMS_IGNORE"')' | sort -u | awk '{print ($3 > '$METAL_IGNORE_THRESHOLD') ? "/dev/"$1 : ""}' | tr '\n' ' ' | sed 's/ *$//')"
doomed_raids="$(lsblk -l -o NAME,TYPE | grep raid | sort -u | awk '{print "/dev/"$1}' | tr '\n' ' ' | sed 's/ *$//')"
doomed_volume_groups=( 'vg_name=~ceph*' 'vg_name=~metal*' )
set -o pipefail

vgfailure=0

if [ "${DRY_RUN}" -ne 0 ]; then
    echo "Disk(s) to be wiped : [$doomed_disks]"
    echo "RAID(s) to be wiped : [$doomed_raids]"
    echo "VG(s)   to be wiped : [${doomed_volume_groups[*]}]"
    if [ -n "$root_disk" ]; then
        if lsblk -b -d -l -o SUBSYSTEMS /dev/sdd | grep -qoE '('"$METAL_SUBSYSTEMS_IGNORE"')'; then
            echo "Root is installed   : [$root_disk] ($METAL_SUBSYSTEMS_IGNORE)"
        else
            echo "Root is installed   : [$root_disk]"
        fi
    fi
    exit 2
fi

mkdir -p /var/log/crucible/
exec 2>"/var/log/crucible/$(basename $0).err"

if [ -n "$root_disk" ]; then
    if [[ "$doomed_disks" =~ .*"/dev/${root_disk}".* ]]; then
        echo >&2 "Root is installed on [$root_disk] which is targeted to be wiped! Aborting!"
        exit 1
    fi
fi

vgscan >&2 && vgs >&2
for volume_group in "${doomed_volume_groups[@]}"; do
    vgremove -f --select "${volume_group}" -y >&2 || warn "no ${volume_group} volumes found"
    if [ "$(vgs --select "$volume_group")" != '' ]; then
        echo >&2 "${volume_group} still exists, this is unexpected. Printing vgs table:"
        vgs >&2
    fi
done
if [ ${vgfailure} -ne 0 ]; then
    echo >&2 'Failed to remove all volume groups! Try rebooting this node again.'
    echo >&2 'If this persists, try running the manual wipe in the emergency shell and reboot again.'
    echo >&2 'After trying the manual wipe, run 'echo b >/proc/sysrq-trigger' to reboot'
fi

echo >&2 "local storage device wipe is targeting the following RAID(s): [$doomed_raids]"
for doomed_raid in $doomed_raids; do
    wipefs --all --force "$doomed_raid"
    mdadm --stop "$doomed_raid"
done

echo >&2 "local storage device wipe is targeting the following block devices: [$doomed_disks]"
for doomed_disk in $doomed_disks; do
    mdadm --zero-superblock "$doomed_disk"*
    wipefs --all --force "$doomed_disk"*
done

for doomed_disk in $doomed_disks; do
    lsblk "$doomed_disk"
    partprobe "$doomed_disk"
    lsblk "$doomed_disk"
done

echo 'local storage disk wipe complete'
