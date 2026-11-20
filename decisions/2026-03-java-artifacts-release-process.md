# Java Artifacts Release Process

* **Status:** Draft
* **Last Updated:** 2026-03-30
* **Objective:** Agree release mechanism and any associated procedures

## Context & Problem Statement

The repo [at_java](https://github.com/atsign-foundation/at_java) contains the
Java SDK, libraries, tools and samples. This repo is a multi-module maven
project and, as per the maven norms, each module creates at most a single
artifact.

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

1. Agree the supported version scheme.
2. Define the mechanics for how a release happens

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

### Release Outputs

There are 3 types of outcomes from a release.

1. Artifacts that are uploaded to Maven Central.
2. Changes to the github repo. A commit that sets the pom
   versions to the release version (README and CHANGELOG.md etc...), a tag
   on that commit and then a commit that sets the pom versions to the next
   dev version.
3. A GitHub release that contains SBOMs for each submodule and checksums for
   those SBOMs.

## Proposal in Detail

### Release Mechanics

1. A developer prepares a release commit (and a commit for the next
   development version) by running a release script and then pushes this PR.
   This can be done by hand (checking out the repo, running the script and
   following the push instruction) or by invoking the release workflow from
   the GitHub UI
2. A reviewer approves / merges the PR
3. A maintainer create a GitHub release for the corresponding tag and the 1st
   commit that was created by the release script (will have comment
   build: release x.y.z).
4. The Deploy to Central Portal (maven-deploy.yml) Github workflow will be
   triggered by the release tag. This will verify that the POM version matches,
   build, run all the tests, publish to Maven Central, upload the SBOMs and
   checksums to the GitHub release.
