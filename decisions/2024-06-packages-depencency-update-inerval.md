# Packages Dependency Update Interval

<!-- This template is inspired by
https://github.com/GoogleCloudPlatform/emblem/tree/main/docs/decisions -->

* **Status:** Approved
* **Last Updated:** 2024-06-18
* **Objective:** Endure our packages uses the latest compatible dependencies to streamline the update process and avoid dependencies conflicts.

## Context & Problem Statement

* Our packages have dependencies on each other and share external dependencies.

* Updating a package usually requires updating its dependent packages to maintain compatibility

## Goals
* Update package dependencies quarterly.
* Publish new package versions with updated dependencies.
### Non-goals

## Other considerations <!-- optional -->

## Considered Options <!-- optional -->

<!-- * ### Option 1 -->

<!-- * ### Option 2 -->

## Proposal Summary
This proposal recommends updating dependencies for all our packages quarterly and publishing new versions accordingly. 
The update sequence prioritizes core packages (at_client, at_client_mobile) followed by at_widgets packages in their dependency 
order (at_commons_flutter first). Refer to the package [hierarchy tree](https://github.com/atsign-foundation/at_mono/tree/trunk/docs/diagrams) 
for the update order.

## Proposal in Detail
We propose updating the dependencies of all our packages on a quarterly basis. New versions of the packages will be published 
where applicable. The update order is crucial to ensure successful updates and avoid conflicts. Here's the recommended sequence:
 * Core packages (at_client, at_client_mobile etc)
 * at_widgets packages (in dependency order, starting with at_commons_flutter)
   
For determining the exact update order, refer to the package [hierarchy tree](https://github.com/atsign-foundation/at_mono/blob/trunk/docs/diagrams/package_tree_hierarchical.svg).
### Expected Consequences <!-- optional -->
* Developers using our packages avoid dependency conflicts caused by outdated packages.
* Individual package updates won't be blocked by dependent packages.
