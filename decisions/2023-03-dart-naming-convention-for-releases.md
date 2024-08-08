# Dart naming convention for releases

* **Status:** Agreed
* **Last Updated:** 2024-08
* **Objective:** Define how we notate which platform and architecture a
release file is applicable to.

## Context & Problem Statement

We offer a number of command line tools (e.g. NoPorts) and as a
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

### Optional ABI qualifiers

Different Linux distributions make use of various C standard library
[libc](https://en.wikipedia.org/wiki/C_standard_library) implementations
such as GNU libc ([glibc](https://www.gnu.org/software/libc/)),
[musl](https://musl.libc.org/) and [uClib-ng](https://uclibc-ng.org/).
It's thus necessary to qualify which application binary interface
([ABI](https://en.wikipedia.org/wiki/Application_binary_interface)) a binary
is linked against.

This introduces an (optional) ABI qualifier:

* gnu
* musl

`<packagename>-<platform>-<architecture>(-<abi>).<format>`

e.g. a compressed tar file for C sshnpd for Linux on RISC-V compiled against
musl:

`sshnpd-linux-riscv64-musl.tgz`
