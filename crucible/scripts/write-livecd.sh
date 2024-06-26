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
name=$(basename $0)

# Size in MB to use for cow partition
cow_size=0

# Size of specified block device
dev_size=0

# Initial empty values for usb device and iso file
usb=""
iso_file=""


usage () {
    cat << EOF
Usage $name DEVICE ISO-FILE [COW-SIZE] [SET-BOOT]

where:
    DEVICE      Raw device file of a disk device to use as a bootable device

    ISO-FILE    Pathname or URL of LiveCD ISO file to write to the usb
                flash drive.

    COW-SIZE    Size of the Copy on Write partition to create,(value in
                MB). If not specified the default value of 5000 is used.

EOF
}

error () {
    mesg ERROR "$@"
}

warning () {
    mesg WARNING "$@"
}

info () {
    mesg INFO "$@"
}

mesg () {
    LEVEL=$1
    shift 1
    echo "$LEVEL: $*"
}

create_partition () {
    local part=$1
    local label=$2
    local dev=$3
    local start=$4
    local size=$5

    local dev_part=${dev}${part}
    local end_num=0


    if [[ $size -gt 0 ]]; then
        # Use specified size
        ((end_num=start+size))
    else
        # Use all remaining space on device
        ((end_num=dev_size - 1 ))
    fi

    if [[ $end_num -ge $dev_size ]]; then
        error "Not enough space to create ${dev_part} of size {$size}MB"
        exit 1
    fi

    info "Creating partition ${dev_part} for ${label} data: ${start}MB to ${end_num}MB"
    parted --wipesignatures -m --align=opt -s $dev unit MB mkpart primary ext4 ${start}MB ${end_num}MB
    [[ $? -ne 0 ]] && error "Failed to create partition ${dev_part}" && exit 1

    # Wait for the partitioning and device file creation to complete.
    # Spin until file command is successful or too many atttempts.
    retcode=1
    tries=5
    while [[ $retcode -ne 0 ]]; do
        file ${dev_part} > /dev/null
        retcode=$?
        ((tries--))
        [[ $tries -eq 0 ]] && error "Failed to access partition ${dev_part}." && exit 1
        info "Waiting on ${dev_part} creation to complete"
        sleep 1
    done

    info "Making ext4 filesystem on partition ${dev_part}"
    mke2fs -L ${label} -t ext4 ${dev_part}
    [[ $? -ne 0 ]] && error "Failed to make filesystem on ${dev_part}" && exit 1
}

