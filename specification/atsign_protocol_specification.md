# Atsign Protocol Specification

<!-- pyml disable-num-lines 5000 md013-->
**This document describes atServer 3.19.0** (production release [p3.19.0](https://github.com/atsign-foundation/at_server/releases/tag/p3.19.0), 2026-10-26). Behaviour marked *Unreleased* is on at_server's trunk but not yet in a production release. Changes by version are in [Appendix E](#appendix-e-changes-by-atserver-version).

This document specifies the **Atsign Protocol** at the level required to
implement either side of the wire, an atClient or an atServer, in any
language. Every byte that crosses a TCP socket between an atClient,
atServer, or atDirectory is in scope. Higher-level concerns that are
client-only (file formats, key derivation, query languages) are out of
scope unless they affect what is on the wire.

The companion document
[`building_on_the_atsign_protocol.md`](./building_on_the_atsign_protocol.md)
is the entry-point for **application developers** building on the
Atsign Protocol via the Dart `at_client_sdk`. If you are writing an app
rather than a protocol implementation, start there.

The canonical source for protocol behaviour is the implementation in
the [`at_client_sdk`](https://github.com/atsign-foundation/at_client_sdk)
and [`at_server`](https://github.com/atsign-foundation/at_server)
repositories. Where this document and that source disagree, the source
wins and this document is a bug. Pull requests welcomed.

---

## Table of contents

1. [Introduction](#1-introduction)
2. [Deployment topologies](#2-deployment-topologies)
3. [Transport](#3-transport)
4. [Framing](#4-framing)
5. [The atSign identity model](#5-the-atsign-identity-model)
6. [The atKey model](#6-the-atkey-model)
7. [The metadata fragment](#7-the-metadata-fragment)
8. [The atDirectory protocol](#8-the-atdirectory-protocol)
9. [Authentication](#9-authentication)
10. [CRUD verbs](#10-crud-verbs)
11. [Notification verbs](#11-notification-verbs)
12. [The sync verb](#12-the-sync-verb)
13. [Server-admin and utility verbs](#13-server-admin-and-utility-verbs)
14. [End-to-end encryption](#14-end-to-end-encryption)
15. [The inter-atServer protocol](#15-the-inter-atserver-protocol)
16. [Worked flows](#16-worked-flows)
17. [Errors](#17-errors)
18. [Glossary](#18-glossary)
19. [Appendix A, Verb reference](#appendix-a-verb-reference)
20. [Appendix B, Legacy and deprecated](#appendix-b-legacy-and-deprecated)
21. [Appendix C, Significant near-term projects](#appendix-c-significant-near-term-projects)
22. [Appendix D, Inconsistencies and quirks](#appendix-d-inconsistencies-and-quirks)
23. [Appendix E, Changes by atServer version](#appendix-e-changes-by-atserver-version)

---

## 1. Introduction

The Atsign Protocol is a text-based, line-oriented, request/response
protocol over TLS. Three roles participate.

An **atClient** is software acting on behalf of an atSign owner. It
authenticates only to its own atSign's atServer, which carries its
cross-atSign reads and notifications to other atServers (see
[§15](#15-the-inter-atserver-protocol)). It may also open an
unauthenticated connection to another atServer to `lookup` that
atSign's public records.

An **atServer** is the personal server for one atSign. It stores that
atSign's keys (encrypted blobs at rest), serves them on request,
delivers notifications, and connects out to other atServers when its
owner's atClient asks for cross-atSign data.

An **atDirectory** is a lookup service that maps an atSign to the
`host:port` of its atServer. It is conceptually similar to DNS.

The protocol is built around a small set of **verbs**, single-line
commands a client sends to a server. Each verb has a regex-defined
syntax. Servers respond with a single line of `data:…` or `error:…`,
followed by a prompt that frames the next request. `monitor` keeps the
connection open for streamed notifications; everything else is
single-shot.

End-to-end encryption is **entirely an atClient concern**. atServers
store opaque ciphertext and opaque metadata fields, and never see
plaintext values. Server-side filtering on values is therefore
architecturally impossible, see [§14](#14-end-to-end-encryption).

### How this document is versioned

These rules keep the header under the title, the markers in the text
and [Appendix E](#appendix-e-changes-by-atserver-version) in step.
`tools/check_spec_versions.py`, which CI runs, checks that they agree.

1. **The header** names the production release of the atServer this
   document describes, with a link to its release and the date it was
   published.
2. **What is described** is that production release. Newer behaviour,
   on at_server's trunk but not yet in a production release, may
   appear marked *Unreleased*, linking to the Unreleased block at the
   top of Appendix E; an entry there may name the canary release that
   first carried it. A removal keeps its old text, marked *Removed,
   unreleased*, until the removal reaches a production release. The
   change that moves the header to a new production release turns the
   Unreleased block into that release's block, and its markers into
   "Since atServer X.Y.Z".
3. **One block per production release.** A version released only as a
   canary belongs to the first production release that shipped it,
   and that release's block lists the canary versions it includes. A
   "Since atServer X.Y.Z" marker cites the production version, and
   links to its block.
4. **Each block's date** is the date its production release was
   published on GitHub, as YYYY-MM-DD.
5. **Blocks run newest first**, with Unreleased at the very top.
6. **Only production releases that changed the protocol have a block.**
   The history starts at atServer 3.0.35.
7. **A change is listed** when an implementer of either side needs it:
   verbs and grammar; responses, refusals and error codes; record
   shapes and reserved keys; authentication and authorization rules;
   limits that change what is accepted; removals and deprecations.
   Refactors, performance, logging, dependencies and builds are not.
8. **Versions are atServer versions.** A change a client originates is
   listed under the atServer release that first accepted or required
   it, and a change to clients alone is not listed. A change to the
   atDirectory is listed under the atServer release whose source first
   carried it.

### For implementers, read these first

If you're implementing this specification, read these appendices
first:

- [Appendix C, Significant near-term projects](#appendix-c-significant-near-term-projects)
  enumerates active workstreams that will change parts of this
  specification within the next few releases (post-quantum
  cryptography, fast-sync / "fsync", new atKeys structure, pluggable
  encryption, canonical conformance test suite, etc.). Read this
  before committing to a long-lived implementation choice.

- [Appendix D, Inconsistencies and quirks](#appendix-d-inconsistencies-and-quirks)
  enumerates the places where the wire reality is surprising, error
  separators that aren't uniform, response shapes that differ
  per-verb, semantics that flip on auth state, and similar gotchas.
  Read this if your implementation is failing in ways that the
  per-verb sections don't seem to predict.

- [Appendix E, Changes by atServer version](#appendix-e-changes-by-atserver-version)
  lists what each production release of the atServer changed on the
  wire. Read this if your implementation may meet an atServer older
  than the one this document describes.

### Spelling and capitalisation

The protocol's name is **Atsign Protocol** (capital A, capital P,
single-spaced). The domain terms are:

- `atSign`, an identity like `@alice`
- `atServer`, the personal server for an atSign
- `atDirectory`, the directory service
- `atKey`, a key in an atServer's keystore
- `atClient`, software talking to atServers

Preserve those capitalisations exactly in code and docs.

---

## 2. Deployment topologies

`atDirectory` and `atServer` are **addresses, not endpoints**. The
default atDirectory for the public Atsign Protocol is at
`root.atsign.org:64`, but any atDirectory address may be used. An
atClient learns its atServer's address by querying its atDirectory; an
atServer learns another atServer's address the same way (via its own
atDirectory pointer, which need not be the same one).

Three deployment modes are commonly seen:

1. **Public hosted.** Default. Clients use `root.atsign.org:64` as
   their atDirectory; atSigns are hosted by Atsign on shared
   infrastructure. This is what `at_register` and `at_activate` produce
   out of the box.
2. **Self-hosted atServer with public atDirectory.** An organisation
   runs its own atServers, but the atSigns are still resolvable via
   `root.atsign.org:64`. The atDirectory entry points at the
   organisation's hosts.
3. **Fully self-hosted.** An organisation runs its own
   atDirectory **and** its own atServers, with atSign registration and
   provisioning entirely under its control. atSigns hosted in this
   topology are not resolvable on the public Atsign Protocol; clients
   must be configured with the alternate atDirectory address. This is
   the model for a hermetically-sealed enterprise deployment.

Implementations MUST allow the atDirectory address to be configured.
A hard-coded `root.atsign.org:64` is not Atsign-Protocol-compliant.

---

## 3. Transport

### 3.1 atDirectory

| Property     | Value                                                                                                                                                                                                             |
|--------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Transport    | TCP                                                                                                                                                                                                               |
| TLS          | One-way (atDirectory presents a server certificate; client does not)                                                                                                                                              |
| Default port | `64`                                                                                                                                                                                                              |
| Default host | `root.atsign.org` (configurable)                                                                                                                                                                                  |
| HTTP         | HTTPS on port `443` and, by ALPN, on the default port; see below                                                                                                                                                  |

The atDirectory answers HTTP over TLS on port `443` and, since atServer
[3.19.0](#atserver-3190), on its Atsign Protocol port to a client that
negotiates `http/1.1` by ALPN. A client that negotiates `atProtocol/1.0`,
or no protocol, speaks the Atsign Protocol ([§8](#8-the-atdirectory-protocol)).

- `GET /<atSign>` returns `host:port`, and `GET /<atSign>/<path>`
  redirects to `https://<host:port>/@<atSign>/<path>`. The atSign may
  be given with or without its `@`, and is matched in its canonical form
  ([§5](#5-the-atsign-identity-model)).
- An unknown atSign gets `404`, a path that does not decode `400`, any
  method other than `GET` `401`, and a request the atDirectory cannot
  answer `500`.
- Every answer carries `Access-Control-Allow-Origin: *` and closes its
  connection, and an HTTP connection that sends no complete request is
  closed within 10 seconds.

Before atServer 3.19.0, HTTP is answered on port `443` only, a redirect
goes to `https://<host:port>/<path>` without the atSign, and the atSign
is looked up as given. The `400` for a path that does not decode, the
`500`, the `Access-Control-Allow-Origin` header and the closing of
connections are since 3.19.0.

### 3.2 atServer

The atServer transport is TCP with TLS. Connections between atServers
use mutual TLS by default: the connecting atServer presents a client
certificate, and a `from:` naming another atSign is checked against
it. The atServer looks that atSign up in the atDirectory, and a
certificate that does not match the host it gives, or no certificate,
gets `AT0401`. A `from:` naming the atServer's own atSign is not
checked against a certificate. Setting at_secondary_server's
`clientCertificateRequired` to `false` (it is `true` by default) turns
the check off, and the atServer then presents no client certificate on
its own outbound connections.

The atServer's port also negotiates ALPN. A connection that selects
`atProtocol/1.0`, or no protocol, speaks the Atsign Protocol. One that
selects `http/1.1` reaches an HTTP server, which answers a `GET` for
one of the atSign's public records and upgrades `/ws` to a WebSocket
carrying the Atsign Protocol. Since atServer [3.17.0](#atserver-3170), a command that
starts like an HTTP request, on a connection that did not select
`http/1.1`, is answered `AT0003` and the connection is closed.

The port is per-atSign and is discovered via the atDirectory. The
atDirectory response is the canonical source for the host and port to
connect to.

### 3.3 Connection lifecycle

1. Client opens TCP connection.
2. TLS handshake; server certificate is validated against the trusted
   roots (and optionally a pinned `cacert.pem`).
3. **Banner.** On accept, the atServer writes a bare `@`, with no
   newline, then waits for the client's first verb; clients discard it.
   An atServer at its connection limit writes
   `error:AT0012-Inbound connection limit exceeded\n` instead, with no
   prompt, and closes the connection.
4. Client sends verb, terminated by `\n`.
5. Server responds with `data:…\n@…@` or `error:…\n@…@`. The trailing
   `@…@` (or bare `@` before authentication) is the **prompt**, see
   [§4](#4-framing).
6. Steps 4–5 repeat. Either side may close the connection at any time.
   On the atDirectory a client may close with `@exit\n`. An atServer
   answers `@exit` with `AT0003`, so a client ends an atServer
   connection by closing the socket.

### 3.4 Idle and timeout behaviour

- atClient default outbound idle timeout: **600 000 ms** (10 minutes).
  Source: `at_lookup/lib/src/connection/outbound_connection_impl.dart`.
- atClient default per-response wait: **90 000 ms**, with a
  **10 000 ms** wait between data packets in at_lookup 3.6.1, and
  **30 000 ms** in at_lookup 3.7.0. Source:
  `at_lookup/lib/src/connection/outbound_message_listener.dart`.
- atServer idle limits, in at_secondary_server's `connection`
  configuration, with their defaults: `inbound_idle_time_millis`
  (600 000) for an inbound connection that has not authenticated, and
  `authenticated_inbound_idle_time_millis` (600 000) for one that has
  authenticated or proved itself with `pol`; `outbound_idle_time_millis`
  (599 000) and `authenticated_outbound_idle_time_millis` (599 000) for
  its own outbound connections, before and after `pol`. The allowed inbound idle time can
  shrink towards a minimum as the number of inbound connections nears
  `inbound_max_limit` (200).

When the server-side idle timeout fires, the server closes the
connection without warning. Long-lived `monitor` connections must be
within the configured idle limit, or the server side will need to
disable idle-close for that connection class.

---

## 4. Framing

### 4.1 Line terminator

All client-to-server and server-to-server commands end with a single
**LF** (`\n`, ASCII 10). CR (`\r`) is not part of the protocol, but
the atDirectory ends every reply with `\r\n@`, so clients tolerate
both.

### 4.2 Response delimiter (the "prompt")

A server response is followed by a **prompt** that frames the next
client request. The prompt is one of:

| Connection state                         | Prompt          |
|------------------------------------------|-----------------|
| Unauthenticated                          | `@`             |
| Authenticated as the server's own atSign | `@<atSign>@`    |
| `pol`-authenticated as another atSign    | `<fromAtSign>@` |

On a `pol` connection, some error responses end with the bare `@`
rather than `<fromAtSign>@`; clients should accept either.

A response ends with `\n`, and the server then writes the prompt with
no newline of its own, so the next response follows the prompt on the
same line. A client takes a response as complete at its `\n`.

```text
data:42\n@alice@
^^^^^^^^^^^^^^^^^
| response data | prompt
```

Note: the prompt is **part of the framing**, not the response payload.
A client implementation that includes `\n@…@` in its captured response
is parsing incorrectly.

### 4.3 Charset

UTF-8. atKeys, values, and metadata are all UTF-8 strings on the wire.

### 4.4 Newline escapes in values

Because `\n` is the framing terminator, a value cannot carry one on
the wire. The atServer stores and returns values as sent. `~NL~` is a
convention of the reference SDK: it writes the literal four-character
sequence `~NL~` in place of `\n` in the update commands it syncs, and
turns `~NL~` back into `\n` in `lookup`, `llookup` and `plookup`
results. An encrypted value is base64 ciphertext, so contains no `\n`
to begin with.

### 4.5 Binary values

Values cross the wire as text. The reference SDK turns a binary value
into Base2e15 text (`AtClient.putBinary`) before any encryption, and
sets `isBinary:true`, which declares that the value, once decoded, is
binary.
`isEncrypted:true` declares it is ciphertext. The two are independent
and both can be true. See [§7](#7-the-metadata-fragment).

### 4.6 Maximum value size

at_secondary_server holds at most 10 240 000 bytes per connection that
it has not yet dispatched, the terminating `\n` included. A single
command, verb, atKey and value together, must fit, and commands
pipelined behind one still being handled count towards the same limit.
The limit is fixed: it is not configurable, and `stats` does not report
it. Going over it is answered with `AT0005` (see [§17](#17-errors)), and
the connection is closed.

### 4.7 Pipelining

The protocol is request-response. Since atServer [3.16.6](#atserver-3166), an atServer
handles the commands a connection sends in the order they arrive and
answers each in turn, so a client may send a command before reading
the previous response. A client that may meet an older atServer must
wait for each response, terminated by the prompt, before sending the
next. `monitor` streams notifications continuously, see
[§11.7](#117-monitor).

---

## 5. The atSign identity model

An **atSign** is a unique identifier of the form `@<name>`. In a
verb's syntax, `<name>` matches `[^@:\s]+`.

An atSign has one canonical form: lowercase, with every `.` removed
from the name, so `@Alice`, `@alice` and `@a.lice` are all the atSign
`@alice`. The atServer puts each atSign named in `from:`, `update`,
`delete`, `lookup`, `llookup`, `plookup` and `notify` into this form.
It refuses one that is empty, holds a second `@`, or contains
whitespace, an ASCII control character, one of the control pictures
U+2400–U+241F, U+2421, U+2424 and U+2425, or any of
``!*'`();:&=+$,/?#[]{}``.

Inside an atKey ([§6](#6-the-atkey-model)), an owner or recipient
atSign must also meet a second rule: each character after the `@` is
an ASCII letter, a digit, `_` or `-`, or falls in U+00A9, U+00AE,
U+2000–U+3300, U+FE00–U+FE0F or U+1F000–U+1FBFF.

Inside an atKey, an owner or recipient has at most **55 characters**
after its `@`, so at most 56 with it. An atKey whose owner or recipient
is longer is invalid.

### 5.1 Lifecycle phases

An atSign goes through 3 phases from registration to everyday use.
Each produces credentials that later exchanges on the wire use.

1. **Register.** The atSign gets an atDirectory entry and an
   atServer, for example through a registrar. The atServer is started
   with the atSign's **CRAM secret**, and the atSign's encryption keys
   do not exist yet. An app activates the atSign once its atDirectory
   entry resolves and its atServer answers; the reference SDK waits
   for both. The activating app needs the CRAM secret.
   at_onboarding_cli, for example, has the registrar send a
   verification code to the owner's email or phone, and exchanges
   that code with the registrar for the secret.
2. **Onboard.** The activating app authenticates with `cram`. It
   generates the atSign's RSA encryption keypair and AES
   self-encryption key, and an APKAM keypair of its own. On the CRAM
   connection it sends `enroll:request` with its APKAM public key. The
   atServer approves that enrollment at once and grants it `rw` on
   `__manage` and on `*`. The app reconnects, authenticates with
   `pkam` as that enrollment, stores its keys on the device (for
   example in an `.atKeys` file), publishes
   `public:publickey@<atSign>` and deletes `privatekey:at_secret`.
   From then on `cram` fails. The app does not write
   `public:signing_publickey@<atSign>`: the atServer generates that
   keypair, its server authentication signing key, itself when it
   first starts ([§6.5](#65-reserved-keys)).
3. **Enroll (per app).** Each further app enrolls with APKAM
   ([§9.4](#94-apkam-enroll-otp-keys)). It generates its own APKAM
   keypair and asks for a namespace permission map such as
   `{"todos":"rw"}`, quoting a passcode from `otp:get`
   ([§9.4.2](#942-the-otp-verb)). An approving app approves the
   request and supplies the atSign's encryption private key and
   self-encryption key, encrypted for the new app. The new app then
   authenticates with `pkam` as its own enrollment. The namespace map
   limits what that enrollment may read and write on the atServer,
   and `enroll:revoke` withdraws it.

CRAM serves only activation. After Phase 2 every client authenticates
with `from` and `pkam` ([§9.3](#93-pkam-pkam)), and the reference SDK
names its enrollment with `enrollmentId:` unless that is `primary`.
The exchanges are shown in
[§16.1](#161-cram-bootstrap-phase-2-onboarding) and
[§16.2](#162-apkam-enrollment-end-to-end).

---

## 6. The atKey model

A key in the atServer's keystore is an **atKey**, a structured string
whose shape encodes its visibility and ownership. There are 5 key
shapes plus 2 augmentations.

The atServer stores an atKey in a folded form: trimmed, lowercased,
and with any spaces removed. Two spellings that fold to the same
string name one record, and `scan` returns keys in the folded form.

### 6.1 The 5 shapes

| Shape   | Wire format                                  | Visibility                                |
|---------|----------------------------------------------|-------------------------------------------|
| Public  | `public:<key>[.<namespace>]@<owner>`         | Anyone; `lookup` needs no auth            |
| Self    | `<key>[.<namespace>]@<owner>`                | Owner only                                |
| Shared  | `@<recipient>:<key>[.<namespace>]@<owner>`   | Owner and `<recipient>` only              |
| Local   | `local:<key>[.<namespace>]@<owner>`          | Client only; see [§10.1](#101-update)     |
| Private | `private:<key>@<owner>`, `privatekey:<name>` | atServer internal; never listed or synced |

A `local:` key is kept in a client's own keystore. `update` refuses
one unless its name contains a reserved key ([§10.1](#101-update)),
and the atServer's commit log never records one. On an
atServer, `private:` and `privatekey:` keys are records the atServer
keeps for itself. A `privatekey:` name carries no `@<owner>`.
[§6.5](#65-reserved-keys) lists the reserved ones.

### 6.2 Augmentations

A **hidden** key is a public or self key whose `<key>` part starts
with `_`. Which hidden keys `scan` lists depends on the form:

- `public:__<key>.<namespace>@<owner>` (two underscores) and a self
  key `_<key>@<owner>` are listed only when the caller passes
  `:showhidden:true`. The commit log records both, so both sync.
- `public:_<key>@<owner>` (one underscore) is never listed, even with
  `:showhidden:true`. The commit log never records one, so it never
  syncs, and a write of one answers `data:-1`.

An unauthenticated `scan` lists no hidden key. A shared key whose
`<key>` part starts with `_`, such as `@bob:_handshake.wavi@alice`, is
not hidden: `scan` lists it like any other shared key.

Since atServer [3.19.0](#atserver-3190), a key whose name starts with
`__` and has no `.<namespace>`, such as `public:__location@alice`, uses
a reserved namespace ([§6.5](#65-reserved-keys)), so `update`,
`update:meta` and `delete` refuse it. Give such a key a namespace, as
in `public:__location.wavi@alice`.

A **cached** key is a copy of a remote-owned shared or public key,
stored on the recipient's atServer for offline or fast access. Wire
format is `cached:public:<key>@<owner>` or
`cached:@<recipient>:<key>@<owner>`. The recipient's atServer refreshes
the cache per the original key's `ttr` (time-to-refresh) and deletes
it on owner-side delete if `ccd` is set.

### 6.3 Namespace

A trailing `.<namespace>` segment scopes the key to an application or
domain (e.g. `phone.wavi`, `email.myapp`). APKAM enrollments grant
permissions per namespace, so the namespace is part of the
authorisation surface, not a free-form annotation.

The atServer accepts an atKey without a namespace. Most reserved
keys ([§6.5](#65-reserved-keys)), such as `public:publickey@alice`,
have none. An enrollment's namespace grants match only keys that carry a
namespace, so an enrollment reaches a key without one only through a
`*` grant. Reserved keys have rules of their own, and an enrollment
needs no `*` grant to read a cached copy of another atSign's
`publickey` or `signing_publickey`.

### 6.4 Key length

An atKey is at most **248 characters**, counted over the whole key as
the atServer stores it: any `public:` or `@<recipient>:` prefix, the
name and namespace, and the `@<owner>` suffix. A cached copy
([§6.2](#62-augmentations)), which the atServer writes itself, may be
255 characters, so that a 248-character key still fits with its
`cached:` prefix. Length is counted in UTF-16 code units. The default
Hive keystore also applies the limit to the key's UTF-7 encoding when
it creates a record, so a key with non-ASCII characters reaches the
limit sooner.

Compute against this hard cap, not a typical size. An atSign alone may
take up to 56 characters of the budget, or 111 UTF-16 code units when
its characters are emoji, and a shared key names two.

### 6.5 Reserved keys

An atServer may hold records under these reserved names:

| Reserved key                                                 | Purpose                                                                               |
|--------------------------------------------------------------|---------------------------------------------------------------------------------------|
| `public:publickey@<atSign>`                                  | Encryption public key. Used by other atSigns to encrypt to this owner.                |
| `public:signing_publickey@<atSign>`                          | Public half of the atServer's server authentication signing key (RSA), for checking its `pol` proofs and `notify:all` signatures. |
| `@<atSign>:signing_privatekey@<atSign>`                      | Private half of that keypair. The atServer signs its `pol` proofs, and the `dataSignature` of a `notify:all` notification, with it. |
| `privatekey:signing_keypair_generated`                       | Marks that the atServer has generated its server authentication signing keypair.      |
| `privatekey:at_secret`                                       | CRAM secret. Onboarding deletes it.                                                   |
| `privatekey:at_secret_deleted`                               | Kept once the CRAM secret is deleted, so that it is not planted again.                |
| `privatekey:at_pkam_publickey`                               | Legacy PKAM public key. See below.                                                    |
| `@<recipient>:shared_key@<atSign>`                           | AES key for data shared with `<recipient>`, encrypted to the recipient's `publickey`. |
| `shared_key.<recipient>@<atSign>`                            | The owner's copy of that AES key, encrypted to the owner's `publickey`.               |
| `private:blocklist@<atSign>`                                 | List of atSigns blocked by `config:block:add`.                                        |
| `privatekey:commitLogCompactionStats`                        | Statistics from the last compaction of the commit log.                                |
| `privatekey:accessLogCompactionStats`                        | Statistics from the last compaction of the access log.                                |
| `privatekey:notificationCompactionStats`                     | Statistics from the last compaction of the notification store.                        |
| `privatekey:at_telemetry_signing_privatekey`                 | Experimental. The atServer's telemetry signing key. See below.                        |
| `public:_at_telemetry_signing_publickey.__atserver@<atSign>` | Experimental. Public record of the telemetry signing key.                             |

The atServer generates its RSA signing keypair, its server
authentication signing key, the first time it starts, and records
`privatekey:signing_keypair_generated` so that it does so once.
Another atServer checks this atServer's `pol` proof against
`public:signing_publickey@<atSign>`
([§15.2](#152-the-pol-handshake)), and the atServer also signs
`notify:all`'s `dataSignature` with it
([§14.2](#142-public-data-signatures)). PKAM does not use this
keypair.

This specification names the keys that sign as follows:

- The **client authentication signing key** signs `pkam:`
  ([§9.3](#93-pkam-pkam)). It is the atSign's PKAM key or, under
  APKAM, the enrollment's own APKAM key.
- The **client data signing key** is an enrollment's key for signing
  data. Its public half is published at
  `public:_apsk.<enrollmentId>.a.__e@<atSign>` (below). Unless the app
  has a separate data signing key, the reference SDK advertises the
  enrollment's APKAM key there, so the two client keys are one
  keypair. The request's `apsk` or `apskLegacy` names the key to
  advertise, so the two can differ. The reference SDK already
  requires a separate data signing key when the APKAM key is not
  RSA-2048, and forthcoming releases require the two keys to differ.
- The **legacy data signing key** is the client encryption key, the
  private half of `public:publickey@<atSign>`. The reference SDK's
  `AtClient.put` signs public values with it
  ([§14.2](#142-public-data-signatures)).
- The **server authentication signing key** is the atServer's own
  `signing_privatekey`, above.

The atServer's telemetry key, below, is none of these.

The atServer plants `privatekey:at_secret` at startup from the CRAM
secret it is started with, and stops once
`privatekey:at_secret_deleted` exists. Onboarding deletes the secret
with `delete:privatekey:at_secret` after it first authenticates with
PKAM, and the atServer then keeps `privatekey:at_secret_deleted`.

Since atServer [3.16.5](#atserver-3165) no record is kept under
`privatekey:at_pkam_publickey`. At startup the atServer moves one it
finds into the enrollment named `primary`, or deletes it. A CRAM
`update` of this name installs the key as `primary` and answers
`data:-1`.

With its default encryption, the reference SDK writes
`shared_key.<recipient>@<atSign>` and
`@<recipient>:shared_key@<atSign>` when the owner first shares data
with `<recipient>`. The recipient's copy carries `ttr:3888000`.

Since atServer [3.17.0](#atserver-3170), an atServer started with a telemetry endpoint
creates an Ed25519 key for signing its telemetry, and publishes a
record of the public half at
`public:_at_telemetry_signing_publickey.__atserver@<atSign>`. Only the
atServer writes these two records. Both names are experimental.

These three names are reserved for the atSign's private keys in a
client's own keystore. The atServer creates no record under them.

| Reserved name                    | Purpose                 |
|----------------------------------|-------------------------|
| `privatekey:at_pkam_privatekey`  | PKAM private key.       |
| `privatekey:privatekey`          | Encryption private key. |
| `privatekey:self_encryption_key` | Self-encryption key.    |

`configkey`, and any name that starts with `_` and carries no
`@<atSign>`, are reserved as well.

The atServer reserves namespaces for itself:

- `__manage` holds, among others, each enrollment record, at
  `<enrollmentId>.new.enrollments.__manage@<atSign>`, and the
  encrypted copies of the atSign's encryption private key and
  self-encryption key that `enroll:approve` supplies for it, at
  `<enrollmentId>.default_enc_private_key.__manage@<atSign>` and
  `<enrollmentId>.default_self_enc_key.__manage@<atSign>`.
- `__atserver` holds records the atServer writes for its clients, such
  as `<micros>.events.__atserver@<atSign>` when another atSign's
  `publickey` changes. Every approved enrollment may read it.
- `__otp` holds passcodes: each OTP from `otp:get` at
  `private:<otp>.__otp@<atSign>`, and the semi-permanent passcode from
  `otp:put` at `private:spp.__otp@<atSign>`
  ([§9.4.2](#942-the-otp-verb)).
- `__e` holds each enrollment's own data, below.
- `__global`, `__private` and `__config` are reserved too.

Each approved enrollment also holds `rw` on a namespace of its own,
`<enrollmentId>.a.__e`. When the enrollment is revoked, its data
moves to `<enrollmentId>.r.__e`, and an un-revoke moves it back. When
the enrollment record is removed, by `enroll:delete` or once it has
expired, its data moves to `<enrollmentId>.d.__e`.

Since atServer [3.19.0](#atserver-3190), a record in a reserved
namespace changes only through the verbs that own it. A key uses a
reserved namespace when the last dot-separated segment of its name
begins with `__`, or when any segment is `__e` or begins with
`__manage`, `__atserver`, `__otp`, `__global`, `__private` or
`__config`, compared in the folded form of [§6](#6-the-atkey-model).
`update`, `update:meta` and `delete` refuse such a key with `AT0009` on
every connection, CRAM included, unless it is in the connection's own
enrollment's namespace, `<enrollmentId>.a.__e` (`primary.a.__e` for a
connection that carries no enrollment), or is a cached copy of another
atSign's record. `update` and `update:meta` also refuse, with `AT0009`,
a key in an enrollment's namespace that is shared with another atSign,
such as `@bob:x.<enrollmentId>.a.__e@alice`. A notification may not name
a key in a reserved namespace ([§11.1](#111-notify)), `lookup` and
`llookup` refuse a passcode ([§9.4.2](#942-the-otp-verb)), and
`enroll:list` and the atServer's own checks count only this atSign's
enrollment records.

Since atServer [3.16.5](#atserver-3165), approving an enrollment whose request carries
`apsk` or `apskLegacy` also publishes its `apskLegacy`, or else its
`apsk` as JSON, at `public:_apsk.<enrollmentId>.a.__e@<atSign>`: the
public half of the enrollment's client data signing key.

The `__pkams` namespace is legacy. At startup the atServer deletes any
`public:<app>.<device>.pkam.__pkams.__public_keys@<atSign>` record left
for an enrollment.

### 6.6 atKey examples

| Wire form                              | Shape   | Hidden? | Cached? |
|----------------------------------------|---------|---------|---------|
| `public:phone.wavi@alice`              | Public  | No      | No      |
| `public:_diagnostics@alice`            | Public  | Yes     | No      |
| `public:__location.wavi@alice`         | Public  | Yes     | No      |
| `phone.wavi@alice`                     | Self    | No      | No      |
| `_settings.wavi@alice`                 | Self    | Yes     | No      |
| `@bob:phone.wavi@alice`                | Shared  | No      | No      |
| `@bob:_handshake.wavi@alice`           | Shared  | No      | No      |
| `cached:public:publickey@alice`        | Public  | No      | Yes     |
| `cached:@bob:phone.wavi@alice`         | Shared  | No      | Yes     |
| `local:cache.myapp@alice`              | Local   | No      | No      |
| `private:blocklist@alice`              | Private | —       | —       |
| `privatekey:signing_keypair_generated` | Private | —       | —       |

---

## 7. The metadata fragment

A **metadata fragment** is a sequence of `:tag:value` segments embedded
in the `update`, `update:meta`, and `notify` verbs. The atServer also
keeps metadata that has no tag, which it sets itself: `createdBy`,
`updatedBy`, `status`, `version` and `refreshAt`. Unrecognised tags
must be rejected by an atServer (servers tighten the surface; clients
should not send tags they don't understand). The atServer matches tag
names, and the values `true` and `false`, in any case: `:TTL:60` reads
as `:ttl:60`. It does not relax their order (§7.2).

### 7.1 Catalogue

Source of truth: `at_commons/lib/src/verb/syntax.dart`'s
`metadataFragment`.

| Wire tag          | Type     | Description                                                                                                                               |
|-------------------|----------|-------------------------------------------------------------------------------------------------------------------------------------------|
| `ttl`             | int (ms) | Time-to-live, in ms from the write that sets it (see below). `0` = no expiry.                                                             |
| `ttb`             | int (ms) | Time-to-birth. For `ttb` ms after the write that sets it, `llookup`, `scan`, and an unauthenticated or `pol` `lookup` do not see the key. |
| `ttr`             | int (s)  | Time-to-refresh, in seconds, for another atServer's cached copy. `-1` = cache indefinitely; positive = refresh interval.                  |
| `ccd`             | bool     | Cascade-delete. If `true`, deleting the original key deletes its cached copies.                                                           |
| `cAt`             | ISO 8601 | `createdAt` — UTC timestamp of creation. Regex: `\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z` (fractional seconds optional).           |
| `uAt`             | ISO 8601 | `updatedAt` — UTC timestamp of most recent update.                                                                                        |
| `eAt`             | ISO 8601 | `expiresAt`. Derived from `ttl`; since atServer [3.16.5](#atserver-3165) an asserted value is stored instead (see below).                                   |
| `aAt`             | ISO 8601 | `availableAt`. Derived from `ttb`; since atServer [3.16.5](#atserver-3165) an asserted value is stored instead (see below).                                 |
| `dataSignature`   | string   | Signature over a public value or, in a `notify:all` notification, over the notified key (RSA, SHA-256, base64). See [§14.2](#142-public-data-signatures) for the keys that make them. |
| `sharedKeyStatus` | enum     | Shared-key status (`localUpdated`, `remoteUpdated`, `sharedWithNotified`, etc.). The atServer neither stores nor returns it.              |
| `isBinary`        | bool     | `true` if the value is binary; the reference SDK carries it as Base2e15 text ([§4.5](#45-binary-values)).                                 |
| `isEncrypted`     | bool     | `true` if the value is ciphertext.                                                                                                        |
| `sharedKeyEnc`    | string   | The shared symmetric key, RSA-encrypted to the recipient's encryption public key. Inline in metadata.                                     |
| `pubKeyHash`      | string   | Hash of the recipient public key that encrypted `sharedKeyEnc`, to detect key rotation. Stored only with `hashingAlgo`.                   |
| `pubKeyCS`        | string   | MD5 hex digest of the recipient public key that encrypted `sharedKeyEnc`. Older than `pubKeyHash`; see Appendix B.4.                      |
| `hashingAlgo`     | enum     | Algorithm for `pubKeyHash`. The reference SDK writes `sha512`; the atServer stores any value.                                             |
| `encoding`        | string   | Encoding of the value if not raw UTF-8 (e.g. `base64`).                                                                                   |
| `encKeyName`      | string   | Name of the symmetric key used to encrypt the value (resolves to a key name in the owner's keystore).                                     |
| `encAlgo`         | string   | Symmetric algorithm used to encrypt the value (e.g. `AES/SIC/PKCS7Padding`).                                                              |
| `ivNonce`         | string   | Base64 IV / nonce used in symmetric encryption of the value.                                                                              |
| `skeEncKeyName`   | string   | Name of the public key that wrapped `sharedKeyEnc`.                                                                                       |
| `skeEncAlgo`      | string   | Algorithm used to wrap `sharedKeyEnc` (default `RSA`).                                                                                    |
| `immutable`       | bool     | If `true`, the key cannot be updated; deletion requires `:force:`.                                                                        |
| `appMetadata`     | string   | Base64 of a UTF-8 JSON object whose non-empty string `providerId` names the crypto provider for the value (see below).                    |

The grammar admits a sign on `ttl`, `ttb` and `ttr` (`(-?)\d+`), but
the atServer refuses a negative `ttl` or `ttb`, and a `ttr` below
`-1`, with `AT0003`.

`ttl` and `ttb` count from the write that sets them, and a write that
sets both expires `ttb` + `ttl` ms after it. `ttl:0` clears an expiry.
Since atServer [3.16.5](#atserver-3165), an `update` or `update:meta` that sets neither
`ttl` nor `eAt` keeps the stored `expiresAt`, one that sets neither
`ttb` nor `aAt` keeps the stored `availableAt`, and a `ttl` sent
without `ttb` counts from the write alone, whatever `ttb` the record
holds.

An update notification with no `ttr`, or `ttr:0`, does not cache the
value at the recipient's atServer.

Since atServer [3.13.0](#atserver-3130) (at_commons 5.10.0), the grammar takes `cAt`,
`uAt`, `eAt` and `aAt`. Since atServer [3.16.5](#atserver-3165), the atServer stores
an asserted value, truncated to milliseconds, in place of the one it
would set or derive. An `update` or `update:meta` that asserts `eAt`
with no `ttl`, or `ttl:0`, also stores the `ttl` that `eAt` implies;
`aAt` and `ttb` work the same way.

On `update` and `update:meta`, a string tag that the command omits
keeps its stored value, and one sent as the literal `null` clears it:
`dataSignature`, `sharedKeyEnc`, `pubKeyCS`, `encoding`, `encKeyName`,
`encAlgo`, `ivNonce`, `skeEncKeyName` and `skeEncAlgo`. A `null` does
not clear `pubKeyHash` or `appMetadata`.

`encKeyName`, `encAlgo`, `skeEncKeyName` and `skeEncAlgo` are
optional, and at_commons defines what an absent one means: for
`encKeyName`, the inline `sharedKeyEnc`, else the default shared key;
for `encAlgo`, `AES/SIC/PKCS7Padding` for a value; for
`skeEncKeyName`, the recipient's `public:publickey`; and for
`skeEncAlgo`, `RSA`. When the reference SDK encrypts with its `legacy`
crypto provider, it sets `ivNonce` and none of these four.

Since atServer [3.14.0](#atserver-3140) (at_commons 5.11.0), `appMetadata` may carry
provider-owned fields beside `providerId`. The reference SDK sets it
on each value it encrypts, with `providerId` `legacy` unless the app
configures another provider. The atServer refuses, with `AT0003`, a
value that does not decode to such an object. Otherwise it stores,
returns and forwards it without acting on it, except that since atServer
[3.18.1](#atserver-3181) it writes, keeps and drops the `apskLinks` on an enrollment's
`_apsk` record
([§9.4.4](#944-linking-an-enrollments-client-data-signing-keys-enrolllink)).
An `update` or `update:meta` that omits it, or sends `null`, keeps the
stored value.

### 7.2 Tag ordering

Metadata tags appear in a defined order in the regex. Implementations
producing wire commands SHOULD emit tags in regex-declared order:
`ttl, ttb, ttr, ccd, cAt, uAt, eAt, aAt, dataSignature,
sharedKeyStatus, isBinary, isEncrypted, sharedKeyEnc, pubKeyCS,
pubKeyHash, hashingAlgo, encoding, encKeyName, encAlgo, ivNonce,
skeEncKeyName, skeEncAlgo, immutable, appMetadata`. Servers parse via
the canonical regex which enforces this order; deviating produces a
syntax error.

---

## 8. The atDirectory protocol

The atDirectory speaks a tiny subset of the protocol: it accepts an
atSign and returns the address of that atSign's atServer.

### 8.1 Connect

Open a TLS connection to the atDirectory address (default
`root.atsign.org:64`). The atDirectory sends a single `@` byte as its
prompt. Since atServer [3.19.0](#atserver-3190), a client that
negotiates `http/1.1` by ALPN is answered HTTP instead
([§3.1](#31-atdirectory)).

### 8.2 Lookup

Send the atSign followed by `\n`, without its leading `@` (the
reference SDK strips it). Since atServer [3.19.0](#atserver-3190), the
atDirectory also takes the atSign with its `@`, and looks it up in its
canonical form ([§5](#5-the-atsign-identity-model)): a line that is not
a valid atSign is not found. Before, it lowercased the line and looked
that up:

```text
alice\n
```

### 8.3 Response

When the atSign is found, the atDirectory replies with
`<host>:<port>\r\n@`, where `host` is a hostname or IP and `port` is
the atServer's TLS port for that atSign. When the atSign is not found,
the reply is `null\r\n@`. Clients should also accept `\n@`.

On one connection, the second lookup of an atSign the atDirectory does
not know is answered after a 3-second delay, and the third, after the
same delay, closes the connection without a reply.

### 8.4 Disconnect

The client signals a graceful close with `@exit\n`. After sending,
flush and close the socket. No response is expected.

### 8.5 Worked example

```text
C: <TLS handshake>
S: @
C: alice\n
S: alice.atsign.com:6589\r\n@
C: @exit\n
C: <socket close>
```

The `@exit` verb is the only verb the atDirectory supports beyond
lookups; any other input is treated as an atSign to look up.

---

## 9. Authentication

The atServer recognises 3 authentication mechanisms, all built on
the same `from`-then-prove choreography. Modern atClients use **APKAM**
exclusively, with **CRAM** appearing only during one-time onboarding.

### 9.1 The `from` verb

`from` is the first verb on every atServer connection. It tells the
server which atSign is connecting and, for non-self connections, who
the server should expect to authenticate via `pol`.

#### Syntax

```text
from:<atSign>[:clientConfig:<clientConfig-json>]
```

Source: `at_commons/lib/src/verb/syntax.dart`:

```text
^from:(?<atSign>@?[^:@\s]+)(:clientConfig:(?<clientConfig>\{.+\}))?$
```

The `clientConfig` JSON is optional and free-form. The atServer reads
the following recognised fields and stores them on the connection
metadata:

| Field        | Purpose                                             |
|--------------|-----------------------------------------------------|
| `version`    | Client SDK version string                           |
| `clientId`   | Unique client / device identifier                   |
| `appName`    | Application name                                    |
| `appVersion` | Application version                                 |
| `platform`   | OS or platform tag (e.g. `iOS`, `Android`, `linux`) |

Unrecognised fields are ignored.

Response: the server generates a UUIDv4 challenge and a session
ID and stores the challenge under
`<keyPrefix><sessionId><fromAtSign>` (with TTL 60 s), where
`keyPrefix` is `private:` if the connecting atSign matches the
server's own atSign (self-connect) and `public:` otherwise. This
matters for `pol`: the verifier reads the challenge back under this
name, and the prover stores its copy, signed with its server
authentication signing key, under the same name in its own keystore,
where the verifier fetches it with an unauthenticated `lookup` (see
[§15.2](#152-the-pol-handshake)).

The response payload is:

```text
data:<sessionId><fromAtSign>:<proof>      # if self-connect
data:proof:<sessionId><fromAtSign>:<proof> # if cross-atSign connect
```

Each is followed by the unauthenticated prompt `\n@`.

Source: `at_secondary_server/lib/src/verb/handler/from_verb_handler.dart`
lines 74–103.

Example: self-connect by `@alice` to `@alice`'s atServer:

```text
C: from:@alice\n
S: data:_4af24c03-d732-48f8-a9a2-570e8fb6a01c@alice:d6cac849-9c29-42b0-b0c5-493db62728b9\n@
```

### 9.2 CRAM (`cram`)

CRAM is the **bootstrap-only** authentication mechanism. After
onboarding, the CRAM secret is no longer the canonical credential and
clients must use PKAM/APKAM. CRAM remains in the protocol because
onboarding from a fresh atServer requires a credential that exists
before any keypair has been generated.

#### Syntax

```text
cram:<digest>
```

Source:

```text
^cram:(?<digest>.+$)
```

Digest computation: the client takes the `from` response, strips
the leading `data:` prefix, and computes:

```text
digest = sha512_hex( utf8( <cramSecret> + <strippedFromResponse> ) )
```

For a self-connect, `<strippedFromResponse>` is
`<sessionId><atSign>:<proof>`, the entire body with no further
parsing. Source: `at_lookup/lib/src/at_lookup_impl.dart` lines 540–544.

#### Response

- Success: `data:success\n@<atSign>@`
- Failure: `error:AT0401-Client authentication failed\n@` (connection
  may close)

After success the connection is **authenticated as owner**.

### 9.3 PKAM (`pkam`)

Plain PKAM is the underlying signature-based authentication that APKAM
extends. A client running plain PKAM signs with the atSign's PKAM
private key; under APKAM, each enrollment signs with its own APKAM
private key. Either is a client authentication signing key
([§6.5](#65-reserved-keys)).

#### Syntax

```text
pkam:[signingAlgo:<rsa2048|ecc_secp256r1>:][hashingAlgo:<sha256|sha512>:][enrollmentId:<id>:]<signature>
```

Source:

```text
^pkam:(signingAlgo:(?<signingAlgo>ecc_secp256r1|rsa2048):)?(hashingAlgo:(?<hashingAlgo>sha256|sha512):)?(enrollmentId:(?<enrollmentId>.+):)?(?<signature>.+$)
```

Signature computation: the client signs the `from` challenge
(everything the `from` response payload contained, less any leading
`data:`) with its client authentication signing key, base64-encodes
the result, and sends it as `<signature>`.

Defaults: `signingAlgo:rsa2048`, `hashingAlgo:sha256`. The `enrollmentId`
is omitted for plain PKAM; an APKAM-issued credential includes the
enrollment's ID so the atServer can look up the namespace permission
map.

Response: same as CRAM: `data:success` on success,
`error:AT0401-…` on failure.

### 9.4 APKAM (`enroll`, `otp`, `keys`)

APKAM (Application PKAM) is the modern authentication mechanism. It
issues a per-app, per-device keypair scoped to a namespace permission
map, and supports approval, denial, revocation, and expiry by the
atSign owner.

A high-level flow:

1. **Bootstrap atSign**, the new app generates a fresh APKAM keypair
   and a fresh APKAM symmetric key.
2. **Get an OTP**, the user, on a session with full privilege or
   `__manage` ([§9.4.2](#942-the-otp-verb)), runs `otp:get` and reads
   the OTP to the new app.
3. **`enroll:request`**, the new app submits the request, including
   its APKAM public key, the OTP, the namespace permission map, and
   the APKAM symmetric key encrypted with the **default encryption
   public key** (so only an owner-keys holder can decrypt it).
4. **`enroll:approve`**, the owner-keys holder fetches the request,
   decrypts the APKAM symmetric key, then sends back the
   default encryption private key and self-encryption key, each
   encrypted with the now-shared APKAM symmetric key (with IVs).
   Since atServer [3.18.1](#atserver-3181), the approved enrollment expires no later than
   the approver's own enrollment: the atServer caps its expiry on
   approval.
5. **PKAM-with-enrollmentId**, the new app authenticates as usual via
   `from` + `pkam`, passing `enrollmentId:<id>` so the atServer scopes
   the connection to the granted namespaces.

#### 9.4.1 The `enroll` verb

#### Syntax

```text
enroll:<operation>[:force][:<enrollParams-json>]
```

Source:

```text
^enroll:(?<operation>(?:(request|approve|deny|revoke|listns|infons|list|fetch|unrevoke|delete|update|link)))(:(?<force>force))?(:(?<listNamespace>[^:{\n]+))?(?::)?((?<enrollParams>.+)|(<=list:)<enrollParams>.?)?$
```

`<enrollParams>` is the JSON serialisation of the `EnrollParams` shape
(`at_commons/lib/src/verb/enroll_params.dart`):

| Field                                  | Used by                                        | Description                                                                                                                                                                                             |
|----------------------------------------|------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `enrollmentId`                         | approve/deny/revoke/fetch/delete/unrevoke/link | UUID of the enrollment.                                                                                                                                                                                 |
| `appName`                              | request                                        | Application name, e.g. `"todos"`.                                                                                                                                                                       |
| `deviceName`                           | request                                        | Unique device identifier.                                                                                                                                                                               |
| `namespaces`                           | request                                        | Map of `namespace → permission` (`r`, `w`, `rw`, `rwx`).                                                                                                                                                |
| `otp`                                  | request                                        | One-time passcode from `otp:get`, or the SPP.                                                                                                                                                           |
| `apkamPublicKey`                       | request                                        | New device's APKAM public key (PEM or base64).                                                                                                                                                          |
| `encryptedAPKAMSymmetricKey`           | request                                        | New device's APKAM symmetric key, RSA-encrypted to the default encryption public key.                                                                                                                   |
| `encryptedDefaultEncryptionPrivateKey` | approve                                        | Owner's encryption private key, AES-encrypted with the APKAM symmetric key.                                                                                                                             |
| `encPrivateKeyIV`                      | approve                                        | IV (base64) for the line above.                                                                                                                                                                         |
| `encryptedDefaultSelfEncryptionKey`    | approve                                        | Owner's self-encryption key, AES-encrypted with the APKAM symmetric key.                                                                                                                                |
| `selfEncKeyIV`                         | approve                                        | IV (base64) for the line above.                                                                                                                                                                         |
| `enrollmentStatusFilter`               | list                                           | Optional list of statuses to filter on: `pending`, `approved`, `denied`, `revoked`, `expired`.                                                                                                          |
| `apkamKeysExpiryInMillis`              | request                                        | Lifetime the request asks for, in milliseconds from approval; absent or 0 for none.                                                                                                                     |
| `links`                                | link                                           | For each `kid`, an object holding the `link` to store and, as `expect`, the link the writer read on that key, or `null`. See [§9.4.4](#944-linking-an-enrollments-client-data-signing-keys-enrolllink). |

#### Operations and responses

| Operation  | Response payload                                                                                |
|------------|-------------------------------------------------------------------------------------------------|
| `request`  | `data:{"enrollmentId":"<uuid>","status":"pending"}`, or `"approved"` when approved at once      |
| `approve`  | `data:{"status":"approved","enrollmentId":"<uuid>"}`. Since atServer [3.18.1](#atserver-3181) it also carries `"expiresAt"`, an ISO-8601 UTC string or null |
| `deny`     | `data:{"status":"denied","enrollmentId":"<uuid>"}`                                              |
| `revoke`   | `data:{"status":"revoked","enrollmentId":"<uuid>"}`, with `"cascadedEnrollmentIds":[…]` when it also revoked the enrollments that descend from it, those it approved and those they approved (`:force:` to revoke own enrollment) |
| `unrevoke` | `data:{"status":"approved","enrollmentId":"<uuid>"}`                                            |
| `delete`   | `data:{"enrollmentId":"<uuid>","status":"deleted"}`                                             |
| `fetch`    | `data:{ <full enrollment record JSON> }`                                                        |
| `list`     | `data:{"<enrollKey>":{<enrollment record JSON>}, …}`                                            |
| `link`     | Since atServer [3.18.1](#atserver-3181): `data:{"enrollmentId":"<uuid>","linked":["<kid>", …]}`; see [§9.4.4](#944-linking-an-enrollments-client-data-signing-keys-enrolllink) |

Since atServer [3.18.1](#atserver-3181), a request is refused with `AT0022` unless its
`apkamKeysExpiryInMillis`, when given, is a whole number from 0 to
3155760000000 (36,525 days); before, a negative value also asked for
none.

Since atServer [3.18.1](#atserver-3181), `approve` caps the approved enrollment's expiry at
that of the enrollment the connection authenticated as, when that one
expires, and reports the moment the approved enrollment ends as
`expiresAt`, null when it never does. An earlier expiry the request asked
for is kept. An approval over a CRAM connection, or by an enrollment that
never expires, caps nothing.

The encryption keys stored for an enrollment on approval expire when the
enrollment does.

An `enroll:request` sent over a CRAM connection is the atSign's root
enrollment: it is approved at once and never expires, whatever expiry it
asks for. Since atServer [3.18.1](#atserver-3181) it reports `apkamKeysExpiryInMillis` as
0; a root requested earlier reports the expiry it asked for.

`list` entries and `fetch` carry `apkamKeysExpiryInMillis` and
`expiresAt`. For a pending request, `apkamKeysExpiryInMillis` is the key
expiry it asks for (0 or less for none), and `expiresAt` is when the
request lapses unapproved, 48 hours after it was made by default. Once
a request is approved, they are the term granted and the moment it ends;
a root requested before atServer 3.18.1 is the exception above.
`list` and `fetch` carry `expiresAt` since atServer [3.16.5](#atserver-3165), and `fetch`
carries `apkamKeysExpiryInMillis` since atServer [3.18.1](#atserver-3181).

A pending request is announced to approver apps as a self notification
keyed `<enrollmentId>.new.enrollments.__manage@<atSign>`. Its value
carries `appName`, `deviceName`, `namespace`, the encrypted APKAM
symmetric key under both `encryptedApkamSymmetricKey` and
`encryptedAPKAMSymmetricKey`, and, since atServer [3.18.1](#atserver-3181),
`apkamKeysExpiryInMillis`. A request approved at once is not announced.

#### 9.4.2 The `otp` verb

```text
otp:get[:ttl:<ms>]
otp:put:<spp>[:ttl:<ms>]
otp:list
otp:delete:<otp>
otp:delete:spp
```

Source (at_commons 5.24.0):

```text
^otp:(?<operation>get|put|list|delete)(:(?<otp>(?<=put:)\w{6,}|(?<=delete:)(?:spp|\w{6,})))?(?<=^otp:(?:get|put|put:\w{6,}|list|delete:spp|delete:\w{6,}))(:(?:(?<=^otp:(?:get|put|put:\w{6,}):)ttl:(?<ttl>\d+)))?$
```

An **OTP** is a one-time passcode from `otp:get`. The **SPP**, the
semi-permanent passcode, is the one reusable passcode an atSign holds,
set with `otp:put`. Either is presented as the `otp` of an
unauthenticated `enroll:request` ([§9.4.1](#941-the-enroll-verb)). A
passcode is six or more word characters and matches in any case, as
does `spp`, which names the SPP. The atServer applies the regex
case-insensitively but acts only on a lowercase operation, so
`otp:LIST` is refused with `AT0003`. Since atServer
[3.19.0](#atserver-3190), the atServer also accepts `otp:list` and
`otp:delete`.

#### Operations

- `otp:get` returns `data:<otp>`, a fresh six-character alphanumeric
  OTP that lives for the `ttl` in milliseconds, 5 minutes by default.
  A `ttl` of 0 gives an OTP that never expires; capping it is
  [at_server#2887](https://github.com/atsign-foundation/at_server/issues/2887).
  Since atServer [3.19.0](#atserver-3190), the OTP records the
  namespaces of the enrollment that issued it. One issued over CRAM, or stored by an
  atServer before 3.19.0, records none.
- `otp:put:<spp>` sets the SPP, replacing any SPP already set, and
  returns `data:ok`. Without a `ttl` the SPP never expires.
- `otp:list` returns `data:` and a JSON array of the passcodes the
  caller may manage, as below.
- `otp:delete:<otp>` removes that OTP when the caller may manage it, and
  `otp:delete:spp` removes the SPP when the caller has full privilege.
  `otp:delete:<otp>` never removes the SPP, even when the values match.
  Every well-formed `delete` on an authenticated connection returns
  `data:ok`, whether or not anything was removed, so `delete` reveals
  nothing about which passcodes exist.

Each `otp:list` entry is one of:

```text
{"type":"otp","value":"<otp>","expiresAt":<ms>,"namespaces":{"<namespace>":"<access>"}}
{"type":"spp","value":"<spp>","expiresAt":<ms>}
```

`expiresAt` is milliseconds since the epoch, or -1 for a passcode that
never expires. `namespaces` is present only on an OTP that records them.
An expired passcode is not listed, and an OTP that an `enroll:request`
has spent is gone. A full-privilege caller sees the SPP's value in plain
text.

#### Who may send each operation

Every operation needs an authenticated connection, and is refused with
`AT0401` on any other. **Full privilege** is a CRAM connection, or an
enrollment with write access on both `*` and `__manage`, such as
`*:rw,__manage:rw`; `*` alone or `__manage` alone does not qualify.

- `get`: since atServer [3.16.5](#atserver-3165), full privilege, or an
  enrollment granted `__manage`, read access included. Anyone else is refused with
  `AT0009`. Before, any authenticated connection could send `get`.
- `put`: full privilege only, since atServer [3.19.0](#atserver-3190),
  and anyone else is refused with `AT0009`. Before, an enrollment granted `__manage` could
  set the SPP, and anyone else was answered with `AT0011` and the
  connection closed.
- `list`: full privilege sees every OTP and the SPP. An enrollment
  granted `__manage` sees the OTPs it covers, below, and never the SPP.
  Anyone else is refused with `AT0009`.
- `delete`: as for `list`. A caller who may not remove the passcode
  named still gets `data:ok`, and nothing is removed.

#### Which OTPs an enrollment covers

An enrollment covers an OTP when, for each namespace the OTP records,
the enrollment holds that same namespace with at least the same access
(`rw` covers `r`), or holds no grant for it but holds `*` with that
access. `*` and `__manage` count only when held themselves. Namespaces
are compared whole, in the folded form of [§6](#6-the-atkey-model), so
a grant on `wavi` does not cover an OTP that records `x.wavi`. An OTP
that records no namespaces is covered by full privilege only.

The namespaces an OTP records limit `otp:list` and `otp:delete` only.
They do not yet limit what an `enroll:request` presenting the OTP may
ask for; that is
[at_server#2886](https://github.com/atsign-foundation/at_server/issues/2886).

#### Passcodes in `enroll:request`

Since atServer [3.18.1](#atserver-3181), an `enroll:request` passcode is
accepted only as the SPP or as an OTP issued with `otp:get`, and each OTP admits one
request: the atServer spends an OTP when it accepts it. A passcode
stored outside the `__otp` namespace, as older atServers stored OTPs,
is no longer accepted as an OTP. An SPP stored that way is still
accepted, until `otp:put` sets an SPP, which removes it. A passcode
that is not accepted is refused with `AT0022`.

#### Refusals and compatibility

On an authenticated connection, a command the regex does not match is
refused with `AT0003`: for example `otp:delete` with no passcode, a
`ttl` after `list` or `delete`, and `otp:put:spp`, since `spp` is
shorter than a passcode.
`otp:put` with no passcode matches the regex and, since atServer
[3.19.0](#atserver-3190), is refused with `AT0003` after the privilege
check; before, it was answered with `AT0011` and the connection closed.
After `AT0003` or `AT0009` an authenticated connection stays open.

Since atServer [3.19.0](#atserver-3190), `lookup` and `llookup` refuse a
passcode record with `AT0009`, so passcodes are read only through
`otp:`.

An atServer before 3.19.0 refuses `otp:list` and `otp:delete` with
`AT0003`, as commands its grammar does not know. A client checks that
`info` ([§13.3](#133-info)) lists the features `otp.list` and
`otp.delete`, both `Beta`, before sending them.

#### 9.4.3 The `keys` verb

> **Status: being deprecated.** New implementations should not produce
> `keys` verbs. The current APKAM enrollment flow still emits them
> under the covers, but the verb is on the path to removal, it
> overlaps with `update`/`llookup`/`delete` against the
> `__pkams` / `__manage` namespaces and adds parsing surface without
> adding capability. Track the deprecation work alongside the
> [new AtKeys structure](#c3-new-atkeys-structure) and
> [pluggable encryption](#c1-post-quantum-cryptography-and-crypto-agility)
> projects in Appendix C, both intersect with this verb's role.

```text
keys:<put|get|delete>[:public|private|self][:namespace:<ns>][:appName:<n>][:deviceName:<n>][:keyType:<t>][:encryptionKeyName:<n>][:keyName:<n>] [<value>]
```

Source: see `at_commons/lib/src/verb/syntax.dart`.

`keys` is the storage / retrieval verb for APKAM-issued keys. The
APKAM enrollment flow uses it under the covers to publish the new
device's APKAM public key and to retrieve the encrypted bootstrap keys
on the receiving side. App code rarely calls it directly.

**Response**: `data:-1` on `put` (commit ID; APKAM keys are
non-committed) and `data:<JSON record>` on `get`.

#### 9.4.4 Linking an enrollment's client data signing keys (`enroll:link`)

> **Since atServer [3.18.1](#atserver-3181).**

An enrollment publishes its client data signing keys at
`public:_apsk.<enrollmentId>.a.__e@<atSign>`, from its request or a later
`enroll:update`. Where, as [§6.5](#65-reserved-keys) describes, a key
published there is also the enrollment's client authentication signing key,
its APKAM key, that key takes no link. The value is one bare RSA-2048 public
key, or the list form:

```json
{"v":1,"keys":[{"kid":"<kid>","use":"sign","alg":"<alg>","pub":"<public key>","status":"<status>"}]}
```

`status` is `active` or `retired`, and an entry without one is active. A
**link**
vouches for one of those keys. The atServer keeps an enrollment's links in
one map, `apskLinks`, in that record's `appMetadata`, keyed by `kid`, and
`enroll:link` is the only way to write one. When the record carries no
`appMetadata`, the atServer creates `{"providerId":"legacy","apskLinks":{…}}`,
since a reader requires `providerId`. A reader finds the links in the
record's metadata: `lookup:all` and `plookup:all` return `appMetadata` as a
JSON object, where an `update` carries it as base64.

#### Request and response

```text
enroll:link:{"enrollmentId":"<uuid>","links":{"<kid>":{"link":<link>,"expect":<link or null>}}}
```

| Field          | Description                                                                                                                                                                                       |
|----------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `enrollmentId` | Required. The enrollment whose keys are linked.                                                                                                                                                   |
| `links`        | Required and not empty. For each `kid`, an object holding the link to store as `link`, and as `expect` the link the writer read on that key, or `null` if it read none. `expect` must be present. |

**Response**: `data:{"enrollmentId":"<uuid>","linked":["<kid>", …]}`.

An atServer before 3.18.1 refuses `enroll:link` with `AT0003`, as a command
its grammar does not know, and keeps an authenticated connection open.

#### Who may call it

The enrollment itself, for its own keys; a connection that could approve
it, that is an approved enrollment holding `__manage` explicitly (a `*`
grant does not count) and every namespace the target holds, at the
target's access; or a CRAM connection, as for `enroll:approve`. A target
holding no namespaces can be linked only by itself or over CRAM. Any other
authenticated caller making a well-formed call on an enrollment that exists
is refused with `AT0009`, and nothing is written.

#### What the atServer checks

The atServer writes every link in a call or none of them. A call is
refused, naming what failed, unless:

- the target enrollment is approved;
- each `kid` is one the target's `_apsk` lists, with its public key spelt in
  padded standard base64, and that key is not the target's client
  authentication signing key, the `apkamPublicKey` its enrollment record
  holds, compared as key bytes;
- each link is a JSON object whose `payload`, a JSON object or the base64url
  encoding of one, names the target enrollment and that key's `kid`, `alg`
  and public key as `enrollmentId`, `kid`, `alg` and `pub`;
- each link is at most 16 KiB as JSON, the call's parameters are within
  500 KiB (512,000 bytes) as JSON, and so is the `_apsk` record's value and
  `appMetadata` with every link the record would then hold;
- each `expect` equals, compared as JSON, the link stored on that key, or
  is `null` when none is stored.

A call is also refused when the target's `_apsk` record is immutable or
lists the `kid` more than once. The payload's `enrollmentId` is compared in
the folded form of [§6](#6-the-atkey-model).

A stale `expect` is refused with `AT0032`, so a writer can tell a lost race
from a bad request, read the record again and decide afresh. An immutable
record is refused with `AT0032` too. The request's
required fields and
every other check above are refused with `AT0022`, except the target's own
state: a target that does not exist or is not approved is refused with an
error naming it. Two writers of one key's link therefore cannot lose each
other's write. Beside the links it writes, `enroll:link` keeps only the
stored links that any write of the record keeps
([Other writes of the record](#other-writes-of-the-record)); otherwise a
key's link goes only when another write of the record stops keeping it, or
when the record is deleted.

In the list form, the atServer reads each entry that carries a string
`kid`, `alg` and `pub`, takes its `kid` as written, and ignores `use` and
`status`, so a retired key can take a link. A bare `_apsk` value is one
`rsa2048` key, whose `kid` the atServer derives: the first 8 bytes of the
SHA-256 of the decoded key, as lowercase hex, which is how clients derive
every `kid`. The atServer compares `kid`s exactly. It reads an `_apsk`
value trimmed of surrounding whitespace, as a client does, and a `kid` the
value lists twice takes no link.

#### Links

The atServer checks no more of a link than the above: it never checks a
signature, and a stored link is a claim that whoever reads it verifies. A
reader expects the payload
`{"v":2,"enrollmentId":"<uuid>","kid":"<kid>","alg":"<alg>","pub":"<public key>"}`
in one of two forms:

- a **root link**, signed by a key of `public:pq_signing_root@<atSign>`:
  `{"v":2,"alg":"mldsa65","kid":"<root kid>","payload":{…},"signature":"<base64>"}`.
  The signature is over `at-root-link:` followed by the payload's members,
  in the order they are stored, as JSON with no whitespace, so the atServer
  stores a link's JSON value with its members in the order they were sent;
- a **chain link**, signed by a client data signing key that an enrollment's
  `_apsk` lists, whether another enrollment's or the target's own when it
  links a key it has added: an RFC 7515 JWS in the general JSON
  serialization, carrying the payload base64url-encoded and exactly one
  signature, whose protected header gives `typ` `at-chain-link+jws`, the
  key's `kid` as `kid` and its enrollment as `enid`.

#### Other writes of the record

Every other write of an approved enrollment's `_apsk` record, an
`enroll:update` that republishes it, the publish when an enrollment is
approved, or an `update` or `update:meta` of the record, keeps the links
for the keys the new value still lists, whatever the write sent, and drops
those for keys it no longer lists. `enroll:link`, these writes and a
`delete` of the record run one at a time for each atSign, so each lands
wholly before or after another.

Since atServer [3.18.1](#atserver-3181), these writes, a rotation of the enrollment's client
authentication signing key, and the record's move back when the enrollment
is unrevoked keep a link on a key only while the new value lists that key's
`kid` once, with the `alg` and public key the link's payload names, and
never on the enrollment's client authentication signing key. When such a
write drops the last link from `appMetadata` holding nothing else under the
`providerId` the atServer gives, it drops that `appMetadata` too, and a
publish or republish that changes the value drops a `dataSignature` over
the value it replaces.

Since atServer [3.18.1](#atserver-3181), an `enroll:update` is refused
with `AT0022`, naming the key, when it would leave the enrollment's client
authentication signing key listed in its `_apsk` beside another key, or
carrying a link.

Since atServer [3.18.1](#atserver-3181), an `enroll:update`, an `update` or `update:meta` of
the record, or an `enroll:request` is also refused with `AT0022`, naming
what failed, when the `_apsk` it would leave or carries lists a `kid`
twice, an entry without a string `kid`, `alg` and `pub`, or the
enrollment's client authentication signing key beside another key. An
`enroll:request` is refused before its OTP is spent. A CRAM `update` of
`privatekey:at_pkam_publickey` is refused when `primary`'s `_apsk`, whether
`primary` is approved, revoked or deleted, lists the key it installs beside
another key or with a link. A write that would
take the record, with the links it keeps, over 500 KiB is refused with
`AT0022`; a record that keeps no links is not held to that bound. An
`enroll:update` that republishes an immutable record is refused with
`AT0032`, as an `update` of one is.

Since atServer [3.18.1](#atserver-3181), the publish at `enroll:approve`, a rotation of
`primary`'s key that the atServer makes itself, at startup or on a legacy
`pkam:`, and the move back on unrevoke cannot be refused. Each keeps fewer
links instead: it drops a link on the client authentication signing key,
keeps none when they would take the record over 500 KiB, leaves an
immutable record as it stands, and logs at warning what it drops.

---

## 10. CRUD verbs

`lookup` and `scan` run on any connection and answer from what that
connection may see; see [§10.4](#104-lookup) for `lookup`. A `scan` of
the commit log, or of another atSign's keys, needs a connection
authenticated as the atSign. The other CRUD verbs, `plookup` among them,
need a connection authenticated as the atSign (owner or APKAM).

### 10.1 `update`

Insert or overwrite a value, optionally with metadata.

#### Syntax (positional form)

```text
update[:nc]<metadata>[:public|@<forAtSign>]:<atKey>[@<atSign>] <value>
```

#### Syntax (JSON form)

```text
update[:nc]:json:<json>
```

Source:

```text
^update(:nc(?<noCommit>))?(:json:(?<json>.+)|<metadataFragment>(:(public|@(?<forAtSign>...)))?:(?<atKey>...)(@(?<atSign>...))? (?<value>.+))$
```

Since atServer [3.16.5](#atserver-3165), `:nc` (no-commit) writes no commit-log entry
for the change, removes any entry the key already has, and answers
`data:-1`. From atServer 3.13.0 to 3.15.0 the grammar takes `:nc`, and
the write is committed as usual.

Response: `data:<commitId>` where `commitId` is the integer
commit-log sequence number assigned to the operation. The reference
SDK's sync takes it as the atServer's acknowledgement of a pushed
write. A write to a key the commit log never records, a `public:_`
key (but not `public:__`), or a `local:`, `private:` or `privatekey:`
key, also answers `data:-1`.

```text
C: update:@bob:phone.wavi@alice +1 555 0100\n
S: data:42\n@alice@
```

Setting metadata at update time:

```text
C: update:ttr:86400:ccd:true:isEncrypted:true:@bob:secret.myapp@alice <ciphertext>\n
S: data:43\n@alice@
```

JSON form:

```text
C: update:json:{"atKey":"phone.wavi","sharedBy":"@alice","sharedWith":"@bob","value":"+1 555 0100","metadata":{"ttl":60000,"isPublic":false,"isBinary":false,"isEncrypted":false}}\n
S: data:44\n@alice@
```

`atKey` is a string. The atServer builds the stored key as
`[public:][<sharedWith>:]<atKey>[<sharedBy>]`, with `public:` when
`metadata.isPublic` is `true`; the example stores
`@bob:phone.wavi@alice`. `metadata` is required, and must hold
`isPublic`, `isBinary` and `isEncrypted` as booleans; a document
without them is refused. Its other fields are optional and take the
wire tags' names (§7.1), except that the timestamps are `createdAt`,
`updatedAt`, `expiresAt` and `availableAt`, and `pubKeyHash` is an
object, `{"hash":"…","hashingAlgo":"…"}`. Since atServer
[3.19.0](#atserver-3190), an `atKey` that ends in `@<owner>` is refused
with `AT0016` unless the owner is this atServer's atSign, as a
`sharedBy` naming another atSign is.

The atServer refuses to `update` a `local:`, `cached:` or `private:`
key, or a name that is not a valid atKey, unless a reserved key from
either table in [§6.5](#65-reserved-keys) appears within the name. A
`privatekey:` name counts only at the end of the name,
`@<recipient>:shared_key@<atSign>` only at its start, `configkey` and
`_` names only as the whole name, and any other reserved key wherever
it appears. So `update` stores
`cached:public:publickey@<atSign>`,
`cached:public:signing_publickey@<atSign>` and
`private:blocklist@<atSign>`, and also names such as
`cached:shared_key.bob@alice`, answered with a commit id, and
`local:shared_key.bob@alice`, answered `data:-1`. Only the JSON form
can name a `local:`, `cached:` or `private:` key. The atServer also
refuses to overwrite a record that carries `immutable:true`. Since
atServer [3.16.5](#atserver-3165), a record whose expiry has passed counts as absent, so
an expired immutable record no longer blocks the write. Since atServer
[3.19.0](#atserver-3190), `update` refuses a key in a reserved
namespace, and a key in an enrollment's namespace that is shared with
another atSign, with `AT0009` ([§6.5](#65-reserved-keys)).

When the write creates the key, `ccd` is kept only if the request
also sets a non-zero `ttr`.

### 10.2 `update:meta`

Update only the metadata of a key. Same metadata fragment as
`update`, but it comes after the atKey, and the owner's atSign is
required. Useful for changing TTL or marking a key encrypted after
the fact.

#### Syntax

```text
update:meta[:nc][:public|@<forAtSign>]:<atKey>@<atSign><metadata>
```

```text
C: update:meta:@bob:phone.wavi@alice:ttl:600000:isEncrypted:true\n
S: data:45\n@alice@
```

On a key the atServer does not hold, `update:meta` creates a record
with that metadata and no value. The response, `:nc` and the
refusals are as for `update`. On an APKAM connection, `update:meta`
needs `rw` access to the key's namespace, as `update` does.

### 10.3 `delete`

Remove an atKey.

#### Syntax

```text
delete[:dAt:<timestamp>][:nc][:force][:priority:<low|medium|high>][:cached][:public|@<forAtSign>]:<atKey>[@<atSign>]
```

Source:

```text
^delete(:dAt:...)?(:nc)?(:force)?(:priority:...)?(:cached)?(:public|@<forAtSign>)?:<atKey>(@<atSign>)?$
```

- `:dAt:<timestamp>`, the deletion time the caller asserts, an ISO
  8601 UTC timestamp as for `cAt` (§7.1). Since atServer [3.16.5](#atserver-3165), the
  atServer stamps the DELETE commit entry with it. From atServer 3.13.0
  to 3.15.0 it is accepted and not used.
- `:nc`, no commit. Since atServer [3.16.5](#atserver-3165), no entry is written, any
  entry the key already has is removed, and the response is
  `data:-1`. From atServer 3.13.0 to 3.15.0 it is accepted, and the
  delete is committed as usual.
- `:force`, required to delete an `immutable:true` key.
- `:priority:<low|medium|high>`, the priority of the auto-notification
  described below.
- `:cached`, delete a cached copy on this server (does not affect the
  origin).

`delete` refuses to remove this atServer's own `publickey`,
`signing_publickey` and `signing_privatekey`, whatever `public:` or
`@<recipient>:` scope the command gives them, `at_pkam_publickey`, and
any key listed under `hive.protectedKeys` in the atServer's
configuration. A `:cached` delete is not refused. Since atServer
[3.19.0](#atserver-3190), `delete` also refuses a key in a reserved
namespace with `AT0009` ([§6.5](#65-reserved-keys)).

Response: `data:<commitId>`, even when the key did not exist (see
[§D.13](#d13-delete-is-idempotent-and-always-commits)). A key the
commit log never records, a `public:_` key (but not `public:__`) or
`privatekey:at_secret`, answers `data:-1`.

```text
C: delete:@bob:phone.wavi@alice\n
S: data:46\n@alice@
```

If `autoNotify` is enabled and the key was a shared key with a
recipient on a different atServer, the server emits a `notify:delete`
to the recipient, see [§11](#11-notification-verbs).

### 10.4 `lookup`

Read a value. What `lookup` answers depends on the connection it
arrives on:

- On a connection authenticated as the atSign (owner or APKAM), a key
  owned by this atServer's atSign is read from its own keystore. A key
  owned by another atSign is fetched from that atSign's atServer over a
  `pol`-authenticated connection (see
  [§15.3](#153-cross-atsign-lookup)), and may be answered from a cached
  copy, per the key's `ttr`, unless `bypassCache:true` is set.
- On a connection where another atServer has proved itself as `@x` with
  `pol`, `lookup:<atKey>@<this atSign>` returns the record this atSign
  shares with `@x`, `@x:<atKey>@<this atSign>`.
- On a connection that has not authenticated,
  `lookup:<atKey>@<this atSign>` returns the public record
  `public:<atKey>@<this atSign>`.

Since atServer [3.18.1](#atserver-3181), on a connection not authenticated as the atSign
(a `pol` connection, or one that has not authenticated at all), a
`lookup:` may name only this atServer's atSign as the key's owner. A
lookup naming another owner is refused with `AT0009`, and the connection
is closed. Before 3.18.1, a lookup naming another owner was answered as
the bullets above describe, from the `public:` record or the record
shared with `@x` under that name, so it could read only what that
connection may see; the change is that it is now refused.

#### Syntax

```text
lookup[:bypassCache:<true|false>][:meta|all]:<atKey>@<atSign>
```

Source:

```text
^lookup:(bypassCache:(?<bypassCache>true|false):)?((?<operation>meta|all):)?(?<atKey>(?:[^:]).+)@(?<atSign>[^:@\s]+)$
```

- Default operation: returns the value only.
- `meta:`, return metadata only.
- `all:`, return both value and metadata.
- `bypassCache:true`, force a fetch from the remote rather than
  returning a cached copy.

#### Response shapes

Default:

```text
data:<value>
```

`meta:`:

```text
data:{"createdBy":"@bob","updatedBy":"@bob","createdAt":"…","updatedAt":"…","ttl":null,"ttb":null,"ttr":10000,"ccd":false,"isBinary":false,"isEncrypted":true, …}
```

`all:`:

```text
data:{"key":"@alice:country.wavi@bob","data":"USA","metaData":{ … }}
```

If the remote atServer is unreachable: `error:AT0007-atServer not found.`

Since atServer [3.19.0](#atserver-3190), a `lookup` of a passcode record
is refused with `AT0009` ([§9.4.2](#942-the-otp-verb)).

### 10.5 `plookup`

Read another atSign's public record through this atServer, on a
connection authenticated as the atSign. The atServer fetches
`public:<atKey>@<atSign>` from the owner's atServer with an
unauthenticated `lookup:`, and may answer from its own cached copy, per
the record's `ttr`, unless `bypassCache:true` is set.

#### Syntax

```text
plookup[:bypassCache:<true|false>][:meta|all]:<atKey>@<atSign>
```

Same response shape as `lookup`.

### 10.6 `llookup`

Local lookup, read a key from this atServer's own keystore. Returns
the stored value verbatim (no resolution, no remote fetch).

#### Syntax

```text
llookup[:meta|all][:cached][:public|@<forAtSign>]:<atKey>@<atSign>
```

Source:

```text
^llookup(:(?<operation>meta|all))?(:cached)?(:(public|@<forAtSign>))?:<atKey>@<atSign>$
```

- `:cached:`, look up a cached copy on this atServer.

A key the atServer does not hold answers error `AT0015`. A key past
its expiry (`ttl`), or not yet available (`ttb`), answers `data:null`
(see [§D.4](#d4-expired-keys-return-null-instead-of-an-at0015-error)).

On an APKAM connection, a key that is not `public:` must be one the
enrollment may read, which for a key in a namespace means `r` or `rw`
access to that namespace. A `public:` key, cached or not, is not
checked.

Since atServer [3.19.0](#atserver-3190), an `llookup` of a passcode
record is refused with `AT0009` ([§9.4.2](#942-the-otp-verb)).

Response is identical in shape to `lookup`.

### 10.7 `scan`

Enumerate keys.

#### Syntax

```text
scan[:cl][:showhidden:<true|false>][:@<forAtSign>][:page:<n>][ <regex>]
```

Source:

```text
^scan$|scan(:cl)?(:showhidden:...)?(:@<forAtSign>)?(:page:...)?( <regex>)?$
```

- `:cl`, since atServer [3.16.5](#atserver-3165), list commit-log entries instead of
  keys (see Response below). It needs a connection authenticated as
  the atSign, and naming another atSign with it is refused. From
  atServer 3.13.0 to 3.15.0 `:cl` is accepted, and the scan answers as
  it would without it.
- `:showhidden:true`, on an authenticated connection, also list the
  hidden keys: keys that start with `_` (such as `_x.wavi@alice`) and
  `public:__` keys. `public:_` keys with a single underscore,
  `private:` keys and `privatekey:` keys are never listed. A key that
  starts with `@` (a shared key) is not hidden, whatever its name.
- `:@<forAtSign>`, naming another atSign, asks that atSign's atServer,
  over a `pol` connection, for the keys it shares with this atSign
  (see [§15](#15-the-inter-atserver-protocol)). It needs a connection
  authenticated as the atSign. Only `<regex>` is passed on, and the
  response is that atServer's. Naming this atServer's own atSign
  is an ordinary scan.
- `:page:<n>`, accepted by the grammar and ignored: the whole result
  comes back in one response.
- `<regex>` (after a space), a regular expression matched anywhere in
  each stored key name, such as `@bob:phone.wavi@alice`. It cannot
  contain whitespace.

Keys past their expiry (`ttl`), or not yet available (`ttb`), are not
listed. What else `scan` lists depends on the connection:

- Not authenticated: the `public:` keys, without the `public:` prefix.
  `public:_` keys, `public:__` keys among them, are left out.
- `pol`, as `@<x>`: the keys shared with `@<x>`, without the `@<x>:`
  prefix.
- CRAM: every key that `:showhidden` does not leave out.
- APKAM: the public keys, and the keys the enrollment may read (`r` or
  `rw`) through their namespace. Other keys with no `.` in their name
  are left out unless the enrollment holds `*`, and
  `shared_key.<recipient>@<atSign>` is listed for every approved
  enrollment. Non-public `__manage` keys, and
  other enrollments' `<enrollmentId>.a|r|d.__e` keys, are always left
  out.

#### Response

```text
data:["public:phone.wavi@alice","@bob:email.wavi@alice", …]
```

A JSON array of strings, on a single line. Empty result is `data:[]`.

`scan:cl` answers a JSON array of objects, one per key, in ascending
`commitId` order. DELETE entries are included. The hidden-key, regex
and enrollment filters apply as for a keystore scan on that
connection.

```text
data:[{"atKey":"phone.wavi@alice","operation":"+","commitId":42,"opTime":"2026-10-16T10:52:58.123000Z"}, …]
```

`operation` is `+` or `*` for a write, `#` for a metadata-only write
and `-` for a delete. `opTime` is ISO 8601 UTC with six fractional
digits, or `null`.

The `regex` filter operates on key **structure**, not
value contents, value-level filtering is impossible because the
server has no plaintext to filter against ([§14](#14-end-to-end-encryption)).

---

## 11. Notification verbs

Notifications are the protocol's pub/sub mechanism. An owner emits a
notification when shared data changes; the recipient's atServer
receives it via inter-atServer delivery
([§15](#15-the-inter-atserver-protocol)) and surfaces it to the
recipient's atClient via `monitor`.

### 11.1 `notify`

Emit a notification.

#### Syntax

```text
notify[:id:<id>][:<update|delete>][:messageType:key][:priority:<low|medium|high>][:strategy:<all|latest>][:latestN:<n>][:notifier:<n>][:ttln:<ms>]<metadata>:[public|@<forAtSign>]:<atKey>[@<atSign>][:<value>]
```

Source: see `at_commons/lib/src/verb/syntax.dart` `notify`.

| Tag               | Description                                                                                       |
|-------------------|---------------------------------------------------------------------------------------------------|
| `id`              | Caller-supplied notification ID. Server generates one if omitted.                                 |
| `update\|delete`  | Operation. Defaults to `update`.                                                                  |
| `messageType:key` | Notification refers to an atKey change. `text` is retired since atServer [3.18.1](#atserver-3181) ([Appendix B.3](#b3-notify-messagetypetext)). |
| `priority`        | Delivery priority hint.                                                                           |
| `strategy:all`    | Deliver every notification (default).                                                             |
| `strategy:latest` | Coalesce: deliver only the most recent `<latestN>` for the same atKey if recipient was offline.   |
| `latestN`         | Coalesce window size. Used with `strategy:latest`.                                                |
| `notifier`        | Identifier of the notifying subsystem. Defaults to `SYSTEM`.                                      |
| `ttln`            | Notification time-to-live in ms. After expiry the server gives up delivering and marks `expired`. |

Response: `data:<notificationId>` on success.

```text
C: notify:update:ttr:-1:isEncrypted:true:@bob:phone.wavi@alice <ciphertext>\n
S: data:7c6c8d7d-7e0e-4ab4-9c7d-4b07e1e84a52\n@alice@
```

Since atServer [3.19.0](#atserver-3190), a `notify` or `notify:all` from
a client is refused with `AT0003` when its atKey's name holds a
character other than an ASCII letter or digit, `_`, `.`, `-`, `'`, `*`
or `"`, or one in the ranges [§5](#5-the-atsign-identity-model) allows
in an atSign inside an atKey, and with `AT0009` when the name uses a
reserved namespace
([§6.5](#65-reserved-keys)). A `notify` from another atServer that
breaks either rule is answered `data:success` and dropped.

### 11.2 `notify:all`

Emit one notification to multiple recipients in one round-trip. The
recipients are a comma-separated list (no `@` prefix) where the
single `forAtSign` segment normally goes.

#### Syntax

```text
notify:all:[<update|delete>:][messageType:<key|text>:][ttl:<ms>:][ttb:<ms>:][ttr:<s>:][ccd:<bool>:]<recipient,recipient,…>:<atKey>[@<atSign>][:<value>]
```

The grammar still parses `messageType:text`; since atServer [3.18.1](#atserver-3181) the
atServer refuses it ([Appendix B.3](#b3-notify-messagetypetext)).

Response: a JSON map of `recipient → notificationId`:

```text
data:{"@bob":"…uuid…","@colin":"…uuid…"}
```

### 11.3 `notify:list`

List notifications received by the current atSign.

#### Syntax

```text
notify:list[:<fromDate>][:<toDate>][:<regex>]
```

Dates are `YYYY-MM-DD`. Source:

```text
^notify:list(:(?<fromDate>\d{4}-[01]?\d?-[0123]?\d?))?(:(?<toDate>...))?(:(?<regex>[^:]+))?
```

Response: JSON array of notification records:

```text
data:[{"id":"…","from":"@bob","to":"@alice","key":"@alice:phone.wavi@bob","value":null,"operation":"update","epochMillis":1603714720965}, …]
```

If the connection is `pol`-authenticated, returns notifications **sent
to** that atSign instead.

### 11.4 `notify:status`

Query the delivery status of a notification by ID.

#### Syntax

```text
notify:status:<notificationId>
```

Response: `data:<status>` where status is one of:

| Status        | Meaning                                             |
|---------------|-----------------------------------------------------|
| `queued`      | Not yet sent.                                       |
| `delivered`   | Successfully delivered to the recipient's atServer. |
| `undelivered` | Tried and failed; will retry per server policy.     |
| `errored`     | Delivery errored permanently.                       |
| `expired`     | TTL elapsed before delivery succeeded.              |

### 11.5 `notify:fetch`

Fetch a full notification record by ID.

#### Syntax

```text
notify:fetch:<notificationId>
```

Response: `data:<JSON notification record>`. If the notification
was expired or never existed, returns
`data:{"id":"<id>","notificationStatus":"expired"}`.

### 11.6 `notify:remove`

Remove a notification from the local notification log. Note: this is
log housekeeping; it does **not** send a `notify:delete` to the
recipient.

#### Syntax

```text
notify:remove:<notificationId>
```

Response: `data:success`.

### 11.7 `monitor`

Open a long-lived stream of received notifications.

#### Syntax

```text
monitor[:strict][:selfNotifications][:multiplexed][:<epochMillis>][ <regex>]
```

Source:

```text
^monitor(:strict)?(:selfNotifications)?(:multiplexed)?(:<epochMillis>)?( <regex>)?$
```

| Modifier            | Effect                                                                                              |
|---------------------|-----------------------------------------------------------------------------------------------------|
| `strict`            | Emit **only** notifications matching the regex; suppress server-control notifications (e.g. stats). |
| `selfNotifications` | Include notifications the connecting atSign emitted itself.                                         |
| `multiplexed`       | Accepted, and has no effect.                                                                        |
| `<epochMillis>`     | Replay notifications received at or after this timestamp.                                           |
| `<regex>`           | Filter notifications by atKey regex.                                                                |

Response: a stream. Each notification arrives as one line:

```text
notification: {"id":"…","from":"@bob","to":"@alice","key":"@alice:phone.wavi@bob",…}
```

Lines are not framed by the standard `\n@…@` prompt. The connection
remains open until either side closes it. Server-control
notifications use the same `notification: …` prefix unless `:strict`
is set.

`:multiplexed` is accepted and has no effect. A monitor connection
takes further commands like any other (see [§4.7](#47-pipelining)),
and a notification may arrive between a command and its response.

---

## 12. The sync verb

`sync:from` walks the commit log of an atServer from a given commit ID
to the current head, returning the intervening operations.

### 12.1 `sync:from`

#### Syntax

```text
sync:from:<from_commit_seq>[:limit:<n>][:skipDeletesUntil:<n>][:<regex>]
```

Source:

```text
^sync:from:(?<from_commit_seq>[0-9]+|-1)(:limit:(?<limit>\d+))?(:skipDeletesUntil:(?<skipDeletesUntil>\d+))?(:(?<regex>.+))?$
```

- `<from_commit_seq>`, last commit ID the caller has seen. `-1`
  requests the full commit log from the start.
- `:limit:<n>`, max entries returned in this round-trip. Caller
  paginates by repeating with the highest commit ID seen.
- `:skipDeletesUntil:<n>`, suppress delete operations whose
  `commitId <= n`. Used to elide tombstones older than a known sync
  high-water mark.
- `:<regex>`, filter entries by atKey regex.

Response: JSON array of commit-log entries:

```text
data:[{"atKey":"@bob:phone.wavi@alice","operation":"+","opTime":"2026-05-05T10:30:00.000Z","commitId":42,"value":"<ciphertext>","metadata":{"ttr":-1,"ccd":false,"isEncrypted":true}},
      {"atKey":"@bob:shared_key.wavi@alice","operation":"-","opTime":"2026-05-05T10:31:42.000Z","commitId":43}]
```

Operations: `+` or `*` for a write, `#` for a metadata-only write,
`-` for a delete.

The legacy `sync:<from_commit_seq>` syntax (without `:from:`) is
retained for backward compatibility and is documented in
[Appendix B](#appendix-b-legacy-and-deprecated). New clients must
use `sync:from`.

---

## 13. Server-admin and utility verbs

### 13.1 `config`

Manage server-side block lists and configuration parameters. Owner-
authenticated only.

#### Syntax

```text
config:block:add:@<atSign>[ @<atSign> …]
config:block:remove:@<atSign>[ @<atSign> …]
config:block:show
config:set:<key>=<value>
config:reset:<key>
config:print:<key>
```

The block list, once populated, is consulted by `from`, a blocked
atSign receives `error:AT0013-Connection Exception` and the connection
is closed.

Response: `data:success` for mutating operations, `data:[…]` for
`show` (a JSON array of blocked atSigns), `data:<value>` for `print`.

### 13.2 `stats`

Return server statistics.

#### Syntax

```text
stats[:<id>[,<id>…]][:<regex>]
```

Source:

```text
^stats(?<statId>:((?!0)\d+)?(,(\d+))*)?(:(?<regex>(?<=:3:|:15:).+))?$
```

Without IDs, all statistics are returned. Statistics are identified
by integer IDs:

| ID | Name                        | Value type              |
|----|-----------------------------|-------------------------|
| 1  | `activeInboundConnections`  | int                     |
| 2  | `activeOutboundConnections` | int                     |
| 3  | `lastCommitId`              | int                     |
| 4  | `secondaryStorageSize`      | int (bytes)             |
| 5  | `topAtSigns`                | `{<atSign>: <hits>, …}` |
| 6  | `topKeys`                   | `{<atKey>: <hits>, …}`  |

(Servers may expose additional IDs, IDs 11 and 15 take regex filters
per the syntax; see source for current set.)

#### Response

```text
data:[{"id":"1","name":"activeInboundConnections","value":"1"},
      {"id":"3","name":"lastCommitId","value":"42"}, …]
```

### 13.3 `info`

Return server runtime information.

#### Syntax

```text
info[:brief|mtls|mtlsbrief]
```

#### Response shapes

`info` (full):

```text
data:{"version":"3.0.28","uptimeAsWords":"1 hours 35 minutes 29 seconds","features":[ {…feature record…}, … ]}
```

`info:brief`:

```text
data:{"version":"3.0.28","uptimeAsMillis":5855295}
```

`info:mtls`:

```text
data:{"mtls_fullchain":"<PEM>"}
```

`info:mtlsbrief`:

```text
data:{"mtls_fullchain_last_modified":"2026-05-05T08:00:00.000Z","mtls_privkey_last_modified":"2026-05-05T08:00:00.000Z"}
```

`info` may be called unauthenticated; servers may restrict per
deployment.

### 13.4 `noop`

Sleep for the given number of milliseconds, then respond. Used as a
keep-alive / latency probe.

#### Syntax

```text
noop:<delayMillis>
```

`<delayMillis>` ≤ 5000.

Response: `data:ok` after the delay. Out-of-range values produce
`error:AT0022-Exception: noop:<durationInMillis> where the duration
maximum is 5000 milliseconds`.

### 13.5 `batch`

Execute multiple verbs in a single round-trip. Each member of the
batch is independently parsed and dispatched; failures are per-entry.

#### Syntax

```text
batch:<json-array>
```

Where `<json-array>` is `[{"id":<n>,"command":"<verb>"}, …]` and each
`<verb>` is a single-line verb without the trailing `\n`.

Response: array of `{id, response}` pairs in submission order:

```text
data:[{"id":1,"response":{"data":"42"}},{"id":2,"response":{"data":"43"}}]
```

Since atServer [3.19.0](#atserver-3190), a batch that is not a JSON array
is refused with `AT0003`. An entry that is not an object with a string
`command`, whose `id` is present but not an integer, or whose command
names no verb the atServer has, is answered with `AT0003` in its place,
and the rest of the batch runs. Before, an entry naming no verb was left
out of the response.

---

## 14. End-to-end encryption

End-to-end encryption is **entirely an atClient concern**. For an
encrypted value, the atServer stores ciphertext in the `value` field,
metadata about how the value was encrypted and, for a value shared
with another atSign, the encrypted shared key in the `sharedKeyEnc`
metadata field. Nothing in the atServer decrypts what it stores, and
no server-side behaviour in this specification depends on
understanding what the encrypted material means.

Not everything an atServer stores is ciphertext. Public values and
public keys are plaintext by design, as is any value an atClient sends
unencrypted.

This section describes how the wire-level metadata fields hang together
so an atClient implementer can interoperate with the reference SDK. It
does **not** specify the encryption protocol normatively. In the
reference SDK the scheme lives in the `at_client` package's crypto
providers, built on primitives from
[`at_chops`](https://pub.dev/packages/at_chops), and it is allowed to
evolve: post-quantum cryptography is in active development (see
[Appendix C.1](#c1-post-quantum-cryptography-and-crypto-agility)).

### 14.1 Two layers

The reference SDK's `legacy` crypto provider encrypts a value shared
with another atSign in two layers:

1. **Symmetric layer.** Each atSign holds one AES-256 **shared key**
   per recipient. A value `@alice` shares with `@bob` is encrypted with
   `@alice`'s shared key for `@bob`. The `ivNonce` metadata field
   carries the IV it was encrypted with.
2. **Asymmetric layer.** The shared key is itself encrypted with the
   recipient's encryption public key, `public:publickey@<recipient>`
   (RSA), and carried in the `sharedKeyEnc` metadata field. Two fields
   record which public key wrapped it: `pubKeyHash`, its SHA-512 hash
   (with `hashingAlgo:sha512`), and `pubKeyCS`, its MD5 hex digest (see
   [§14.3](#143-public-key-rotation)).

The SDK does not set `encKeyName`, `encAlgo`, `skeEncKeyName` or
`skeEncAlgo`, and does not read them when it decrypts. A value an
atSign keeps for itself has only the symmetric layer: the SDK encrypts
it with the atSign's self-encryption key.

With the legacy provider, the SDK puts `sharedKeyEnc` in the metadata of
every value it encrypts for another atSign, and a reader uses it when
present. When the SDK finds no copy of its shared key for a recipient,
locally or on the atServer, it creates one and writes two records of it.
In these key names, `<recipient>` and `<owner>` are atSigns without
their `@`:

- `@<recipient>:shared_key@<owner>`, encrypted with the recipient's
  `publickey`;
- `shared_key.<recipient>@<owner>`, the owner's own copy, encrypted
  with the owner's `publickey`.

A reader given a value without `sharedKeyEnc` falls back to
`@<recipient>:shared_key@<owner>`: its cached copy if it has one, else
a `lookup` of `shared_key@<owner>`.

Since at_client 3.13.0, the SDK names the provider that encrypted a
value in the `providerId` of the value's `appMetadata` tag. It decrypts
a value with no `appMetadata`, or with `providerId` `legacy`, by the
scheme above. Other providers may encrypt differently.

### 14.2 Public-data signatures

When the reference SDK's `AtClient.put` writes a public value, it
signs the value with the legacy data signing key, the client
encryption key ([§6.5](#65-reserved-keys)), using RSA with SHA-256,
and puts the base64 signature in `dataSignature`. It signs the UTF-8
bytes of the value's text: for a binary value, its Base2e15 text
([§4.5](#45-binary-values)), and before any `encoding:base64`
([Appendix D.9](#d9-newline-escaping-is-value-class-specific)). The
matching public key is `public:publickey@<owner>`, not
`public:signing_publickey@<owner>`. Signing public values with the
legacy data signing key is the legacy scheme. It will be widened to
sign with client data signing keys, post-quantum ones included
([Appendix C.1](#c1-post-quantum-cryptography-and-crypto-agility)).

In a `notify:all` notification the atServer sets `dataSignature`
itself: a signature over `<atKey>@<atSign>`, the notified key without
its recipient, made with its server authentication signing key. The
atServer stores the same signature on each recipient's notification.
The `notify` it sends on to a recipient's atServer does not carry
it.

### 14.3 Public-key rotation

If a recipient's encryption keypair changes, values shared with it
before the change carry a `sharedKeyEnc` wrapped with the old public
key, which only the old private key opens. Each side has a signal for
this.

The recipient's atClient sees it on read. The reference SDK compares a
received value's `pubKeyHash` and `pubKeyCS`, each when present, with
hashes of its own current `publickey`, and fails the read with
`AtPublicKeyChangeException` when either differs.

The sender's atServer sees it when it fetches the recipient's
`publickey`, as it does each time it opens an outbound connection to
the recipient's atServer. When the fetched key differs from its cached
copy, `cached:public:publickey@<recipient>`, the atServer:

- stores an `AtSignPKChangedEvent` naming the recipient, at
  `<epochMicros>.events.__atserver@<sender>`;
- sends its own atSign a `self` notification of that key, which
  expires after five minutes;
- renames `shared_key.<recipient>@<sender>`, if it holds one, to
  `shared_key.<recipient>.until.<epochMillis>@<sender>`.

The reference SDK creates a new shared key whenever it finds no
`shared_key.<recipient>@<sender>`, locally or on the atServer (see
[§14.1](#141-two-layers)). The atServer re-encrypts nothing: to share
a value again, the sender's atClient re-issues its `update` with a
fresh `sharedKeyEnc`.

### 14.4 Why server-side filtering is impossible

The atServer holds:

- ciphertext in `value`
- ciphertext in `sharedKeyEnc`
- metadata fields whose meaning it cannot interpret without keys it
  does not have

Any feature requiring the server to reason about plaintext, value-
level filters, server-side aggregations over content, content-based
notifications, is therefore architecturally impossible. This is a
**security property**, not a performance limitation. Filtering by
atKey **structure** (regex on the wire-form name) is supported and is
how `scan`, `notify:list` regexes, and `monitor` filters work.

---

## 15. The inter-atServer protocol

When an atClient asks its atServer for cross-atSign data, `lookup`,
remote `scan`, or sending a `notify` whose recipient is on a different
atServer, the atServer **proxies** the request. It opens a TLS
connection to the target atServer (resolved via the atDirectory),
authenticates via the `pol` handshake, and runs the appropriate verb
on behalf of the requesting client.

The verbs an atServer sends to another atServer on this proxied channel
include `from`, `pol`, `lookup`, `scan` and `notify`. Each atServer is
the sole authority for its own atSign's data.

This chapter specifies that proxying. The single most important verb
here is `pol`, the proof-of-life handshake between two atServers.

### 15.1 Outbound connection lifecycle

Source: `at_secondary_server/lib/src/connection/outbound/outbound_client.dart`.

1. Local atServer (call it **A**) needs to talk to remote atServer
   **B**. A's `OutboundClientManager` returns an `OutboundClient`
   for the target atSign, pooled per-target so repeat traffic to the
   same B reuses one connection.
2. **Resolve.** A queries its atDirectory for B's host:port.
3. **Connect.** A opens a TLS connection to B. By default this is
   mutual TLS: A presents a client certificate, which B checks against
   the host the atDirectory gives for A's atSign (see
   [§3.2](#32-atserver)).
4. **Public-key warm-up.** Before any handshake, A runs an
   unauthenticated `lookup:all:publickey<B-atSign>` against B and
   caches the result (cached as
   `cached:public:publickey@<B-atSign>` in A's keystore). This makes
   subsequent encryption-to-B operations cheap and detects key
   rotation early.
5. **Handshake.** If the planned operation requires authentication, A
   runs the `pol` handshake, see [§15.2](#152-the-pol-handshake).
   `lookup` requires it. Serving a `plookup` does not: A fetches the
   public record with an unauthenticated `lookup:`.
6. **Run verbs.** A sends the verb (e.g. `lookup:phone.wavi@alice`),
   reads the response, strips the trailing prompt, returns the
   `data:…` payload to the original caller.
7. **Reuse or close.** The pool keeps the connection open subject to
   `outbound_idle_time_millis`. On idle expiry the connection is
   closed.

### 15.2 The `pol` handshake

`pol` ("proof of life") authenticates A to B. It is built on the same
challenge mechanism as PKAM but inverted: instead of A signing a
challenge from B and sending the signature inline, A *publishes* its
signed challenge as a public atKey on its own atServer (under a
session-scoped name) and tells B to come and look it up. This means
A's server authentication signing key never leaves A; B verifies the
signature with its public half, `public:signing_publickey@A`, which it
fetches from A.

**Step-by-step.** Source:
`at_secondary_server/lib/src/verb/handler/pol_verb_handler.dart` and
`outbound_client.dart::_establishHandShake`.

```text
A ──TLS──► B  (already connected)

A → B:  from:@A
B → A:  data:proof:<sessionId>@A:<challenge-uuid>\n@

A:  parses cookieParams from response → (sessionId, challenge)
A:  signedChallenge = base64( sign_RSA_SHA256(challenge, A_server_auth_priv) )
A:  store in own keystore: public:<sessionId>@A = signedChallenge   (TTL ~60s)

A → B:  pol\n

B's pol handler:
  - Verifies A's `from:` already executed on this connection.
  - Opens its own outbound to A (no handshake required — public lookup):
      B → A:  lookup:<sessionId>@A
      A → B:  data:<signedChallenge>
      B → A:  lookup:signing_publickey@A
      A → B:  data:<A's server authentication signing public key>
  - Reads its own stored secret: get(public:<sessionId>@A) = challenge
  - Verifies: RSA_SHA256_verify(A_server_auth_pub, challenge, signedChallenge)
  - On success: marks the inbound connection as polAuthenticated,
                deletes the stored secret, responds:

B → A:  @A@
       (verb result inside B is `pol:@A@`; the PolResponseHandler
        strips the `pol:` prefix, leaving only the prompt-shaped
        confirmation `@A@` on the wire — no separate `data:`
        framing, no trailing `\n@…@`. A's outbound listener
        recognises completion by the `@<currentAtSign>@` shape.)

A:  reads handshake result; if it begins with "@A@", marks the
    outbound connection authenticated.
```

After `pol` succeeds, A's connection to B is authenticated **as @A**.
B treats subsequent verbs on this connection as coming from `@A`. For
example, where `@bob` is B's atSign, a `lookup:phone.wavi@bob` returns
the record `@bob` shares with `@A`, `@A:phone.wavi@bob`. Since atServer
[3.18.1](#atserver-3181), a lookup on this connection naming an owner other than `@bob` is
refused with `AT0009`, and the connection is closed (see
[§10.4](#104-lookup)).

#### Failure modes

| Cause                             | Error                                                                                |
|-----------------------------------|--------------------------------------------------------------------------------------|
| `pol` sent without prior `from`   | `error:AT0013-You must execute a 'from:' command before you may run the pol command` |
| Signature verification fails      | `error:AT0025-Pol Authentication Failed`                                             |
| Cannot connect outbound to verify | `error:AT0007-atServer not found`                                                    |
| Any other handshake exception     | `error:AT0008-Handshake failure`                                                     |

### 15.3 Cross-atSign `lookup`

Source: `at_secondary_server/lib/src/verb/handler/lookup_verb_handler.dart`.

When @bob's atClient sends `lookup:phone.wavi@alice` to @bob's
atServer:

1. @bob's atServer recognises the target atSign is not its own.
2. It obtains an `OutboundClient` for `@alice` from the manager,
   running the `pol` handshake if needed.
3. It sends `lookup:phone.wavi@alice` over the now-authenticated
   outbound connection.
4. @alice's atServer evaluates the lookup with the inbound connection
   marked `polAuthenticated as @bob`, the result is whatever @alice
   has shared **with @bob** (typically `@bob:phone.wavi@alice`). Since
   atServer [3.18.1](#atserver-3181), it answers a lookup on that connection only for a
   key @alice owns; one naming another owner is refused with `AT0009`,
   and the connection is closed.
5. @alice's atServer responds `data:<value>\n@bob@` (the
   pol-authenticated prompt).
6. @bob's atServer strips the prompt, returns `data:<value>` to
   @bob's atClient.

The entire round-trip is one atServer-to-atServer connection per
(target atSign, source atSign) pair, pooled and reused.

### 15.4 Cross-atSign `notify` delivery

When the originator's atServer needs to deliver a notification to a
recipient on a different atServer, it uses the same
`OutboundClient.pol → notify` path. The remote `notify` verb on the
recipient's atServer recognises the inbound connection as
pol-authenticated and stores the notification in the recipient's
inbox; the recipient sees it via `monitor`.

Also relevant: the worked flow in [§16.4](#164-monitor--notify-round-trip)
shows the full notify→deliver→monitor path end-to-end.

---

## 16. Worked flows

### 16.1 CRAM bootstrap (Phase 2 onboarding)

An app activating a newly registered atSign holds only its CRAM
secret. It authenticates with `cram`, enrolls itself, authenticates
again with `pkam` as that enrollment, stores its keys, publishes the
encryption public key and deletes the CRAM secret. This is the
exchange the reference SDK sends with its default settings, which use
RSA keys, and with its default app and device names. The reference
SDK can also activate an atSign with post-quantum keys
([Appendix C.1](#c1-post-quantum-cryptography-and-crypto-agility)),
which changes the keys and the fields of `enroll:request`.

The flows in this section leave out the optional `:clientConfig:{…}`
that a client may add to `from` ([§9.1](#91-the-from-verb)). The
reference SDK sends none on the connections it activates and enrolls
over.

```text
C: <TCP+TLS connect to alice's atServer>
C: lookup:publickey@alice\n
S: error:AT0015-<description>\n@
# The reference SDK sends this lookup unauthenticated, and retries
# until the atServer answers. AT0015 says that
# public:publickey@alice does not exist yet.

C: from:@alice\n
S: data:_4af24c03-d732-48f8-a9a2-570e8fb6a01c@alice:d6cac849-9c29-42b0-b0c5-493db62728b9\n@

C: cram:<sha512_hex(cramSecret + "_4af24c03-d732-48f8-a9a2-570e8fb6a01c@alice:d6cac849-9c29-42b0-b0c5-493db62728b9")>\n
S: data:success\n@alice@

# Client side, nothing on the wire: generate an RSA-2048 encryption
# keypair, an AES-256 self-encryption key, an AES-256 APKAM symmetric
# key and the app's RSA-2048 APKAM keypair.

C: enroll:request:{
     "appName":"firstApp",
     "deviceName":"firstDevice",
     "apkamPublicKey":"<APKAM public key>",
     "signingAlgo":"rsa2048",
     "apskLegacy":"<APKAM public key>"
   }\n
S: data:{"enrollmentId":"<uuid>","status":"approved"}\n@alice@
# Over CRAM the atServer approves the request at once and grants it
# rw on __manage and on * (§9.4.1). signingAlgo names the algorithm
# of the APKAM key; since atServer 3.15.0 the atServer keeps it with
# the enrollment. Since atServer 3.16.5, the atServer also publishes
# the apskLegacy value as public:_apsk.<uuid>.a.__e@alice: the
# public half of the enrollment's client data signing key, here its
# APKAM public key.

# === Close the connection. On a new one, authenticate as the
#     enrollment. ===
C: <TCP+TLS connect to alice's atServer>
C: from:@alice\n
S: data:<sessionId>@alice:<challenge>\n@
C: pkam:signingAlgo:rsa2048:hashingAlgo:sha256:enrollmentId:<uuid>:<signature>\n
S: data:success\n@alice@
# <signature> is made with the APKAM private key, the enrollment's
# client authentication signing key (§9.3).

# Client side: store the keys and the enrollment id, for example in
# an .atKeys file.

C: update:ttr:-1:isEncrypted:false:public:publickey@alice <encryption public key>\n
S: data:<commitId>\n@alice@

C: delete:privatekey:at_secret\n
S: data:-1\n@alice@
```

Once `privatekey:at_secret` is deleted, `cram` fails
([§6.5](#65-reserved-keys)). The app authenticates every later
session with `from` and `pkam`, as above. The reference SDK then opens
a client on the new keys, which authenticates that way.

Before this exchange, at_onboarding_cli sends the same
`lookup:publickey@alice` on a connection of its own, and stops if the
atServer answers with a key.

Onboarding does not write `public:signing_publickey@alice`. The
atServer generates that keypair, its server authentication signing
key, itself when it first starts ([§6.5](#65-reserved-keys)).

The reference SDK does not send
`update:privatekey:at_pkam_publickey`. Since atServer [3.16.5](#atserver-3165), that
`update` over a CRAM connection installs the key as the enrollment
named `primary` and answers `data:-1`.

### 16.2 APKAM enrollment end-to-end

Phase 3: a new app on a new device enrolls for `@alice`. The approver
here is the first app, whose enrollment holds `rw` on `__manage` and
on `*` ([§16.1](#161-cram-bootstrap-phase-2-onboarding)). Its
connections are authenticated with `from` and `pkam`. Both apps use
the reference SDK's default settings.

```text
# === Approver: issue an OTP. ===
C(approver): otp:get:ttl:300000\n
S:           data:A1B2C3\n@alice@
# (The reference SDK asks for an OTP that lasts 5 minutes. The owner
#  gives "A1B2C3" to the new app.)

# === Approver, on its own monitor connection: listen. ===
C(approver): monitor:selfNotifications:<epochMillis>\n
# (<epochMillis> is that of the last notification the approver
#  received or, before it has received one, the moment its
#  notification service started.)
# (No response line. Notifications stream from here on.)

# === New app: it holds no credential yet, so it does not
#     authenticate. ===
C(new): <TCP+TLS connect to alice's atServer>
C(new): lookup:publickey@alice\n
S:      data:<encryption public key>\n@
# Unauthenticated, lookup reads public:publickey@alice.

# Client side: generate an RSA-2048 APKAM keypair and an AES-256 APKAM
# symmetric key, and encrypt the symmetric key with the encryption
# public key (RSA).

C(new): enroll:request:{
          "appName":"todos",
          "deviceName":"phone-1",
          "namespaces":{"todos":"rw"},
          "otp":"A1B2C3",
          "encryptedAPKAMSymmetricKey":"<RSA ciphertext>",
          "apkamPublicKey":"<APKAM public key>",
          "signingAlgo":"rsa2048",
          "apskLegacy":"<APKAM public key>"
        }\n
S:      data:{"enrollmentId":"<uuid>","status":"pending"}\n@
# The OTP is what admits this unauthenticated request.

# === New app, on a new connection: authenticate as the enrollment,
#     retrying until the request is decided. ===
C(new): <TCP+TLS connect to alice's atServer>
C(new): from:@alice\n
S:      data:<sessionId>@alice:<challenge>\n@
C(new): pkam:signingAlgo:rsa2048:hashingAlgo:sha256:enrollmentId:<uuid>:<signature>\n
S:      error:AT0026:enrollment_id: <uuid> is pending\n@
# <signature> is made with the new app's APKAM private key, its
# client authentication signing key (§9.3).

# === Approver's monitor connection: the request is announced. ===
S(approver): notification: {"id":"<id>","from":"@alice","to":"@alice",
               "key":"<uuid>.new.enrollments.__manage@alice",
               "value":"{…}","operation":"update",…}\n
# value carries appName, deviceName, namespace, the encrypted APKAM
# symmetric key and, since atServer 3.18.1, apkamKeysExpiryInMillis
# (§9.4.1).

# === Approver: read the request from the enrollment list. ===
C(approver): enroll:list:{
             "enrollmentStatusFilter":["pending","approved"]
           }\n
S:           data:{"<uuid>.new.enrollments.__manage@alice":{…,
               "appName":"todos","deviceName":"phone-1",
               "namespaces":{"todos":"rw"},…,
               "encryptedAPKAMSymmetricKey":"<RSA ciphertext>",…,
               "status":"pending",…},…}\n@alice@
# The answer holds every pending or approved enrollment, the
# approver's own among them. The reference SDK sends this request
# twice before it approves.

# Client side: decrypt the APKAM symmetric key with the encryption
# private key (RSA). Encrypt the encryption private key and the
# self-encryption key with it (AES-256, each with a random 16-byte IV).

C(approver): enroll:approve:{
             "enrollmentId":"<uuid>",
             "encryptedDefaultEncryptionPrivateKey":"<AES ciphertext>",
             "encPrivateKeyIV":"<base64 IV>",
             "encryptedDefaultSelfEncryptionKey":"<AES ciphertext>",
             "selfEncKeyIV":"<base64 IV>"
           }\n
S:           data:{"status":"approved","expiresAt":null,
               "enrollmentId":"<uuid>"}\n@alice@
# Since atServer 3.18.1 the answer carries expiresAt, null here
# because neither the request nor the approver's enrollment expires.
# Since atServer 3.16.5 the approval publishes the request's
# apskLegacy value as public:_apsk.<uuid>.a.__e@alice.
# The reference SDK then reads the list again, narrowed to
# ["approved"] and then to ["approved","revoked"].

# === New app: the next attempt succeeds. ===
C(new): from:@alice\n
S:      data:<sessionId>@alice:<challenge>\n@
C(new): pkam:signingAlgo:rsa2048:hashingAlgo:sha256:enrollmentId:<uuid>:<signature>\n
S:      data:success\n@alice@

# === New app: collect what the approval stored for it. ===
C(new): keys:get:keyName:<uuid>.default_enc_private_key.__manage@alice\n
S:      data:{"value":"<encryptedDefaultEncryptionPrivateKey>",
          "iv":"<base64 IV>"}\n@alice@
C(new): keys:get:keyName:<uuid>.default_self_enc_key.__manage@alice\n
S:      data:{"value":"<encryptedDefaultSelfEncryptionKey>",
          "iv":"<base64 IV>"}\n@alice@

# Client side: decrypt both with the APKAM symmetric key, and store
# the keys and the enrollment id, for example in an .atKeys file.
```

The new app generates its own APKAM keypair and never sends the
private half. `enroll:revoke` withdraws its enrollment
([§9.4.1](#941-the-enroll-verb)).

at_onboarding_cli's `otp` command sends `otp:get` with no `:ttl:`
unless it is given an expiry, so the atServer's default applies. Its
`enroll` command adds `"apkamKeysExpiryInMillis":0` to the request
when it is given no expiry.

### 16.3 Cross-atSign read with pol handshake

@bob looks up `@alice`'s phone number, which `@alice` has shared with
him.

```text
# === atClient session as @bob, authenticated to @bob's atServer. ===
C(bob): lookup:phone.wavi@alice\n

# @bob's atServer proxies (this is invisible to the atClient):
#
#   bobServer ──TLS──► aliceServer
#
#   bobServer → aliceServer:  from:@bob
#   aliceServer → bobServer:  data:proof:<sessionId>@bob:<chal>\n@
#
#   bobServer signs <chal> with its server authentication signing key.
#   bobServer stores public:<sessionId>@bob = signedChallenge in its
#   own keystore.
#
#   bobServer → aliceServer:  pol\n
#
#   aliceServer:
#     opens unauthenticated outbound to bobServer
#     aliceServer → bobServer (in pol):
#         lookup:<sessionId>@bob → data:<signedChallenge>
#         lookup:signing_publickey@bob →
#             data:<@bob's server authentication signing public key>
#     verifies signature; succeeds.
#
#   aliceServer → bobServer:  @bob@   (PolResponseHandler strips `pol:`)
#
#   bobServer → aliceServer:  lookup:phone.wavi@alice\n
#   aliceServer → bobServer:  data:<ciphertext>\n@bob@
#
#   bobServer strips prompt, returns to atClient:

S(bob): data:<ciphertext>\n@bob@
```

@bob's atClient decrypts `<ciphertext>` using the AES key in
`sharedKeyEnc` (which it RSA-decrypts with its own encryption private
key). The decryption is end-to-end; neither atServer can read the
phone number.

### 16.4 monitor + notify round-trip

`@bob` listens for live updates from `@alice`; `@alice` notifies him.

```text
# === @bob: open monitor session. ===
C(bob): monitor\n
# (no immediate response; stream begins.)

# === @alice: update a shared key and notify. ===
C(alice): update:ttr:-1:isEncrypted:true:@bob:phone.wavi@alice <ciphertext>\n
S:        data:42\n@alice@
C(alice): notify:update:ttr:-1:isEncrypted:true:@bob:phone.wavi@alice <ciphertext>\n
S:        data:7c6c8d7d-…\n@alice@

# === Inside @alice's atServer:
#    detects @bob's atServer is remote → opens outbound, runs pol →
#    forwards `notify:` to @bob's atServer → @bob's atServer stores
#    the notification → emits to all live monitor connections.

# === @bob's monitor stream: ===
S(bob): notification: {"id":"7c6c8d7d-…","from":"@alice","to":"@bob","key":"@bob:phone.wavi@alice","value":"<ciphertext>","operation":"update","epochMillis":1714900000000}\n
```

`@bob`'s atClient decrypts the value as in §16.3.

### 16.5 Sync resumption after reconnect

An atClient that has been offline picks up where it left off.

```text
# Last seen commit ID: 41.
C: sync:from:41:limit:100\n
S: data:[
     {"atKey":"@bob:phone.wavi@alice","operation":"+","commitId":42,"opTime":"…","value":"<ciphertext>","metadata":{"ttr":-1,"isEncrypted":true}},
     {"atKey":"@bob:email.wavi@alice","operation":"-","commitId":43,"opTime":"…"}
   ]\n@alice@

# Apply locally; record new high-water mark = 43.
# If response had reached limit, repeat:
C: sync:from:43:limit:100\n
S: data:[]\n@alice@   # fully caught up.
```

Deletes older than the client's `skipDeletesUntil` threshold can be
elided to compact long sync windows:

```text
C: sync:from:0:limit:1000:skipDeletesUntil:43\n
```

---

## 17. Errors

Error responses are framed identically to data responses but with the
prefix `error:` instead of `data:`:

```text
error:AT0003-Invalid Syntax
```

(Some errors include a colon-separated detail message instead of a
hyphen, e.g. `error:AT0025:Authentication Failed`. Implementations
must accept both forms.)

After certain errors the server closes the connection (notably
syntax errors and authentication failures). Other errors leave the
connection open.

### 17.1 Code reference

Sorted by code. The "Class" column gives the Dart exception that
canonically produces the code; implementations in other languages
should map to an equivalent.

| Code     | Message                                  | Class                              | Connection        |
|----------|------------------------------------------|------------------------------------|-------------------|
| `AT0001` | Server exception                         | `AtServerException`                | Closed            |
| `AT0002` | DataStore exception                      | `DataStoreException`               | Closed            |
| `AT0003` | Invalid syntax                           | `InvalidSyntaxException`           | Closed            |
| `AT0004` | Socket error                             | `AtIOException`                    | Closed            |
| `AT0005` | Buffer limit exceeded                    | `BufferOverFlowException`          | Closed            |
| `AT0006` | Outbound connection limit exceeded       | `OutboundConnectionLimitException` | Open              |
| `AT0007` | atServer not found                       | `SecondaryNotFoundException`       | Open              |
| `AT0008` | Handshake failure                        | `HandShakeException`               | Closed            |
| `AT0009` | UnAuthorized client in the request       | `UnAuthorizedException`            | Closed            |
| `AT0010` | Internal server error                    | `InternalServerError`              | Closed            |
| `AT0011` | Internal server exception                | `InternalServerException`          | Closed            |
| `AT0012` | Inbound connection limit exceeded        | `InboundConnectionLimitException`  | Closed            |
| `AT0013` | Connection Exception                     | `BlockedConnectionException`       | Closed            |
| `AT0014` | Unknown AtClient exception               | `AtClientException`                | n/a (client-only) |
| `AT0015` | Key not found                            | `KeyNotFoundException`             | Open              |
| `AT0016` | Invalid key                              | `InvalidAtKeyException`            | Open              |
| `AT0021` | Unable to connect to atServer            | `SecondaryConnectException`        | n/a (client-only) |
| `AT0022` | Illegal arguments                        | `IllegalArgumentException`         | Open              |
| `AT0023` | Timeout waiting for response             | `AtTimeoutException`               | Open              |
| `AT0024` | Server is paused                         | `ServerIsPausedException`          | Open              |
| `AT0025` | Authentication failed (cram/pol)         | `UnAuthenticatedException`         | Closed            |
| `AT0026` | APKAM enrollment pending                 | `UnAuthenticatedException`         | Closed            |
| `AT0027` | APKAM enrollment revoked                 | `UnAuthenticatedException`         | Closed            |
| `AT0028` | Too many requests / throttle exceeded    | `AtThrottleLimitExceeded`          | Open              |
| `AT0029` | APKAM enrollment expired                 | `AtInvalidEnrollmentException`     | Closed            |
| `AT0031` | Cannot revoke own enrollment             | `AtEnrollmentRevokeException`      | Open              |
| `AT0032` | Illegal state                            | `IllegalStateException`            | Open              |
| `AT0401` | Client authentication failed (cram/pkam) | `UnAuthenticatedException`         | Closed            |

### 17.2 Note on `AT0009` vs `AT0401`

`AT0401` is emitted on **authentication** failure (the credential is
wrong). `AT0009` is emitted on **authorisation** failure (the
authenticated principal lacks permission for the requested key, notably
APKAM scopes prohibiting the namespace). Since atServer [3.18.1](#atserver-3181), `AT0009`
also refuses a `lookup` that names another owner on a connection not
authenticated as the atSign (see [§10.4](#104-lookup)). Implementations
must distinguish between them; clients may retry on `AT0401` but not on
`AT0009`.

---

## 18. Glossary

- **APKAM**, Application PKAM. Per-app, per-device, namespace-scoped
  authentication built on PKAM. The modern way to authenticate.
- **atClient**, Software acting on behalf of an atSign owner.
- **atDirectory**, Service mapping atSign → `host:port` of the
  atSign's atServer.
- **atKey**, A key in an atServer's keystore. Five shapes (public,
  self, shared, local, private) plus augmentations (hidden, cached).
- **atServer**, The personal server for one atSign.
- **atSign**, An identifier of the form `@<name>`. At most 55
  characters after the `@`.
- **Commit log**, Append-only log of `update`/`delete` operations.
  Walked by `sync:from`.
- **CRAM**, Challenge-Response Authentication Mechanism. The
  bootstrap-only credential, used during onboarding.
- **Enrollment**, An APKAM record granting an app a namespace-scoped
  keypair. Has lifecycle states `pending`, `approved`, `denied`,
  `revoked`, `expired`.
- **Master AtKeys**, The atSign's root keys, produced at
  onboarding: the PKAM key (a client authentication signing key), the
  encryption key (also the legacy data signing key) and the
  self-encryption key.
- **OTP**, Six-character alphanumeric one-time passcode. Used to bind
  an APKAM enrollment to an out-of-band human approval.
- **PKAM**, Public-Key Authentication Mechanism. Sign-the-challenge
  authentication; underpins APKAM.
- **`pol`**, Proof-of-life. The atServer-to-atServer authentication
  handshake in which the connecting atServer publishes a signed
  challenge as a public atKey on its own atServer for the receiving
  atServer to fetch and verify.
- **Prompt**, The trailing `\n@…@` (or `\n@`) that frames the next
  request on a connection.
- **`sharedKeyEnc`**, Inline-in-metadata, RSA-encrypted shared
  symmetric key.
- **Signing keys**, The client authentication, client data, legacy
  data and server authentication signing keys. See
  [§6.5](#65-reserved-keys).
- **SPP**, Semi-permanent passcode. The one reusable passcode an atSign
  holds, accepted like an OTP by `enroll:request`. See
  [§9.4.2](#942-the-otp-verb).
- **Verb**, A single-line command in the protocol.

---

## Appendix A, Verb reference

Terse reference for ctrl-F. Authoritative regex source:
[`at_commons/lib/src/verb/syntax.dart`](https://github.com/atsign-foundation/at_client_sdk/blob/trunk/packages/at_commons/lib/src/verb/syntax.dart).

| Verb            | Auth   | Purpose                                                               | Section |
|-----------------|--------|-----------------------------------------------------------------------|---------|
| `from`          | —      | Identify connecting atSign; receive challenge.                        | §9.1    |
| `cram`          | —      | Bootstrap-only authentication.                                        | §9.2    |
| `pkam`          | —      | Sign-the-challenge authentication.                                    | §9.3    |
| `pol`           | —      | Inter-atServer proof-of-life. Server-emitted only.                    | §15.2   |
| `enroll`        | varies | APKAM enrollment lifecycle; `enroll:link` in §9.4.4.                  | §9.4.1  |
| `otp`           | varies | Issue, set, list and delete OTPs and the SPP.                         | §9.4.2  |
| `keys`          | yes    | APKAM-issued key storage. **Being deprecated** — see §9.4.3 and §B.7. | §9.4.3  |
| `update`        | yes    | Insert/overwrite an atKey.                                            | §10.1   |
| `update:meta`   | yes    | Update only metadata.                                                 | §10.2   |
| `delete`        | yes    | Remove an atKey.                                                      | §10.3   |
| `lookup`        | varies | Read a value; the answer depends on the connection (see §10.4).       | §10.4   |
| `plookup`       | yes    | Another atSign's public record, through this atServer.                | §10.5   |
| `llookup`       | yes    | Local-server-only lookup.                                             | §10.6   |
| `scan`          | varies | Enumerate atKeys (regex/filter).                                      | §10.7   |
| `notify`        | yes    | Emit a notification.                                                  | §11.1   |
| `notify:all`    | yes    | Emit to multiple recipients.                                          | §11.2   |
| `notify:list`   | yes    | List received (or sent, if pol-auth) notifications.                   | §11.3   |
| `notify:status` | yes    | Query delivery status.                                                | §11.4   |
| `notify:fetch`  | yes    | Fetch full notification record.                                       | §11.5   |
| `notify:remove` | yes    | Remove from local notification log.                                   | §11.6   |
| `monitor`       | yes    | Stream of received notifications.                                     | §11.7   |
| `sync:from`     | yes    | Walk the commit log from an offset.                                   | §12.1   |
| `config`        | owner  | Block-list and config management.                                     | §13.1   |
| `stats`         | yes    | Server statistics.                                                    | §13.2   |
| `info`          | varies | Server runtime info.                                                  | §13.3   |
| `noop`          | —      | Sleep then `data:ok`.                                                 | §13.4   |
| `batch`         | yes    | Multiple verbs in one round-trip.                                     | §13.5   |
| `@exit`         | —      | atDirectory graceful close.                                           | §8.4    |

---

## Appendix B, Legacy and deprecated

The following items remain in the wire grammar for backward
compatibility but new implementations should not produce them.

### B.1 `cram` as a permanent credential

Pre-onboarding, `cram` is the only credential. Post-onboarding, an
atServer accepts `cram` only as a fallback for compatibility; modern
clients use `pkam`/APKAM exclusively. Servers may disable `cram`
post-onboarding entirely.

### B.2 `sync` (without `:from:`)

```text
sync:<from_commit_seq>[:<regex>]
```

The pre-`sync:from` syntax. Equivalent to `sync:from:<seq>:<regex>`
without the `:limit:` and `:skipDeletesUntil:` knobs. New clients use
`sync:from`.

### B.3 `notify` `messageType:text`

`notify:…:messageType:text:…` is a freeform-text notification, not
tied to an atKey change. Since atServer [3.18.1](#atserver-3181), text notifications are
retired. A client's `notify` or `notify:all` with `messageType:text` is
refused with AT0003 (`messageType:text is no longer supported`), one
arriving from a peer atServer over `pol` is answered `data:success`
and dropped, and `info` lists `notify.text` as `Retired`. Freeform
messaging uses a shared atKey and `notify:update`.

### B.4 `pubKeyCS`

The MD5 checksum, as a hex digest, of the recipient's encryption
public key (`public:publickey@<recipient>`) that encrypted
`sharedKeyEnc`. It is older than `pubKeyHash`, which names its
algorithm in `hashingAlgo`, but at_commons does not mark it
deprecated. When the reference SDK shares a value with its `legacy`
crypto provider, it sets both: `pubKeyCS`, and `pubKeyHash` as
SHA-512 with `hashingAlgo:sha512`. On read it refuses to decrypt when
either no longer matches its own public key. The atServer stores
`pubKeyCS` as given.

### B.5 `stream`

Removed in atServer [3.19.0](#atserver-3190), and listed here only so
that references to it resolve. An atServer refuses `stream:`, batched or
not, with `AT0003`. To share binary data, use `update` with
`isBinary:true` and `isEncrypted:true`.

### B.6 `*Commons*` and *atServer/atSecondary* terminology drift

In code you will see the older term **secondary** as a synonym for
**atServer** (e.g. `at_secondary_server`, `SecondaryNotFoundException`,
`secondaryAddressFinder`). The two refer to the same thing.
Documentation and new APIs prefer **atServer**. Implementations should
emit "atServer not found" in user-facing strings; existing error
messages with "Secondary Server not found" remain accepted.

### B.7 `keys` verb

The `keys:put|get|delete` verb (§9.4.3) is **being deprecated**. It
overlaps with `update`/`llookup`/`delete` against the `__pkams` /
`__manage` namespaces and adds parsing surface without adding
capability. The current APKAM enrollment flow still uses it under
the covers; new implementations should not produce it. Removal is
expected to ride alongside the new AtKeys structure and pluggable
encryption work in [Appendix C.3](#c3-new-atkeys-structure) /
[C.1](#c1-post-quantum-cryptography-and-crypto-agility). Servers
should accept it for the foreseeable future.

---

## Appendix C, Significant near-term projects

This appendix lists active workstreams that will materially change
parts of this specification. Each entry links to the tracking issue;
issue threads carry the current design state. Implementers should not
commit to long-lived choices in these areas without checking the
tracking issues for the present direction. The list is current as of
2026-05-05; it is not a roadmap commitment, only a snapshot of what is
moving.

### C.1 Post-quantum cryptography and crypto agility

The current encryption stack is RSA-2048 (asymmetric) + AES-256
(symmetric) + SHA-256/SHA-512 (hashing). Transition to post-quantum
primitives is in active design.

[at_client_sdk #1891](https://github.com/atsign-foundation/at_client_sdk/issues/1891)
covers **pluggable encryption / decryption schemes**. The plan is to
refactor the client encrypt/decrypt path so the algorithm is a
pluggable strategy rather than hard-coded RSA + AES. Direction:
Signal-style triple-ratchet as the new default. Affects every
metadata field that names an algorithm (`encAlgo`, `skeEncAlgo`,
`hashingAlgo`).

[at_client_sdk #1889](https://github.com/atsign-foundation/at_client_sdk/issues/1889)
covers **post-quantum (PQ) cryptography with crypto agility**, landing
the first PQ primitives behind the pluggable interface above.

[at_client_sdk #1893](https://github.com/atsign-foundation/at_client_sdk/issues/1893)
covers **post-quantum end-to-end encryption where actors communicate
over Atsign Protocol**, the protocol-visible part of the PQ work.

Implementers should treat algorithm names in metadata as
forward-compatible enums and design for new values appearing.

### C.2 Fast sync ("fsync"), Better sync

[at_client_sdk #1894](https://github.com/atsign-foundation/at_client_sdk/issues/1894).
Replacement for the current commit-log walk-based sync. Targets
**~10–30 ms end-to-end** (excluding network transit) versus today's
~50–200 ms. Likely affects:

- The `sync:from` verb's pagination contract or replaces it with a
  push-based delta channel.
- The `monitor` connection or a new dedicated channel for delta
  delivery.
- Local storage commit semantics on the client side.

The current `sync:from` verb is documented in §12 and remains the
canonical sync mechanism until fsync ships.

### C.3 New AtKeys structure

[at_client_sdk #1892](https://github.com/atsign-foundation/at_client_sdk/issues/1892).
Refactor of the on-device `.atKeys` file (and keychain entry) format
that holds an atSign's private credentials. Not a wire-protocol
change in itself, but it is paired with the post-quantum work above
so the file can carry multiple keypairs of differing algorithms. May
also change which fields appear in `enroll:approve`'s encryption
envelope.

### C.4 Standardise exception handling across SDK packages

[at_client_sdk #1910](https://github.com/atsign-foundation/at_client_sdk/issues/1910).
Cleanup of the exception hierarchy, error-code emission, and
on-the-wire `error:…` shapes. Implementers should expect the error
catalogue in §17 to gain entries (and possibly normalise the
hyphen/colon separator inconsistency noted
in [§D.1](#d1-error-code-separator-hyphen-vs-colon)).

### C.5 Canonical SDK conformance test suite

[at_client_sdk #1900](https://github.com/atsign-foundation/at_client_sdk/issues/1900).
A canonical test suite for SDKs in any language to implement. When
this lands it becomes the de-facto compliance gate for an
"Atsign-Protocol-compliant" implementation; clients of this
specification should adopt it.

Related:
[at_client_sdk #1782](https://github.com/atsign-foundation/at_client_sdk/issues/1782)
adds at_commons tests reflecting at_server and NoPorts usage.

### C.6 Move and improve `at_server_spec` into `at_client_sdk/at_commons`

[at_server #2608](https://github.com/atsign-foundation/at_server/issues/2608).
The `at_server_spec` package (interface definitions used by both the
server and the client) is being relocated into `at_commons`. This
specification cites paths in `at_commons/lib/src/verb/syntax.dart`
that will remain stable, but related interface paths under
`at_server_spec` should be expected to move.

### C.7 Multi-language SDKs (Java APKAM, others)

[operations #348](https://github.com/atsign-foundation/operations/issues/348)
adds **APKAM support to the Java SDK**, bringing it to parity with
the Dart SDK on Phase-3 authentication.

[at_client_sdk #1885](https://github.com/atsign-foundation/at_client_sdk/issues/1885)
is the tracking parent for **ports of the SDK to additional
languages**. This specification document is the basis for those ports.

### C.8 `monitor` immediate-ack response

[at_server #2542](https://github.com/atsign-foundation/at_server/issues/2542).
Extends the `monitor` verb (§11.7) with an option to request an
immediate acknowledgement (a prompt) before the notification stream
begins, so a client can deterministically distinguish "monitor
established" from "no notifications yet". This will be a backward-
compatible additive parameter.

### C.9 `at_activate` approval via OTP

[at_client_sdk #1862](https://github.com/atsign-foundation/at_client_sdk/issues/1862).
Streamlines the Phase-2 onboarding path so that activation can be
approved via an OTP flow analogous to APKAM's. Not a wire-protocol
change in itself but tightens the relationship between the `cram`
bootstrap path (§9.2) and the `otp` verb (§9.4.2).

### C.10 Fork the `encrypt` and `crypton` packages

[operations #385](https://github.com/atsign-foundation/operations/issues/385).
Atsign-controlled forks of the upstream Dart `encrypt` and `crypton`
packages, motivated by the post-quantum work and supply-chain
audit concerns. Affects which crypto primitives are reachable from
the SDK; not a wire-protocol change.

### C.11 Expired-key lookup returns null

[at_server #2568](https://github.com/atsign-foundation/at_server/issues/2568).
Today, an atServer answering `llookup`, or an unauthenticated or `pol`
`lookup`, of a key whose `eAt` has passed returns `data:null`; the
proposed correction is `AT0015`. A small change but observable on the
wire (see
[§D.4](#d4-expired-keys-return-null-instead-of-an-at0015-error)).

---

## Appendix D, Inconsistencies and quirks

This appendix documents on-the-wire surprises that the per-verb
sections don't make obvious. Implementers writing a parser, a server,
or an interoperable client need this list. None of these are
specification bugs in this document, they are facts about the
deployed protocol that this document accurately describes; they are
collected here so an implementer can sanity-check failure modes
against them.

### D.1 Error-code separator: hyphen vs colon

Both forms appear in current servers:

```text
error:AT0003-Invalid Syntax
error:AT0025:Authentication Failed
```

The hyphen form predates the colon form; newer error sites tend to
use `:`. Clients must accept both, splitting only on `-` will fail
on `AT0025`-class errors, splitting only on `:` will misparse
hyphen-separated messages.

The base response handler (`base_response_handler.dart` line 35)
emits `error:<code>:<message>`, but many call sites construct the
final string with a hyphen instead.
[Standardise exception handling](#c4-standardise-exception-handling-across-sdk-packages)
will normalise this.

### D.2 "Secondary Server" vs "atServer" in error messages

Several error messages still use the old "Secondary Server"
terminology, e.g. `error:AT0007-Secondary Server not found.` Some
sites have been updated to "atServer not found"; both wordings are
emitted in different code paths. Same code (`AT0007`), different
text. Match on the code, not the message.

See also [Appendix B.6](#b6-commons-and-atserveratsecondary-terminology-drift).

### D.3 Per-verb response framing differs

Most verbs follow `data:<payload>\n@<atSign>@` (or `\n@`
unauthenticated). A handful do not:

- **`pol`**, emits just `@<atSign>@` with no `data:` prefix and no
  trailing `\n@…@` framing. The `PolResponseHandler` strips the
  `pol:` prefix from the verb's internal result. Outbound clients
  detect "pol succeeded" by matching the wire shape `<currentAtSign>@`.
- **`monitor`**, emits a stream of `notification: {<json>}\n` lines
  with no per-line `data:` prefix and no trailing prompt between
  events. Connection remains open until either side closes.
- **`from`**, see [§D.6](#d6-from-response-shape-self-vs-cross).

### D.4 Expired keys return null instead of an AT0015 error

`llookup`, and a `lookup` on a connection that is unauthenticated or
`pol`-authenticated, answer `data:null` for a key the atServer holds
whose `eAt` has passed, or whose `aAt` has not yet come. A key it does
not hold is answered `AT0015` (see [§17](#17-errors)). Two other paths
differ:

- An authenticated `lookup`, or a `plookup`, of another atSign's key
  is answered by the caller's own atServer, with `AT0015` for an
  expired key: it skips an expired cached copy, and turns the owner's
  `data:null` into `AT0015`.
- An authenticated `lookup` of a key the atServer's own atSign owns
  checks neither `eAt` nor `aAt`. It returns the stored value until
  the atServer's expiry sweep removes the key.

Tracked in
[at_server #2568](https://github.com/atsign-foundation/at_server/issues/2568);
the proposed fix is to emit `AT0015` consistently. Until then,
clients reading possibly-expired keys must handle `data:null` as a
not-found indicator.

### D.5 `notify:list` semantics flip on auth mode

`notify:list` returns:

- the **received** notifications when the connection is authenticated
  as the server's own atSign (owner)
- the **sent** notifications when the connection is `pol`-
  authenticated (i.e. cross-atSign caller asking the recipient's
  server for what it has on record)

Same verb, same arguments, completely different result set. This is
intentional but undocumented at the call site; clients may be
surprised when they switch authentication contexts.

### D.6 `from` response shape: self vs cross

For a self-connect, the `from` response payload is

```text
data:<sessionId><atSign>:<proof>
```

For a cross-atSign connect, it is

```text
data:proof:<sessionId>@<atSign>:<proof>
```

The `proof:` infix is the difference. The `FromResponseHandler`
prepends `data:` only when the verb result starts with `proof:`, the
self-connect handler emits a string already prefixed `data:`, so
there is no double-prefixing. Parsers must not assume a uniform
"`data:` then payload" shape for `from`.

### D.7 `keys:put` returns `data:-1`

`keys:put` is used for APKAM-issued keys, which by design are not
written to the commit log. Rather than return a real commit ID, the
handler returns the sentinel `-1`. Clients must not interpret this
as an error.

### D.8 Mutating verbs typically require auth, `enroll:request` does not

`enroll:request` is a mutating verb (it creates a pending enrollment
record on the server) but it can be sent on an **unauthenticated**
connection. The OTP carried in the request is the auth surrogate.
Every other write verb (`update`, `update:meta`, `delete`, `notify`,
`keys`) requires an authenticated connection.

### D.9 Newline escaping is value-class-specific

The atServer does no newline escaping, and `~NL~` is a convention of
the reference SDK (see [§4.4](#44-newline-escapes-in-values)). What
keeps a `\n` out of a value written by the reference SDK's
`AtClient.put` depends on the class of value:

- An encrypted value (`isEncrypted:true`) is base64 ciphertext, which
  contains no `\n`.
- An unencrypted binary value (`isBinary:true`) is Base2e15 text (see
  [§4.5](#45-binary-values)), which contains no `\n` either.
- The SDK base64-encodes any other unencrypted value that contains a
  `\n`, public or not, and sets `encoding:base64`. A reader decodes it
  by `encoding`.

Whatever the class, a `\n` in a command ends it: the atServer takes
the `\n` as the terminator (see [§4.1](#41-line-terminator)).

### D.10 atDirectory historically emits `\r\n@`

Some atDirectory implementations emit `\r\n@` instead of `\n@` after
their lookup response. Implementations should accept both. atServers
emit only `\n@`.

### D.11 Metadata fragment is order-sensitive

The `metadataFragment` regex in `at_commons/lib/src/verb/syntax.dart`
is a sequence of `(:tag:value)?` groups in a fixed order. A request
that emits `:isEncrypted:true:ttr:-1:` (out of order) does **not**
match the regex and produces `error:AT0003-Invalid Syntax`. Clients
must emit metadata tags in the canonical order (the order they
appear in the regex; reproduced in §7.2). The atServer matches the
regex ignoring case, so `:TTL:60` reads as `:ttl:60`, but order still
matters.

### D.12 `clientConfig` JSON is unenforced free-form

The `from` verb's `:clientConfig:<json>` segment is parsed by
`jsonDecode` and a small set of fields (`version`, `clientId`,
`appName`, `appVersion`, `platform`) is read into the connection's
metadata. Every other field is silently discarded. There is no
schema enforcement: malformed-but-parseable JSON is accepted; an
unrecognised key produces no warning.

### D.13 `delete` is idempotent and always commits

Calling `delete` on a non-existent key returns `data:<commitId>`
exactly as if the key had existed. The commit log gains a DELETE
entry regardless. The exceptions answer `data:-1` and write no entry:
`:nc` (since atServer [3.16.5](#atserver-3165)), and a key the commit log never records
(a `public:_` key, but not `public:__`, or `privatekey:at_secret`).

`update` and `update:meta` do not error on a missing key either: they
create it. `llookup` of a missing key answers `AT0015`.

### D.14 Negative metadata integers are refused, except `ttr:-1`

The metadata regex permits `(-?)\d+` for `ttl`, `ttb`, `ttr`, but the
atServer refuses a negative `ttl` or `ttb`, and a `ttr` below `-1`,
with `AT0003`. `ttr:-1` ("cache indefinitely") is the only negative it
accepts. For no expiry, omit `ttl` when creating a record, or send
`ttl:0` to clear an expiry; since atServer [3.16.5](#atserver-3165), a later write that
omits both `ttl` and `eAt` keeps the stored expiry.

### D.15 `info` auth requirement is per-deployment

The `info` verb's authentication requirement is a server-side config
toggle, not a fixed property of the protocol. Some deployments
accept `info` from anonymous connections; others require an
authenticated session. Implementations should attempt unauthenticated
first and fall back if rejected.

### D.16 Two metadata tags for the same concept: `pubKeyCS` and `pubKeyHash`

`pubKeyCS` (an MD5 checksum) is older than `pubKeyHash` (a hash plus a
`hashingAlgo` companion field), but both are in use: the reference SDK
sets both on a value it shares with its `legacy` crypto provider, and
checks both on read. The atServer stores both as given, keeping
`pubKeyHash` only when `hashingAlgo` comes with it. See Appendix B.4.

### D.17 Session ID format

Session IDs (`<sessionID>` in `from`/`pol`) are produced server-side and
have a leading `_` followed by a UUID, e.g.
`_4af24c03-d732-48f8-a9a2-570e8fb6a01c`. `from` stores its challenge
under `public:<sessionID><fromAtSign>`, or
`private:<sessionID><fromAtSign>` when an atSign connects to its own
atServer, and `scan` lists neither: it never lists a `public:_` key (see
[§6.2](#62-augmentations)).

---

## Appendix E, Changes by atServer version

This appendix lists what each production release of the atServer changed
in the protocol, newest first, by the rules in
[How this document is versioned](#how-this-document-is-versioned). Only
production releases that changed the protocol are listed; at_server's
[releases](https://github.com/atsign-foundation/at_server/releases) list
them all. Each block names the canary releases it includes, since a
version released only as a canary is listed under the first production
release that shipped it. The history starts at atServer 3.0.35.

### Unreleased

No changes yet.

### atServer 3.19.0

Production release [p3.19.0](https://github.com/atsign-foundation/at_server/releases/tag/p3.19.0), 2026-10-26. Includes canary release 3.19.0.

- **Passcodes.** `otp:put`, which sets the semi-permanent passcode
  (SPP), is refused with `AT0009` unless the connection is CRAM or an
  enrollment holding `*:rw` and `__manage:rw`; access to `__manage` was
  enough before. `otp:list` returns the live OTPs, and the SPP, as a JSON
  array of `{type, value, expiresAt, namespaces}`. `otp:delete:<otp>` and
  `otp:delete:spp` delete one, and always answer `data:ok`. An OTP
  records the namespaces of the enrollment that issued it: an enrollment
  holding `__manage` may list and delete only the OTPs whose namespaces
  it holds, and never the SPP, while a full-privilege connection may list
  and delete them all, including OTPs that record no namespaces. `info`
  lists `otp.list` and `otp.delete` as `Beta`. The grammar is at_commons
  5.24.0's ([§9.4.2](#942-the-otp-verb)).
- **Reserved namespaces.** A record in a reserved namespace changes only
  through the verbs that own it ([§6.5](#65-reserved-keys)). `update`,
  `update:meta` and `delete` refuse such a key with `AT0009`, other than
  one in the connection's own `<enrollmentId>.a.__e` namespace or a
  cached copy of another atSign's record; a key whose name starts with
  `__` and has no namespace counts as one. `update` and `update:meta`
  refuse a key in an enrollment's namespace that is shared with another
  atSign. `lookup` and `llookup` refuse a passcode record with `AT0009`.
  A client's `notify` or `notify:all` is refused with `AT0009` when its
  key uses a reserved namespace, and with `AT0003` when the key's name
  holds a character an atKey may not; such a notification from another
  atServer is answered `data:success` and dropped. `enroll:list` lists
  only this atSign's own enrollment records.
- **`update:json`** refuses, with `AT0016`, an `atKey` that ends in
  `@<owner>` for an owner other than this atServer's atSign.
- **`batch:`** refuses a batch that is not a JSON array with `AT0003`. An
  entry that is not an object with a string `command`, whose `id` is not
  an integer, or that names no verb, is answered `AT0003` in its place,
  and the rest of the batch runs.
- **`stream` removed.** A `stream:` command inside a `batch:` is refused
  with `AT0003`, as one outside a batch has been since atServer
  [3.12.0](#atserver-3120), and a `stream:init` notification from an
  older atServer is dropped ([Appendix B.5](#b5-stream)).
- **atDirectory.** The atDirectory answers HTTP on its Atsign Protocol
  port to a client that negotiates `http/1.1` by ALPN, as on its HTTPS
  port. A redirect for a path below an atSign keeps the atSign:
  `GET /@alice/x` redirects to `https://<atServer>/@alice/x`. It matches
  an atSign in its canonical form over HTTP and the Atsign Protocol, and
  takes the Atsign Protocol's lookup line with or without its `@`. Every
  HTTP answer carries `Access-Control-Allow-Origin: *` and closes its
  connection, an HTTP connection that sends no complete request is
  closed within 10 seconds, a path that does not decode gets `400`, and
  a request it cannot answer `500` ([§3.1](#31-atdirectory),
  [§8](#8-the-atdirectory-protocol)).

### atServer 3.18.1

Production release [p3.18.1](https://github.com/atsign-foundation/at_server/releases/tag/p3.18.1), 2026-10-22. Includes canary releases 3.18.0 and 3.18.1.

- **Text notifications retired.** A client's `notify` or `notify:all`
  with `messageType:text` is refused with `AT0003`; one from another
  atServer is answered `data:success` and dropped. `info` lists
  `notify.text` as `Retired`. Text notifications already stored still
  list and fetch ([Appendix B.3](#b3-notify-messagetypetext)).
- **`enroll:link`** stores links vouching for the client data signing
  keys an approved enrollment's `_apsk` record lists, in `apskLinks` in
  the record's `appMetadata`, and every other write of that record keeps
  the links for the keys it still lists. The grammar is at_commons
  5.23.0's
  ([§9.4.4](#944-linking-an-enrollments-client-data-signing-keys-enrolllink)).
- **`_apsk` values.** `enroll:request`, `enroll:update`, `update` and
  `update:meta` are refused with `AT0022` when the `_apsk` they would
  leave lists a `kid` twice, an entry without a string `kid`, `alg` and
  `pub`, or the enrollment's client authentication signing key beside
  another key, and `enroll:update` also when that key carries a link. A
  write that would take the record and its links over 500 KiB is refused
  with `AT0022`, and an `enroll:update` republishing an immutable record
  with `AT0032`.
- **Lookups from connections not authenticated as the atSign.** On an
  unauthenticated or `pol` connection, a `lookup:` naming an owner other
  than this atServer's atSign is refused with `AT0009`, and the
  connection is closed. A `pol` connection's `lookup:` names its key as
  `<key>@<atSign>`; one naming a scope, such as `public:` or
  `@<atSign>:`, is refused with `AT0009` and the connection closed. A
  client's `lookup:` of another atSign's key that names a scope is
  refused with `AT0009`, and the client keeps its connection
  ([§10.4](#104-lookup)).
- **Authentication order.** A `from:` naming another atSign on a
  connection that has authenticated, and a `cram:` on one that has
  authenticated with `pkam:`, are refused with `AT0009`, and the
  connection is closed. A `batch:` answers a `cram:` or `pkam:` among its
  commands with `AT0009` and does not run it.
- **Passcodes.** An `enroll:request` passcode is accepted only as the SPP
  or as an OTP from `otp:get`, and each OTP admits one request. An OTP
  stored in the namespace-less form older atServers used is not
  accepted; an SPP in that form is, until `otp:put` sets an SPP, which
  removes it.
- **Enrollment expiry.** `enroll:approve` caps the approved enrollment's
  expiry at that of the enrollment that approved it, and answers with
  `expiresAt`. `enroll:fetch` and the `new.enrollments.__manage`
  notification carry `apkamKeysExpiryInMillis`, and an enrollment
  requested over CRAM reports it as 0. A retrofit successor expires no
  later than its predecessor. An `enroll:request` is refused with
  `AT0022` unless its `apkamKeysExpiryInMillis`, when given, is a whole
  number from 0 to 3155760000000 ([§9.4.1](#941-the-enroll-verb)).
- **atSigns.** An atSign of more than 55 characters after its `@`, or
  otherwise invalid, is refused with `AT0003` wherever a command names
  one, a `batch:` entry included, as is a `notify` naming no recipient;
  an authenticated client, or a `pol` peer, keeps its connection.
  `config:block:add`, `config:block:remove` and `scan` take each atSign
  in its canonical form, and `from:` compares atSigns with
  the blocklist in that form and never blocks this atServer's own
  atSign.
- **Cached copies.** A lookup of another atSign's public record leaves a
  cached copy only when the record has a `ttr`, and the 24-hour copies
  kept before are removed. A `plookup` that spells `publickey` in another
  case leaves this atServer's copy of another atSign's encryption public
  key unchanged. A cached copy the daily refresh finds unchanged is
  served until its `ttr` next runs out.
- **Sync.** A lookup of a record that does not exist, and the removal of
  an enrollment, add no entry to clients' sync. The first `lookup`,
  `llookup` or HTTP `GET` of an expired enrollment's data moves it to
  `<enrollmentId>.d.__e`.

### atServer 3.17.0

Production release [p3.17.0](https://github.com/atsign-foundation/at_server/releases/tag/p3.17.0), 2026-10-12. Includes canary release 3.17.0.

- **Notification persistence and expiry.** `notify` takes `eph`, for a
  notification no atServer stores, which lives at most two minutes and
  which a restart loses, and `eAtn`, the moment a notification expires.
  `eAtn` with `ttln`, or `eph` with `delete`, `ttr` or `ccd`, is refused
  with `AT0003`. Before it passes either on, an atServer sends
  `info:brief` to the receiving atServer, and passes them on, as given,
  only when its `info` lists them with any status but `Retired`. `info`
  and `info:brief` list `features`, among them `notify.eph` and
  `notify.eAtn`. The grammar is at_commons 5.20.0's.
- **Notifications from other atServers.** A notification another
  atServer delivers is refused with `AT0009` unless it is addressed to
  this atServer's atSign and, for a key notification, its key is owned
  by the atSign that atServer proved with `pol`.
- **`notify:all` deprecated.** `info` lists `notify.all` as
  `Deprecated`; send a `notify` to each recipient instead. It judges
  each recipient's key as `notify` does and, when it refuses one,
  notifies nobody.
- **HTTP.** A command that starts like an HTTP request, on a connection
  that did not negotiate `http/1.1`, is answered `AT0003` and the
  connection is closed ([§3.2](#32-atserver)). A request for `/ws` that
  is not a WebSocket upgrade is answered `400`.
- **Syntax errors before authentication.** A connection that has not
  authenticated is closed after it is answered `AT0003`; an
  authenticated one stays open.
- **`clientConfig`.** The `clientId`, `appName`, `appVersion` and
  `platform` a `from:` sends are kept to 64 characters, and a field that
  is not a string, or a `version` that does not parse, is ignored rather
  than failing the `from:`.
- **Enrollment data.** Data in an enrollment's own namespace is not
  served once that enrollment is no longer approved: `lookup` and
  `llookup` answer `AT0015`, and an HTTP `GET` `404`.
- **Monitors** are not sent notifications that have expired.
- **`config:set`** refuses, with `AT0003`, a value its setting cannot
  take, naming what it takes.
- **Telemetry.** An atServer started with a telemetry endpoint keeps an
  Ed25519 telemetry signing key and publishes its public half at
  `public:_at_telemetry_signing_publickey.__atserver@<atSign>`. No
  connection, CRAM included, can change either record, and neither an
  enrollment request nor `keys:put` can name the `__atserver` namespace
  ([§6.5](#65-reserved-keys)).

### atServer 3.16.6

Production release [p3.16.6](https://github.com/atsign-foundation/at_server/releases/tag/p3.16.6), 2026-10-09. Includes canary release 3.16.6.

- **Pipelining.** Commands are framed one per `\n` and handled in the
  order they arrive, so a client may send a command before it reads the
  previous response ([§4.7](#47-pipelining)). A read that carries no
  bytes no longer closes the connection.
- **`notify:all`** stores each recipient as an atSign and notifies it
  once however it is spelt, notifies the atServer's own atSign as
  `notify` does, refuses a key another atSign owns as `notify` does, and
  stores the time in UTC. Its reply is keyed by the canonical atSign.
- **Protected keys.** `delete` refuses this atServer's own `publickey`,
  `signing_publickey` and `signing_privatekey`, and
  `at_pkam_publickey`, with `AT0009` however their name is spelt
  ([§10.3](#103-delete)).
- **Commit ids.** A commit id is never issued twice. `stats:3` with no
  regex, and a monitor's stats notification, report the last commit id
  issued, `-1` for an empty log. On a namespace-restricted enrollment,
  `stats:3` counts by the rule `sync:from` sends by.
- **`to:`.** An atServer opens a connection to another atServer with
  `to:@<atSign>`, and falls back to `lookup:all:publickey@<atSign>` when
  that atServer does not accept it.

### atServer 3.16.5

Production release [p3.16.5](https://github.com/atsign-foundation/at_server/releases/tag/p3.16.5), 2026-09-30. Includes canary releases 3.16.0 to 3.16.5.

Authentication:

- **`pol` challenges.** A `from:` naming another atSign is answered with
  a challenge of the form `pol1.<base64url JSON>`, whose JSON names the
  issuing atServer's atSign as `v` and a fresh nonce as `n`; a `from:`
  naming the atServer's own atSign still gets a bare UUID. Proving itself
  to another atServer, an atServer signs a `pol1.` challenge only when
  `v` names the atSign it connected to, and signs a bare challenge as
  before.
- **One attempt per challenge.** Each `from:` challenge admits one
  `pkam`, `cram` or `pol` attempt within its 60 seconds; a retry needs a
  new `from:`, and `pkam` or `cram` without a live challenge is refused
  with `AT0401`.
- **APKAM algorithms.** An APKAM `pkam:` is verified under the signing
  algorithm recorded on its enrollment, whatever it sends, and keys with
  `signingAlgo` `mldsa65` authenticate.
- **The `primary` enrollment.** At startup the atServer moves the legacy
  PKAM public key into an enrollment named `primary`, approved, holding
  `*:rw` and `__manage:rw` and never expiring, and keeps no record at
  `privatekey:at_pkam_publickey`. A `pkam:` with no enrollment id, or
  with `enrollmentId:primary`, authenticates as `primary`. A CRAM
  `update` of `privatekey:at_pkam_publickey` installs the key as
  `primary` and answers `data:-1`; any other write of it is refused with
  `AT0009`. An `enroll:request` approved over CRAM no longer writes
  `at_pkam_publickey`, and no enrollment may write
  `privatekey:at_secret` or `privatekey:at_secret_deleted`
  ([§6.5](#65-reserved-keys)).
- **Retrofits.** An `enroll:request` on a connection authenticated as an
  enrollment creates an approved successor, with no OTP or approver, that
  holds exactly that enrollment's grants, needs a keypair of its own and
  expires no later than it; a successor may not itself be replaced this
  way. When the successor first authenticates, the enrollments its
  predecessor approved move to it, and a predecessor that does not hold
  `*:rw` and `__manage:rw` is revoked as superseded.
- **Connections follow their enrollment.** A connection whose enrollment
  is revoked, denied or pending is answered `AT0027`, `AT0025` or
  `AT0026` on its next command, and closed.

Authorization:

- **Full access is CRAM's.** Only a CRAM connection holds every
  permission. An unauthenticated `notify:all`, or `notify:status` of a
  notification that exists, is refused with `AT0009`. `__manage` keys
  never sync.
- **Enrollment management.** `otp:get` needs access to `__manage`.
  `enroll:fetch` and `enroll:delete` of another enrollment need
  `__manage` and access to every namespace it holds, and acting on an
  enrollment that holds `__manage:rw` needs `__manage:rw`; each refusal
  is `AT0009`. A caller holding `__manage:r` gets `enroll:list` as a
  roster without key material. `enroll:listns` and `enroll:infons` admit
  a caller to `__manage` only when it holds `__manage` explicitly.
- **Reserved namespaces and `*`.** A `*` grant does not reach `__manage`
  records, or another enrollment's `<enrollmentId>.a|r|d.__e` records
  beyond reading public ones. Another enrollment's `_apsk` record is
  read-only.
- **Keys without a namespace** are decided by kind: the two `shared_key`
  forms are readable by every approved enrollment and writable by one
  holding write access on some namespace; the atSign's own public and
  signing keys are readable by all and writable only by a root
  enrollment; `privatekey:` keys, the blocklist and `configkey` are
  writable only by a root enrollment; any other needs a `*` grant. No
  enrolled namespace matches such a key, one named `null` included, and
  a key that does not parse is judged as one.
- **`config:block`** needs a CRAM connection, or an approved enrollment
  holding write access on `*` and `__manage`; any other is refused with
  `AT0009`.
- **`update:meta`** is authorized like `update`: it needs `rw` on the
  key's namespace.

Enrollments:

- **`enroll:update`** lets an approved enrollment, authenticated as
  itself, change its own `apkamPublicKey`, `signingAlgo`, `apsk`,
  `apskLegacy` and `metadata` (merged per key), but never `namespaces`
  or its state. A new `apkamPublicKey` needs `apkamPublicKeySignature`,
  a signature by the new private key over
  `<enrollmentId>|<apkamPublicKey>|<signingAlgo>`.
- **Client data signing keys.** The atServer publishes an enrollment's
  `public:_apsk.<enrollmentId>.a.__e@<atSign>` only from the `apsk`, or
  the bare RSA `apskLegacy`, that `enroll:request` carries, and
  publishes nothing otherwise; before, it published every enrollment's
  `apkamPublicKey` there. A request carrying both is refused with
  `AT0022`, as is one that would take the enrollment record over 500 KiB.
- **Requests.** A grant's access must be `r` or `rw`, else `AT0022`. A
  request installing a key a stored enrollment already holds is refused
  with `AT0032`. An `enroll:request` must name at least one namespace,
  unless it is over CRAM or a retrofit. One whose `metadata` carries a
  `keyPackage` may omit `encryptedAPKAMSymmetricKey`. An enrollment
  holding no namespaces is refused by `enroll:fetch`, `approve`, `deny`,
  `revoke`, `unrevoke` and `delete`, except from itself or over CRAM.
- **Revocation.** Revoking an enrollment revokes every enrollment it
  approved, to any depth, and the response lists them as
  `cascadedEnrollmentIds`. A revoke whose cascade would take the caller,
  or that would leave no approved, permanent enrollment holding `*:rw`
  and `__manage:rw`, is refused with `AT0031`, even with `force`. An
  `enroll:unrevoke` or `enroll:approve` of an enrollment whose approver
  exists and is not approved is refused with `AT0032`.
  `enroll:infons:<namespace>` answers `{"lastRevokedAt":…}`, the last
  revocation of an enrollment holding that namespace, or null.
- **Records.** `enroll:list` and `enroll:fetch` report `expiresAt`, and
  `enroll:list` also `parentEnrollmentId` (the approver),
  `retrofitPredecessorEnrollmentId` and `predecessorSettledAt`. An
  expired enrollment is listed as `expired` until the expiry sweep
  removes it. Amending, revoking or un-revoking an enrollment keeps its
  expiry, and a key expiry of zero or less means none. `enroll:fetch`
  returns `metadata`. Enrollment ids are compared in the folded form of
  [§6](#6-the-atkey-model).

Records and data verbs:

- **Timestamps.** `update`, `update:meta` and `update:json` store an
  asserted `cAt`, `uAt`, `eAt` and `aAt`, derive a missing `ttl` or `ttb`
  from them, and keep the stored expiry and availability unless the
  write names them ([§7.1](#71-catalogue)). Notifications between
  atServers carry the record's `cAt` and `uAt`, and its `eAt` and `aAt`
  when set; an atServer whose grammar predates at_commons 5.10.0 refuses
  them. An `update:json` changes `ttl`, `ttb` or `ttr` only when it names
  them.
- **Commit log.** `:nc` writes no commit entry, removes the key's
  existing one and answers `data:-1`; `delete:dAt` stamps the delete's
  commit entry; `scan:cl` lists commit-log entries
  ([§10.1](#101-update), [§10.3](#103-delete), [§10.7](#107-scan)).
- **`update:json`** is held to the rules of the positional form: an
  empty, multi-line or non-string value, a negative `ttl`, a timestamp
  that is not UTC, `isPublic` with `sharedWith`, a `sharedBy` naming
  another atSign, or no atKey, is refused.
- **Immutable records.** An expired immutable record no longer blocks a
  new one.
- **Cached public keys.** `plookup:all:publickey@<atSign>` and
  `plookup:meta:publickey@<atSign>` report `ttr` `-1` and no `ttl`.

### atServer 3.15.0

Production release [p3.15.0](https://github.com/atsign-foundation/at_server/releases/tag/p3.15.0), 2026-08-08. Includes canary release 3.15.0.

- **`to:`.** An unauthenticated `to:@<atSign>` for this atServer's
  atSign answers
  `data:{"publickey":<lookup:all JSON or null>,"signing_publickey":<lookup:all JSON or null>}`;
  one naming another atSign gets `AT0007`. An atServer opens its own
  connections with it only when configured to.
- **`enroll:listns:<namespace>`** lists the approved enrollments holding
  that namespace, as `{enrollmentId, access, apkamPubKey, metadata}`
  (at_commons 5.12.0). It needs an APKAM connection whose approved
  enrollment holds `r` or more on the namespace: else `AT0401` when not
  APKAM, `AT0009` otherwise, and `AT0022` for an empty namespace.
- **Enrollment records.** `enroll:request` stores the `metadata` and
  `signingAlgo` it carries, and `enroll:list` entries return them. CRAM
  auto-approval and `enroll:approve` publish the enrollment's APKAM public
  key at `public:_apsk.<enrollmentId>.a.__e@<atSign>`.
- **`pkam:`** accepts `signingAlgo:mldsa65` (at_commons 5.12.0), and this
  release verifies such a signature as `rsa2048`.
- **`keys:get:keyName:<k>`** and **`keys:delete:keyName:<k>`** are
  refused with `AT0009` unless `<k>` is one of the calling enrollment's
  own records.
- **`cram`** fails when the atServer holds no CRAM secret, or an empty
  one.
- **Data moves.** Approving, revoking, un-revoking or removing an
  enrollment moves only that enrollment's own
  `<enrollmentId>.a|r|d.__e` data.
- **Sync.** `sync:from` skips a commit entry whose key no longer exists,
  rather than failing the request.

### atServer 3.14.0

Production release [p3.14.0](https://github.com/atsign-foundation/at_server/releases/tag/p3.14.0), 2026-06-19. Includes canary release 3.14.0.

- **`appMetadata`.** `update`, `update:meta` and `notify` take
  `:appMetadata:<base64 JSON>` (at_commons 5.11.0) and refuse a value
  that does not decode with `AT0003`. The atServer stores it, keeps it
  when a later update omits it or sends `null`, returns it as an object
  in `llookup:meta`, `llookup:all` and monitor notifications and as
  base64 in `sync:from`, and passes it on to the recipient's atServer
  ([§7.1](#71-catalogue)).
- **Commit log.** `config:block:add` and `config:block:remove` are not
  recorded in the commit log, and the removal of an expired key never
  writes a commit entry, so neither appears in `sync:from`.
- **`notify:list`** dates are UTC calendar days.

### atServer 3.13.2

Production release [p3.13.2](https://github.com/atsign-foundation/at_server/releases/tag/p3.13.2), 2026-06-05. Includes canary releases 3.13.1 and 3.13.2.

- **Split commands.** The atServer checks a command's verb once it has a
  `\n` or 16 bytes, so a command whose first read is shorter than its
  verb is no longer refused.

### atServer 3.13.0

Production release [p3.13.0](https://github.com/atsign-foundation/at_server/releases/tag/p3.13.0), 2026-05-21. Includes canary release 3.13.0.

- **Grammar.** at_commons 5.10.0 takes `cAt`, `uAt`, `eAt` and `aAt` in
  the metadata fragment, `:nc` on `update`, `update:meta`,
  `update:json` and `delete`, `:dAt:` on `delete`, and `:cl` on `scan`.
  The atServer accepts them and acts on none of them until 3.16.5.

### atServer 3.12.0

Production release [p3.12.0](https://github.com/atsign-foundation/at_server/releases/tag/p3.12.0), 2026-04-30. Includes canary releases 3.11.0 to 3.11.3 and 3.12.0.

- **Known verbs only.** As a command arrives, the atServer refuses with
  `AT0003` one whose verb is not `update`, `llookup`, `plookup`,
  `delete`, `sync`, `notify`, `monitor`, `otp`, `keys`, `batch`,
  `stats`, `config`, `from`, `cram`, `pkam`, `pol`, `scan`, `lookup`,
  `info`, `noop` or `enroll`. `@exit` and `stream:` are among those
  refused ([§3.3](#33-connection-lifecycle)).
- **Client certificates.** For a `from:` naming another atSign, the
  client certificate must name that atSign's atServer host exactly, as
  its subject, CN or a SAN entry ([§3.2](#32-atserver)).
- **Challenges.** A successful `cram`, `pkam` or `pol` removes its `from:`
  challenge, so authenticating again on the connection needs a new
  `from:`.
- **`config`.** `config:set` and `config:reset` act for a connection
  with access to `__config`, CRAM or legacy PKAM, or an enrollment
  holding `__config` or `*`, and refuse any other with `AT0009`;
  `config:print` acts for any authenticated connection. Before, all three
  answered `data:testing mode disabled by default`.
- **HTTP.** An HTTP `GET` also takes a path that starts with
  `/<atSign>/`.
- **Monitors.** A monitor notification's `metadata` carries `ttr`, `ttl`
  and `ttb`.

### atServer 3.10.3

Production release [p3.10.3](https://github.com/atsign-foundation/at_server/releases/tag/p3.10.3), 2026-03-18. Includes canary releases 3.10.0 to 3.10.3, and versions 3.9.3 and 3.9.4.

- **`enroll:deny`** of an enrollment that is not pending is refused with
  `AT0032`.
- **Notifications from other atServers.** One that has expired, or that
  the atServer already holds, is answered `data:success` and neither
  stored nor delivered.
- **Notification lifetime.** A notification lives at most 8 days, and
  one sent with no `ttln`, or a `ttln` of 0 or less, gets the default,
  `notificationExpiryInMins` (15 minutes). An atServer passing a
  notification on sends its remaining lifetime as `ttln`, and retries
  until it is delivered, it expires, or its recipient leaves the
  atDirectory.
- **`notify:list`** on a `pol` connection lists, from this atServer's own
  store, the notifications it has sent to that atSign.
- **Monitors.** A monitor's live notifications carry `availableAt` and
  `expiresAt` in `metadata`, as replayed ones do; `monitor:<epochMillis>`
  replays in the order they were created; and a `monitor` whose regex
  does not compile is refused with `AT0003`.
- **Self notifications.** An `update` of a key shared with this
  atServer's own atSign sends no notification.

### atServer 3.9.0

Production release [p3.9.0](https://github.com/atsign-foundation/at_server/releases/tag/p3.9.0), 2026-01-12. Includes canary releases 3.8.0 and 3.9.0, and version 3.7.2.

- **mTLS.** On its connections to other atServers, an atServer presents
  the client certificate at `certs/mtls/fullchain.pem` and
  `certs/mtls/privkey.pem` when it has one, and its server certificate
  otherwise ([§3.2](#32-atserver)).
- **`info:mtls`** returns that certificate chain as `mtls_fullchain`, and
  **`info:mtlsbrief`** the times the chain and its key last changed
  (at_commons 5.7.0). Neither needs authentication
  ([§13.3](#133-info)).
- **Expired keys.** When the expiry sweep removes a key, it writes no
  delete commit entry and removes the key's latest one, so `sync:from`
  sends no delete for it; clients expire such keys themselves.

### atServer 3.7.1

Production release [p3.7.1](https://github.com/atsign-foundation/at_server/releases/tag/p3.7.1), 2025-09-25. Includes canary releases 3.7.0 and 3.7.1.

- **`stats:16`** returns inbound connection counts,
  `{"total","self","other","anon"}`, and **`stats:17`** adds a list of
  `{from, created, lastAccessed}` for each connection.
- **Idle limits.** An authenticated inbound connection is closed after
  10 minutes idle, not 30 days, and an outbound one after 9 minutes 59
  seconds, not 10 minutes. As inbound connections near their limit, the
  allowed idle time starts to shrink at 80% of it, not 50%, and to no
  less than 5 minutes, not 60 seconds ([§3.4](#34-idle-and-timeout-behaviour)).

### atServer 3.6.0

Production release [p3.6.0](https://github.com/atsign-foundation/at_server/releases/tag/p3.6.0), 2025-09-05. Includes canary release 3.6.0.

- **HTTP `GET`** reads a public record named by the path's segments in
  reverse, so `/baz/bar/index.html` reads `public:index.html.bar.baz@<atSign>`.
  It answers the raw value, decoding a binary one, with `200`; `404` when
  there is none; `405` for any other method; and `400` for a URI over
  1000 characters. `at_rt=meta` or `at_rt=all` returns the metadata or
  the `lookup:all` JSON, and `at_ct` sets the `Content-Type`.
- **Monitors.** A monitor notification's `metadata` carries `pubKeyCS`
  and `dataSignature`, and a replayed one `sharedKeyEnc`.
- **atDirectory.** It answers HTTPS, by default on port `443`:
  `GET /<atSign>`, with or without `@`, returns `host:port`;
  `GET /<atSign>/<path>` redirects to `https://<host:port>/<path>`; an
  unknown atSign gets `404`, any method but `GET` `401`, and a URI over
  1000 characters `400` ([§3.1](#31-atdirectory)).

### atServer 3.5.1

Production release [p3.5.1](https://github.com/atsign-foundation/at_server/releases/tag/p3.5.1), 2025-06-08. Includes canary releases 3.5.0 and 3.5.1.

- **Per-enrollment namespaces.** Each APKAM enrollment holds `rw` on a
  namespace of its own, `<enrollmentId>.a.__e`. Its data moves to
  `<enrollmentId>.r.__e` when it is revoked, back on approval or
  un-revocation, and to `<enrollmentId>.d.__e` when it is removed or
  expires; the moves sync ([§6.5](#65-reserved-keys)).
- **APKAM `scan` and `sync:from`** list what the enrollment may read by
  the rule other verbs apply: its namespaces, `__atserver`, its own
  `<enrollmentId>.a.__e` and reserved keys. A key without a namespace, or
  in a namespace it does not hold, does not sync to an enrollment without
  `*`, whatever else it holds.
- **Enrollment errors.** An `enroll` refusal carries `AT0022` for a
  passcode or parameter that is not valid, `AT0032` for an operation the
  enrollment's state does not allow or a duplicate request, and `AT0009`
  for an approver without the access it needs, in place of `AT0011`.
- **`enroll:list`** entries carry the whole stored record, `sessionId`,
  `apkamPublicKey`, `namespaces`, `requestType`, `approval` and
  `apkamKeysExpiryInMillis` among them.
- **`__pkams`.** Approval no longer publishes
  `public:<appName>.<deviceName>.pkam.__pkams.__public_keys@<atSign>`,
  and the atServer removes such records at startup.
- **Lookups.** `lookup` and `llookup` of a key in an enrollment's
  namespace check that enrollment first, and `plookup` of one does not
  answer from a cached copy.

### atServer 3.4.1

Production release [p3.4.1](https://github.com/atsign-foundation/at_server/releases/tag/p3.4.1), 2025-06-07. Includes canary release 3.4.1.

- **Relayed values.** A value another atServer returns for a `lookup` is
  passed on with only its leading `data:` removed, so a value containing
  `data:` arrives unaltered.

### atServer 3.4.0

Production release [p3.4.0](https://github.com/atsign-foundation/at_server/releases/tag/p3.4.0), 2025-03-12. Includes canary releases 3.3.0 and 3.4.0.

- **atServer events.** When the atServer finds another atSign's
  `public:publickey` has changed, it writes
  `<microsecondsSinceEpoch>.events.__atserver@<atSign>` with value
  `{"category":"atProtocol","name":"atsign_pk_changed","data":{"atSign":"@<other>"}}`,
  and sends its own atSign a self notification of that key that lasts 5
  minutes ([§14.3](#143-public-key-rotation)). Every APKAM enrollment may
  read the `__atserver` namespace, and none may write it.
- **Immutable records.** `update` and `update:meta` take
  `:immutable:true|false` (at_commons 5.3.0), and refuse with `AT0032` a
  later write of a record that is immutable. `delete` takes `:force`, and
  refuses an immutable record without it with `AT0032`; a `delete:cached:`
  is not refused. `notify` carries `immutable`, which is passed on to the
  recipient's atServer and returned in `llookup:meta` and `sync:from`
  metadata ([§7.1](#71-catalogue)).
- **CRAM enrollment.** An `enroll:request` over CRAM is not refused for
  the `appName` and `deviceName` of a pending or approved enrollment.

### atServer 3.2.0

Production release [p3.2.0](https://github.com/atsign-foundation/at_server/releases/tag/p3.2.0), 2025-02-04. Includes canary release 3.2.0.

- **ALPN.** The atServer's TLS port offers `atProtocol/1.0` and
  `http/1.1` by ALPN. A connection that negotiates `atProtocol/1.0`, or
  no protocol, speaks the Atsign Protocol; one that negotiates
  `http/1.1` reaches an HTTP server ([§3.2](#32-atserver)).
- **WebSocket.** An HTTP request for `/ws` is upgraded to a WebSocket
  carrying the Atsign Protocol: the atServer sends `@`, then its
  responses as text frames, and takes commands as text or binary frames.
- **HTTP `GET /<key>`** answers `data:<value>` for
  `public:<key>@<atSign>`, or an error when there is none, and any other
  method gets `400`.
- **TLS only.** The atServer will not start without TLS.

### atServer 3.1.1

Production release [p3.1.1](https://github.com/atsign-foundation/at_server/releases/tag/p3.1.1), 2024-12-20. Includes canary release 3.1.1.

- **`pubKeyHash`.** `update`, `update:meta` and `notify` store
  `pubKeyHash` and `hashingAlgo`, which come back as a `pubKeyHash`
  object in `llookup:meta` and `llookup:all`, as a JSON string in
  `sync:from` and monitor metadata, and are passed on to the recipient's
  atServer.
- **`sync:from`** honours `:limit:` as the most entries in a response,
  the atServer's page size by default.

### atServer 3.1.0

Production release [p3.1.0](https://github.com/atsign-foundation/at_server/releases/tag/p3.1.0), 2024-12-11. Includes canary release 3.1.0.

- **`sync:from`** takes `:skipDeletesUntil:<n>`, and leaves out delete
  entries up to commit id `n` other than the log's latest entry;
  `:limit:` becomes optional (at_commons 5.1.1)
  ([§12.1](#121-syncfrom)).
- **Approval IVs.** `enroll:approve` takes `encPrivateKeyIV` and
  `selfEncKeyIV`, stored as `iv` beside each encrypted key and returned
  by `keys:get`. An `enroll:request` approved over CRAM stores no
  encrypted key copies.

### atServer 3.0.52

Production release [p3.0.52](https://github.com/atsign-foundation/at_server/releases/tag/p3.0.52), 2024-12-04. Includes canary release 3.0.52.

- **`pubKeyHash`.** `update`, `update:meta` and `notify` accept
  `pubKeyHash:<hash>` and `hashingAlgo:<algo>` (at_commons 5.0.2), and a
  `pubKeyHash` object in an `update:json` document is stored and
  returned in the key's metadata.
- **`enroll:delete`** also removes the enrollment's `__pkams` public-key
  record and the encrypted key copies its approval stored.
- **Sync.** `sync:from` with a regex always includes the reserved
  `shared_key` keys, `public:publickey@<atSign>` and `public:` keys
  without a namespace, and no longer every `public:` key.

### atServer 3.0.51

Production release [p3.0.51](https://github.com/atsign-foundation/at_server/releases/tag/p3.0.51), 2024-10-14. Includes canary release 3.0.51.

- **`enroll:unrevoke`** returns a revoked enrollment to `approved`,
  under the checks `enroll:approve` applies.
- **`enroll:delete`** removes a denied or revoked enrollment and answers
  `{"enrollmentId":…,"status":"deleted"}`; an expired one gets `AT0028`.
- **APKAM key expiry.** `enroll:request` takes `apkamKeysExpiryInMillis`
  (0 for none), and approval gives the enrollment that lifetime. Once it
  lapses, a `pkam` naming the enrollment gets `AT0028`, and a connection
  authenticated as it is closed on its next command.
- **`pkam:`** accepts `hashingAlgo:sha512` (at_commons 5.0.0).
- **`enroll:update`** is refused with `AT0003`: the grammar no longer
  takes it.
- **`info`** returns `apkam_metadata` as a JSON object, not a JSON
  string.
- **Records.** The `__pkams` public-key record an approval writes is not
  recorded in the commit log, so it does not sync. `stats:15` returns
  every key, not at most 25.

### atServer 3.0.50

Production release [p3.0.50](https://github.com/atsign-foundation/at_server/releases/tag/p3.0.50), 2024-09-27. Includes canary release 3.0.50.

- **Namespaces with a dot.** An enrollment granted a namespace that
  contains a `.`, such as `foo.bar`, reaches keys in it, such as
  `phone.foo.bar@<atSign>`.

### atServer 3.0.49

Production release [p3.0.49](https://github.com/atsign-foundation/at_server/releases/tag/p3.0.49), 2024-08-27. Includes canary release 3.0.49.

- **Approvers.** `enroll:approve`, `deny` and `revoke` on an APKAM
  connection need an approved enrollment holding `__manage` and, for
  each namespace the target holds, `rw`, or `r` where the target holds
  only `r`.
- **Required parameters.** `enroll:request` needs `appName`,
  `deviceName` and `apkamPublicKey` and, with an `otp`, also
  `encryptedAPKAMSymmetricKey` and at least one namespace;
  `enroll:approve` needs `enrollmentId`,
  `encryptedDefaultEncryptionPrivateKey` and
  `encryptedDefaultSelfEncryptionKey`; `deny` and `revoke` need
  `enrollmentId`.
- **Notifications.** `notify` honours `isEncrypted:false` on a key
  notification, and atServers pass `isEncrypted` on as given. A
  monitor's notifications carry `sharedKeyEnc` in `metadata`.
- **`info`** no longer returns `features`.
- **Grants.** Where an enrollment holds both a namespace and `*`, the
  namespace's own access applies to its keys. A denied enrollment keeps
  the 48-hour expiry of its request.

### atServer 3.0.48

Production release [p3.0.48](https://github.com/atsign-foundation/at_server/releases/tag/p3.0.48), 2024-07-11. Includes canary release 3.0.48.

- **`notify:list`** entries, and the notifications `monitor:<epochMillis>`
  replays, carry `availableAt` and `expiresAt` in `metadata`.

### atServer 3.0.47

Production release [p3.0.47](https://github.com/atsign-foundation/at_server/releases/tag/p3.0.47), 2024-06-17. Includes canary release 3.0.47.

- **Passcode records.** An OTP is kept at
  `private:<otp>.__otp@<atSign>` and the SPP at
  `private:spp.__otp@<atSign>`; passcodes kept in the earlier form are
  still honoured.
- **SPP lifetime.** `otp:put:<spp>:ttl:<ms>` sets the SPP's lifetime,
  none by default, and an expired SPP is not accepted.
- **Enrollment notification.** The pending-enrollment notification
  carries the encrypted APKAM symmetric key as
  `encryptedAPKAMSymmetricKey` too, beside `encryptedApkamSymmetricKey`.

### atServer 3.0.46

Production release [p3.0.46](https://github.com/atsign-foundation/at_server/releases/tag/p3.0.46), 2024-05-22. Includes canary release 3.0.46.

- **Revocation closes connections.** `enroll:revoke` closes the
  connections authenticated as the revoked enrollment. A forced revoke of
  the caller's own enrollment adds a `message` to its answer and closes
  the connection 10 seconds later.
- **Enrollment notification.** The pending-enrollment notification is
  keyed `<enrollmentId>.new.enrollments.__manage@<atSign>`, and reaches
  APKAM monitors holding `r` or `rw` on `__manage`.
- **`otp:get`** without `:ttl:` always issues a 5-minute OTP.

### atServer 3.0.45

Production release [p3.0.45](https://github.com/atsign-foundation/at_server/releases/tag/p3.0.45), 2024-05-02. Includes canary release 3.0.45.

- **Self-revocation.** A connection revokes its own enrollment only with
  `enroll:revoke:force:<json>` (at_commons 4.0.9); without `force` it gets
  `AT0031`.
- **`enroll:fetch`** answers
  `{appName, deviceName, namespace, encryptedAPKAMSymmetricKey, status}`,
  as an `enroll:list` entry does.
- **Monitors.** An APKAM monitor receives a notification only when its
  enrollment may read the key: `r` or `rw` on its namespace, `*` for a
  key without one, and always for a reserved key.

### atServer 3.0.44

Production release [p3.0.44](https://github.com/atsign-foundation/at_server/releases/tag/p3.0.44), 2024-04-29. Includes canary release 3.0.44.

- **`otp:`** needs an authenticated connection, else `AT0401`.
- **`enroll:fetch:{"enrollmentId":…}`** returns the stored enrollment
  record (at_commons 4.0.8); an unknown or expired id gets `AT0015`.
- **Unique app and device.** `enroll:request` is refused while another
  pending or approved enrollment has the same `appName` and
  `deviceName`.
- **`shared_key.<atSign>@<atSign>`** is a reserved key.

### atServer 3.0.43

Production release [p3.0.43](https://github.com/atsign-foundation/at_server/releases/tag/p3.0.43), 2024-04-23. Includes canary release 3.0.43.

- **Key length.** An atKey longer than 248 characters, or 255 for a
  `cached:` key, is refused: by `update` and `update:meta` with
  `AT0016`, and elsewhere with `AT0002`, which closes the connection
  ([§6.4](#64-key-length)).

### atServer 3.0.42

Production release [p3.0.42](https://github.com/atsign-foundation/at_server/releases/tag/p3.0.42), 2024-04-05. Includes canary release 3.0.42.

- **APKAM notifications.** On an APKAM connection, `notify`,
  `notify:all` and `notify:remove` need `rw`, and `notify:fetch` and
  `notify:status` `r` or `rw`, on the key's namespace; `notify:list`
  leaves out notifications the connection may not read.
- **Keys without a namespace.** On an APKAM connection, a key without a
  namespace needs `*`; reserved keys are open to every enrollment.
- **`enroll:list:{"enrollmentStatusFilter":[…]}`** filters by status
  (at_commons 4.0.5), and each entry carries `status`; without a filter,
  every status is listed.
- **`delete`** of a `cached:` key is never refused as protected.

### atServer 3.0.41

Production release [p3.0.41](https://github.com/atsign-foundation/at_server/releases/tag/p3.0.41), 2024-03-18. Includes canary release 3.0.41.

- **`otp:put`** is accepted from an approved enrollment holding `r` or
  `rw` on `__manage`, directly or through `*`, and from a connection
  that carries no enrollment.

### atServer 3.0.40

Production release [p3.0.40](https://github.com/atsign-foundation/at_server/releases/tag/p3.0.40), 2024-03-04. Includes canary release 3.0.40.

- **Enrollments.** `enroll:list` entries carry
  `encryptedAPKAMSymmetricKey`, and the pending-enrollment notification
  carries `appName`, `deviceName` and `namespace`.

### atServer 3.0.39

Production release [p3.0.39](https://github.com/atsign-foundation/at_server/releases/tag/p3.0.39), 2024-02-07. Includes canary release 3.0.39.

- **Semi-permanent passcodes.** `otp:put:<spp>`, six or more word
  characters, stores an SPP at `private:spp@<atSign>` and answers
  `data:ok`. `enroll:request` accepts it in place of an OTP, and does not
  use it up. Only an APKAM enrollment holding `__manage` or `*` may set
  it.
- **OTPs.** `otp:get:ttl:<ms>` sets an OTP's lifetime, 5 minutes by
  default, and an OTP is used up the first time it is presented. An
  `enroll:request` with a passcode that is not valid is answered after a
  delay that grows with consecutive failures, up to 55 seconds by
  default.
- **`enroll` field.** `encryptedDefaultEncryptedPrivateKey` is renamed
  `encryptedDefaultEncryptionPrivateKey` (at_commons 4.0.0).
- **Blocklist.** The `config:block` list is kept at
  `private:blocklist@<atSign>`.
- **atSigns** named in `update`, `delete`, `notify`, `notify:all` and
  `plookup` are lowercased.

### atServer 3.0.36

Production release [p3.0.36](https://github.com/atsign-foundation/at_server/releases/tag/p3.0.36), 2023-10-23. Includes canary release 3.0.36.

- **OTPs.** An OTP from `otp:get` lasts 5 minutes, is matched in any
  case, and is removed when an `enroll:request` presenting it succeeds.
  `otp:validate` is removed (at_commons 3.0.57).
- **Enrollment limits.** `enroll:request` is limited to 5 per connection
  per hour by default; a request over the limit gets `AT0011`, and the
  connection stays open. A pending enrollment expires 48 hours after its
  request: `enroll:approve`, `deny`, `revoke` or `pkam` naming an expired
  or unknown enrollment gets `AT0028`, and `enroll:list` leaves it out.
- **Enrollment states.** `enroll:approve` accepts only a pending
  enrollment and `enroll:revoke` only an approved one, and every
  operation but `list` needs its JSON parameters, else `AT0022`.
- **APKAM monitor and sync.** An APKAM monitor receives only
  notifications in its enrolled namespaces, all of them with `*` or
  `__manage`, and none once its enrollment is not approved. APKAM
  `sync` returns only entries in the enrolled namespaces and entries
  without a namespace, all of them with `*` or `__manage`, and `stats:3`
  reports the highest commit id among them.
- **Notification values.** A `notify` with a value and no `ttr` passes
  the value on to the recipient's atServer, which delivers it without
  caching it.
- **atDirectory.** On one connection, the second lookup of an atSign the
  atDirectory does not know is answered after 3 seconds, and the third
  closes the connection ([§8.3](#83-response)).

### atServer 3.0.35

Production release [p3.0.35](https://github.com/atsign-foundation/at_server/releases/tag/p3.0.35), 2023-09-07. Includes canary release 3.0.35.

- **`otp`.** The `totp` verb is replaced by `otp` (at_commons 3.0.54):
  `otp:get`, on an authenticated connection, returns a passcode of six or
  more uppercase letters and digits that lasts 90 seconds, and
  `otp:validate:<otp>` answers `valid` or `invalid`.
- **`enroll` parameters.** `enroll:request`, `approve`, `deny` and
  `revoke` take one JSON object, `enroll:<operation>:<json>`, with
  `enrollmentId`, `appName`, `deviceName`, `namespaces` (namespace to
  `r` or `rw`), `otp`, `apkamPublicKey`,
  `encryptedDefaultEncryptedPrivateKey`,
  `encryptedDefaultSelfEncryptionKey` and `encryptedAPKAMSymmetricKey`,
  in place of the colon-separated form.
- **Approval.** An `enroll:request` over CRAM is approved at once with
  `rw` on `__manage` and on `*`, answers status `approved`, and stores
  the APKAM public key at `privatekey:at_pkam_publickey`; any other
  request is stored as `pending`, and announced as a self notification
  `<enrollmentId>.new.enrollments.__manage` whose value carries
  `encryptedApkamSymmetricKey`. Approval stores the APKAM public key at
  `public:<appName>.<deviceName>.pkam.__pkams.__public_keys@<atSign>`
  and the encrypted keys at
  `<enrollmentId>.default_enc_private_key.__manage@<atSign>` and
  `<enrollmentId>.default_self_enc_key.__manage@<atSign>`. Enrollment
  records and these copies are not recorded in the commit log.
- **`pkam:`** names its enrollment with `enrollmentId:<id>`, in place of
  `enrollApprovalId:<id>`, and a denied, pending or revoked enrollment is
  answered `AT0025`, `AT0026` or `AT0027`.
- **`keys`.** `keys:put`, `keys:get` and `keys:delete` serve connections
  authenticated as an approved APKAM enrollment
  ([§9.4.3](#943-the-keys-verb)).
- **APKAM namespaces.** On an APKAM connection, `lookup` and `llookup`
  need `r` or `rw`, and `update` and `delete` `rw`, on the key's
  namespace; `*` grants every namespace, and `__manage` keys are refused.
  APKAM `scan` lists `public:` keys and keys in the enrolled namespaces,
  all of them with `*`.
- **`lookup` before `pol`.** After `from:`, a `lookup` answers from
  `public:` records until `pol` succeeds, and from records shared with
  the `from:` atSign only after.
- **Protected keys.** `delete` refuses this atSign's
  `public:publickey`, `public:signing_publickey` and
  `@<atSign>:signing_privatekey`, and any key configured as protected,
  with `AT0009`.
- **Errors.** An `enroll` failure, such as a passcode that is not valid,
  keeps the connection open. A `sync` response carries at most 25 commit
  entries.
