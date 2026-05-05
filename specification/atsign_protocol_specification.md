# Atsign Protocol Specification

This document specifies the **Atsign Protocol** at the level required to
implement either side of the wire — an atClient or an atServer — in any
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
19. [Appendix A — Verb reference](#appendix-a--verb-reference)
20. [Appendix B — Legacy and deprecated](#appendix-b--legacy-and-deprecated)
21. [Appendix C — Significant near-term projects](#appendix-c--significant-near-term-projects)
22. [Appendix D — Inconsistencies and quirks](#appendix-d--inconsistencies-and-quirks)

---

## 1. Introduction

The Atsign Protocol is a text-based, line-oriented, request/response
protocol over TLS. Three roles participate:

- **atClient** — software acting on behalf of an atSign owner. Talks to
  exactly one atServer at a time (the owner's atServer or a
  remote-owner's atServer for cross-atSign reads/writes).
- **atServer** — the personal server for one atSign. Stores that
  atSign's keys (encrypted blobs at rest), serves them on request,
  delivers notifications, and connects out to other atServers when its
  owner's atClient asks for cross-atSign data.
- **atDirectory** — a lookup service that maps an atSign to the
  `host:port` of its atServer. Conceptually similar to DNS.

The protocol is built around a small set of **verbs** — single-line
commands a client sends to a server. Each verb has a regex-defined
syntax. Servers respond with a single line of `data:…` or `error:…`,
followed by a prompt that frames the next request. Two verbs (`monitor`
and the legacy `stream`) keep the connection open for streamed
responses; everything else is single-shot.

End-to-end encryption is **entirely an atClient concern**. atServers
store opaque ciphertext and opaque metadata fields, and never see
plaintext values. Server-side filtering on values is therefore
architecturally impossible — see [§14](#14-end-to-end-encryption).

### For implementers — read these first

Two appendices are load-bearing for anyone implementing this
specification:

- **[Appendix C — Significant near-term projects](#appendix-c--significant-near-term-projects)**
  enumerates active workstreams that will change parts of this
  specification within the next few releases (post-quantum
  cryptography, fast-sync / "fsync", new atKeys structure, pluggable
  encryption, canonical conformance test suite, etc.). Read this
  before committing to a long-lived implementation choice.
- **[Appendix D — Inconsistencies and quirks](#appendix-d--inconsistencies-and-quirks)**
  enumerates the places where the wire reality is surprising — error
  separators that aren't uniform, response shapes that differ
  per-verb, semantics that flip on auth state, and similar gotchas.
  Read this if your implementation is failing in ways that the
  per-verb sections don't seem to predict.

### Spelling and capitalisation

The protocol's name is **Atsign Protocol** (capital A, capital P,
single-spaced). The domain terms are:

- `atSign` — an identity like `@alice`
- `atServer` — the personal server for an atSign
- `atDirectory` — the directory service
- `atKey` — a key in an atServer's keystore
- `atClient` — software talking to atServers

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
3. **Fully self-hosted (split-horizon).** An organisation runs its own
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

- **Transport:** TCP.
- **TLS:** **One-way TLS** — the atDirectory presents a server
  certificate; the client does not present one.
- **Default port:** `64`.
- **Default host:** `root.atsign.org` (configurable).

### 3.2 atServer

- **Transport:** TCP.
- **TLS:** **One-way TLS by default.** Some deployments require client
  certificates (mTLS) for atServer-to-atServer connections — the
  outbound connection factory chooses based on configuration. mTLS is
  not used between atClients and atServers in the default
  configuration.
- **Port:** Per-atSign. Discovered via the atDirectory. The atDirectory
  response is the canonical source for the host and port to connect
  to.

### 3.3 Connection lifecycle

1. Client opens TCP connection.
2. TLS handshake; server certificate is validated against the trusted
   roots (and optionally a pinned `cacert.pem`).
3. **No pre-banner.** The server does not send a greeting line; it
   waits for the client's first verb.
4. Client sends verb, terminated by `\n`.
5. Server responds with `data:…\n@…@` or `error:…\n@…@`. The trailing
   `@…@` (or bare `@` before authentication) is the **prompt** — see
   [§4](#4-framing).
6. Steps 4–5 repeat. Either side may close the connection at any time;
   the client may signal a graceful close with `@exit\n` (atDirectory
   only) or by simply closing the socket.

### 3.4 Idle and timeout behaviour

- atClient default outbound idle timeout: **600 000 ms** (10 minutes).
  Source: `at_lookup/lib/src/connection/outbound_connection_impl.dart`.
- atClient default per-response wait: **90 000 ms**, with a
  **10 000 ms** transient-wait between data packets. Source:
  `at_lookup/lib/src/connection/outbound_message_listener.dart`.
- atServer default inbound and outbound idle limits are configurable
  per deployment (see `inbound_idle_time_millis`,
  `outbound_idle_time_millis`).

When the server-side idle timeout fires, the server closes the
connection without warning. Long-lived `monitor` connections must be
within the configured idle limit, or the server side will need to
disable idle-close for that connection class.

---

## 4. Framing

### 4.1 Line terminator

All client-to-server and server-to-server commands end with a single
**LF** (`\n`, ASCII 10). CR (`\r`) is not part of the protocol; some
older atDirectory implementations emit `\r\n@`, and clients tolerate
both.

### 4.2 Response delimiter (the "prompt")

A server response is followed by a **prompt** that frames the next
client request. The prompt is one of:

| Connection state                          | Prompt           |
| ----------------------------------------- | ---------------- |
| Unauthenticated                           | `@`              |
| Authenticated as the server's own atSign  | `@<atSign>@`     |
| `pol`-authenticated as another atSign     | `<fromAtSign>@`  |

The prompt is appended to the response line preceded by `\n`. Clients
detect "response complete" by scanning for the byte sequence `\n@`.
Source: `at_lookup/lib/src/connection/outbound_message_listener.dart`
treats `\n` followed by `@` as the frame boundary.

```
data:42\n@alice@
^^^^^^^^^^^^^^^^^
| response data | prompt
```

Note: the prompt is **part of the framing**, not the response payload.
A client implementation that includes `\n@…@` in its captured response
is parsing incorrectly.

### 4.3 Charset

UTF-8. atKeys, values, and metadata are all UTF-8 strings on the wire.

### 4.4 Newline escaping in values

Because `\n` is the framing terminator, an atServer rewrites embedded
newlines in **public** data values: `\n` becomes the literal
six-character sequence `~NL~` on the wire. Clients writing values that
contain newlines apply the same escape; clients reading public values
reverse it. The escape is not applied to encrypted (binary)
ciphertext — that is base64-encoded and so contains no `\n` to begin
with.

### 4.5 Binary values

Binary values cross the wire base64-encoded. The metadata flag
`isBinary:true` declares that the value, once decoded, is binary.
`isEncrypted:true` declares it is ciphertext. The two are independent
and both can be true. See [§7](#7-the-metadata-fragment).

### 4.6 Maximum value size

Bounded by the atServer's `bufferLimit` configuration parameter.
Implementations should expose the limit via the `stats` verb. Clients
that exceed the limit receive `error:AT0005-Buffer limit exceeded` and
the connection is closed.

### 4.7 Pipelining

The protocol is request-response with a single in-flight verb per
connection. A client must not send a second verb before reading the
first verb's complete response (terminated by the prompt). The
exception is `monitor`, which streams notifications continuously and
optionally accepts request-response interleaving when `:multiplexed:`
is set — see [§11.7](#117-monitor).

---

## 5. The atSign identity model

An **atSign** is a unique identifier of the form `@<name>` where
`<name>` matches `[^@:\s]+`. Comparison is case-preserving but
case-insensitive on the wire — `@Alice` and `@alice` resolve to the
same identity (atServers normalise to lowercase before keystore
lookup).

The maximum atSign length is **55 characters** including the leading
`@`. Anything longer is invalid.

### 5.1 Lifecycle phases

The full lifecycle of an atSign from registration to active use breaks
into three phases. The `at_auth` package documents this in detail; the
phases are summarised here because each produces credentials that
appear on the wire.

1. **Register.** The atSign is created on the atDirectory's registrar.
   Output: a one-time **CRAM secret** delivered to the registered email
   address. No cryptographic keys exist yet.
2. **Onboard.** The atClient CRAM-authenticates exactly once, generates
   the atSign's master keypairs (PKAM signing, encryption,
   self-encryption), publishes the public halves to the atServer, and
   stores the private halves locally (`.atKeys` file or device
   keychain). After onboarding, the CRAM secret is no longer accepted.
3. **Authenticate (per app).** Subsequent apps authenticate via
   **APKAM enrollment** — they request a scoped key set bound to a
   namespace permission map (e.g. `{'todos': 'rw'}`); the master-keys
   holder approves; the atServer issues new scoped credentials.
   APKAM-issued keys are revocable.

CRAM is bootstrap-only. After Phase 2, all client authentication is
PKAM (with or without APKAM scoping). See [§9](#9-authentication).

---

## 6. The atKey model

A key in the atServer's keystore is an **atKey** — a structured string
whose shape encodes its visibility and ownership. There are five key
shapes plus two augmentations.

### 6.1 The five shapes

| Shape       | Wire format                              | Visibility                                                  |
| ----------- | ---------------------------------------- | ----------------------------------------------------------- |
| Public      | `public:<key>[.<namespace>]@<owner>`     | Any atSign (no auth needed via `plookup`)                   |
| Self        | `<key>[.<namespace>]@<owner>`            | Owner only                                                  |
| Shared      | `@<recipient>:<key>[.<namespace>]@<owner>` | Owner and `<recipient>` only                              |
| Local       | `local:<key>[.<namespace>]@<owner>`      | Owner only; **never synced** to a remote atServer           |
| Private     | `privatekey:<key>[.<namespace>]@<owner>` | Owner only; not enumerated by `scan` (system keys)         |

### 6.2 Augmentations

- **Hidden** — if the `<key>` part starts with `_`, the key is not
  returned by `scan` unless the caller passes `:showhidden:true`.
  Public, self, and shared keys may all be hidden.
- **Cached** — a copy of a remote-owned shared or public key, stored on
  the recipient's atServer for offline / fast access. Wire format:
  `cached:public:<key>@<owner>` or `cached:@<recipient>:<key>@<owner>`.
  The recipient's atServer refreshes the cache per the original key's
  `ttr` (time-to-refresh) and deletes it on owner-side delete if `ccd`
  is set.

### 6.3 Namespace

A trailing `.<namespace>` segment scopes the key to an application or
domain (e.g. `phone.wavi`, `email.myapp`). APKAM enrollments grant
permissions per namespace, so the namespace is part of the
authorisation surface, not a free-form annotation.

The namespace can be omitted when the atKey represents an
infrastructural item (atSign-wide encryption keys, e.g.
`public:publickey@alice`).

### 6.4 Key length

The maximum on-wire length of an atKey is **255 characters**
inclusive of all segments and separators. Compute against this hard
cap, not a typical size — atSigns alone may consume up to 55
characters of the budget.

### 6.5 Reserved keys

Every atServer carries a set of system keys created during onboarding.
These are required for the protocol to function and have stable names:

| Reserved key                        | Purpose                                                                 |
| ----------------------------------- | ----------------------------------------------------------------------- |
| `public:publickey@<atSign>`         | Encryption public key. Used by other atSigns to encrypt to this owner.  |
| `public:signing_publickey@<atSign>` | PKAM/pol signing public key. Used to verify pol challenges.             |
| `privatekey:at_pkam_publickey`      | PKAM authentication public key (single-key model; legacy).              |
| `privatekey:at_pkam_privatekey`     | PKAM authentication private key (in the on-disk `.atKeys` file).        |
| `privatekey:privatekey`             | Encryption private key (`.atKeys`).                                     |
| `privatekey:self_encryption_key`    | Self-encryption symmetric key (`.atKeys`).                              |
| `privatekey:at_secret`              | CRAM secret. Rotated to the keystore at onboarding; not used after.     |
| `<atSign>:shared_key@<atSign>`      | Symmetric key wrapping shared-with values. Not actually used; reserved. |
| `private:blocklist@<atSign>`        | List of atSigns blocked by `config:block:add`.                          |

APKAM-issued keys live under the `__pkams` and `__manage` reserved
namespaces.

### 6.6 atKey parsing examples

| Wire form                                  | Shape  | Hidden? | Cached? |
| ------------------------------------------ | ------ | ------- | ------- |
| `public:phone.wavi@alice`                  | Public | No      | No      |
| `public:_diagnostics@alice`                | Public | Yes     | No      |
| `phone.wavi@alice`                         | Self   | No      | No      |
| `@bob:phone.wavi@alice`                    | Shared | No      | No      |
| `@bob:_handshake.wavi@alice`               | Shared | Yes     | No      |
| `cached:public:publickey@alice`            | Public | No      | Yes     |
| `cached:@bob:phone.wavi@alice`             | Shared | No      | Yes     |
| `local:cache.myapp@alice`                  | Local  | No      | No      |
| `privatekey:at_pkam_publickey`             | Private | —      | —       |

---

## 7. The metadata fragment

A **metadata fragment** is a sequence of `:tag:value` segments embedded
in the `update`, `update:meta`, and `notify` verbs. Every metadata
field a key can carry has a corresponding wire tag. Unrecognised tags
must be rejected by an atServer (servers tighten the surface; clients
should not send tags they don't understand).

### 7.1 Catalogue

Source of truth: `at_commons/lib/src/verb/syntax.dart`'s
`metadataFragment`.

| Wire tag           | Type        | Description                                                                                              |
| ------------------ | ----------- | -------------------------------------------------------------------------------------------------------- |
| `ttl`              | int (ms)    | Time-to-live. Key auto-deletes `ttl` ms after creation. `0` or omitted = never expires.                 |
| `ttb`              | int (ms)    | Time-to-birth. Key is invisible to lookups for `ttb` ms after creation.                                  |
| `ttr`              | int (ms)    | Time-to-refresh for cached copies. `-1` = cache forever; positive = re-fetch interval.                   |
| `ccd`              | bool        | Cascade-delete. If `true`, deleting the original key deletes its cached copies.                          |
| `cAt`              | ISO 8601    | `createdAt` — UTC timestamp of creation. Regex: `\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z` (fractional seconds optional). |
| `uAt`              | ISO 8601    | `updatedAt` — UTC timestamp of most recent update.                                                       |
| `eAt`              | ISO 8601    | `expiresAt` — derived from `cAt + ttl`. Normally server-emitted; clients can also set explicitly (e.g. on sync replay). |
| `aAt`              | ISO 8601    | `availableAt` — derived from `cAt + ttb`. Same write semantics as `eAt`.                                  |
| `dataSignature`    | string      | Signature over a public value, signed by the owner's signing private key. Verifies authenticity.        |
| `sharedKeyStatus`  | enum        | Lifecycle status of a shared key: `localUpdated`, `remoteUpdated`, `sharedWithNotified`, etc.            |
| `isBinary`         | bool        | `true` if the value is binary (base64-encoded on the wire).                                             |
| `isEncrypted`      | bool        | `true` if the value is ciphertext.                                                                       |
| `sharedKeyEnc`     | string      | The shared symmetric key, RSA-encrypted to the recipient's encryption public key. Inline in metadata.   |
| `pubKeyHash`       | string      | Hash of the recipient public key that encrypted `sharedKeyEnc`. Lets the recipient detect key rotation. |
| `pubKeyCS`         | string      | **Deprecated.** Predecessor to `pubKeyHash`. New code must emit `pubKeyHash` + `hashingAlgo`.            |
| `hashingAlgo`      | enum        | Algorithm for `pubKeyHash`: `sha256` or `sha512`.                                                       |
| `encoding`         | string      | Encoding of the value if not raw UTF-8 (e.g. `base64`).                                                 |
| `encKeyName`       | string      | Name of the symmetric key used to encrypt the value (resolves to a key name in the owner's keystore).   |
| `encAlgo`          | string      | Symmetric algorithm used to encrypt the value (e.g. `AES/SIC/PKCS7Padding`).                            |
| `ivNonce`          | string      | Base64 IV / nonce used in symmetric encryption of the value.                                            |
| `skeEncKeyName`    | string      | Name of the public key that wrapped `sharedKeyEnc`.                                                      |
| `skeEncAlgo`       | string      | Algorithm used to wrap `sharedKeyEnc` (default `RSA`).                                                  |
| `immutable`        | bool        | If `true`, the key cannot be updated; deletion requires `:force:`.                                      |

Negative integer values for `ttl`/`ttb` are accepted by the regex (the
syntax allows `(-?)\d+`) but server-side semantics are documented at
the constants level — typically only `ttr:-1` ("cache forever") is a
useful negative.

### 7.2 Tag ordering

Metadata tags appear in a defined order in the regex. Implementations
producing wire commands SHOULD emit tags in regex-declared order:
`ttl, ttb, ttr, ccd, cAt, uAt, eAt, aAt, dataSignature,
sharedKeyStatus, isBinary, isEncrypted, sharedKeyEnc, pubKeyCS,
pubKeyHash, hashingAlgo, encoding, encKeyName, encAlgo, ivNonce,
skeEncKeyName, skeEncAlgo, immutable`. Servers parse via the canonical
regex which enforces this order; deviating produces a syntax error.

---

## 8. The atDirectory protocol

The atDirectory speaks a tiny subset of the protocol: it accepts an
atSign and returns the address of that atSign's atServer.

### 8.1 Connect

Open a TLS connection to the atDirectory address (default
`root.atsign.org:64`). The atDirectory sends a single `@` byte as its
prompt.

### 8.2 Lookup

Send the atSign followed by `\n`. Either form is accepted:

```
@alice\n
alice\n
```

### 8.3 Response

Two possible replies:

- **Found:** `<host>:<port>\n@` — `host` is a hostname or IP, `port` is
  the atServer's TLS port for that atSign.
- **Not found:** `null\n@`

Some atDirectory implementations emit `\r\n@` instead of `\n@`;
implementations should accept both.

### 8.4 Disconnect

The client signals a graceful close with `@exit\n`. After sending,
flush and close the socket. No response is expected.

### 8.5 Worked example

```
C: <TLS handshake>
S: @
C: @alice\n
S: alice.atsign.com:6589\n@
C: @exit\n
C: <socket close>
```

The `@exit` verb is the only verb the atDirectory supports beyond
lookups; any other input is treated as an atSign to look up.

---

## 9. Authentication

The atServer recognises three authentication mechanisms, all built on
the same `from`-then-prove choreography. Modern atClients use **APKAM**
exclusively, with **CRAM** appearing only during one-time onboarding.

### 9.1 The `from` verb

`from` is the first verb on every atServer connection. It tells the
server which atSign is connecting and, for non-self connections, who
the server should expect to authenticate via `pol`.

**Syntax**

```
from:<atSign>[:clientConfig:<clientConfig-json>]
```

Source: `at_commons/lib/src/verb/syntax.dart`:
```
^from:(?<atSign>@?[^:@\s]+)(:clientConfig:(?<clientConfig>\{.+\}))?$
```

The `clientConfig` JSON is optional and free-form. The atServer reads
the following recognised fields and stores them on the connection
metadata:

| Field        | Purpose                                                    |
| ------------ | ---------------------------------------------------------- |
| `version`    | Client SDK version string                                  |
| `clientId`   | Unique client / device identifier                          |
| `appName`    | Application name                                           |
| `appVersion` | Application version                                        |
| `platform`   | OS or platform tag (e.g. `iOS`, `Android`, `linux`)        |

Unrecognised fields are ignored.

**Response** — the server generates a UUIDv4 challenge and a session
ID and stores the challenge under
`<keyPrefix><sessionId><fromAtSign>` (with TTL 60 s), where
`keyPrefix` is `private:` if the connecting atSign matches the
server's own atSign (self-connect) and `public:` otherwise (this
matters for `pol`, which retrieves the challenge via `plookup`).

The response payload is:

```
data:<sessionId><fromAtSign>:<proof>      # if self-connect
data:proof:<sessionId><fromAtSign>:<proof> # if cross-atSign connect
```

— each followed by the unauthenticated prompt `\n@`.

Source: `at_secondary_server/lib/src/verb/handler/from_verb_handler.dart`
lines 74–103.

**Example** — self-connect by `@alice` to `@alice`'s atServer:

```
C: from:@alice\n
S: data:_4af24c03-d732-48f8-a9a2-570e8fb6a01c@alice:d6cac849-9c29-42b0-b0c5-493db62728b9\n@
```

### 9.2 CRAM (`cram`)

CRAM is the **bootstrap-only** authentication mechanism. After
onboarding, the CRAM secret is no longer the canonical credential and
clients must use PKAM/APKAM. CRAM remains in the protocol because
onboarding from a fresh atServer requires a credential that exists
before any keypair has been generated.

**Syntax**

```
cram:<digest>
```

Source:
```
^cram:(?<digest>.+$)
```

**Digest computation** — the client takes the `from` response, strips
the leading `data:` prefix, and computes:

```
digest = sha512_hex( utf8( <cramSecret> + <strippedFromResponse> ) )
```

For a self-connect, `<strippedFromResponse>` is
`<sessionId><atSign>:<proof>` — the entire body with no further
parsing. Source: `at_lookup/lib/src/at_lookup_impl.dart` lines 540–544.

**Response**

- Success: `data:success\n@<atSign>@`
- Failure: `error:AT0401-Client authentication failed\n@` (connection
  may close)

After success the connection is **authenticated as owner**.

### 9.3 PKAM (`pkam`)

Plain PKAM is the underlying signature-based authentication that APKAM
extends. A client running plain PKAM holds the master signing private
key directly.

**Syntax**

```
pkam:[signingAlgo:<rsa2048|ecc_secp256r1>:][hashingAlgo:<sha256|sha512>:][enrollmentId:<id>:]<signature>
```

Source:
```
^pkam:(signingAlgo:(?<signingAlgo>ecc_secp256r1|rsa2048):)?(hashingAlgo:(?<hashingAlgo>sha256|sha512):)?(enrollmentId:(?<enrollmentId>.+):)?(?<signature>.+$)
```

**Signature computation** — the client signs the `from` challenge
(everything the `from` response payload contained, less any leading
`data:`) with the owner's signing private key, base64-encodes the
result, and sends it as `<signature>`.

Defaults: `signingAlgo:rsa2048`, `hashingAlgo:sha256`. The `enrollmentId`
is omitted for plain PKAM; an APKAM-issued credential includes the
enrollment's ID so the atServer can look up the namespace permission
map.

**Response** — same as CRAM: `data:success` on success,
`error:AT0401-…` on failure.

### 9.4 APKAM (`enroll`, `otp`, `keys`)

APKAM (Application PKAM) is the modern authentication mechanism. It
issues a per-app, per-device keypair scoped to a namespace permission
map, and supports approval, denial, revocation, and expiry by the
atSign owner.

A high-level flow:

1. **Bootstrap atSign** — the new app generates a fresh APKAM keypair
   and a fresh APKAM symmetric key.
2. **Get an OTP** — the user, on a session already authenticated as
   owner, runs `otp:get` and reads the OTP to the new app.
3. **`enroll:request`** — the new app submits the request, including
   its APKAM public key, the OTP, the namespace permission map, and
   the APKAM symmetric key encrypted with the **default encryption
   public key** (so only an owner-keys holder can decrypt it).
4. **`enroll:approve`** — the owner-keys holder fetches the request,
   decrypts the APKAM symmetric key, then sends back the
   default encryption private key and self-encryption key, each
   encrypted with the now-shared APKAM symmetric key (with IVs).
5. **PKAM-with-enrollmentId** — the new app authenticates as usual via
   `from` + `pkam`, passing `enrollmentId:<id>` so the atServer scopes
   the connection to the granted namespaces.

#### 9.4.1 The `enroll` verb

**Syntax**

```
enroll:<operation>[:force][:<enrollParams-json>]
```

Source:
```
^enroll:(?<operation>(?:(request|approve|deny|revoke|list|fetch|unrevoke|delete)))(:(?<force>force))?(?::)?((?<enrollParams>.+)|(<=list:)<enrollParams>.?)?$
```

`<enrollParams>` is the JSON serialisation of the `EnrollParams` shape
(`at_commons/lib/src/verb/enroll_params.dart`):

| Field                                  | Used by         | Description                                                                                  |
| -------------------------------------- | --------------- | -------------------------------------------------------------------------------------------- |
| `enrollmentId`                         | approve/deny/revoke/fetch/delete/unrevoke | UUID of the enrollment.                                                  |
| `appName`                              | request         | Application name, e.g. `"todos"`.                                                           |
| `deviceName`                           | request         | Unique device identifier.                                                                    |
| `namespaces`                           | request         | Map of `namespace → permission` (`r`, `w`, `rw`, `rwx`).                                    |
| `otp`                                  | request         | One-time password from `otp:get`.                                                            |
| `apkamPublicKey`                       | request         | New device's APKAM public key (PEM or base64).                                              |
| `encryptedAPKAMSymmetricKey`           | request         | New device's APKAM symmetric key, RSA-encrypted to the default encryption public key.       |
| `encryptedDefaultEncryptionPrivateKey` | approve         | Owner's encryption private key, AES-encrypted with the APKAM symmetric key.                 |
| `encPrivateKeyIV`                      | approve         | IV (base64) for the line above.                                                              |
| `encryptedDefaultSelfEncryptionKey`    | approve         | Owner's self-encryption key, AES-encrypted with the APKAM symmetric key.                    |
| `selfEncKeyIV`                         | approve         | IV (base64) for the line above.                                                              |
| `enrollmentStatusFilter`               | list            | Optional list of statuses to filter on: `pending`, `approved`, `denied`, `revoked`, `expired`. |
| `apkamKeysExpiryDuration`              | request         | ISO-8601 duration: lifetime of the APKAM credentials before forced re-enrollment.            |

**Operations and responses**

| Operation   | Response payload                                                       |
| ----------- | ---------------------------------------------------------------------- |
| `request`   | `data:{"enrollmentId":"<uuid>","status":"pending"}`                    |
| `approve`   | `data:{"enrollmentId":"<uuid>","status":"approved"}`                   |
| `deny`      | `data:{"enrollmentId":"<uuid>","status":"denied"}`                     |
| `revoke`    | `data:{"enrollmentId":"<uuid>","status":"revoked"}` (`:force:` to revoke own enrollment) |
| `unrevoke`  | `data:{"enrollmentId":"<uuid>","status":"approved"}`                   |
| `delete`    | `data:{"enrollmentId":"<uuid>","status":"deleted"}`                    |
| `fetch`     | `data:{ <full enrollment record JSON> }`                               |
| `list`      | `data:{"<enrollKey>":{<enrollment record JSON>}, …}`                   |

#### 9.4.2 The `otp` verb

```
otp:get[:ttl:<ms>]
otp:put:<otp>[:ttl:<ms>]
```

Source:
```
^otp:(?<operation>get|put)(:(?<otp>(?<=put:)\w{6,}))?(:(?:ttl:(?<ttl>\d+)))?$
```

- `otp:get` — owner-authenticated. Returns a fresh 6-character
  alphanumeric OTP. Used as the `otp` field of `enroll:request`.
- `otp:put:<otp>` — owner-authenticated. Stores a semi-permanent OTP
  for use in headless / CLI enrollment flows.
- `:ttl:<ms>` — sets the OTP validity window.

**Response**: `data:<otp>` (for `get`) or `data:ok` (for `put`).

#### 9.4.3 The `keys` verb

> **Status: being deprecated.** New implementations should not produce
> `keys` verbs. The current APKAM enrollment flow still emits them
> under the covers, but the verb is on the path to removal — it
> overlaps with `update`/`llookup`/`delete` against the
> `__pkams` / `__manage` namespaces and adds parsing surface without
> adding capability. Track the deprecation work alongside the
> [new AtKeys structure](#c3-new-atkeys-structure) and
> [pluggable encryption](#c1-post-quantum-cryptography-and-crypto-agility)
> projects in Appendix C — both intersect with this verb's role.

```
keys:<put|get|delete>[:public|private|self][:namespace:<ns>][:appName:<n>][:deviceName:<n>][:keyType:<t>][:encryptionKeyName:<n>][:keyName:<n>] [<value>]
```

Source: see `at_commons/lib/src/verb/syntax.dart`.

`keys` is the storage / retrieval verb for APKAM-issued keys. The
APKAM enrollment flow uses it under the covers to publish the new
device's APKAM public key and to retrieve the encrypted bootstrap keys
on the receiving side. App code rarely calls it directly.

**Response**: `data:-1` on `put` (commit ID; APKAM keys are
non-committed) and `data:<JSON record>` on `get`.

---

## 10. CRUD verbs

All CRUD verbs require an authenticated connection (owner or APKAM-
authenticated). The unauthenticated case for `lookup` is handled by
the dedicated `plookup` verb.

### 10.1 `update`

Insert or overwrite a value, optionally with metadata.

**Syntax (positional form)**

```
update[:nc]<metadata>[:public|@<forAtSign>]:<atKey>[@<atSign>] <value>
```

**Syntax (JSON form)**

```
update[:nc]:json:<json>
```

Source:
```
^update(:nc(?<noCommit>))?(:json:(?<json>.+)|<metadataFragment>(:(public|@(?<forAtSign>...)))?:(?<atKey>...)(@(?<atSign>...))? (?<value>.+))$
```

`:nc` (no-commit) suppresses the commit-log entry, used for local
keys that should not be synced.

**Response** — `data:<commitId>` where `commitId` is the integer
commit-log sequence number assigned to the operation. Self-connected
clients use this to detect that their local cache is at least as
fresh as the server.

```
C: update:@bob:phone.wavi@alice +1 555 0100\n
S: data:42\n@alice@
```

Setting metadata at update time:

```
C: update:ttr:60000:ccd:true:isEncrypted:true:@bob:secret.myapp@alice <ciphertext>\n
S: data:43\n@alice@
```

JSON form (atomic put with full metadata):

```
C: update:json:{"atKey":{"key":"phone","sharedWith":"@bob","sharedBy":"@alice","namespace":"wavi"},"value":"+1 555 0100","metadata":{"ttl":60000}}\n
S: data:44\n@alice@
```

### 10.2 `update:meta`

Update only the metadata of an existing key. Same metadata fragment as
`update`. Useful for changing TTL or marking a key encrypted after
the fact.

```
C: update:meta:@bob:phone.wavi@alice:ttl:600000:isEncrypted:true\n
S: data:45\n@alice@
```

### 10.3 `delete`

Remove an atKey.

**Syntax**

```
delete[:dAt:<timestamp>][:nc][:force][:priority:<low|medium|high>][:cached][:public|@<forAtSign>]:<atKey>[@<atSign>]
```

Source:
```
^delete(:dAt:...)?(:nc)?(:force)?(:priority:...)?(:cached)?(:public|@<forAtSign>)?:<atKey>(@<atSign>)?$
```

- `:dAt:<timestamp>` — assert deletion time (used by sync).
- `:nc` — no commit.
- `:force` — required to delete an `immutable:true` key.
- `:cached` — delete a cached copy on this server (does not affect the
  origin).

**Response** — `data:<commitId>` (yes, even when the key didn't exist
— `delete` is idempotent and always commits).

```
C: delete:@bob:phone.wavi@alice\n
S: data:46\n@alice@
```

If `autoNotify` is enabled and the key was a shared key with a
recipient on a different atServer, the server emits a `notify:delete`
to the recipient — see [§11](#11-notification-verbs).

### 10.4 `lookup`

Read a value from another atSign's atServer (cross-atSign read,
authenticated). Internally proxied via the requestor's local atServer
— see [§15](#15-the-inter-atserver-protocol).

**Syntax**

```
lookup[:bypassCache:<true|false>][:meta|all]:<atKey>@<atSign>
```

Source:
```
^lookup:(bypassCache:(?<bypassCache>true|false):)?((?<operation>meta|all):)?(?<atKey>(?:[^:]).+)@(?<atSign>[^:@\s]+)$
```

- Default operation: returns the value only.
- `meta:` — return metadata only.
- `all:` — return both value and metadata.
- `bypassCache:true` — force a fetch from the remote rather than
  returning a cached copy.

**Response shapes**

Default:
```
data:<value>
```

`meta:`:
```
data:{"createdBy":"@bob","updatedBy":"@bob","createdAt":"…","updatedAt":"…","ttl":null,"ttb":null,"ttr":10000,"ccd":false,"isBinary":false,"isEncrypted":true, …}
```

`all:`:
```
data:{"key":"@alice:country.wavi@bob","data":"USA","metaData":{ … }}
```

If the remote atServer is unreachable: `error:AT0007-atServer not found.`

### 10.5 `plookup`

Public lookup — read a public key from any atSign without
authentication. The server may answer from its own cache (per the
key's `ttr`) unless `:bypassCache:true:` is set.

**Syntax**

```
plookup[:bypassCache:<true|false>][:meta|all]:<atKey>@<atSign>
```

Same response shape as `lookup`.

### 10.6 `llookup`

Local lookup — read a key from this atServer's own keystore. Returns
the stored value verbatim (no resolution, no remote fetch).

**Syntax**

```
llookup[:meta|all][:cached][:public|@<forAtSign>]:<atKey>@<atSign>
```

Source:
```
^llookup(:(?<operation>meta|all))?(:cached)?(:(public|@<forAtSign>))?:<atKey>@<atSign>$
```

- `:cached:` — look up a cached copy on this atServer.

Response is identical in shape to `lookup`.

### 10.7 `scan`

Enumerate keys.

**Syntax**

```
scan[:cl][:showhidden:<true|false>][:<forAtSign>][:page:<n>][ <regex>]
```

Source:
```
^scan$|scan(:cl)?(:showhidden:...)?(:<forAtSign>)?(:page:...)?( <regex>)?$
```

- `:cl` — scan the commit log instead of the keystore.
- `:showhidden:true` — include keys whose `<key>` starts with `_`.
- `:<forAtSign>` — only return keys shared with that atSign.
- `:page:<n>` — pagination index (server-defined page size).
- `<regex>` (space-separated) — filter results by regex.

**Response**

```
data:["public:phone.wavi@alice","@bob:email.wavi@alice", …]
```

A JSON array of strings, on a single line. Empty result is `data:[]`.

The `forAtSign` and `regex` filters operate on key **structure**, not
value contents — value-level filtering is impossible because the
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

**Syntax**

```
notify[:id:<id>][:<update|delete>][:messageType:key][:priority:<low|medium|high>][:strategy:<all|latest>][:latestN:<n>][:notifier:<n>][:ttln:<ms>]<metadata>:[public|@<forAtSign>]:<atKey>[@<atSign>][:<value>]
```

Source: see `at_commons/lib/src/verb/syntax.dart` `notify`.

| Tag             | Description                                                                                           |
| --------------- | ----------------------------------------------------------------------------------------------------- |
| `id`            | Caller-supplied notification ID. Server generates one if omitted.                                     |
| `update|delete` | Operation. Defaults to `update`.                                                                      |
| `messageType:key` | Notification refers to an atKey change. (`text` exists; **deprecated** — see Appendix B.)            |
| `priority`      | Delivery priority hint.                                                                               |
| `strategy:all`  | Deliver every notification (default).                                                                 |
| `strategy:latest` | Coalesce: deliver only the most recent `<latestN>` for the same atKey if recipient was offline.    |
| `latestN`       | Coalesce window size. Used with `strategy:latest`.                                                    |
| `notifier`      | Identifier of the notifying subsystem. Defaults to `SYSTEM`.                                          |
| `ttln`          | Notification time-to-live in ms. After expiry the server gives up delivering and marks `expired`.    |

**Response** — `data:<notificationId>` on success.

```
C: notify:update:ttr:-1:isEncrypted:true:@bob:phone.wavi@alice <ciphertext>\n
S: data:7c6c8d7d-7e0e-4ab4-9c7d-4b07e1e84a52\n@alice@
```

### 11.2 `notify:all`

Emit one notification to multiple recipients in one round-trip. The
recipients are a comma-separated list (no `@` prefix) where the
single `forAtSign` segment normally goes.

**Syntax**

```
notify:all:[<update|delete>:][messageType:<key|text>:][ttl:<ms>:][ttb:<ms>:][ttr:<ms>:][ccd:<bool>:]<recipient,recipient,…>:<atKey>[@<atSign>][:<value>]
```

**Response** — a JSON map of `recipient → notificationId`:

```
data:{"@bob":"…uuid…","@colin":"…uuid…"}
```

### 11.3 `notify:list`

List notifications received by the current atSign.

**Syntax**

```
notify:list[:<fromDate>][:<toDate>][:<regex>]
```

Dates are `YYYY-MM-DD`. Source:
```
^notify:list(:(?<fromDate>\d{4}-[01]?\d?-[0123]?\d?))?(:(?<toDate>...))?(:(?<regex>[^:]+))?
```

**Response** — JSON array of notification records:

```
data:[{"id":"…","from":"@bob","to":"@alice","key":"@alice:phone.wavi@bob","value":null,"operation":"update","epochMillis":1603714720965}, …]
```

If the connection is `pol`-authenticated, returns notifications **sent
to** that atSign instead.

### 11.4 `notify:status`

Query the delivery status of a notification by ID.

**Syntax**

```
notify:status:<notificationId>
```

**Response** — `data:<status>` where status is one of:

| Status        | Meaning                                                |
| ------------- | ------------------------------------------------------ |
| `queued`      | Not yet sent.                                          |
| `delivered`   | Successfully delivered to the recipient's atServer.    |
| `undelivered` | Tried and failed; will retry per server policy.        |
| `errored`     | Delivery errored permanently.                          |
| `expired`     | TTL elapsed before delivery succeeded.                 |

### 11.5 `notify:fetch`

Fetch a full notification record by ID.

**Syntax**

```
notify:fetch:<notificationId>
```

**Response** — `data:<JSON notification record>`. If the notification
was expired or never existed, returns
`data:{"id":"<id>","notificationStatus":"expired"}`.

### 11.6 `notify:remove`

Remove a notification from the local notification log. Note: this is
log housekeeping; it does **not** send a `notify:delete` to the
recipient.

**Syntax**

```
notify:remove:<notificationId>
```

**Response** — `data:success`.

### 11.7 `monitor`

Open a long-lived stream of received notifications.

**Syntax**

```
monitor[:strict][:selfNotifications][:multiplexed][:<epochMillis>][ <regex>]
```

Source:
```
^monitor(:strict)?(:selfNotifications)?(:multiplexed)?(:<epochMillis>)?( <regex>)?$
```

| Modifier            | Effect                                                                                              |
| ------------------- | --------------------------------------------------------------------------------------------------- |
| `strict`            | Emit **only** notifications matching the regex; suppress server-control notifications (e.g. stats). |
| `selfNotifications` | Include notifications the connecting atSign emitted itself.                                         |
| `multiplexed`       | Allow request-response interleaving on the same connection.                                          |
| `<epochMillis>`     | Replay notifications received at or after this timestamp.                                            |
| `<regex>`           | Filter notifications by atKey regex.                                                                 |

**Response** — a stream. Each notification arrives as one line:

```
notification: {"id":"…","from":"@bob","to":"@alice","key":"@alice:phone.wavi@bob",…}
```

Lines are not framed by the standard `\n@…@` prompt. The connection
remains open until either side closes it. Server-control
notifications use the same `notification: …` prefix unless `:strict`
is set.

If `:multiplexed` is set, the server processes a subsequent verb
arriving on the same connection (e.g. `lookup`) when no notification
delivery is mid-flight, and emits the response with the standard
prompt; notifications resume after the response.

---

## 12. The sync verb

`sync:from` walks the commit log of an atServer from a given commit ID
to the current head, returning the intervening operations. Used both
by clients (to keep a local cache fresh) and by atServers (to
synchronise with their cloud counterpart).

### 12.1 `sync:from`

**Syntax**

```
sync:from:<from_commit_seq>[:limit:<n>][:skipDeletesUntil:<n>][:<regex>]
```

Source:
```
^sync:from:(?<from_commit_seq>[0-9]+|-1)(:limit:(?<limit>\d+))?(:skipDeletesUntil:(?<skipDeletesUntil>\d+))?(:(?<regex>.+))?$
```

- `<from_commit_seq>` — last commit ID the caller has seen. `-1`
  requests the full commit log from the start.
- `:limit:<n>` — max entries returned in this round-trip. Caller
  paginates by repeating with the highest commit ID seen.
- `:skipDeletesUntil:<n>` — suppress delete operations whose
  `commitId <= n`. Used to elide tombstones older than a known sync
  high-water mark.
- `:<regex>` — filter entries by atKey regex.

**Response** — JSON array of commit-log entries:

```
data:[{"atKey":"@bob:phone.wavi@alice","operation":"+","opTime":"2026-05-05T10:30:00.000Z","commitId":42,"value":"<ciphertext>","metadata":{"ttr":-1,"ccd":false,"isEncrypted":true}},
      {"atKey":"@bob:shared_key.wavi@alice","operation":"-","opTime":"2026-05-05T10:31:42.000Z","commitId":43}]
```

Operations: `+` for upsert, `-` for delete, `*` for metadata-only
update.

The legacy `sync:<from_commit_seq>` syntax (without `:from:`) is
retained for backward compatibility and is documented in
[Appendix B](#appendix-b--legacy-and-deprecated). New clients must
use `sync:from`.

---

## 13. Server-admin and utility verbs

### 13.1 `config`

Manage server-side block lists and configuration parameters. Owner-
authenticated only.

**Syntax**

```
config:block:add:@<atSign>[ @<atSign> …]
config:block:remove:@<atSign>[ @<atSign> …]
config:block:show
config:set:<key>=<value>
config:reset:<key>
config:print:<key>
```

The block list, once populated, is consulted by `from` — a blocked
atSign receives `error:AT0013-Connection Exception` and the connection
is closed.

**Response** — `data:success` for mutating operations, `data:[…]` for
`show` (a JSON array of blocked atSigns), `data:<value>` for `print`.

### 13.2 `stats`

Return server statistics.

**Syntax**

```
stats[:<id>[,<id>…]][:<regex>]
```

Source:
```
^stats(?<statId>:((?!0)\d+)?(,(\d+))*)?(:(?<regex>(?<=:3:|:15:).+))?$
```

Without IDs, all statistics are returned. Statistics are identified
by integer IDs:

| ID  | Name                        | Value type                    |
| --- | --------------------------- | ----------------------------- |
| 1   | `activeInboundConnections`  | int                           |
| 2   | `activeOutboundConnections` | int                           |
| 3   | `lastCommitId`              | int                           |
| 4   | `secondaryStorageSize`      | int (bytes)                   |
| 5   | `topAtSigns`                | `{<atSign>: <hits>, …}`       |
| 6   | `topKeys`                   | `{<atKey>: <hits>, …}`        |

(Servers may expose additional IDs — IDs 11 and 15 take regex filters
per the syntax; see source for current set.)

**Response**

```
data:[{"id":"1","name":"activeInboundConnections","value":"1"},
      {"id":"3","name":"lastCommitId","value":"42"}, …]
```

### 13.3 `info`

Return server runtime information.

**Syntax**

```
info[:brief|mtls|mtlsbrief]
```

**Response shapes**

`info` (full):
```
data:{"version":"3.0.28","uptimeAsWords":"1 hours 35 minutes 29 seconds","features":[ {…feature record…}, … ]}
```

`info:brief`:
```
data:{"version":"3.0.28","uptimeAsMillis":5855295}
```

`info:mtls`:
```
data:{"mtls_fullchain":"<PEM>"}
```

`info:mtlsbrief`:
```
data:{"mtls_fullchain_last_modified":"2026-05-05T08:00:00.000Z","mtls_privkey_last_modified":"2026-05-05T08:00:00.000Z"}
```

`info` may be called unauthenticated; servers may restrict per
deployment.

### 13.4 `noop`

Sleep for the given number of milliseconds, then respond. Used as a
keep-alive / latency probe.

**Syntax**

```
noop:<delayMillis>
```

`<delayMillis>` ≤ 5000.

**Response** — `data:ok` after the delay. Out-of-range values produce
`error:AT0022-Exception: noop:<durationInMillis> where the duration
maximum is 5000 milliseconds`.

### 13.5 `batch`

Execute multiple verbs in a single round-trip. Each member of the
batch is independently parsed and dispatched; failures are per-entry.

**Syntax**

```
batch:<json-array>
```

Where `<json-array>` is `[{"id":<n>,"command":"<verb>"}, …]` and each
`<verb>` is a single-line verb without the trailing `\n`.

**Response** — array of `{id, response}` pairs in submission order:

```
data:[{"id":1,"response":{"data":"42"}},{"id":2,"response":{"data":"43"}}]
```

---

## 14. End-to-end encryption

End-to-end encryption is **entirely an atClient concern**. atServers
store opaque ciphertext in the `value` field, opaque ciphertext in the
`sharedKeyEnc` metadata field, and opaque metadata about which keys
encrypted which — but they never see plaintext keys, plaintext values,
or have any way to decrypt anything they store. No server-side
behaviour in this specification depends on understanding what the
encrypted material means.

This section describes how the wire-level metadata fields hang together
so an atClient implementer can interoperate with the existing Dart
SDK. It does **not** specify the encryption protocol normatively; that
lives in the [`at_chops`](https://pub.dev/packages/at_chops) package
and is allowed to evolve.

### 14.1 Two layers

Atsign Protocol e2ee uses two layers:

1. **Symmetric layer.** Each atSign holds one symmetric **shared key**
   per recipient. Values shared from `@alice` to `@bob` are encrypted
   with `alice`'s sharedKey-for-bob (AES). The metadata fields
   `encKeyName`, `encAlgo`, `ivNonce`, and `encoding` describe this
   encryption.
2. **Asymmetric layer.** The shared key is itself encrypted with the
   recipient's encryption public key (RSA), serialised into the
   `sharedKeyEnc` metadata field, and pinned to the public key that
   wrapped it via `pubKeyHash` (and `hashingAlgo`) and `skeEncKeyName`
   / `skeEncAlgo`.

Inline shared-key delivery (`sharedKeyEnc` carried in the metadata of
the value itself) is the supported pattern. Alternative delivery via a
separately-stored `<atSign>:shared_key.<namespace>@<owner>` atKey is
accepted for backward compatibility but not recommended.

### 14.2 Public-data signatures

Public values may be signed by the owner's signing private key; the
signature appears in `dataSignature`. Recipients verify against the
owner's `public:signing_publickey@<owner>`. This is the only signature
on a value-side payload — encrypted (shared) values rely on the AES
authenticated-encryption mode in `encAlgo` to detect tampering.

### 14.3 Public-key rotation

If the recipient rotates their encryption keypair, every shared key
encrypted to the old public key becomes unrecoverable. `pubKeyHash`
lets the recipient detect this on read: if the hash doesn't match
their current public key, the recipient asks the sender to re-share.
There is no in-protocol re-key flow; the sender simply re-issues the
update with a fresh `sharedKeyEnc`.

### 14.4 Why server-side filtering is impossible

The atServer holds:

- ciphertext in `value`
- ciphertext in `sharedKeyEnc`
- metadata fields whose meaning it cannot interpret without keys it
  does not have

Any feature requiring the server to reason about plaintext — value-
level filters, server-side aggregations over content, content-based
notifications — is therefore architecturally impossible. This is a
**security property**, not a performance limitation. Filtering by
atKey **structure** (regex on the wire-form name) is supported and is
how `scan`, `notify:list` regexes, and `monitor` filters work.

---

## 15. The inter-atServer protocol

When an atClient asks its atServer for cross-atSign data — `lookup`,
remote `scan`, or sending a `notify` whose recipient is on a different
atServer — the atServer **proxies** the request. It opens a TLS
connection to the target atServer (resolved via the atDirectory),
authenticates via the `pol` handshake, and runs the appropriate verb
on behalf of the requesting client.

This chapter specifies that proxying. The single most important verb
here is `pol`, the proof-of-life handshake between two atServers.

### 15.1 Outbound connection lifecycle

Source: `at_secondary_server/lib/src/connection/outbound/outbound_client.dart`.

1. Local atServer (call it **A**) needs to talk to remote atServer
   **B**. A's `OutboundClientManager` returns an `OutboundClient`
   for the target atSign — pooled per-target so repeat traffic to the
   same B reuses one connection.
2. **Resolve.** A queries its atDirectory for B's host:port.
3. **Connect.** A opens a TLS connection to B. Most A→B connections
   are one-way TLS (B presents a cert). For deployments configured
   with `clientCertificateRequired`, A presents a client cert (mTLS).
4. **Public-key warm-up.** Before any handshake, A runs an
   unauthenticated `lookup:all:publickey<B-atSign>` against B and
   caches the result (cached as
   `cached:public:publickey@<B-atSign>` in A's keystore). This makes
   subsequent encryption-to-B operations cheap and detects key
   rotation early.
5. **Handshake.** If the planned operation requires authentication, A
   runs the `pol` handshake — see [§15.2](#152-the-pol-handshake).
   `lookup` requires it; `plookup` does not.
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
the secret signing key never leaves A; B verifies by fetching A's
public signing key from A and verifying the signature.

**Step-by-step.** Source:
`at_secondary_server/lib/src/verb/handler/pol_verb_handler.dart` and
`outbound_client.dart::_establishHandShake`.

```
A ──TLS──► B  (already connected)

A → B:  from:@A
B → A:  data:proof:<sessionId>@A:<challenge-uuid>\n@

A:  parses cookieParams from response → (sessionId, challenge)
A:  signedChallenge = base64( sign_RSA_SHA256(challenge, A_signing_priv) )
A:  store in own keystore: public:<sessionId>@A = signedChallenge   (TTL ~60s)

A → B:  pol\n

B's pol handler:
  - Verifies A's `from:` already executed on this connection.
  - Opens its own outbound to A (no handshake required — public lookup):
      B → A:  lookup:<sessionId>@A
      A → B:  data:<signedChallenge>
      B → A:  plookup:signing_publickey@A
      A → B:  data:<A's RSA signing public key>
  - Reads its own stored secret: get(public:<sessionId>@A) = challenge
  - Verifies: RSA_SHA256_verify(A_signing_pub, challenge, signedChallenge)
  - On success: marks the inbound connection as polAuthenticated,
                deletes the stored secret, responds:

B → A:  @A@
       (verb result inside B is `pol:@A@`; the PolResponseHandler
        strips the `pol:` prefix, leaving just the prompt-shaped
        confirmation `@A@` on the wire — no separate `data:`
        framing, no trailing `\n@…@`. A's outbound listener
        recognises completion by the `@<currentAtSign>@` shape.)

A:  reads handshake result; if it begins with "@A@", marks the
    outbound connection authenticated.
```

After `pol` succeeds, A's connection to B is authenticated **as @A**.
B treats subsequent verbs on this connection as coming from `@A` — for
example, a `lookup:phone.wavi@A` returns only the keys `@A` is allowed
to read on B's atServer (`@bob:phone.wavi@A`-shaped, where `@bob` is
B's atSign).

**Failure modes:**

| Cause                                       | Error                                          |
| ------------------------------------------- | ---------------------------------------------- |
| `pol` sent without prior `from`             | `error:AT0013-You must execute a 'from:' command before you may run the pol command` |
| Signature verification fails                | `error:AT0025-Pol Authentication Failed`       |
| Cannot connect outbound to verify           | `error:AT0007-atServer not found`              |
| Any other handshake exception               | `error:AT0008-Handshake failure`               |

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
   marked `polAuthenticated as @bob` — the result is whatever @alice
   has shared **with @bob** (typically `@bob:phone.wavi@alice`).
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

### 15.5 Server-to-server `sync:from`

For self-hosted deployments where an atServer pairs with a "cloud"
mirror (or vice versa), `sync:from` runs over the same
pol-authenticated outbound connection. Both ends use the same
commit-log walking protocol described in [§12](#12-the-sync-verb); no
new verbs are introduced.

---

## 16. Worked flows

### 16.1 CRAM bootstrap (Phase 2 onboarding)

The first time an atClient authenticates as a freshly-registered
atSign, it has only the CRAM secret. It must (a) authenticate, (b)
generate keypairs, (c) publish the public halves, (d) write the
private halves to disk.

```
C: <TCP+TLS connect to alice's atServer>
C: from:@alice\n
S: data:_4af24c03-d732-48f8-a9a2-570e8fb6a01c@alice:d6cac849-9c29-42b0-b0c5-493db62728b9\n@

C: cram:<sha512_hex(cramSecret + "_4af24c03-d732-48f8-a9a2-570e8fb6a01c@alice:d6cac849-9c29-42b0-b0c5-493db62728b9")>\n
S: data:success\n@alice@

# Generate RSA-2048 PKAM keypair, RSA-2048 encryption keypair, AES-256
# self-encryption key (all client-side, never on the wire as plaintext).

C: update:privatekey:at_pkam_publickey <PKAM public key>\n
S: data:0\n@alice@

C: update:public:publickey@alice <encryption public key>\n
S: data:1\n@alice@

C: update:public:signing_publickey@alice <signing public key>\n
S: data:2\n@alice@

# Write .atKeys file: PKAM private key + encryption private key +
# self-encryption key, all encrypted-at-rest with the user's password.
```

After bootstrap, the CRAM secret is no longer accepted. The same
client now reconnects with `from` + `pkam` for any subsequent session.

### 16.2 APKAM enrollment end-to-end

Phase 3 — a new app on a new device authenticates as `@alice` without
ever holding the master keys.

```
# === New device: generate APKAM keypair, generate APKAM symmetric key,
#                 RSA-encrypt the APKAM symmetric key to alice's
#                 public:publickey@alice ===

# === Existing master-keys session: get an OTP for the new device. ===
C(master): otp:get\n
S:        data:A1B2C3\n@alice@
# (Owner reads "A1B2C3" to the new device.)

# === New device: submit enrollment request. ===
C(new): from:@alice\n
S:      data:proof:<sessionId>@alice:<chal>\n@
# (No prior PKAM keys; the new device authenticates the enroll:request
# verb as unauthenticated — the OTP is the credential here.)
C(new): enroll:request:{
          "appName":"todos",
          "deviceName":"phone-1",
          "namespaces":{"todos":"rw"},
          "otp":"A1B2C3",
          "apkamPublicKey":"<base64 RSA pub>",
          "encryptedAPKAMSymmetricKey":"<RSA-to-alice's-encryption-pub>"
        }\n
S:      data:{"enrollmentId":"<uuid>","status":"pending"}\n@

# === Existing master-keys session: monitor for enrollment notifications. ===
C(master): monitor\n
S:         notification: {"id":"…","key":"<uuid>.new.enrollments.__manage@alice", …}

# === Existing master-keys session: fetch and approve. ===
C(master): enroll:fetch:{"enrollmentId":"<uuid>"}\n
S:         data:{ <full request including encryptedAPKAMSymmetricKey> }\n@alice@

# Master decrypts encryptedAPKAMSymmetricKey using its
# default encryption private key. Now both sides share the APKAM
# symmetric key.

# Master encrypts its OWN default encryption private key + self-encryption
# key with the APKAM symmetric key (AES, with random IVs).

C(master): enroll:approve:{
             "enrollmentId":"<uuid>",
             "encryptedDefaultEncryptionPrivateKey":"<AES ciphertext>",
             "encPrivateKeyIV":"<base64 IV>",
             "encryptedDefaultSelfEncryptionKey":"<AES ciphertext>",
             "selfEncKeyIV":"<base64 IV>"
           }\n
S:         data:{"enrollmentId":"<uuid>","status":"approved"}\n@alice@

# === New device: PKAM-authenticate using the APKAM private key + enrollmentId. ===
C(new): from:@alice\n
S:      data:proof:<sessionId>@alice:<chal>\n@
C(new): pkam:enrollmentId:<uuid>:<base64 RSA-SHA256 signature of chal>\n
S:      data:success\n@alice@

# New device now retrieves its bootstrap material:
C(new): keys:get:keyName:public:encryption_<uuid>.__public_keys.__pkams@alice\n
S:      data:{ "enrollmentId":"<uuid>", "value":"<encryptedDefaultEncryptionPrivateKey>", "iv":"…" }\n@alice@
# (And likewise for the self-encryption key.)

# New device decrypts those using its now-shared APKAM symmetric key,
# writes them locally as its scoped .atKeys, and is fully provisioned.
```

The new device never sees the master signing private key. APKAM-issued
keys are revocable via `enroll:revoke`.

### 16.3 Cross-atSign read with pol handshake

@bob looks up `@alice`'s phone number, which `@alice` has shared with
him.

```
# === atClient session as @bob, authenticated to @bob's atServer. ===
C(bob): lookup:phone.wavi@alice\n

# @bob's atServer proxies (this is invisible to the atClient):
#
#   bobServer ──TLS──► aliceServer
#
#   bobServer → aliceServer:  from:@bob
#   aliceServer → bobServer:  data:proof:<sessionId>@bob:<chal>\n@
#
#   bobServer signs <chal> with @bob's signing private key.
#   bobServer stores public:<sessionId>@bob = signedChallenge in its
#   own keystore.
#
#   bobServer → aliceServer:  pol\n
#
#   aliceServer:
#     opens unauthenticated outbound to bobServer
#     bobServer → aliceServer (in pol):
#         lookup:<sessionId>@bob → data:<signedChallenge>
#         plookup:signing_publickey@bob → data:<@bob's signing pub key>
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

```
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

```
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

```
C: sync:from:0:limit:1000:skipDeletesUntil:43\n
```

---

## 17. Errors

Error responses are framed identically to data responses but with the
prefix `error:` instead of `data:`:

```
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

| Code     | Message                                | Class                              | Connection |
| -------- | -------------------------------------- | ---------------------------------- | ---------- |
| `AT0001` | Server exception                       | `AtServerException`                | Closed     |
| `AT0002` | DataStore exception                    | `DataStoreException`               | Closed     |
| `AT0003` | Invalid syntax                         | `InvalidSyntaxException`           | Closed     |
| `AT0004` | Socket error                           | `AtIOException`                    | Closed     |
| `AT0005` | Buffer limit exceeded                  | `BufferOverFlowException`          | Closed     |
| `AT0006` | Outbound connection limit exceeded     | `OutboundConnectionLimitException` | Open       |
| `AT0007` | atServer not found                     | `SecondaryNotFoundException`       | Open       |
| `AT0008` | Handshake failure                      | `HandShakeException`               | Closed     |
| `AT0009` | UnAuthorized client in the request     | `UnAuthorizedException`            | Closed     |
| `AT0010` | Internal server error                  | `InternalServerError`              | Closed     |
| `AT0011` | Internal server exception              | `InternalServerException`          | Closed     |
| `AT0012` | Inbound connection limit exceeded      | `InboundConnectionLimitException`  | Closed     |
| `AT0013` | Connection Exception                   | `BlockedConnectionException`       | Closed     |
| `AT0014` | Unknown AtClient exception             | `AtClientException`                | n/a (client-only) |
| `AT0015` | Key not found                          | `KeyNotFoundException`             | Open       |
| `AT0016` | Invalid key                            | `InvalidAtKeyException`            | Open       |
| `AT0021` | Unable to connect to atServer          | `SecondaryConnectException`        | n/a (client-only) |
| `AT0022` | Illegal arguments                      | `IllegalArgumentException`         | Open       |
| `AT0023` | Timeout waiting for response           | `AtTimeoutException`               | Open       |
| `AT0024` | Server is paused                       | `ServerIsPausedException`          | Open       |
| `AT0025` | Authentication failed (cram/pol)       | `UnAuthenticatedException`         | Closed     |
| `AT0026` | APKAM enrollment pending               | `UnAuthenticatedException`         | Closed     |
| `AT0027` | APKAM enrollment revoked               | `UnAuthenticatedException`         | Closed     |
| `AT0028` | Too many requests / throttle exceeded  | `AtThrottleLimitExceeded`          | Open       |
| `AT0029` | APKAM enrollment expired               | `AtInvalidEnrollmentException`     | Closed     |
| `AT0031` | Cannot revoke own enrollment           | `AtEnrollmentRevokeException`      | Open       |
| `AT0032` | Illegal state                          | `IllegalStateException`            | Open       |
| `AT0401` | Client authentication failed (cram/pkam) | `UnAuthenticatedException`       | Closed     |

### 17.2 Note on `AT0009` vs `AT0401`

`AT0401` is emitted on **authentication** failure (the credential is
wrong). `AT0009` is emitted on **authorisation** failure (the
authenticated principal lacks permission for the requested key —
notably APKAM scopes prohibiting the namespace). Implementations must
distinguish between them; clients may retry on `AT0401` but not on
`AT0009`.

---

## 18. Glossary

- **APKAM** — Application PKAM. Per-app, per-device, namespace-scoped
  authentication built on PKAM. The modern way to authenticate.
- **atClient** — Software acting on behalf of an atSign owner.
- **atDirectory** — Service mapping atSign → `host:port` of the
  atSign's atServer.
- **atKey** — A key in an atServer's keystore. Five shapes (public,
  self, shared, local, private) plus augmentations (hidden, cached).
- **atServer** — The personal server for one atSign.
- **atSign** — An identifier of the form `@<name>`. Maximum length 55
  characters.
- **Commit log** — Append-only log of `update`/`delete` operations.
  Walked by `sync:from`.
- **CRAM** — Challenge-Response Authentication Mechanism. The
  bootstrap-only credential, used during onboarding.
- **Enrollment** — An APKAM record granting an app a namespace-scoped
  keypair. Has lifecycle states `pending`, `approved`, `denied`,
  `revoked`, `expired`.
- **Master AtKeys** — The atSign's root keypairs (PKAM signing,
  encryption, self-encryption), produced at onboarding.
- **OTP** — Six-character alphanumeric one-time password. Used to bind
  an APKAM enrollment to an out-of-band human approval.
- **PKAM** — Public-Key Authentication Mechanism. Sign-the-challenge
  authentication; underpins APKAM.
- **`pol`** — Proof-of-life. The atServer-to-atServer authentication
  handshake in which the connecting atServer publishes a signed
  challenge as a public atKey on its own atServer for the receiving
  atServer to fetch and verify.
- **Prompt** — The trailing `\n@…@` (or `\n@`) that frames the next
  request on a connection.
- **`sharedKeyEnc`** — Inline-in-metadata, RSA-encrypted shared
  symmetric key.
- **Verb** — A single-line command in the protocol.

---

## Appendix A — Verb reference

Terse reference for ctrl-F. Authoritative regex source:
[`at_commons/lib/src/verb/syntax.dart`](https://github.com/atsign-foundation/at_client_sdk/blob/trunk/packages/at_commons/lib/src/verb/syntax.dart).

| Verb            | Auth | Purpose                                          | Section |
| --------------- | ---- | ------------------------------------------------ | ------- |
| `from`          | —    | Identify connecting atSign; receive challenge.   | §9.1    |
| `cram`          | —    | Bootstrap-only authentication.                    | §9.2    |
| `pkam`          | —    | Sign-the-challenge authentication.                | §9.3    |
| `pol`           | —    | Inter-atServer proof-of-life. Server-emitted only.| §15.2   |
| `enroll`        | varies | APKAM enrollment lifecycle.                      | §9.4.1  |
| `otp`           | owner | Get/put OTP for APKAM.                            | §9.4.2  |
| `keys`          | yes  | APKAM-issued key storage. **Being deprecated** — see §9.4.3 and §B.7. | §9.4.3  |
| `update`        | yes  | Insert/overwrite an atKey.                        | §10.1   |
| `update:meta`   | yes  | Update only metadata.                             | §10.2   |
| `delete`        | yes  | Remove an atKey.                                  | §10.3   |
| `lookup`        | yes  | Cross-atSign read.                                | §10.4   |
| `plookup`       | —    | Public lookup.                                    | §10.5   |
| `llookup`       | yes  | Local-server-only lookup.                         | §10.6   |
| `scan`          | varies | Enumerate atKeys (regex/filter).                  | §10.7   |
| `notify`        | yes  | Emit a notification.                              | §11.1   |
| `notify:all`    | yes  | Emit to multiple recipients.                      | §11.2   |
| `notify:list`   | yes  | List received (or sent, if pol-auth) notifications.| §11.3  |
| `notify:status` | yes  | Query delivery status.                            | §11.4   |
| `notify:fetch`  | yes  | Fetch full notification record.                   | §11.5   |
| `notify:remove` | yes  | Remove from local notification log.               | §11.6   |
| `monitor`       | yes  | Stream of received notifications.                 | §11.7   |
| `sync:from`     | yes  | Walk the commit log from an offset.               | §12.1   |
| `config`        | owner | Block-list and config management.                 | §13.1   |
| `stats`         | yes  | Server statistics.                                | §13.2   |
| `info`          | varies | Server runtime info.                              | §13.3   |
| `noop`          | —    | Sleep then `data:ok`.                             | §13.4   |
| `batch`         | yes  | Multiple verbs in one round-trip.                 | §13.5   |
| `@exit`         | —    | atDirectory graceful close.                       | §8.4    |

---

## Appendix B — Legacy and deprecated

The following items remain in the wire grammar for backward
compatibility but new implementations should not produce them.

### B.1 `cram` as a permanent credential

Pre-onboarding, `cram` is the only credential. Post-onboarding, an
atServer accepts `cram` only as a fallback for compatibility; modern
clients use `pkam`/APKAM exclusively. Servers may disable `cram`
post-onboarding entirely.

### B.2 `sync` (without `:from:`)

```
sync:<from_commit_seq>[:<regex>]
```

The pre-`sync:from` syntax. Equivalent to `sync:from:<seq>:<regex>`
without the `:limit:` and `:skipDeletesUntil:` knobs. New clients use
`sync:from`.

### B.3 `notify` `messageType:text`

`notify:…:messageType:text:…` is a freeform-text notification (not
tied to an atKey change). Marked deprecated in `at_commons`. New code
uses `messageType:key` exclusively; freeform messaging is now done via
a regular shared atKey + `notify:update`.

### B.4 `pubKeyCS`

Predecessor metadata field to `pubKeyHash`. A truncated checksum
rather than a full hash; lacks an `algo` companion field. Servers
accept it on read; new metadata writes must use `pubKeyHash` +
`hashingAlgo`.

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

## Appendix C — Significant near-term projects

This appendix lists active workstreams that will materially change
parts of this specification. Each entry links to the tracking issue;
issue threads carry the current design state. Implementers should not
commit to long-lived choices in these areas without checking the
tracking issues for the present direction. The list is current as of
2026-05-05; it is not a roadmap commitment, just a snapshot of what is
moving.

### C.1 Post-quantum cryptography and crypto agility

The current encryption stack is RSA-2048 (asymmetric) + AES-256
(symmetric) + SHA-256/SHA-512 (hashing). Transition to post-quantum
primitives is in active design.

- **Pluggable encryption / decryption schemes** —
  [at_client_sdk #1891](https://github.com/atsign-foundation/at_client_sdk/issues/1891).
  Refactor the client encrypt/decrypt path so the algorithm is a
  pluggable strategy rather than hard-coded RSA + AES. Direction:
  Signal-style triple-ratchet as the new default. Affects every
  metadata field that names an algorithm (`encAlgo`, `skeEncAlgo`,
  `hashingAlgo`).
- **Implement post-quantum (PQ) cryptography along with crypto
  agility** —
  [at_client_sdk #1889](https://github.com/atsign-foundation/at_client_sdk/issues/1889).
  Land the first PQ primitives behind the pluggable interface above.
- **Implement post-quantum end-to-end encryption where actors
  communicate over Atsign Protocol** —
  [at_client_sdk #1893](https://github.com/atsign-foundation/at_client_sdk/issues/1893).
  End-to-end PQ encryption on the wire — the protocol-visible part of
  the PQ work.

Implementers should treat algorithm names in metadata as
forward-compatible enums and design for new values appearing.

### C.2 Fast sync ("fsync") — Better sync

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
hyphen/colon separator inconsistency noted in [§D.1](#d1-error-code-separator-hyphen-vs-colon)).

### C.5 Canonical SDK conformance test suite

[at_client_sdk #1900](https://github.com/atsign-foundation/at_client_sdk/issues/1900).
A canonical test suite for SDKs in any language to implement. When
this lands it becomes the de-facto compliance gate for an
"Atsign-Protocol-compliant" implementation; clients of this
specification should adopt it.

Related: **at_commons tests reflecting at_server / NoPorts usage** —
[at_client_sdk #1782](https://github.com/atsign-foundation/at_client_sdk/issues/1782).

### C.6 Move and improve `at_server_spec` into `at_client_sdk/at_commons`

[at_server #2608](https://github.com/atsign-foundation/at_server/issues/2608).
The `at_server_spec` package (interface definitions used by both the
server and the client) is being relocated into `at_commons`. This
specification cites paths in `at_commons/lib/src/verb/syntax.dart`
that will remain stable, but related interface paths under
`at_server_spec` should be expected to move.

### C.7 Multi-language SDKs (Java APKAM, others)

- **Java SDK APKAM support** —
  [operations #348](https://github.com/atsign-foundation/operations/issues/348).
  The Java SDK is gaining APKAM support, bringing it to parity with
  the Dart SDK on Phase-3 authentication.
- **Multi-language support** —
  [at_client_sdk #1885](https://github.com/atsign-foundation/at_client_sdk/issues/1885).
  Tracking parent for ports of the SDK to additional languages. This
  specification document is the basis for those ports.

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
Today, looking up a key whose `eAt` has passed returns `data:null`;
the proposed correction is `error:AT0015-Key not found`. A small
change but observable on the wire — see [§D.4](#d4-expired-keys-return-null-instead-of-an-at0015-error).

---

## Appendix D — Inconsistencies and quirks

This appendix documents on-the-wire surprises that the per-verb
sections don't make obvious. Implementers writing a parser, a server,
or an interoperable client need this list. None of these are
specification bugs in this document — they are facts about the
deployed protocol that this document accurately describes; they are
collected here so an implementer can sanity-check failure modes
against them.

### D.1 Error-code separator: hyphen vs colon

Both forms appear in current servers:

```
error:AT0003-Invalid Syntax
error:AT0025:Authentication Failed
```

The hyphen form predates the colon form; newer error sites tend to
use `:`. Clients must accept both — splitting only on `-` will fail
on `AT0025`-class errors, splitting only on `:` will misparse
hyphen-separated messages.

The base response handler (`base_response_handler.dart` line 35)
emits `error:<code>:<message>`, but many call sites construct the
final string with a hyphen instead.
[Standardise exception handling](#c4-standardise-exception-handling-across-sdk-packages)
will normalise this.

### D.2 "Secondary Server" vs "atServer" in error messages

Several error messages still use the old "Secondary Server"
terminology — e.g. `error:AT0007-Secondary Server not found.` Some
sites have been updated to "atServer not found"; both wordings are
emitted in different code paths. Same code (`AT0007`), different
text. Match on the code, not the message.

See also [Appendix B.6](#b6-commons-and-atserveratsecondary-terminology-drift).

### D.3 Per-verb response framing differs

Most verbs follow `data:<payload>\n@<atSign>@` (or `\n@`
unauthenticated). A handful do not:

- **`pol`** — emits just `@<atSign>@` with no `data:` prefix and no
  trailing `\n@…@` framing. The `PolResponseHandler` strips the
  `pol:` prefix from the verb's internal result. Outbound clients
  detect "pol succeeded" by matching the wire shape `<currentAtSign>@`.
- **`monitor`** — emits a stream of `notification: {<json>}\n` lines
  with no per-line `data:` prefix and no trailing prompt between
  events. Connection remains open until either side closes.
- **`stream`** — uses binary framing with `stream:ack` / `stream:done`
  control lines interleaved with raw payload bytes. (`stream` is
  legacy, see Appendix B.5.)
- **`from`** — see [§D.6](#d6-from-response-shape-self-vs-cross).

### D.4 Expired keys return null instead of an AT0015 error

A `lookup` against an expired key returns `data:null` rather than
`error:AT0015-Key not found`. This conflicts with the documented
behaviour of `KeyNotFoundException` and surprises clients that switch
on the error path. Tracked in
[at_server #2568](https://github.com/atsign-foundation/at_server/issues/2568)
— the proposed fix is to emit `AT0015` consistently. Until then,
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

```
data:<sessionId><atSign>:<proof>
```

For a cross-atSign connect, it is

```
data:proof:<sessionId>@<atSign>:<proof>
```

The `proof:` infix is the difference. The `FromResponseHandler`
prepends `data:` only when the verb result starts with `proof:` — the
self-connect handler emits a string already prefixed `data:`, so
there is no double-prefixing. Parsers must not assume a uniform
"`data:` then payload" shape for `from`.

### D.7 `keys:put` returns `data:-1`

`keys:put` is used for APKAM-issued keys, which by design are not
written to the commit log. Rather than return a real commit ID, the
handler returns the sentinel `-1`. Clients must not interpret this
as an error.

### D.8 Mutating verbs typically require auth — `enroll:request` does not

`enroll:request` is a mutating verb (it creates a pending enrollment
record on the server) but it can be sent on an **unauthenticated**
connection. The OTP carried in the request is the auth surrogate.
Every other write verb (`update`, `update:meta`, `delete`, `notify`,
`keys`) requires an authenticated connection.

### D.9 Newline escaping is value-class-specific

`~NL~` is the on-wire escape for a literal `\n` inside a value, but
it is applied **only to plaintext public values** by the atServer.

- Encrypted values (`isEncrypted:true`) carry ciphertext that has
  been base64-encoded; base64 contains no newlines, so the escape is
  irrelevant.
- Binary values (`isBinary:true`) are likewise base64-encoded.
- Self / shared plaintext values are atypical (clients almost always
  encrypt) and the escape behaviour for them is implementation-
  specific; do not rely on either path.

Because `\n` is the framing terminator, a client must never write a
plaintext value containing an unescaped `\n` — the server will treat
the `\n` as end-of-command.

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
appear in the regex; reproduced in §7.2).

### D.12 `clientConfig` JSON is unenforced free-form

The `from` verb's `:clientConfig:<json>` segment is parsed by
`jsonDecode` and a small set of fields (`version`, `clientId`,
`appName`, `appVersion`, `platform`) is read into the connection's
metadata. Every other field is silently discarded. There is no
schema enforcement: malformed-but-parseable JSON is accepted; an
unrecognised key produces no warning.

### D.13 `delete` is idempotent and always commits

Calling `delete` on a non-existent key returns `data:<commitId>`
exactly as if the key had existed. The commit log gains a tombstone
entry regardless. Other CRUD verbs error on a missing target; only
`delete` is idempotent in this way.

### D.14 Negative metadata integers are mostly meaningless

The metadata regex permits `(-?)\d+` for `ttl`, `ttb`, `ttr`. Only
`ttr:-1` ("cache forever") is a useful negative; `ttl:-1` and
`ttb:-1` are accepted by the regex and produce undefined / silently
useless behaviour. Clients should emit `0` (or omit the tag entirely)
for "no TTL".

### D.15 `info` auth requirement is per-deployment

The `info` verb's authentication requirement is a server-side config
toggle, not a fixed property of the protocol. Some deployments
accept `info` from anonymous connections; others require an
authenticated session. Implementations should attempt unauthenticated
first and fall back if rejected.

### D.16 Two metadata tags for the same concept: `pubKeyCS` and `pubKeyHash`

`pubKeyCS` (a checksum) was the predecessor of `pubKeyHash` (a hash
plus `hashingAlgo` companion field). Servers accept both on read.
New writes must emit `pubKeyHash` + `hashingAlgo`. A record may
carry one or the other, never both meaningfully — see Appendix B.4.

### D.17 Session ID format

Session IDs (`<sessionID>` in `from`/`pol`) are produced server-side
and have a leading `_` followed by a UUID, e.g.
`_4af24c03-d732-48f8-a9a2-570e8fb6a01c`. The leading underscore
matters: it makes the per-session keystore entries (`public:<sessionID><atSign>`)
"hidden" by atKey-shape rules and so they don't appear in `scan`
output without `:showhidden:true`.
