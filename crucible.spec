#
# MIT License
#
# (C) Copyright 2022-2023 Hewlett Packard Enterprise Development LP
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

%define install_dir /usr/lib/%(echo $NAME)

# Define which Python flavors python-rpm-macros will use (this can be a list).
# https://github.com/openSUSE/python-rpm-macros#terminology
%define pythons %(echo $PYTHON_BIN)

%define conf_dir /etc/%{name}

# python*-devel is not listed because we do not ship the ability to rebuild our PIP package.
AutoReqProv: no
BuildRequires: python-rpm-generators
BuildRequires: python-rpm-macros
Requires: python%{python_version_nodots}-base
Name: %(echo $NAME)
BuildArch: %(echo $ARCH)
License: MIT License
Summary: A library for providing common functions to Cray System Management procedures and operations.
Version: %(echo $VERSION)
Release: 1
Source: %{name}-%{version}.tar.bz2
Vendor: Hewlett Packard Enterprise Development LP
Obsoletes: %{python_flavor}-%{name}

%description
A Python application for managing block devices
for use by an Operating system.

%prep
%setup

%build
%python_exec -m build --sdist
%python_exec -m build --wheel

%install

# Create our virtualenv
%python_exec -m venv --upgrade-deps %{buildroot}%{install_dir}

# Build a source distribution.
%{buildroot}%{install_dir}/bin/python -m pip install --disable-pip-version-check --no-cache ./dist/*.whl

# Remove build tools to decrease the virtualenv size.
%{buildroot}%{install_dir}/bin/python -m pip uninstall -y pip setuptools wheel

# Fix the virtualenv activation script, ensure VIRTUAL_ENV points to the installed location on the system.
sed -i -E 's:^(VIRTUAL_ENV=).*:\1'%{install_dir}':' %{buildroot}%{install_dir}/bin/activate
echo $RPM_BUILD_ROOT
sed -i 's:^#!.*$:#!%{install_dir}/bin/python:' %{buildroot}%{install_dir}/bin/%{name}

# Add the PoC mock files
cp -pr poc-mocks %{buildroot}%{install_dir}

install -D -m 755 -d %{buildroot}%{_bindir}
ln -snf %{install_dir}/scripts/lsnics.sh %{buildroot}%{_bindir}/lsnics
ln -snf %{install_dir}/bin/%{name} %{buildroot}%{_bindir}/%{name}

install -D -m 755 -d %{buildroot}%{conf_dir}
install -m 644 %{name}/network/ifname.yml %{buildroot}%{conf_dir}/ifname.yml

find %{buildroot}%{install_dir} | sed 's:'${RPM_BUILD_ROOT}'::' | tee -a INSTALLED_FILES
cat INSTALLED_FILES | xargs -i sh -c 'test -f $RPM_BUILD_ROOT{} && echo {} || test -L $RPM_BUILD_ROOT{} && echo {} || echo %dir {}' | sort -u > FILES

%clean

%files -f FILES
/usr/bin/%{name}
/usr/bin/lsnics
%config(noreplace) %{conf_dir}/ifname.yml
%doc README.adoc
%defattr(755,root,root)
%license LICENSE

%changelog
