# C protected header files

<!-- This template is inspired by
https://github.com/GoogleCloudPlatform/emblem/tree/main/docs/decisions -->

* **Status:** Draft <!-- / Approved / Rejected / Superseded -->
* **Last Updated:** 2024-01-03
* **Objective:** Add a formal specification for supporting protected
  (i.e. visible for testing in Dart) header files

## Context & Problem Statement

Right now we support entirely public, or entirely private (to the single C file)
symbols. What's missing is a way to add header files that are shared between
multiple C files and the tests, but not exposed in the public API of the C SDK.
This document's goal is to come to a decision on how best to solve this problem.

## Goals

* Expose symbols to tests and multiple C files without exposing to the public API

### Non-goals

* Change the existing project layout in any way, this should be an entirely
  additive approach. Symbols may be moved to the new semantic, but entirely
  public/private symbols should remain where they are.

## Other considerations <!-- optional -->

* We should take into account how this might affect packaging in the future.

## Considered Options <!-- optional -->

* ### Option 1 - `.h` files in `src/`

A simple approach which avoids adding new directories to the project. The protected
files go into .h files which are stored with the `.c` files in `src/`. Then the
`src/` folder can be included for internal linking, but the symbols remain excluded
from the include directories exported from our package.

* ### Option 2 - New internal include directory

Add a new directory to store these protected include files. Then they can be
included for testing and internal linking, but not exposed to end consumers of
the SDK.

## Proposal Summary

There are two main options, add these symbols to the existing `src/` directory,
or create a new directory for them.

## Proposal in Detail

### Expected Consequences <!-- optional -->

* We will be able to make breaking changes in the internal API without affecting
  end consumers of the SDK.
* We don't have to worry about polluting the included symbols in order to break
  functions up for unit testing.
