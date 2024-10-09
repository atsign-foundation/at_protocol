# Python Deprecation

* **Status:** Approved
* **Last Updated:** 2024-10-09
* **Objective:** Our approach for deprecating support for Python releases.

## Context & Problem Statement

Over time Python releases progress through a defined
[development cycle](https://devguide.python.org/developer-workflow/development-cycle/#devcycle):

* feature: new features, bugfixes, and security fixes are accepted.
* prerelease: feature fixes, bugfixes, and security fixes are accepted for
the upcoming feature release.
* bugfix: bugfixes and security fixes are accepted, new binaries are still
released. (Also called maintenance mode or stable release)
* security: only security fixes are accepted and no more binaries are
released, but new source-only versions can be released
* end-of-life: release cycle is frozen; no further changes can be pushed to it.

This document deals with how we treat end-of-life Python versions that we've
previously supported in things like our Python SDK
[atPython](https://github.com/atsign-foundation/at_python)

At the time of writing Python 3.13 has just been released as stable, meaning
that Python 3.8 is now end-of-life. atPython has supported Python from 3.8.1

## Goals

Articulate an approach that balances customer expectations for continuing
support with the practicalities of dealing with software that has passed
end of life.

### Non-goals

## Considered Options

* ### Immediate deprecation of end-of-life versions

We would immediately remove old Python versions from testing, and bump
`pyproject.toml` to specify the oldest version getting security fixes.

* ### Announced grace period

When a Python version becomes end of life we will announce a grace period
(say 6 months) during which we will still attempt best efforts support.

That best efforts support will be conditional upon key dependencies
continuing to support the end-of-life version.

## Proposal Summary

A 6 month grace period.

## Proposal in Detail

When a release reaches end-of-life we will post a note on the accompanying
README.md to declare the grace period. Following the end of the grace
period the end-of-life version will be removed from the test matrix and
the package will be bumped to require the oldest security fixes version.

### Expected Consequences

We will have periods where there is a new bugfix release added to our test
matrix without the old end-of-life version being removed, which will extend
the time taken for tests to run (and the likelyhood of flake failures).
