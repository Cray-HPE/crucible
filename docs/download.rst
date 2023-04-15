Downloading Crucible
====================

Downloading the crucible app
----------------------------

.. note::
   The RPM can be fetched directly from GitHub or from PIP.

pip
^^^

At this time, `crucible` is not uploaded to pypi or a private registry but it can be installed from its VCS source.

Install using `pip`

.. note::
   Note that the blocks below use `@main`, if you'd like to target a specific version you may use a branch name, git-tag, or git-hash instead.

* Without HTTP proxy

  .. code-block:: shell

        python3 -m pip install git+https://github.com/Cray-HPE/crucible.git@main
        crucible --version

* With HTTP proxy

  .. code-block:: shell

        python3 -m pip --proxy=http://hpeproxy.its.hpecorp.net:443 install git+https://github.com/Cray-HPE/crucible.git@main
        crucible --version

Artifactory
^^^^^^^^^^^

#. Set Credentials and the crucible artifact version

   .. code-block:: shell

        version='0.0.1a1'

   .. code-block:: shell

        ARTIFACTORY_USER=

   .. code-block:: shell

        ARTIFACTORY_TOKEN=

#. Download the Crucible application

   .. note::
      Note if you are using a different machine to download these artifacts, then set the `os` to the machine you plan on switching to a hypervisor.

      .. code-block:: shell

            os=15sp4

      Otherwise run this to auto-set the `os`

      .. code-block:: shell

            os="$(awk -F= '/VERSION=/{gsub(/["-]/, "") ; print tolower($NF)}' /etc/os-release)"

   * Without an HTTP proxy

     .. code-block:: shell

           curl -O "https://${ARTIFACTORY_USER}:${ARTIFACTORY_TOKEN}@artifactory.algol60.net/artifactory/csm-rpms/hpe/unstable/sle-${os}/crucible/noarch/crucible-${version}-1.noarch.rpm"

   * With an HTTP proxy

     .. code-block:: shell

           curl --proxy http://hpeproxy.its.hpecorp.net:443 -O "https://${ARTIFACTORY_USER}:${ARTIFACTORY_TOKEN}@artifactory.algol60.net/artifactory/csm-rpms/hpe/unstable/sle-${os}/crucible/noarch/crucible-${version}-1.noarch.rpm"

Downloading the Hypervisor Image
--------------------------------

Ideally run these commands from the server you want to setup as a hypervisor.

#. Set credentials

   .. code-block:: shell

         ARTIFACTORY_USER=

   .. code-block:: shell

       ARTIFACTORY_TOKEN=

#. Download the Hypervisor ISO

   * Without an HTTP proxy

     .. code-block:: shell

         curl -O "https://${ARTIFACTORY_USER}:${ARTIFACTORY_TOKEN}@artifactory.algol60.net/artifactory/csm-images/staging/hypervisor/hyperv-x86_64.iso"

   * With an HTTP proxy

     .. code-block:: shell

           curl --proxy http://hpeproxy.its.hpecorp.net:443 -O "https://${ARTIFACTORY_USER}:${ARTIFACTORY_TOKEN}@artifactory.algol60.net/artifactory/csm-images/staging/hypervisor/hyperv-x86_64.iso"
