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
STORE=/vms/storeA
MGMTCLOUD="${STORE}/cloud-init/management-vm"
INTERFACE=lan0
SSH_KEY=/root/.ssh/
DEPLOYMENT_SSH_KEY_TYPE=ed25519

SITE_CIDR=''
SITE_DNS=()
GATEWAY=''
SYSTEM_NAME=''

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
-I      IP address to use for the management VM's external interface
-d      DNS servers (a comma delimited string) to use
-S      System name
-g      Gateway IP for the default route
EOF
exit 0
}

while getopts ":rc:s:i:I:d:S:g:" o; do
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
        I)
            SITE_CIDR="${OPTARG}"
            ;;
        d)
            IFS=$',' read -ra SITE_DNS <<< "${OPTARG}"
            unset IFS
            ;;
        S)
            SYSTEM_NAME="${OPTARG}"
            ;;
        g)
            GATEWAY="${OPTARG}"
            ;;
        *)
            usage
            ;;
    esac
done
shift $((OPTIND-1))

if [ "$RESET" -eq 1 ]; then
    virsh destroy management-vm 2>/dev/null || echo 'Domain already destroyed.'
    virsh undefine management-vm 2>/dev/null || echo 'Domain already undefined.'
    virsh vol-delete --pool management-pool management-vm.qcow2 2>/dev/null || echo 'Volume already deleted.'
    virsh pool-destroy management-pool 2>/dev/null || echo 'Pool already destroyed.'
    virsh pool-undefine management-pool 2>/dev/null || echo 'Pool already undefined.'
    virsh net-destroy isolated 2>/dev/null || echo 'Isolated network already destroyed. '
    virsh net-undefine isolated 2>/dev/null || echo 'Isolated network already undefined.'
    echo -n "Restoring ${BOOTSTRAP} files ... "
    cp -p "/run/rootfsbase/${BOOTSTRAP}/meta-data" "${MGMTCLOUD}/meta-data" || true
    cp -p "/run/rootfsbase/${BOOTSTRAP}/user-data" "${MGMTCLOUD}/user-data" || true
    cp -p "/run/rootfsbase/${BOOTSTRAP}/network-config" "${MGMTCLOUD}/network-config" || true
    cp -p "/run/rootfsbase/${BOOTSTRAP}/domain.xml" "${BOOTSTRAP}/domain.xml" || true
    echo 'Done'
    echo -n "Removing $MGMTCLOUD ... "
    rm -fr "${MGMTCLOUD}"
    echo 'Done'
    echo -n "Removing SSH host signatures ... "
    ssh-keygen -R management-vm.local >/dev/null 2>&1 || true
    ssh-keygen -R management-vm >/dev/null 2>&1 || true
    echo 'Done'
    echo "Management VM was purged, bootstrap files were reset."
    exit 0
fi

mkdir -p "${MGMTCLOUD}"
cp -p "$BOOTSTRAP/meta-data" "${BOOTSTRAP}/user-data" "${BOOTSTRAP}/network-config" ${MGMTCLOUD}

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

