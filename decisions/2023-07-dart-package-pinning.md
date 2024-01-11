# Dart package pinning

* **Status:** Agreed
* **Last Updated:** 2023-07
* **Objective:** Define when we should pin dependencies in Dart pubspec.yaml

## Context & Problem Statement

We make extensive use of Dart, and dependencies from the Dart package
manager [pub.dev](https://pub.dev).

We also publish packages to pub.dev

Where possible we should have control of our dependencies by use of
dependency pinning (with automated updates using Dependabot). This
helps us achieve repeatable builds, and improve the score for our
[OpenSSF Scorecards](https://github.com/atsign-foundation/.github/blob/trunk/docs/OpenSSF_scorecards.md).

## Goal

Have a consistent approach to dependency pinning in our pubspec.yaml files.

## Summary

We need to take a different approach for packages we publish to pub.dev
versus other packages and apps:

### Packages we publish to pub.dev

To maximise [pub points](https://pub.dev/help/scoring) packages should
[support up-to-date dependencies](https://pub.dev/help/scoring#support-up-to-date-dependencies):

* Works with the latest stable Dart SDK.
* Works with the latest stable Flutter SDK (if applicable).
* Works with the latest versions of all dependencies.

Dart dependencies [best practices](https://dart.dev/tools/pub/dependencies#best-practices)
advocate:

* Use caret syntax
* Depend on the latest stable package versions
* Test whenever you update package dependencies

Thus, published packages shouldn't make use of pinned dependencies, but
rather use caret syntax:

```yaml
dependencies:
  path: ^1.3.0
  collection: ^1.1.0
  string_scanner: ^0.1.2
```

### Applications and internal packages

When we're not publishing to pub.dev we should pin dependencies:

```yaml
dependencies:
  path: 1.3.0
  collection: 1.1.0
  string_scanner: 0.1.2
```

Dependabot can then be configured to raise Pull Requests for updated
dependencies:

`.github/dependabot.yml`

```yaml
version: 2
enable-beta-ecosystems: true
updates:
  - package-ecosystem: "pub"
    directory: "/packages/package_name"
    schedule:
      interval: "daily"
```
