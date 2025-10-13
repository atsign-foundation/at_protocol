# APKAM key unrevoke

* **Status:** Draft
* **Last Updated:** 2025-10-13
* **Objective:** Set out a mechanism to safely manage the revoke/unrevoke
cycle for APKAM keys.

## Context & Problem Statement

When an APKAM key is revoked we have provided a means to unrevoke it using the
`at_activate` command line tool.

For the trivial case of a single key being revoked then unrevoked this doesn't
present a problem.

It is possible however to revoke a number of keys with the same app name
(`-A` or `--arx`) and device name (`-D` or `--drx`), which then calls into
question which key should be unrevoked when using those parameters rather
than a specific enrollment ID.

In the worst case a key that was revoked because it is known to be lost or
otherwise compromised might be unintentionally unrevoked when trying to
unrevoke an adjacent key.

## Goals

Set forth a clear approach to key lifecycle such that keys can be unrevoked
in line with user expectations set by `at_activate` help whilst ensuring that
unintentional unrevokation is avoided.

### Non-goals

Alter the behaviour of `at_activate` such that we would re-write the help.

## Other considerations

[Issue](https://github.com/atsign-foundation/at_client_sdk/issues/1677)
raised by @cconstab

## Considered Options

* ### Option 1 - More specific if unsure

If a seach of the app/device namespace finds a single key match then simply
unrevoke it.

Should that search find multiple keys then:

* **Note** that multiple keys have been found
* **Warn** that keys may have been revoked due to loss/compromise
* **List** the keys and their IDs
* **Prompt** for which ID should be unrevoked

* ### Option 2 - Highlander "There can be only one"

Rather than allowing multiple (revoked) keys with the same app and device name
we could ensure uniqueness by establishing that only one key for a given
app/device pairing can exist. If there is a revoked key for `-a foo -d bar`
then it must be deleted before another key for `-a foo -d bar` is created.

## Proposal Summary

## Proposal in Detail

### Expected Consequences <!-- optional -->
