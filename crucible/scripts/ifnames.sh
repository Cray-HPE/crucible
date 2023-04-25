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
trap cleanup EXIT ERR
hsnID=0
lanID=0
mgmtID=0

management_vendor_ids=(
# Mellanox
'15b3'
# QLogic
'1077'
# Solarflare
'1924'
)

highspeed_network_ids=(
# Cassini
'17db:0501'
# ConnectX-5
'15b3:1017'
# ConnectX-6
'15b3:101b'
)

blessed_names=(
hsn
mgmt
lan
)


TEMP=$(mktemp -d)
RULES='80-ifname.rules'

function cleanup {
    rm -rf "${TEMP}"
}

function usage {
    cat << EOF
usage:

NOTE: If -o, -m, or -s is not present then there may be a prompt if /etc/udev/rules.d/$RULES already exists.

-o      Overwrite /etc/udev/rules/$RULES
-m      Merge all new rules with /etc/udev/rules/$RULES
-s      Skip writing udev rules to /etc/udev/rules/$RULES
-S      Skip renaming any interfaces (only generate udev rules)

To run this in a preview mode, use -s -S
EOF
}

overwrite=0
merge=0
skip_udev=0
skip_rename=0
install_location=/etc/udev/rules.d
while getopts "omsSi:" o; do
    case "${o}" in
        o)
            overwrite=1
            ;;
        m)
            merge=1
            ;;
        S)
            skip_udev=1
            ;;
        s)
            skip_rename=1
            ;;
        i)
            install_location="${OPTARG}"
            ;;
        *)
            usage
            return 2
            ;;
    esac
done
shift $((OPTIND-1))

mapfile -t nic_files < <(ls -1d /sys/bus/pci/drivers/*/0000\:*/net/*)
for nic_file in "${nic_files[@]}"; do
    up=0
    nic="$(basename "$nic_file")"
    mac="$(ethtool -P "$nic" | awk '{print $NF}')"

    pci_id="$(grep PCI_ID "$(dirname "$(dirname "$nic_file")")/uevent" | cut -f 2 -d '=')"
    vendor_id="${pci_id%:*}"

    if printf '%s|' "${highspeed_network_ids[@]}" | sed 's/|$//' | grep -q "${pci_id,,}" ; then
        nic_name="hsn${hsnID}"
        hsnID=$((hsnID + 1))
    elif printf '%s|' "${management_vendor_ids[@]}" | sed 's/|$//' | grep -q "${vendor_id,,}" ; then
        nic_name="mgmt${mgmtID}"
        mgmtID=$((mgmtID + 1))
    else
        nic_name="lan${lanID}"
        lanID=$((lanID + 1))
    fi

    printf 'SUBSYSTEM=="net", ACTION=="add", DRIVERS=="?*", ATTR{address}=="%s", ATTR{type}=="1", NAME="%s"\n' "${mac}" "${nic_name}" >> "${TEMP}/${RULES}"

    # Rename the NIC
    if [ "${skip_rename}" -eq 0 ]; then
        if [ "${nic}" == "${nic_name}" ]; then
            echo "Skipping rename, $nic is already named $nic_name"
        else
            echo "Renaming ${nic} to ${nic_name}"
            if ip l show "${nic}" | grep -qo UP ; then
                ip l s "${nic}" down
                up=1
            fi

            ip l s "${nic}" name ${nic_name}

            if [ "${up}" -ne 0 ]; then
                ip l s ${nic_name} up
            fi
        fi
    else
        echo "Skip rename (-S) was set; not renaming ${nic} to ${nic_name}"
    fi
done

if [ "${skip_udev}" -eq 0 ]; then
    if [ ! -d "${install_location}" ]; then
        mkdir -pv "${install_location}"
    fi
    if [ -f "${install_location}/${RULES}" ]; then
        echo "Detected a pre-existing rules file: ${install_location}/${RULES}"

        if [ "${overwrite}" -eq 1 ]; then

            mv -v "${TEMP}/${RULES}" "${install_location}/${RULES}"

        elif [ "${merge}" -eq 1 ]; then

            cat "${install_location}/${RULES}" "${TEMP}/${RULES}" | sort -u > "${TEMP}/${RULES}.merged"
            mv -v "${TEMP}/${RULES}.merged" "${install_location}/${RULES}"

        elif [ "${skip_udev}" -eq 1 ]; then

            echo '-S was given, not writing udev rules: '
            cat "${TEMP}/${RULES}"

        else

            read -r -p "Overwrite, merge, or skip touching the original udev file? [o/m/s]:" response
            case "$response" in
                [oO])
                    echo 'Overwriting ... '
                    mv "${TEMP}/${RULES}" "${install_location}/${RULES}"
                    ;;
                [mM])
                    echo 'Merging ... '
                    cat ${install_location}/${RULES} "${TEMP}/${RULES}" | sort -u | tee "${TEMP}/${RULES}.merged"
                    mv "${TEMP}/${RULES}.merged" "${install_location}/${RULES}"
                    ;;
                [sS])
                    echo 'Skipping ... old udev rules are still in place'
                    ;;
                *)
                    echo "Received response [$response], exiting ... "
                    return 0
                    ;;
            esac
        fi
    else
        mv -v "${TEMP}/${RULES}" "${install_location}/${RULES}"
    fi
else
    echo 'Skip udev rules (-s) was set; not overwriting udev rules with generated rules:'
    cat "${TEMP}/${RULES}"
fi

echo 'Done'
