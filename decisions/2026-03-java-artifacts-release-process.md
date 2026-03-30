# Java Artifacts Release Process

* **Status:** Draft
* **Last Updated:** 2026-03-30
* **Objective:** Agree release mechanism and any associated procedures

## Context & Problem Statement

The repo [at_java](https://github.com/atsign-foundation/at_java) contains the Java SDK, libraries,
tools and samples. This repo is a multi-module maven project and, as per the maven
norms, each module creates at most a single artifact.

| Directory / Module | Artifact       | Artifact Type | Maven Central Deploy |
|--------------------|----------------|---------------|----------------------|
| root               | at_java_parent | pom           | ✓ (snapshots)        |
| at_client          | at_client.jar  | (library) jar | ✓ (snapshots)        |
| at_shell           | at_shell.jar   | (fat) jar     | ✓ (snapshots)        |
| at_util            | at_util.jar    | (library) jar | ✓ (snapshots)        |
| examples           |                |               |                      |

We currently have a GitHub workflow that will publish to Maven Central this
is triggered by pushes to the main branch (trunk) and will pick up the pom
version, which because this is trunk will always -SNAPSHOT.

The repo currently has good test coverage based on unit and integration tests.
The overall coverage is 80%, however the coverage for the core SDK is much
higher. The project pom enforces that coverage cannot be below 80% (this will
be raised to 90% once unit tests for the registration API have been created).

The Java SDK is now suitably mature that we want to publish release versions
of the artifacts to Maven Central.

The purpose of this document to agree how that mechanism should work.

## Goals

1. Define an automated process that performs the following.
   * Check release candidate builds and passes all the unit and integration tests.
   * Transition the maven pom versions to the release version.
   * Update a CHANGELOG based on the git commits.
   * Generate a SBOM (Software Bill of Materials).
   * Generate a SLSA attestations (Supply-chain Levels for Software Artifacts).
   * Add a git tag which corresponds to the release version.
   * Publish the appropriate artifacts to Maven Central.
   * Upload the SBOM, SLSA attestations to GitHub.
   * Transition the maven pom versions to the next snapshot version.
2. Agree how a release is triggered.
3. Agree the supported version scheme.

### Non-goals

## Other considerations

## Considered Options

## Proposal Summary

### Release Versions / Tags

Release versions should be limited to the **major.minor.patch** format
where each of those values is an integer. The convention for incrementing those
values is as follows.

| Component | Description                               | Example        |
|-----------|-------------------------------------------|----------------|
| Major     | Significant and possibly breaking changes | 1.1.0 -> 2.0.0 |
| Minor     | Periodic release of non breaking changes  | 1.1.0 -> 1.2.0 |
| Patch     | Small or Break fix change                 | 1.1.0 -> 1.1.1 |

The git tags used to denote releases will correspond to the release version
prefixed with a lowercase v. e.g. **v1.1.0**.

### Release Initiation

Releases will be triggered by performing a git tag on the release branch.
For Major and Minor release this will typically be trunk. Patch releases
will typically be based off no trunk branches (branched at the point the
corresponding major / minor release was tagged).

### Release Mechanics

The steps involved in generating a release will be performed by a new GitHub
action workflow.

## Proposal in Detail

The workflow needs to make changes to the repo and we want the version
tag to be applied to the commit that includes those changes. This means
the tag which initiates the release is not the version tag. It's a separate
tag which is ultimately deleted if the workflow succeeds.

The workflow will be configured to be triggered on tags that are prefixed
with release_ and correspond to the major minor patch version tuple,
i.e. the workflow will include this configuration.

```yml
on:
  tags:
    - release_*_*_*
```

The workflow will then perform the following steps.

1. Parse the release version from the tag (ensuring that major, minor and patch are
   integers).
2. Check that we don't already have a corresponding version tag.
3. Checkout the workflow branch.
4. Set up Java with maven central server configuration (required for publish).
5. Set up the virtual environment for integration tests.
6. Configure Git for subsequent commits.
7. Calculate the next release version (this will be a -SNAPSHOT version).
   If the workflow branch is trunk then this will be **major.minor+1.0**. If the
   workflow branch is not trunk then this will be **major.minor.patch+1**.
8. Run maven versions plugin to change the pom versions to the release version.
9. Update references to the new version and next version in the README. 
10. Update the CHANGELOG from the git history (prepend the generated output to the 
    existing file).
11. Run maven clean deploy this will
    * run all tests
    * javadoc
    * package
    * sign the artifacts
    * upload to central
12. Commit the changes.
13. Create a tag for the version (vx.y.z).
14. Run maven versions plugin to change the pom versions to the next release version.
15. Commit the changes.
16. Push the commits and tag.
17. Delete the release_ tag (release_x_y_z).
18. Generate the SBOM and SLSA (per artifact) and upload to GitHub release using.

### Expected Consequences

1. Any failure prior to the upload to central can be recovered by, deleting the release_x_y_z
   tag, fixing the issue on the release branch and re-tagging with release_x_y_z.
2. A failure once Maven Central has validated and publish the artifacts will prevent
   the release workflow from being re-run. In circumstances where that is the desired
   object this will require a support ticket for maven central, requested that they delete
   the artifacts.

