# Ephemeral notifications and explicit expiry

* **Status:** Draft
* **Last Updated:** 2026-10-04
* **Objective:** Let a client mark a notification that no atServer persists,
and state exactly when a notification expires.

## Context & Problem Statement

Every notification is persisted by both the sending and the receiving
atServer, though much notification traffic is only useful for seconds. That
storage is load with nothing to show for it.

A notification's expiry travels as a relative `ttln`, which each atServer
turns into an absolute time on arrival, so the expiry the client asked for
drifts at every hop.

## Goals

* A notification can be marked ephemeral, so that no atServer persists it.
* A notification carries its exact expiry, and every atServer it passes
  through honours it.
* A client or atServer uses each new field only where the atServer it sends
  to advertises it.

### Non-goals

* Guaranteed delivery of an ephemeral notification, since best effort is the
  point of it.

## Considered Options

* ### Option 1 - Reuse eAt for the notification's expiry

  Rejected, as on `notify` `eAt` already means the expiry of the record that a
  `ttr` caches at the recipient.

* ### Option 2 - Two new fields, with capabilities listed in info

  `eAtn` carries the notification's own expiry and `eph` marks it ephemeral. A
  `features` list in `info` tells a client or atServer what the atServer it
  sends to supports. A version number can't do this job, because each atServer
  implementation numbers its releases differently.

## Proposal Summary

Option 2. Two new fields, `eAtn` (the notification's own expiry) and `eph`
(ephemeral), work on `notify`. Each is advertised in `info`, and a client or
atServer uses it only where it's advertised.

## Proposal in Detail

### Capabilities in info

Every form of `info` gains the `features` list that at_server_spec already
documents:

```json
"features": [
  {"name": "notify.eph", "status": "GA", "description": "..."},
  {"name": "notify.eAtn", "status": "GA", "description": "..."}
]
```

A client or atServer acts on the `name` alone. An `info` it can't read, or one
without the entry, means the capability isn't there.

### Grammar

Both fields follow `ttln`, in this order:

```text
notify[...][:ttln:<ms>][:eAtn:<ISO-8601>][:eph]<metadata fragment>:...
```

### eAtn

`eAtn:<ISO-8601 UTC>` is the notification's own expiry, in the format `eAt`
uses. The client sets it and it replaces `ttln`, so a command carrying both is
refused. An atServer clamps it at 8 days, as it does `ttln`, and forwards it
verbatim to an atServer that lists `notify.eAtn` (as the remaining `ttln` to
one that doesn't). A notification that has already expired when it arrives is
accepted and discarded: the client gets its id, a sending atServer gets
`data:success`, and nothing is stored or forwarded.

### eph

`eph` marks an update that neither the sending nor the receiving atServer
persists. It's a bare flag: present means ephemeral, absent means not, and
`eph:true` is a syntax error. It's held in memory, where `notify:list`,
`notify:status`, `notify:fetch` and a monitor's backlog all see it, until it
expires or the atServer restarts. Its expiry is clamped to 2 minutes, which
bounds that memory. It's refused with `delete`, `ttr` or `ccd`, each of which
would make the recipient's atServer write its keystore (a delete removes a
record that an earlier `ttr` update cached). An atServer forwards it as
ephemeral only to an atServer that lists `notify.eph`, and as an ordinary
notification otherwise.

### Forwarding

A sending atServer checks a peer's `info` before forwarding either field,
since it delivers to each atSign one notification at a time, and a field the
peer doesn't support would hold up every later notification to that atSign
until it expired.

No atServer writes an expired notification to a monitor, live or from the
backlog.

### Expected Consequences

* at_commons carries the grammar and the builders, and publishes before
  at_server_spec, whose specs depend on it.
* Every atServer implementation adds the two fields, the `features` list, and
  the peer check before forwarding `eph` or `eAtn`.
* at_client asks its atServer's `info` once per client (and again after 5
  minutes), and sends `ttln` and stored notifications wherever a capability
  isn't advertised.
* Ephemeral notifications take load off both atServers' notification stores,
  at the price of being lost to a restart.
