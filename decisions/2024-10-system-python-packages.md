# System Python Packages

* **Status:** Approved
* **Last Updated:** 2024-10-02
* **Objective:** Our approach for installing additional Python packages for use
by our automation scripts.

## Context & Problem Statement

Since Debian 12 (including Ubuntu 24.04 and Raspberry Pi OS 'Bookworm') the
system Python is configured in such a way that packages can't be installed
using `pip`. This is done to ensure that system scripts have a correct set
of underlying dependencies.

```text
error: externally-managed-environment

× This environment is externally managed
╰─> To install Python packages system-wide, try apt install
    python3-xyz, where xyz is the package you are trying to
    install.

    If you wish to install a non-Debian-packaged Python package,
    create a virtual environment using python3 -m venv path/to/venv.
    Then use path/to/venv/bin/python and path/to/venv/bin/pip. Make
    sure you have python3-full installed.

    If you wish to install a non-Debian packaged Python application,
    it may be easiest to use pipx install xyz, which will manage a
    virtual environment for you. Make sure you have pipx installed.

    See /usr/share/doc/python3.12/README.venv for more information.

note: If you believe this is a mistake, please contact your Python
installation or OS distribution provider. You can override this, at the risk
of breaking your Python installation or OS, by passing --break-system-packages.
hint: See PEP 668 for the detailed specification.
```

Many additional Python packages are available as apt packages, and can be
installed with `python3-` as a prefix for their Python Package Index (PyPI)
package name e.g. `apt install python3-dnspython`.

But a number of packages that we use, most notablely the google-cloud-*
packages aren't packaged for apt. This leaves us with a choice of using pip
with the `--break-system-packages` flag, or switching to using Python
virtual environments (venvs).

## Goals

Determine a way of installing the packages we need that causes minimal
disruption to how we deploy and manage scripts, whilst preserving the
integrity of the system Python dependencies.

## Considered Options

* ### Continue using `pip` (along with `--break-system-packages`)

This approach carries on with our past practices, with the wrinkle that we
acknowledge some risk that the additional packages we install might
introduce an updated transitive dependency that could break system scripts.

After evaluation of the `google-cloud-compute` and `google-cloud-pubsub`
dependencies it was determined that they were unlikely to cause breakage to
the system dependencies.

* ### Use Python virtual environments

This would require that we first create the required virtual environment
on each machine, and also modify all of our scripts to call that virtual
environment.

* ### Use uv

[uv](https://docs.astral.sh/uv/) is a Rust based tool for Python package
management. `uv run` can make use of of dependency metadata in a script
to ensure that the required dependencies are available. Scripts can be
modified to use a `#!/bin/env uv run -q` shebang so that `uv run` is
invoked.

Unfortunately uv isn't yet at 1.0.0 and so isn't considered production ready.

## Proposal Summary

We will continue to install packages that aren't packaged for apt using `pip`
and the `--break-system-packages` flag.

## Proposal in Detail

Wherever possible dependencies will be installed using their apt package.
e.g. `python3-dnspython` and `python3-dotenv`.

Where necessary additional dependencies such as `google-cloud-compute` and
`google-cloud-pubsub` will be installed with `pip` and the
`--break-system-packages` flag.

Any new dependencies that we introduce to the production environment will
need to be evaluated to determine whether they're likely to cause actual
breakage to system packages.

### Expected Consequences

We do not expect the packages that we presently use to cause any breakage
to system packages.

We will continue to monitor the development of uv with a view to adopting
the `uv run` approach once it has passed 1.0.0.
