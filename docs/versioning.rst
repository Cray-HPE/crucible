Versioning
==========

The version is derived from Git by the ``setuptools_scm`` Python module and follows `PEP0440's <https://peps.python.org/pep-0440/#abstract>`_ version identification
and dependency specification for `final <https://peps.python.org/pep-0440/#final-releases>`_ and `pre <https://peps.python.org/pep-0440/#pre-releases>`_ releases.

.. note::
    All Git-Tags in this repository are prefixed with ``v``.

Classification
--------------

The items below denote how stable, pre-release, and unstable versions are classified through
version strings.

* **(stable) final release**: A git-tag following the ``X.Y.Z`` semver format is considered a final release version.

  .. code-block::

    # Format:
    # {tag}
    # X.Y.Z
    # X - Major
    # Y - Minor
    # Z - Micro (a.k.a. patch)
    0.1.2

* **(stable) post release**: A git-tag following the ``X.Y.Z.postN`` (where ``N`` is an integer), indicates a post-release.
  These are seldom used, and are strictly for handling documentation, packaging, or other meta
  updates after a release tag was already created where it isn't warranted to publish an
  entirely new release. ``1.0.0.post0`` and ``1.0.0`` are considered the same version in this repository. ``1.0.0.post1`` would
  produce an RPM with a release version of ``2`` (since our RPMs index their releases starting at ``1``).

  .. code-block::

        # Format:
        # {tag}
        # X.Y.Z.postN
        # X - Major
        # Y - Minor
        # Z - Micro (a.k.a. patch)
        # Z - Post release [1-9]+
        0.1.2.post1

* **(unstable) pre-release**: A git-tag with an alpha (``a``), beta (``b``), or release candidate (``rc``) annotation and an identification number ``N`` denotes a pre-release/preview.

  .. code-block::

        # Format:
        # {tag}[{a|b|rc}N]
        0.1.2a1
        0.1.2b1
        0.1.2rc1

* **(unstable) development**: Development builds **auto-increment** the micro version (the ``Z`` in ``X.Y.Z``) or pre-release version (the `N` in ``X.Y.Z{[a|b|rc]N}``), and
  then append a suffix based on whether the working directory was **clean**, **dirty**, or **mixed**.

  * **clean**: When the version shows an appended ``devN+{scm_letter}{revision_short_hash}``, that means there have been commits made since the previous git-tag.

    .. code-block::

        # Format:
        # {next_version}.dev{distance}+{scm_letter}{revision_short_hash}

        # If the previous git-tag was 0.1.2:
                   0.1.3.dev4+g818da8a

        # If the previous get-tag was a pre-release of 0.1.3a1:
                 0.1.3a2.dev4+g818da8a

  * **dirty**: When the version shows an appended ``.d{YYYYMMDD}`` datestamp, that means there were modified/uncommitted changes in the working directory when the application was built.

    .. code-block::

        # Format:
        # {next_version}.d(datestamp}

        # If the previous git-tag was 0.1.2:
                   0.1.3.d20230123

        # If the previous get-tag was a pre-release of 0.1.3a1:
                 0.1.2a2.d20230123

  * **mixed**: When the version shows a development tag with an appended datestamp, this means commits have been made but there were uncommitted changes present in the working directory when the application was built.

    .. code-block::

        # Format:
        # {next_Version}.dev{distance}+{scm_letter}{revision_short_hash}.d{datestamp}

        # If the previous git-tag was 0.1.2:
                   0.1.3.dev3+g3071655.d20230123

        # If the previous get-tag was a pre-release of 0.1.3a1:
                0.1.3a2.dev3+g3071655.d20230123

.. note::
    For more information about versioning, see `versioning scheme information <https://github.com/pypa/setuptools_scm/#default-versioning-scheme>`_.

Configuration
-------------

The ``setuptools_scm`` module is configured by ``pyproject.toml``.

.. note::
    For more information regarding configuration of ``setuptools_scm``, see `version number construction <https://github.com/pypa/setuptools_scm/#version-number-construction>`_.

Retrieving the Python Package Version at Runtime
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If at any point code within the module wants to print or be aware of the modules own version, it can. The following snippet demonstrates how to do this.

.. code-block:: python

    from importlib.metadata import version
    from importlib.metadata import PackageNotFoundError

    try:
        __version__ = version("crucible")
    except PackageNotFoundError:
        # package is not installed
        pass
