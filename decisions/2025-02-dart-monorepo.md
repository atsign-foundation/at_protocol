# Dart Client Packages Monorepo

<!-- This template is inspired by
https://github.com/GoogleCloudPlatform/emblem/tree/main/docs/decisions -->

* **Status:** Draft <!--/ Approved / Rejected / Superseded-->
* **Last Updated:** 2025-02-12
* **Objective:** To solve issues with client package resolution & management in
  Dart.

## Context & Problem Statement

Dependency management of all of the client packages, has always been a problem
for us. In addition, some packages don't get upgraded when they need to because
of an upstream change.

See also [Package Upgrade Solutions](2025-02-package-upgrade-solution.md).

The following is a list of reasons why we have changed to focus on a monorepo
solution:

* Melos' next version (v7) will use pub workspaces, which effectively means no
  more upgrades to melos unless we migrate to a monorepo (or do something hacky)
* We have encountered situations where a Dart dependency is upgraded to a range
  outside of a pinned dependency in the Flutter SDK
  * As stated in the Package Upgrade Solutions document, if the Flutter team
    cannot trust themselves to make non-breaking changes to dependencies, then
    it's probably best we don't either. (i.e. dependency overrides is not a
    sane solution)
* Centralizing package resolution with pub workspaces allows us to ensure that
  our packages in client space always remain compatible with each other
  * This also means that updates to dependency versions can be done safely
    through CI/CD without fear of incompatibilities. (If the job fails then
    that means an incompatibility was introduced and manual intervention can
    be performed)

## Goals

To verify that migrating to pub workspaces is a sane solution.
To introduce an approach which allows us to migrate with the least amount of:
* effort
* impact to other in-progress changesets

### Non-goals

To continue hacking our way around community standards.

## Other considerations <!-- optional -->

See [Package Upgrade Solutions](2025-02-package-upgrade-solution.md).

* An attempt was made to solve resolution issues in at_mono, but the attempt
failed, any further efforts require non-standard modification to the Flutter
SDK in the CI workflows that use melos.

## Considered Options <!-- optional -->

* ### Option 1 - A monorepo which includes all of the Dart packages in at_mono

This includes packages from:

* at_client_sdk
* at_server
* at_libraries
* at_widgets
* at_services
* at_tools

The problem with this is that both at_server and at_client_sdk have components
which will be particularly troublesome to migrate.

A sub option that was considered is migrating everything into at_server.

* ### Option 2 - Make at_client_sdk the monorepo, leave at_server alone

Instead, keep at_server separate, and make at_client_sdk the monorepo.

Reasons for this:
* at_client_sdk and packages it depends on as well as packages that depend on it
  are where the conflicts are happening.
* at_server is complex and has a different release cycle than the rest of the
  packages
* If at_client_sdk were the monorepo, then it would contain only the packages
  that are relevant to external developers
* Because both at_server and at_client_sdk are the troublesome repos to migrate,
  we can make at_client_sdk the monorepo itself, meaning neither at_server or
  at_client_sdk need to be migrated.

Packages to migrate into at_client_sdk:
* at_libraries
* at_widgets
* at_tools (maybe)
* at_services (maybe)

## Proposal Summary

To migrate for any of the options we would do so in a way that preserves
git history.

## Proposal in Detail

This is a similar migration approach to the one that  has been previously used
to merge at_app_flutter from at_app into at_widgets before it was deprecated.

Legend:
* import repo - original source repo to have it's history imported
* monorepo - destination repo where the import repo will be added

1. In the import repo, create a new branch
1. Move the entire contents of the import repo into a subdirectory with a name
   that will not conflict with the monorepo's contents
   (using git renames or git filter-repo)
1. In the monorepo, add the import repo as a remote
   (named as `<new remote>` in later steps)
1. Fetch the new remote
1. Make a new branch in the monorepo to serve as the import changeset
1. Use git merge to import the import repo
   `git merge --allow-unrelated-histories <new remote>/<import repo branch>`
1. Remove `<new remote>`
1. Use git renames to move the contents of the temporary subdirectory to their
   new locations
1. Update any path names in workflows & tools which need to be updated
1. Raise a PR to merge this import branch into trunk

Once a repo has been imported successfully, it doesn't have to be added to the
pub workspace immediately. We can do this incrementally.

### Expected Consequences <!-- optional -->

* `dart pub upgrade` no longer introduces dependency conflicts elsewhere in our
  dependency tree.
* Package management and deployment becomes easier
* Changing something in an upstream dependency to address an issue in the
  current workspace becomes easier
  * You no longer have to first change the upstream dependency, then push it to
    git, then do a dependency override just to test/make a change in an upstream
    package. It's in the same repo, and locally linked, so it's easy.
