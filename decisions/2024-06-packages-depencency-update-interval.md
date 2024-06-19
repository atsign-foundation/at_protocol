# Packages Dependency Update Interval

<!-- This template is inspired by
https://github.com/GoogleCloudPlatform/emblem/tree/main/docs/decisions -->

* **Status:** Draft
* **Last Updated:** 2024-06-19
* **Objective:** Ensure our packages uses the latest compatible dependencies
to streamline the update process and avoid dependency conflicts.

## Context & Problem Statement

* Our packages have dependencies on each other and share external
dependencies.
* Updating a package usually requires updating its dependent packages to
maintain compatibility.

## Goals

* Ensure that Atsign packages stay broadly compatible with other packages
that developers are likely to be using.
* Establish a regular cadence for checking and updating dependencies.

### Non-goals

* Insecure dependencies - these will be addressed more urgently.
* Whether to fork abandoned dependencies.

## Other considerations

* Dependency review gives us the opportunity to consider whether we should
continue using a dependency or consider an alternative.

## Considered Options

* Initial suggestion was every six months.
* After some discussion in arch call it was decided to (initially) go with
three months (quarterly).

## Proposal Summary

This proposal recommends reviewing and updating dependencies for all our
packages quarterly and publishing new versions accordingly. The update
sequence prioritizes core packages (at_client, at_client_mobile) followed
by at_widgets packages in their dependency order (at_commons_flutter first).
Refer to the package
[hierarchy tree](https://github.com/atsign-foundation/at_mono/tree/trunk/docs/diagrams)
for the update order.

## Proposal in Detail

On a querterly basis:

We propose reviewing the dependencies of all our packages on a quarterly
basis, and updating where necessary. New versions of the packages will be
published where applicable. The update order is crucial to ensure successful
updates and avoid conflicts. Here's the recommended sequence:
* Core packages (at_client, at_client_mobile etc)
* at_widgets packages (in dependency order, starting with at_commons_flutter)

For determining the exact update order, refer to the package
[hierarchy tree](https://github.com/atsign-foundation/at_mono/blob/trunk/docs/diagrams/package_tree_hierarchical.svg).

### Expected Consequences <!-- optional -->

* Developers using our packages avoid dependency conflicts caused by outdated packages.
* Individual package updates won't be blocked by dependent packages.
