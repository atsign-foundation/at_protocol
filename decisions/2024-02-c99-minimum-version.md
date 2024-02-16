# C99 Minimum Version

<!-- This template is inspired by
https://github.com/GoogleCloudPlatform/emblem/tree/main/docs/decisions -->

* **Status:** Approved
* **Last Updated:** 2024-02-14
* **Objective:** Objective of this document is to analyze C89/C90 and C99,
and decide on a minimum version of C to support in the C SDK. Approval of
this document will mean that C99 is the approved minimum version of C to
support in the [at_c C SDK](https://github.com/atsign-foundation/at_c).

## Context & Problem Statement

We have not made a concrete decision on which version of C to support in the
C SDK. We need to make a decision on which version of C to support in the C
SDK.

## Goals

Goal of this document is to decide on a minimum version of C to support in
the C SDK. Approval of this document will mean that C99 is the approved
minimum version of C to support in the C SDK. This document analyzes the
impacts of choosing C99 as the minimum version of C to support in the C SDK.

### Non-goals

N/A

## Other considerations <!-- optional -->

C99 supports backwards compatibility with C89/90 (kind of).
[source](https://en.wikipedia.org/wiki/C99).

From the source:

> In particular, a declaration that lacks a type specifier no longer has
int implicitly assumed. The C standards committee decided that it was of
more value for compilers to diagnose inadvertent omission of the type
specifier than to silently process legacy code that relied on implicit int.
In practice, compilers are likely to display a warning, then assume int and
continue translating the program.

## Considered Options <!-- optional -->

* ### Option 1

Make C99 the minimum version of the C SDK and freely utilize C99 features.

* ### Option 2

Limit ourselves to ANSI C (C89/90) and avoid using C99 features.

## Proposal Summary

After discussions found
[here](https://github.com/atsign-foundation/at_c/issues/105),
we are leaning to making C99 the minimum version of the C SDK.

## Proposal in Detail

We are leaning towards C99 because:

1. Faster time to market (we can use C99 features such as bool from stdbool.h,
sized ints from stdint.h), and inline functions.
2. C99 supports backwards compatibility with C89/90 (kind of).
[source](https://en.wikipedia.org/wiki/C99). See the
["Other considerations"](#other-considerations) section for more details.

### Expected Consequences <!-- optional -->

* If a customer is programming in C89/90 strictly, the C SDK (in C99) may
not be compatible with their code.
