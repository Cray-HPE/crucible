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
set -e

function usage() {
cat << 'EOF'
Prints PCI Vendor and Device IDs for network devices.
EOF
}

while getopts "hCPp:" o; do
    case "${o}" in
        h)
            usage
            exit 0
            ;;
        *)
            :
            ;;
    esac
done
shift $((OPTIND-1))

mapfile -t nics < <(ls -1d /sys/bus/pci/drivers/*/*/net/*)

if [ "${#nics[@]}" -eq 0 ]; then
    echo >&2 'No NICs detected in /sys/bus/pci/drivers/'
    exit 1
fi

printf '% -6s % -4s % -4s \n' 'Name' 'VID' 'DID'
for nic in "${nics[@]}"; do
    DID="$(awk -F: '/PCI_ID/{gsub("PCI_ID=","");print $NF}' "$(dirname "$(dirname "${nics[0]}")")/uevent")"
    VID="$(awk -F: '/PCI_ID/{gsub("PCI_ID=","");print $1}' "$(dirname "$(dirname "${nics[0]}")")/uevent")"
    printf '% -6s % -4s % -4s \n' "$(basename "$nic")" "${VID}" "${DID}"
done
