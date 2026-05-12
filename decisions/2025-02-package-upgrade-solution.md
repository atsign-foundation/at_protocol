# Package Upgrade Solutions

<!-- This template is inspired by
https://github.com/GoogleCloudPlatform/emblem/tree/main/docs/decisions -->

* **Status:** Superseded <!--/ Approved / Rejected / Superseded-->
* **Last Updated:** 2025-02-04
* **Objective:** Solve issues with dependency compatibility.

## Context & Problem Statement

The Flutter SDK pins packages instead of using the caret constraint to allow for
minor upgrades.

## Goals

To determine a viable package version resolution strategy that ensures all of
our dependencies remain up to date and compatible.

### Non-goals

Although this should be a goal, based on the state of the ecosystem, we should
not necessarily ensure that our upgrade strategy prevents breakage, but rather
test for when it does. There have consistently been breaking changes across
minor version bumps in the ecosystem, and if we want to keep packages up to date,
ensuring we receive security fixes when they come, we will have to accept the
reality of breaking changes occurring when the semver increase dictates otherwise.

## Other considerations <!-- optional -->

### Flutter SDK Pinned Packages

In the Dart SDK docs they mention the reason for package pins in the Flutter SDK
[here](https://github.com/dart-lang/sdk/blob/2ac59922d2e6ab5f62ceb8725ffad96cfd147c68/docs/Flutter-Pinned-Packages.md?plain=1#L13-L15).
This statement indicates that teams maintaining Flutter & Dart have no intention
of respecting semver, as they don't even trust themselves to respect it.
More elaboration on the consequences of this in the following options.

### at_mono resolution issues

at_mono depends on all major library packages in our ecosystem to ensure
compatibility, and lately the Flutter packages have been incompatible with the
Dart ones. The reason for this is that dependabot has bumped meta to `^1.16.0`
yet the latest stable flutter SDK has `flutter_test` pinned to `1.15.0`. This
is an ongoing issue that occurs as we upgrade dependencies across the ecosystem.

### Package tree version resolution tooling

Another thing to note is the differences between tooling options for maintaining
dependencies:

* [melos](https://melos.invertase.dev/)
* [dart workspaces](https://dart.dev/tools/pub/workspaces)

While on the surface these tools seem to resolve dependencies similarly, there
is one major distinction:

* melos allows packages to resolve dependencies independently, then attempts
  to link them locally by consolidating them on demand.
* dart workspaces aims to keep all package versions under its workspace in sync
  by resolving them centrally first.

Id est, melos resolutions starts locally then centralizes on bootstrap.
Dart workspace resolution starts centrally then the resolved versions are
localized to each package.

## Considered Options <!-- optional -->

* ### Option 1 - Monorepo + Dart workspaces

The ideal solution here would be to move all of our dependencies which need
to remain in sync into a monorepo. Then we can replace melos with a dart workspace.
Having both Flutter and Dart dependencies being resolved centrally means that the
Dart dependencies are never allowed to surpass the Flutter SDK's constraints.

Obviously, the problem with this solution is that it requires a massive migration,
and then we run into a bunch more problems with migrating:

* in progress changesets
* CI workflows
* Updating references to packages/repos
  * This likely means we would need to keep the old repos with submodules
    pointing to the new location of the dependency
* probably many more unforeseen issues.

Of course this solution is ideal for dependency resolution, but highly impractical
for all of the reasons mentioned above, as well as for the reasons we chose against
having a monorepo.

* ### Option 2 - Upgrade Flutter SDK dependencies during resolution

The next option would be to upgrade Flutter SDK dependencies during resolution.
The problem here is that our Dart packages still surpass the Flutter SDK. While
this realistically isn't a problem for app developers, it does lead to
inconsistencies between the allowed constraints in Dart vs Flutter packages.

The other problem here was mentioned above, which is that if the Google teams
don't trust themselves to respect semver. Then we shouldn't either. If we pick
this option, which would be the least amount of work to implement, it may create
future problems where our packages break due to breaking changes across minor
version increases in the Flutter SDK dependencies. Having acknowledged that,
this same scenario is already possible in all of our Dart packages which do
not depend on the Flutter SDK, so it will be a problem we have to face regardless
of whether we pick this option or not.

* ### Option 3 - Enforce a maximum lower bound on Dart package constraints

Dependabot causes a problem by upgrading dependencies in Dart packages to have
a higher minimum constraint than the pins in the Flutter SDK. This is because
the Flutter SDK packages are not included in the tree during resolution by
dependabot.

The way we could go about enforcing this, is by creating a tool to replace
dependabot which ensures that dependency constraints are no stricter than
being inclusive of the pins in the Flutter SDK.

## Proposal Summary

Three options of varying stability and effort required, see above.

## Proposal in Detail

In addition to the options above, there were two acceptable policies for
dependency resolution established during an architecture discussion.

1. Enforce that packages which do not depend on the Flutter SDK enforce
   minimum constraints which are inclusive of the pinned version in the Flutter
   SDK.
2. Relax the restriction on Flutter packages during resolution with melos.
   In the cases we've experienced, the pinned dependencies are transitive
   flutter_test dependencies. flutter_test is only ever used as a dev_dependency
   and thus it doesn't affect library consumer usage.

### Expected Consequences <!-- optional -->

Our dependency tree remains fully compatible and at_mono is able to run its
weekly analysis job successfully again.

---

## Update 2025-08-06

@xavierchanth: I've opted for pub workspaces, reasoning follows.

Having merged at_libraries into at_client_sdk a preferred solution became clear.
We often perform the following development cycles:

* Make changes to a package
* Update the version number, changelog, etc.
* Use dependency overrides with the git info for the package changes so that CI
  can be run.
* Upon CI passing, request initial approval

Upon initial approval:

* Remove the dependency overrides.
* Publish the packages
* Resubmit for review (since the dependency overrides removal commit was pushed)
* Upon final approval, merge

This particular development flow conflicted heavily with melos when I merged the
two repos. Melos doesn't have a good way to manage dependency overrides in a
single place. This is important, as we've currently got 15 packages post-merge,
and adding at_widgets would bring that number to 29. Anytime we need to raise
a constraint which forces us to raise the minimum at_commons version, we'd have
to create 28 dependency_overrides entries in order to get CI to run.

However, in further investigation with pub workspaces, because pub workspaces
does version resolution centrally, a single dependency_overrides block in the
workspace root's pubspec.yaml applies to the entire workspace.

For now, melos 6 is the latest stable, and melos 7 brings pub workspaces support
so I've dropped melos 7, since we don't really need it. If melos 7 comes out
with features which enhance our workflow we can reconsider it.
