# Dart naming convention for releases

* **Status:** Agreed
* **Last Updated:** 2023-03
* **Objective:** Define how we notate which platform and architecture a
release file is applicable to.

## Context & Problem Statement

We offer a number of command line tools (e.g. SSH No Ports) and as a
convenience to users the binaries for those tools are often added to a GitHub
release.

Given a number of platforms (MacOS, Linux, Windows) and architectures (arm,
arm64, x64) there are multiple ways that the releases can be named.

## Goal

Have a consistent way of denoting which platform and architecture a given
binary (or package containing a binary) is intended for.

## Summary

Adopt the Dart convention (as used for
[SDK downloads](https://dart.dev/get-dart/archive)), which gives us:

* macOS
  * arm64
  * x64
* Linux
  * arm
  * arm64
  * ia32
  * riscv64
  * x64
* Windows
  * arm64
  * ia32
  * x64

The release package would then be:

`<packagename>-<platform>-<architecture>.<format>`

e.g. a compressed tar file for at_activate for Linux on arm64:

`at_activate-linux-arm64.tgz`
