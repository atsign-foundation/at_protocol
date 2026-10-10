# atServer gatekeeper

* **Status:** Draft
* **Last Updated:** 2026-10-10
* **Objective:** Let an atSign's owner decide, at the atServer and per
namespace, which other atSigns may exchange data with that atSign, in both
directions, holding atSigns not yet admitted in quarantine.

The detail is on the at_server branch [`gkc-gatekeeper`][branch]: the
[goals][goals], the [decision ledger][decisions], the [design][design] and the
agreed [scenarios][features]. This record summarises them, and where the two
differ, the branch is current.

## Context & Problem Statement

The only control an owner has today is the atSign-wide blocklist,
`config:block`. It's checked once, when another atServer sends `from:`, and
nothing consults it on the way out, so @alice's atServer still delivers
notifications to a blocked atSign and looks up its keys.

Every application with access to a namespace can exchange data in it with any
other atSign. A badly written application can share a key with the wrong
atSign, or take in notifications from atSigns nobody knows, and nothing at the
atServer limits how far that spreads.

## Goals

* An owner, through applications, sets a rule per namespace: open, where any
  atSign may exchange and one not yet admitted is held in quarantine, or
  closed, where only admitted atSigns may.
* A rule binds @alice's own outbound exchanges as well as inbound ones.
* A quarantined atSign gets a small allowance. Nothing it sends is cached
  through `ttr`, it has a limited number of exchanges in a rolling window, its
  notifications are capped in size, and they reach only clients that ask for
  them.
* A refusal is final, so a sending atServer discards the notification rather
  than retrying it.
* Once applications are ready, the default becomes closed, so a namespace no
  application has claimed exchanges with nobody.

### Non-goals

* Public data. `plookup` reads of `public:` keys stay outside the gate.
* Values. They're end-to-end encrypted, so the gate decides only on what the
  atServer can read: the other atSign, and the key's namespace.
* Streams. No connection from another atServer can reach the stream verb
  today, and it's being deprecated.

## Considered Options

The ledger records every alternative weighed. These four shaped the design.

* ### Option 1 - Gate notifications only

  Rejected, as a key shared with the wrong atSign is exposed through lookup,
  not notify.

* ### Option 2 - Sending to an atSign admits it

  Rejected. It needed three guards (admit only an atSign in none of the sets,
  only on delivery, and only on a notification) and still let an application
  widen its reach with no deliberate admission.

* ### Option 3 - Sync gate state to clients

  Rejected, as a client could edit a synced record locally and push it, and a
  refused push is retried every sync round.

* ### Option 4 - Answer older senders with success and drop the notification

  Rejected, as they would record as delivered notifications that never were.

## Proposal Summary

A gatekeeper in the atServer is consulted on every exchange between atSigns,
in both directions. Applications set its rules for the namespaces they hold
through a new verb, `gate:`. Three new error codes make a refusal final. Each
atSign has a default, `ungated` (today's behaviour) until its owner switches it
to `closed`, so released applications keep working until they're ready.

## Proposal in Detail

### Rules, and who sets them

A namespace with a rule is open or closed. An open one holds three sets of
atSigns, admitted, quarantined and denied, and a closed one holds only an
admitted set. A rule on `chat` covers `x.chat` and `group.chat` by the suffix
match enrollments use, and the more specific rule decides. Beside the sets of
each namespace there's one atSign-wide admitted set, which admits in every
open namespace and in no closed one, and a namespace's deny overrides it. The
blocklist stays as it is, and overrides everything.

An enrollment with `rw` on a namespace sets its rule, its limits and its sets,
and `r` reads them. The atSign-wide set and the default need a root enrollment.

Scan and `notify:list` from another atSign answer only namespaces where it's
admitted, and a value reference in a looked-up key resolves only into one.

### Both directions

In an open namespace, @alice reaches any atSign not denied there, and in a
closed one only atSigns admitted there. Nothing @alice sends, looks up or scans
changes another atSign's standing, so an application admits an atSign
deliberately. With `chat` closed and `invitations.chat` open on both sides,
@alice invites @dave, @dave's reply arrives in quarantine, and accepting the
invitation is the chat application admitting @dave in `chat`.

A key @alice shares with an atSign the namespace refuses is still stored,
since clients are local-first and a refused sync push would be retried for
ever. Its auto-notify isn't sent, and the atSign can't look it up.

### Quarantine

An atSign's first inbound exchange in an open namespace, a notification or a
lookup, puts it in quarantine there. Per namespace and atSign, at most N
exchanges are accepted in any window of W, by default 10 in 24 hours. A
quarantined notification is at most 15,360 bytes, measured over the whole
notify command, and it never creates or removes a cached key. Each open
namespace bounds how many atSigns it holds in quarantine and how many bytes of
their notifications, and each atSign bounds how many open namespaces it has and
its total of quarantined bytes. Applications set these values within limits
the atServer operator sets.

A quarantined notification is marked `"quarantined": true`. Monitor,
`notify:list` and `notify:fetch` return it only to a client that asks with a
new `:quarantined` flag, so a released application never sees one.

### Exchanges with no namespace

These follow the pair's standing. A short list is permitted when the other
atSign is admitted somewhere: a lookup of `shared_key`, the legacy shared-key
notifications, and text notifications until they're retired. Everything else
with no namespace is refused once the default is closed.

### Refusals

A refusal answers one command and leaves the connection open. It's one of three
new codes: AT0033 (not accepted), AT0034 (quarantine limit reached) and AT0035
(too large for quarantine). A denied atSign and a closed namespace look the
same to the sender. A sending atServer stops at once on any of the three, gives
the notification a new status, `refused`, and moves on to its next
notification for that atSign.

### Defaults, and losing admission

An atSign's default is `ungated` or `closed`. Only a root enrollment switches
it, and the atServer operator sets the default a new atSign starts with. When
an atSign loses admission, keys shared with it and notifications already stored
from it stay, cached copies of its keys go, and anything queued for it is
checked again at delivery.

### Expected Consequences

* at_commons carries the `gate:` grammar, the three codes and the
  `:quarantined` flag, and publishes first.
* Every atServer implementation adds the gate, a `gate` feature in `info`, and
  the sending side's discard, the last no later than it enforces the gate. An
  older atServer retries a refusal until the notification expires, holding its
  own later notifications to that atSign behind it.
* On the atServer, `local:` records become the atServer's own, holding gate
  state. They never sync, scan hides them, and every client verb naming one is
  refused.
* at_client gains the gate API, and sends `:quarantined` only to an atServer
  whose `info` lists `gate`.
* Released applications see no change until a rule, or a closed default, binds
  them.

<!-- pyml disable-num-lines 5 md013-->
[branch]: https://github.com/atsign-foundation/at_server/tree/gkc-gatekeeper/docs/projects/gatekeeper
[goals]: https://github.com/atsign-foundation/at_server/blob/gkc-gatekeeper/docs/projects/gatekeeper/goals.md
[decisions]: https://github.com/atsign-foundation/at_server/blob/gkc-gatekeeper/docs/projects/gatekeeper/decisions.md
[design]: https://github.com/atsign-foundation/at_server/blob/gkc-gatekeeper/docs/projects/gatekeeper/design.md
[features]: https://github.com/atsign-foundation/at_server/tree/gkc-gatekeeper/docs/projects/gatekeeper/features
