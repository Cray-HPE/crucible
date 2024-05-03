#!/bin/bash
#
# MIT License
#
# (C) Copyright 2024 Hewlett Packard Enterprise Development LP
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
set -euo pipefail

REPO_URL=${REPO_URL:-'http://bootserver/nexus/repository'}

# Some distros (e.g. centos) use space delimited values in /etc/os-release for ID_LIKE, ensure we just grab
# the first entry.
OS="$(awk -F= '/ID_LIKE/{gsub("\"", ""); print $NF}' /etc/os-release | awk '{print $1}')"
if [ -z "${OS}" ]; then
    echo >&2 'Failed to detect OS from /etc/os-release'
    exit 1
else
    echo "Detected OS family: ${OS}"
fi

function update {
    echo 'Checking for crucible updates ... '
    case "${OS}" in
        suse)
            if ! zypper addrepo --gpgcheck-allow-unsigned "${REPO_URL}"'/fawkes-sle-${releasever_major}sp${releasever_minor}' fawkes-sle; then
                echo "Repository already added, or unavailable."
            fi

            if ! zypper addrepo --gpgcheck-allow-unsigned "${REPO_URL}/fawkes-noos" fawkes-noos; then
                echo "Repository already added, or unavailable."
            fi

            if ! zypper --no-gpg-checks up --no-confirm --auto-agree-with-licenses crucible; then
                echo "No updates found, or no repository was reachable."
            fi
            ;;
        *)
            echo >&2 'Unhandled OS; nothing to do'
            ;;
    esac
}

update