SSH_TEMP="$(mktemp -d)"
ssh-keygen -q -t $DEPLOYMENT_SSH_KEY_TYPE -N '' -C 'deployment_id' -f "$SSH_TEMP/deployment_id" <<< y >/dev/null 2>&1
yq -i eval '(.ssh_keys.'"$DEPLOYMENT_SSH_KEY_TYPE"'_private = "'"$(sed '$a\' "$SSH_TEMP/deployment_id")"'")' "${MGMTCLOUD}/user-data"
yq -i eval '(.ssh_keys.'"$DEPLOYMENT_SSH_KEY_TYPE"'_public = "'"$(sed '$a\' "$SSH_TEMP/deployment_id.pub")"'")' "${MGMTCLOUD}/user-data"
yq -i eval '.runcmd += ["cp -p /etc/ssh/ssh_host_'"$DEPLOYMENT_SSH_KEY_TYPE"'_key /root/.ssh/id_'"$DEPLOYMENT_SSH_KEY_TYPE"'"]' "${MGMTCLOUD}/user-data"
yq -i eval '.runcmd += ["cp -p /etc/ssh/ssh_host_'"$DEPLOYMENT_SSH_KEY_TYPE"'_key.pub /root/.ssh/id_'"$DEPLOYMENT_SSH_KEY_TYPE"'.pub"]' "${MGMTCLOUD}/user-data"
yq -i eval '.runcmd += ["sed -i'\'''\'' '\''$a\\'\'' /root/.ssh/id_'"$DEPLOYMENT_SSH_KEY_TYPE"'"]' "${MGMTCLOUD}/user-data"
yq -i eval '.runcmd += ["sed -i'\'''\'' '\''$a\\'\'' /root/.ssh/id_'"$DEPLOYMENT_SSH_KEY_TYPE"'.pub"]' "${MGMTCLOUD}/user-data"
yq -i eval '.runcmd += ["ssh-keyscan -H hypervisor.local hypervisor >> /root/.ssh/known_hosts 2>/dev/null"]' "${MGMTCLOUD}/user-data"
sed -i'' '/deployment_id$/d' /root/.ssh/authorized_keys
cat "$SSH_TEMP/deployment_id.pub" >> /root/.ssh/authorized_keys
rm -rf "$SSH_TEMP"

if virsh pool-define-as management-pool dir --target "${STORE}/pools/fawkes-management-storage-pool"; then
    virsh pool-start --build management-pool
    virsh pool-autostart management-pool

    # Hack around the capacity. The alloc ends up being .02 GB higher than the capacity, and after we vol-upload the capacity drops to ~20.
    # We can't set the capacity to CAPACITY afterwards due to the ALLOC being .02 higher, so we just set the CAPACITY to be minus one beforehand.
    # This way, the ending capacity will match what the user specified.
    virsh vol-create-as --pool management-pool --name management-vm.qcow2 "$((CAPACITY - 1))G" --prealloc-metadata --format qcow2
    management_vm_image=''
    management_vm_image="$(find /vms/store0/assets -name "management-vm*.qcow2")"
    virsh vol-upload --sparse --pool management-pool management-vm.qcow2 --file "${management_vm_image}"
    virsh vol-resize --pool management-pool management-vm.qcow2 "${CAPACITY}G"
fi
virsh net-define "${BOOTSTRAP}/isolated.xml"
virsh net-start isolated || echo 'Already started'
virsh net-autostart isolated || echo 'Already auto-started'

yq --xml-attribute-prefix='+@' -i -o xml -p xml eval '.domain.devices.interface |= [
{"+@type": "network", "source": {"+@network": "isolated"}, "model": {"+@type": "virtio"}},
{"+@type": "direct", "source": {"+@dev": "bond0", "+@mode": "bridge"}, "model": {"+@type": "virtio"}},
{"+@type": "direct", "source": {"+@dev": "'"$INTERFACE"'", "+@mode": "bridge"}, "model": {"+@type": "virtio"}}
]' "${BOOTSTRAP}/domain.xml"

if [ -z "$SYSTEM_NAME" ]; then
    :
else
    yq -i eval '.local-hostname = "'"$SYSTEM_NAME"'-management"' "${MGMTCLOUD}/meta-data"
fi
yq -i eval '.network.ethernets.eth1 = {"dhcp4": false, "dhcp6": false, "mtu": 9000, "addresses": ["10.1.1.1/16"]}' "${MGMTCLOUD}/network-config"
if [ -z "$SITE_CIDR" ]; then
    echo >&2 'No SITE_CIDR was provided, the external interface will not be assigned an IP address and will rely on DHCP.'
    yq -i eval '.network.ethernets.eth2 = {"dhcp4": true, "dhcp6": false, "mtu": 1500}' "${MGMTCLOUD}/network-config"
else
    yq -i eval '.network.ethernets.eth2 = {"dhcp4": false, "dhcp6": false, "mtu": 1500, "addresses": ["'"${SITE_CIDR}"'"]}' "${MGMTCLOUD}/network-config"
fi
if [ -z "$GATEWAY" ]; then
    echo >&2 'No GATEWAY was provided, no default route will be set up! This may have undesirable consequences.'
else
    yq -i eval '.network.ethernets.eth2.routes += [{"to": "0.0.0.0/0", "via": "'"$GATEWAY"'"}]' "${MGMTCLOUD}/network-config"
fi
if [ "${#SITE_DNS[@]}" -eq 0 ]; then
    echo >&2 'No SITE_DNS was provided, no static nameservers will be configured.'
else
    for dns in "${SITE_DNS[@]}"; do
        yq -i eval '.network.ethernets.eth2.nameservers.addresses += ["'"$dns"'"]' "${MGMTCLOUD}/network-config"
    done
fi

xorriso -as genisoimage \
    -output "${MGMTCLOUD}/cloud-init.iso" \
    -volid CIDATA -joliet -rock -f \
    "${MGMTCLOUD}/user-data" \
    "${MGMTCLOUD}/meta-data" \
    "${MGMTCLOUD}/network-config"
yq --xml-attribute-prefix='+@' -o xml -i -p xml eval '(.domain.devices.disk.[] | select(.source."+@file" == "*cloud-init.iso").source) |= {"+@file": "'"${MGMTCLOUD}/cloud-init.iso"'"}' "${BOOTSTRAP}/domain.xml"
yq --xml-attribute-prefix='+@' -o xml -i -p xml eval '(.domain.devices.filesystem | select(.target."+@dir" == "assets").source) |= {"+@dir": "/vms/store0/assets"}' "${BOOTSTRAP}/domain.xml"
virsh create "${BOOTSTRAP}/domain.xml"

echo -en 'Management VM created ... observe startup with:\n\n'
echo -en '\tvirsh console management-vm\n\n'
echo 'Waiting for SSH to become available ... '
plural='' # do not set to 0, or the ${plural:+s} won't work. Must be empty.
seconds=1
while ! ssh-keyscan -T 1 -H management-vm.local management-vm >> /root/.ssh/known_hosts 2>/dev/null ; do
    if [ "$seconds" -gt 1 ]; then
        plural=1
    fi
    echo -n '.'
    seconds="$(("$seconds" + 1))"
    sleep 1
done
echo "'Waited for ${seconds} second${plural:+s}"
echo -e '\nManagement VM is online.'
if [ -n "$SITE_CIDR" ]; then
    echo -en 'Login to the management-vm externally with:\n\n'
    echo -en "\tssh ${SITE_CIDR%/*}\n\n"
fi
