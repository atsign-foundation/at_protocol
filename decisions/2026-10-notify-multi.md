# Notifying many atSigns in one request

* **Status:** Draft
* **Last Updated:** 2026-10-04
* **Objective:** Let a client notify many atSigns with one value and its
metadata in one request.

## Context & Problem Statement

An app that sends the same content to 10 atSigns makes 10 `notify` requests
today. Once the recipients share a content key the ciphertext is the same for
all 10, so only the transport repeats.

`notify:all` was meant for this, but it's unused legacy. It can't carry the
metadata a recipient needs to decrypt the value (`isEncrypted`,
`appMetadata`), and at_client's own `notifyAll` sends one `notify` per
recipient rather than use it.

## Goals

* One request notifies many atSigns with one value and its metadata.
* One ciphertext serves every recipient.
* A client uses the new verb only where its atServer advertises it.

### Non-goals

* Group messaging, which is the planned MLS work (`at/pqmls`).

## Considered Options

* ### Option 1 - Extend notify:all

  Add the metadata fragment to `notify:all`. Rejected, as it would rework the
  grammar of an unused legacy verb, where a new verb can be designed for the
  job from the start.

* ### Option 2 - A new verb

  Add `notify:multi` and deprecate `notify:all` in its favour.

## Proposal Summary

Option 2. A new verb, `notify:multi`, replaces `notify:all`, which is
deprecated as unused legacy. It's advertised in `info` as `notify.multi`, in
the `features` list described in
[Ephemeral notifications and explicit expiry](2026-10-ephemeral-notifications-and-explicit-expiry.md).
A multi-recipient content key lets every recipient open the one ciphertext.

## Proposal in Detail

### notify:multi

```text
notify:multi[:ttln:<ms>][:eAtn:<ISO-8601>][:eph]
  <metadata fragment>:@<recipient>[,@<recipient>...]:<key>@<sender>[:<value>]
```

Every recipient starts with `@` and the sender is required, so a malformed
metadata field is a syntax error rather than a recipient. It's always a
key-type update. It carries no operation, since a delete would remove a cached
record at every recipient, and no `ttr` or `ccd`, so no recipient keeps one. It
carries `eAtn` and `eph` with the same meaning and the same rules as `notify`
does. The atServer refuses, by name, the fields that are right for one
recipient only (`sharedKeyEnc`, `pubKeyCS`, `pubKeyHash`,
`hashingAlgo`, `skeEncKeyName`, `skeEncAlgo`) and those plain `notify` never
delivers (`isBinary`, `encoding`, `sharedKeyStatus`, `dataSignature`). The
reply maps each recipient to its notification id:

```text
data:{"@bob":"<id>","@carol":"<id>"}
```

An atServer whose `notify` handler accepts on a `notify:` prefix has to
exclude `notify:multi` from it.

A client sends `notify:multi` only where its atServer's `info` lists
`notify.multi`, and one `notify` per recipient where it doesn't.

### notify:all

`notify:all` is deprecated as unused legacy, with `notify:multi` as its
replacement. at_commons and at_server_spec mark it deprecated, and atServers
go on accepting it until it's removed.

### Multi-recipient content keys

A client mints a content key for a fixed list of recipients and conveys it to
each of them. The value is encrypted once, under the provider
`at/symmetric/AES/GCM/multirecipient`, with this AAD:

```text
at/symmetric/AES/GCM/multirecipient:<sharedBy>:<key>.<namespace>
```

It leaves out `sharedWith`, which differs for every recipient, so one
ciphertext serves them all, and its own provider id keeps it apart from the
per-recipient AAD, so a multi-recipient value can't pass as a per-recipient or
self value. Everyone the key was conveyed to can read everything sent under
it, so a different recipient list means a different key. No recipient is ever
added to or removed from a key, and no key is rotated in place.

This isn't group messaging. Groups, with membership, epochs and forward
secrecy across membership changes, are the planned MLS work (`at/pqmls`). A
multi-recipient content key neither builds towards that work nor constrains
it.

### Expected Consequences

* at_commons carries the grammar and `NotifyMultiVerbBuilder`. at_server_spec's
  `NotifyMulti` spec depends on it, so at_commons publishes first.
* Every atServer implementation adds the verb and lists `notify.multi` in
  `info`.
* at_client sends one `notify:multi` where its atServer lists `notify.multi`,
  and one `notify` per recipient where it doesn't.
* `notify:all` is marked deprecated in at_commons and at_server_spec.
