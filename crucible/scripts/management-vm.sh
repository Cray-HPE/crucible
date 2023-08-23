#!/bin/bash
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
# TODO: Rewrite script in Python or Go.
set -euo pipefail

BOOTSTRAP=/srv/cray/bootstrap
CAPACITY=100
MGMTCLOUD=/vms/cloud-init/management-vm
INTERFACE=lan0
SSH_KEY=/root/.ssh/
RESET=0
error=0
required_programs=( "yq" "xorriso" "virsh" )
for required_program in "${required_programs[@]}"; do
    if ! command -v  >/dev/null 2>&1 ; then
        echo >&2 "$required_program is required but was not found in PATH."
        error=1
    fi
done
if [ "$error" -ne 0 ]; then
    exit 1
fi

function usage {
    cat << EOF
-c      CAPACITY of the management VM storage (interpreted in Gigabytes), defaults to 100.
-r      Resets the management VM. Destroys all volumes, pools, and the management virtual machine. Resets the cloud-init ISO.
-s      SSH_KEY path to install into the management VM's root user (default: /root/.ssh/id_rsa.pub)
-i      INTERFACE to use for the Management external network (default: lan0).
EOF
exit 0
}

while getopts ":rc:s:i:" o; do
    case "${o}" in
        c)
            CAPACITY="${OPTARG}"
            ;;
        r)
            RESET=1
            ;;
        i)
            INTERFACE="${OPTARG}"
            ;;
        s)
            SSH_KEY="${OPTARG}"
            ;;
        *)
            usage
            ;;
    esac
done
shift $((OPTIND-1))

if [ "$RESET" -eq 1 ]; then
    virsh destroy management-vm || echo 'Already destroyed ... '
    virsh vol-delete --pool management-pool management-vm.qcow2 || echo 'Volume already deleted ... '
    virsh pool-destroy management-pool || echo 'Pool already destroyed ... '
    virsh pool-undefine management-pool || echo 'Pool already undefined ... '
    virsh net-destroy isolated || echo 'Isolated network already destroyed ... '
    virsh net-undefine isolated || echo 'Isolated network already undefined ... '
    cp -p /run/rootfsbase/srv/cray/bootstrap/user-data "${MGMTCLOUD}/user-data"
    cp -p /run/rootfsbase/srv/cray/bootstrap/domain.xml "${BOOTSTRAP}/domain.xml"
    rm -f "${MGMTCLOUD}/cloud-init.iso"
    echo "Management VM was purged, bootstrap files were reset."
    exit 0
fi

mkdir -p "${MGMTCLOUD}"
cp -p "$BOOTSTRAP/meta-data" "${BOOTSTRAP}/user-data" ${MGMTCLOUD}

if [ -f "$SSH_KEY" ]; then
    yq -i eval '(.users.[] | select(.name = "root") | .ssh_authorized_keys) += "'"$(cat "$SSH_KEY")"'"' "${MGMTCLOUD}/user-data"
elif [ -d "$SSH_KEY" ]; then
    # Remove trailing slash for niceness.
    ssh_keys="$(realpath -s "$SSH_KEY")"
    for key in "$ssh_keys"/*.pub; do
        # For safety, ensure a new line is always at end of file.
        yq -i eval '(.users.[] | select(.name = "root") | .ssh_authorized_keys) += "'"$(sed '$a\' "${key}")"'"' "${MGMTCLOUD}/user-data"
    done
else
    echo >&2 "SSH Key at [$SSH_KEY] was not found."
    exit 1
fi
xorriso -as genisoimage \
    -output "${MGMTCLOUD}/cloud-init.iso" \
    -volid CIDATA -joliet -rock -f \
    "${MGMTCLOUD}/user-data" \
    "${MGMTCLOUD}/meta-data"

virsh pool-define-as management-pool dir --target /var/lib/libvirt/management-pool
virsh pool-build management-pool
virsh pool-start management-pool
virsh pool-autostart management-pool

virsh vol-create-as --pool management-pool --name management-vm.qcow2 --capacity "${CAPACITY}G" --format qcow2
management_vm_image=''
management_vm_image="$(find /vms/assets -name "management-vm*.qcow2")"
virsh vol-upload --pool management-pool management-vm.qcow2 "${management_vm_image}"

virsh net-define "${BOOTSTRAP}/isolated.xml"
virsh net-start isolated || echo 'Already started'
virsh net-autostart isolated || echo 'Already auto-started'

yq --xml-attribute-prefix='+@' -i -o xml -p xml eval '.domain.devices.interface |= [
{"+@type": "network", "source": {"+@network": "isolated"}, "model": {"+@type": "virtio"}},
{"+@type": "direct", "source": {"+@dev": "bond0", "+@mode": "bridge"}, "model": {"+@type": "virtio"}},
{"+@type": "direct", "source": {"+@dev": "'"$INTERFACE"'", "+@mode": "bridge"}, "model": {"+@type": "virtio"}}
]' "${BOOTSTRAP}/domain.xml"

virsh create "${BOOTSTRAP}/domain.xml"

cat << EOF
Management VM created ... observe its launch with:

    virsh console management-vm
EOF