unmount_partitions () {
    local dev=$1

    # Check for device partitions that are mounted
    readarray -t mount_list < <(mount | egrep "${dev}[0-9]+" | awk '{print $1,$3}')
    if [[ ${#mount_list[@]} != 0 ]]; then
        echo "The following partition on ${dev} are mounted:"
        #shellcheck disable=SC2068
        for i in ${!mount_list[@]}; do
            echo "    ${mount_list[$i]}"
        done
        error "Please unmount before attempting to run this format script again."
        exit 5
    fi
}

[[ $# -lt 2 ]] && usage && exit 1
[[ $# -gt 3 ]] && usage && exit 1
usb=$1
shift 1
iso_file=$1
shift 1
if [[ $# -eq 0 ]]; then
    cow_size=5000
else
    cow_size=$1
    shift 1
fi

# Validate the cow size is an integer > 1
if [[ $cow_size =~ [^0-9] ]]; then
    error "COW partition size was not specified as a number."
    echo ""
    usage
    exit 1
else
    if [[ $cow_size -lt 1 ]]; then
        error "COW partition must be at least 1MB in size."
        echo ""
        usage
        exit 1
    fi
fi


info "USB-DEVICE: $usb"
info "ISO-FILE:   $iso_file"
info "COW-SIZE:   ${cow_size}MB"

# Check to ensure the device exists
disk=${usb##*/}
if [[ $(lsblk | egrep "^${disk} " | wc -l) == 0 ]]; then
    error "Device ${usb} not found via lsblk."
    exit 1
fi

# check to ensure the ISO file exists
if [[ ! -r "$iso_file" ]]; then
    error "File ${iso_file} does not exist or is not readable."
    exit 1
fi

unmount_partitions $usb

# Check the downloaded ISO to ensure it is valid. Better
# to know now vs. when it fails the checkmedia during boot.
# Emit a warning if the command is not there
if ! eval command -v checkmedia; then
  info "Unable to validate ISO using 'checkmedia'."
else
  info "Validating ISO via checkmedia"
  checkmedia $iso_file
  [[ $? -ne 0 ]] && error "Failed checkmedia verification of $iso_file" && exit 1
fi

# Write new partition table
info "Writing new GUID partition table to ${usb}"
parted --wipesignatures -m --align=opt -s $usb mktable gpt

# Write the ISO to the USB raw device, creating an exact duplicate
# of the ISO image layout.
info "Writing ISO to $usb"
dd bs=1M if=$iso_file of=$usb conv=fdatasync
[[ $? -ne 0 ]] && error "Failed to write $iso_file to $usb" && exit 1

# The ISO's GPT geometry will not match the USB, the unallocated space will be hidden. Fix the headers.
sgdisk -e $usb

info "Scanning $usb for where to begin creating partition"
readarray -t parted_line < <(parted -s -m $usb unit MB print)
start_num=0
end_num=0
part_num=0
for i in "${!parted_line[@]}"; do

    # Parse the line into fields
    IFS=":" read -r -a fields <<< ${parted_line[$i]}

    # Line beginning with USB device name gives total size of drive
    if [[ "${fields[0]}" == "${usb}" ]]; then
        # Get disk dev size
        dev_size=${fields[1]%%MB*}


    # Error if three partitions found, no space for cow
    # and install data partitions
    elif [[ ${fields[0]} == 3 ]]; then
        error "Found 3 partitions, no partition left for install data"
        exit 1

    # Find end of each existing partition, install data partition will
    # begin after the end of the last partition.
    elif [[ ${fields[0]} == [12] ]]; then

        # Get end of partition
        start_num=${fields[2]%%MB*}

        # Start partition after end of last found partition
        ((start_num++))

        # Track what number next partition will be
        part_num=${fields[0]}
        ((part_num++))
    fi
done

# Create cow partition for liveCD
create_partition "$part_num" "cow" "$usb" "$start_num" "$cow_size"

temp_mount=$(mktemp -d)
mkdir "${temp_mount}/boot"
mkdir "${temp_mount}/iso"
mkdir "${temp_mount}/live"
mkdir "${temp_mount}/overlayfs"
mkdir "${temp_mount}/root"
mkdir "${temp_mount}/sqfs"
mount "${usb}3" "$temp_mount/root"
overlay_mount_label=livecd_overlay
LABEL=$(blkid -s LABEL -o value "${usb}1")
USB_ISO_UUID="$(blkid -s UUID -o value "/dev/disk/by-label/$LABEL")"
mkdir -v -p \
    "${temp_mount}/root/LiveOS/overlay-${LABEL}-${USB_ISO_UUID}" \
    "${temp_mount}/root/LiveOS/overlay-${LABEL}-${USB_ISO_UUID}/../ovlwork"
chmod -R 0755 "${temp_mount}/root/LiveOS/"
if [ -n "$RELEASE" ]; then
    mount "${usb}1" "${temp_mount}/boot"

    mount "${temp_mount}/boot/LiveOS/squashfs.img" "${temp_mount}/sqfs"
    mount -t overlay -o "lowerdir=${temp_mount}/sqfs,upperdir=${temp_mount}/root/LiveOS/overlay-${LABEL}-${USB_ISO_UUID},workdir=${temp_mount}/root/LiveOS/ovlwork" ${overlay_mount_label} "${temp_mount}/overlayfs"

    echo "Updating crucible from release archive."
    # Only run this if we're on an RPM system already.
    if eval command -v rpm >/dev/null 2>&1; then
        # Update crucible on the soon-to-be-running LiveCD. Ignore errors, if this doesn't work it isn't the end of the world.
        rpm -Uvh --root "${temp_mount}/overlayfs" "fawkes-${RELEASE}/rpm/sle-$(awk -F= '/VERSION=/{gsub(/["-]/, "") ; print tolower($NF)}' /etc/os-release)/$(uname -m)/crucible-"*".rpm" 2>/dev/null
    fi

    # Print the release into a file so it's readily available in the env.
    install -m 0755 -d "${temp_mount}/overlayfs/etc"
    echo "RELEASE=$RELEASE" >"${temp_mount}/overlayfs/etc/environment"

    # Create SSH directory, do not use `-D` as it only applies `-m` to child directory.
    echo "Installing any/all SSH keys from /root/.ssh/*.pub ... "
    install -m 0700 -d "${temp_mount}/overlayfs/root/"
    install -m 0700 -d "${temp_mount}/overlayfs/root/.ssh"

fi
umount "$overlay_mount_label"
umount "${temp_mount}/sqfs"
umount "${usb}1"
umount "${usb}3"
rm -rf "${temp_mount}"

# Create the install data partition for configuration data using
# remaining space
((part_num++))
((start_num=start_num+cow_size+1))
create_partition "$part_num" "data" "$usb" "$start_num" 0

if [ -n "${RELEASE}" ]; then
  archives="$(find . -name "fawkes-${RELEASE}*" -type f)"
  if [ -d "fawkes-${RELAESE}" ] || [ -z "$archives" ]; then

    temp_mount_data=$(mktemp -d)
    mount "${usb}4" "${temp_mount_data}"
    echo "Copying archive and extracted files to USB"
    if eval command -v rsync >/dev/null 2>&1 ; then
      rsync -rltDv "fawkes-${RELEASE}*" "${temp_mount}/"
    else
      echo "Falling back to cp command, rsync was not available"
      cp -pvr "fawkes-${RELEASE}*" "${temp_mount}/"
    fi
  else
    echo >&2 'Failed to find release archive or its extracted contents. Skipping archive copy.'
  fi
fi

info "Partition table for $usb"
parted -s $usb unit MB print

if command -v efibootmgr >/dev/null 2>&1; then
    hctl=$(lsblk $usb -o HCTL -n -d)
    if [ -n "$hctl" ]; then
        pci_bus=0x$(echo "$hctl" | awk -F':' '{print $1}')
        efi_entry=$(efibootmgr -v | grep -i "Pci($pci_bus")
        efi_number=$(echo "$efi_entry" | sed 's/^Boot//g' | awk '{print $1}' | tr -d '*' )
        if [ -n "$efi_number" ]; then
            echo "Resolved [$usb] as EFI entry $efi_number; setting BootNext to $efi_number"
            #efibootmgr -n "$efi_number" | grep "$efi_number" | grep -v BootOrder
        else
            echo >&2 "Failed to resolve the EFI entry for [$usb]; please boot to BIOS and manually select the USB from the boot menu."
        fi
    fi
else
    echo 'efibootmgr is not present; skipping setting BootNext'
fi
