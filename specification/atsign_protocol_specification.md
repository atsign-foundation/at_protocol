# Atsign Protocol Specification

<!-- pyml disable-num-lines 5000 md013-->

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

### For implementers, read these first

If you're implementing this specification, read these two appendices
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
| HTTPS        | Also on port `443`: `GET /<atSign>` returns `host:port`, `GET /<atSign>/<path>` redirects to `https://<host:port>/<path>`, an unknown atSign gets `404`, any other method `401`; the atSign is looked up as given |

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
carrying the Atsign Protocol. Since atServer 3.17.0, a command that
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

The protocol is request-response. Since atServer 3.16.6, an atServer
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

- `public:__<key>@<owner>` (two underscores) and a self key
  `_<key>@<owner>` are listed only when the caller passes
  `:showhidden:true`. The commit log records both, so both sync.
- `public:_<key>@<owner>` (one underscore) is never listed, even with
  `:showhidden:true`. The commit log never records one, so it never
  syncs, and a write of one answers `data:-1`.

An unauthenticated `scan` lists no hidden key. A shared key whose
`<key>` part starts with `_`, such as `@bob:_handshake.wavi@alice`, is
not hidden: `scan` lists it like any other shared key.

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

Since atServer 3.16.4 no record is kept under
`privatekey:at_pkam_publickey`. At startup the atServer moves one it
finds into the enrollment named `primary`, or deletes it. A CRAM
`update` of this name installs the key as `primary` and answers
`data:-1`.

With its default encryption, the reference SDK writes
`shared_key.<recipient>@<atSign>` and
`@<recipient>:shared_key@<atSign>` when the owner first shares data
with `<recipient>`. The recipient's copy carries `ttr:3888000`.

Since atServer 3.17.0, an atServer started with a telemetry endpoint
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

Two namespaces are reserved:

- `__manage` holds, among others, each enrollment record, at
  `<enrollmentId>.new.enrollments.__manage@<atSign>`, and the
  encrypted copies of the atSign's encryption private key and
  self-encryption key that `enroll:approve` supplies for it, at
  `<enrollmentId>.default_enc_private_key.__manage@<atSign>` and
  `<enrollmentId>.default_self_enc_key.__manage@<atSign>`.
- `__atserver` holds records the atServer writes for its clients, such
  as `<micros>.events.__atserver@<atSign>` when another atSign's
  `publickey` changes. Every approved enrollment may read it.

Each approved enrollment also holds `rw` on a namespace of its own,
`<enrollmentId>.a.__e`. When the enrollment is revoked, its data
moves to `<enrollmentId>.r.__e`, and an un-revoke moves it back. When
the enrollment record is removed, by `enroll:delete` or once it has
expired, its data moves to `<enrollmentId>.d.__e`.

Since atServer 3.16.1, approving an enrollment whose request carries
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
| `public:__location@alice`              | Public  | Yes     | No      |
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
| `eAt`             | ISO 8601 | `expiresAt`. Derived from `ttl`; since atServer 3.16.3 an asserted value is stored instead (see below).                                   |
| `aAt`             | ISO 8601 | `availableAt`. Derived from `ttb`; since atServer 3.16.3 an asserted value is stored instead (see below).                                 |
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
Since atServer 3.16.3, an `update` or `update:meta` that sets neither
`ttl` nor `eAt` keeps the stored `expiresAt`, one that sets neither
`ttb` nor `aAt` keeps the stored `availableAt`, and a `ttl` sent
without `ttb` counts from the write alone, whatever `ttb` the record
holds.

An update notification with no `ttr`, or `ttr:0`, does not cache the
value at the recipient's atServer.

Since atServer 3.13.0 (at_commons 5.10.0), the grammar takes `cAt`,
`uAt`, `eAt` and `aAt`. Since atServer 3.16.3, the atServer stores
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

Since atServer 3.14.0 (at_commons 5.11.0), `appMetadata` may carry
provider-owned fields beside `providerId`. The reference SDK sets it
on each value it encrypts, with `providerId` `legacy` unless the app
configures another provider. The atServer refuses, with `AT0003`, a
value that does not decode to such an object. Otherwise it stores,
returns and forwards it without acting on it, except that since atServer
3.18.0 it writes, keeps and drops the `apskLinks` on an enrollment's
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
prompt.

### 8.2 Lookup

