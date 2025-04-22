# Change Line Length to 80

<!-- This template is inspired by
https://github.com/GoogleCloudPlatform/emblem/tree/main/docs/decisions -->

* **Status:** Draft <!-- / Approved / Rejected / Superseded -->
* **Last Updated:** 2025-04-11
* **Objective:** Simplify formatting standards in the organization

## Context & Problem Statement

## Goals

* Simplify tooling
* Make code more readable in splits (on non-ultrawide screens)

### Non-goals

N/A

## Proposal Summary

Change formatting to 80 cols instead of 120 cols.

## Proposal in Detail

### Dart

pub.dev dictates that packages must be formatted to 80 cols.
This also means our standard for formatting complies with the publishing
standards by default.

Initially we chose to use line length of 120 to allow for more room in Flutter
widget trees, making it "easier" to read. However, having continued on with line
length 120 for a while, we've ended up with the opposite effect.
We tend to write less readable code, as the standard allows us to nest deeper,
when in reality things should be refactored into separate widgets.

### C

LLVM style standard is 80 lines, formatting to 120 is our only deviation from
that standard.

Also in LLVM style, macros are terrible to read if you have wrapping turned on
and split your screen. Multi-line macros place a "\" at the end of the line as
a continuation, which in LLVM style, extends to the furthest right column
(i.e. col 120).

When splitting your screen, you end up with code that looks
like this:

![CleanShot 2025-04-11 at 21 46 47@2x](https://github.com/user-attachments/assets/93c47f3c-9fa4-4a2e-a924-1defb442b804)