Send the atSign followed by `\n`, without its leading `@` (the
reference SDK strips it). The atDirectory lowercases the line before it
looks it up:

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
2. **Get an OTP**, the user, on a session already authenticated as
   owner, runs `otp:get` and reads the OTP to the new app.
3. **`enroll:request`**, the new app submits the request, including
   its APKAM public key, the OTP, the namespace permission map, and
   the APKAM symmetric key encrypted with the **default encryption
   public key** (so only an owner-keys holder can decrypt it).
4. **`enroll:approve`**, the owner-keys holder fetches the request,
   decrypts the APKAM symmetric key, then sends back the
   default encryption private key and self-encryption key, each
   encrypted with the now-shared APKAM symmetric key (with IVs).
   Since atServer 3.17.1, the approved enrollment expires no later than
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
| `otp`                                  | request                                        | One-time password from `otp:get`.                                                                                                                                                                       |
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
| `approve`  | `data:{"status":"approved","enrollmentId":"<uuid>"}`. Since atServer 3.17.1 it also carries `"expiresAt"`, an ISO-8601 UTC string or null |
| `deny`     | `data:{"status":"denied","enrollmentId":"<uuid>"}`                                              |
| `revoke`   | `data:{"status":"revoked","enrollmentId":"<uuid>"}`, with `"cascadedEnrollmentIds":[…]` when it also revoked the enrollments that descend from it, those it approved and those they approved (`:force:` to revoke own enrollment) |
| `unrevoke` | `data:{"status":"approved","enrollmentId":"<uuid>"}`                                            |
| `delete`   | `data:{"enrollmentId":"<uuid>","status":"deleted"}`                                             |
| `fetch`    | `data:{ <full enrollment record JSON> }`                                                        |
| `list`     | `data:{"<enrollKey>":{<enrollment record JSON>}, …}`                                            |
| `link`     | Since atServer 3.18.0: `data:{"enrollmentId":"<uuid>","linked":["<kid>", …]}`; see [§9.4.4](#944-linking-an-enrollments-client-data-signing-keys-enrolllink) |

Since atServer 3.17.1, a request is refused with `AT0022` unless its
`apkamKeysExpiryInMillis`, when given, is a whole number from 0 to
3155760000000 (36,525 days); before, a negative value also asked for
none.

Since atServer 3.17.1, `approve` caps the approved enrollment's expiry at
that of the enrollment the connection authenticated as, when that one
expires, and reports the moment the approved enrollment ends as
`expiresAt`, null when it never does. An earlier expiry the request asked
for is kept. An approval over a CRAM connection, or by an enrollment that
never expires, caps nothing.

The encryption keys stored for an enrollment on approval expire when the
enrollment does.

An `enroll:request` sent over a CRAM connection is the atSign's root
enrollment: it is approved at once and never expires, whatever expiry it
asks for. Since atServer 3.17.1 it reports `apkamKeysExpiryInMillis` as
0; a root requested earlier reports the expiry it asked for.

`list` entries and `fetch` carry `apkamKeysExpiryInMillis` and
`expiresAt`. For a pending request, `apkamKeysExpiryInMillis` is the key
expiry it asks for (0 or less for none), and `expiresAt` is when the
request lapses unapproved, 48 hours after it was made by default. Once
a request is approved, they are the term granted and the moment it ends;
a root requested before atServer 3.17.1 is the exception above.
`list` and `fetch` carry `expiresAt` since atServer 3.16.4, and `fetch`
carries `apkamKeysExpiryInMillis` since 3.17.1.

A pending request is announced to approver apps as a self notification
keyed `<enrollmentId>.new.enrollments.__manage@<atSign>`. Its value
carries `appName`, `deviceName`, `namespace`, the encrypted APKAM
symmetric key under both `encryptedApkamSymmetricKey` and
`encryptedAPKAMSymmetricKey`, and, since atServer 3.17.1,
`apkamKeysExpiryInMillis`. A request approved at once is not announced.

#### 9.4.2 The `otp` verb

```text
otp:get[:ttl:<ms>]
otp:put:<otp>[:ttl:<ms>]
```

Source:

```text
^otp:(?<operation>get|put)(:(?<otp>(?<=put:)\w{6,}))?(:(?:ttl:(?<ttl>\d+)))?$
```

- `otp:get`, owner-authenticated. Returns a fresh 6-character
  alphanumeric OTP. Used as the `otp` field of `enroll:request`.
- `otp:put:<otp>`, owner-authenticated. Stores a semi-permanent OTP
  for use in headless / CLI enrollment flows.
- `:ttl:<ms>`, sets the OTP validity window.

**Response**: `data:<otp>` (for `get`) or `data:ok` (for `put`).

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

> **Since atServer 3.18.0.**

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

An atServer before 3.18.0 refuses `enroll:link` with `AT0003`, as a command
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

- the target enrollment is approved, and its `_apsk` record is not
  immutable;
- each `kid` is one the target's `_apsk` lists once, with its public key
  spelt in padded standard base64, and that key is not the target's client
  authentication signing key, the `apkamPublicKey` its enrollment record
  holds, compared as key bytes;
- each link is a JSON object whose `payload`, a JSON object or the base64url
  encoding of one, names the target enrollment, its id compared in the
  folded form of [§6](#6-the-atkey-model), and that key's `kid`, `alg` and
  public key as `enrollmentId`, `kid`, `alg` and `pub`;
- each link is at most 16 KiB as JSON, the call's parameters are within
  500 KiB (512,000 bytes) as JSON, and so is the `_apsk` record's value and
  `appMetadata` with every link the record would then hold;
- each `expect` equals, compared as JSON, the link stored on that key, or
  is `null` when none is stored.

A stale `expect` is refused with `AT0032`, so a writer can tell a lost race
from a bad request, read the record again and decide afresh. An immutable
record is refused with `AT0032` too. The request's required fields and
every other check above are refused with `AT0022`, except the target's own
state: a target that does not exist or is not approved is refused with an
error naming it. Two writers of one key's link therefore cannot lose each
other's write. Beside the links it writes, `enroll:link` keeps only the
stored links that any write of the record keeps
([Other writes of the record](#other-writes-of-the-record)); otherwise a
key's link goes only when another write of the record stops keeping it, or
when the record is deleted.

The atServer reads an `_apsk` value trimmed of surrounding whitespace, as a
client does. In the list form, it reads each entry that carries a string
`kid`, `alg` and `pub`, takes its `kid` as written, and ignores `use` and
`status`, so a retired key can take a link. A `kid` the value lists twice
takes no link. A bare `_apsk` value is one `rsa2048` key, whose `kid` the
atServer derives: the first 8 bytes of the SHA-256 of the decoded key, as
lowercase hex, which is how clients derive every `kid`. The atServer
compares `kid`s exactly.

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

Every other write of an approved enrollment's `_apsk` record keeps a link
on a key only while the new value lists that key's `kid` once, with the
`alg` and public key the link's payload names, and never on the
enrollment's client authentication signing key. It drops every other link
in the same write, whatever the write sent, and when it drops the last one
from `appMetadata` holding nothing else under the `providerId` the atServer
gives, it drops that `appMetadata` too. These writes are an `enroll:update`
that republishes the record, the publish when an enrollment is approved, an
`update` or `update:meta` of the record, a rotation of the enrollment's
client authentication signing key, and the record's move back when the
enrollment is unrevoked. A publish or republish that changes the value
drops a `dataSignature` over the value it replaces. `enroll:link`, these
writes and a `delete` of the record run one at a time for each atSign, so
each lands wholly before or after another.

An `enroll:update`, an `update` or `update:meta` of the record, or an
`enroll:request` is refused with `AT0022`, naming what failed, when the
`_apsk` it would leave or carries lists a `kid` twice, an entry without a
string `kid`, `alg` and `pub`, or the enrollment's client authentication
signing key beside another key. An `enroll:request` is refused before its
OTP is spent. An `enroll:update` is also refused, naming the key, when the
client authentication signing key it would leave carries a link, and so is
a CRAM `update` of `privatekey:at_pkam_publickey` when `primary`'s `_apsk`
lists the key it installs beside another key or with a link. A write that
would take the record, with the links it keeps, over 500 KiB is refused
with `AT0022`; a record that keeps no links is not held to that bound. An
`enroll:update` that republishes an immutable record is refused with
`AT0032`, as an `update` of one is.

The publish at `enroll:approve`, a rotation of `primary`'s key that the
atServer makes itself, at startup or on a legacy `pkam:`, and the move back
on unrevoke cannot be refused. Each keeps fewer links instead: it drops a
link on the client authentication signing key, keeps none when they would
take the record over 500 KiB, leaves an immutable record as it stands, and
logs at warning what it drops.

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

Since atServer 3.16.3, `:nc` (no-commit) writes no commit-log entry
for the change, removes any entry the key already has, and answers
`data:-1`. From atServer 3.13.0 to 3.16.2 the grammar takes `:nc`, and
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
object, `{"hash":"…","hashingAlgo":"…"}`.

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
atServer 3.16.2, a record whose expiry has passed counts as absent, so
an expired immutable record no longer blocks the write.

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
  8601 UTC timestamp as for `cAt` (§7.1). Since atServer 3.16.3, the
  atServer stamps the DELETE commit entry with it. From atServer 3.13.0
  to 3.16.2 it is accepted and not used.
- `:nc`, no commit. Since atServer 3.16.3, no entry is written, any
  entry the key already has is removed, and the response is
  `data:-1`. From atServer 3.13.0 to 3.16.2 it is accepted, and the
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
configuration. A `:cached` delete is not refused.

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

Since atServer 3.17.1, on a connection not authenticated as the atSign
(a `pol` connection, or one that has not authenticated at all), a
`lookup:` may name only this atServer's atSign as the key's owner. A
lookup naming another owner is refused with `AT0009`, and the connection
is closed. Before 3.17.1, a lookup naming another owner was answered as
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

- `:cl`, since atServer 3.16.3, list commit-log entries instead of
  keys (see Response below). It needs a connection authenticated as
  the atSign, and naming another atSign with it is refused. From
  atServer 3.13.0 to 3.16.2 `:cl` is accepted, and the scan answers as
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
| `messageType:key` | Notification refers to an atKey change. `text` is retired since atServer 3.17.1 ([Appendix B.3](#b3-notify-messagetypetext)). |
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

### 11.2 `notify:all`

Emit one notification to multiple recipients in one round-trip. The
recipients are a comma-separated list (no `@` prefix) where the
single `forAtSign` segment normally goes.

#### Syntax

```text
notify:all:[<update|delete>:][messageType:<key|text>:][ttl:<ms>:][ttb:<ms>:][ttr:<s>:][ccd:<bool>:]<recipient,recipient,…>:<atKey>[@<atSign>][:<value>]
```

The grammar still parses `messageType:text`; since atServer 3.17.1 the
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
3.17.1, a lookup on this connection naming an owner other than `@bob` is
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
   atServer 3.17.1, it answers a lookup on that connection only for a
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
# the enrollment. Since atServer 3.16.1, the atServer also publishes
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
`update:privatekey:at_pkam_publickey`. Since atServer 3.16.4, that
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
# symmetric key and, since atServer 3.17.1, apkamKeysExpiryInMillis
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
# Since atServer 3.17.1 the answer carries expiresAt, null here
# because neither the request nor the approver's enrollment expires.
# Since atServer 3.16.1 the approval publishes the request's
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
APKAM scopes prohibiting the namespace). Since atServer 3.17.1, `AT0009`
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
- **OTP**, Six-character alphanumeric one-time password. Used to bind
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
| `otp`           | owner  | Get/put OTP for APKAM.                                                | §9.4.2  |
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
tied to an atKey change. Since atServer 3.17.1, text notifications are
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

Binary-framed file transfer between two atSigns. Not used by current
SDKs; the recommended pattern for sharing binary blobs is `update`
with `isBinary:true` + `isEncrypted:true`. The `stream` verb's
implementation is preserved in the atServer but is intentionally not
specified in this document.

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
- **`stream`**, uses binary framing with `stream:ack` / `stream:done`
  control lines interleaved with raw payload bytes. (`stream` is
  legacy, see Appendix B.5.)
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
`:nc` (since atServer 3.16.3), and a key the commit log never records
(a `public:_` key, but not `public:__`, or `privatekey:at_secret`).

`update` and `update:meta` do not error on a missing key either: they
create it. `llookup` of a missing key answers `AT0015`.

### D.14 Negative metadata integers are refused, except `ttr:-1`

The metadata regex permits `(-?)\d+` for `ttl`, `ttb`, `ttr`, but the
atServer refuses a negative `ttl` or `ttb`, and a `ttr` below `-1`,
with `AT0003`. `ttr:-1` ("cache indefinitely") is the only negative it
accepts. For no expiry, omit `ttl` when creating a record, or send
`ttl:0` to clear an expiry; since atServer 3.16.3, a later write that
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
