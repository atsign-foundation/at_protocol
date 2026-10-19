# Per-key links for an enrollment's signing keys

* **Status:** Draft
* **Last Updated:** 2026-10-17
* **Objective:** Let an enrollment vouch for each of another enrollment's
signing keys in one call to the atServer, so a signing chain can be mended at
once, without waiting for the other enrollment to come online.

Today's mechanism is described in at_client_sdk's post-quantum design,
[section 9.8.3][design-chain], and in its decision ledger, rulings
[22.2][ruling-22-2], [24.2][ruling-24-2], [144.2][ruling-144-2] and
[152][ruling-152]. This record summarises the change to it. The ledger will
carry the ruling, and these rulings will be amended where the new ruling
differs from them.

## Context & Problem Statement

Each enrollment of an atSign publishes the keys it signs with at
`public:_apsk.<enrollmentId>.a.__e@<atSign>`, as a list of entries each naming
a `kid`, an `alg` and the public key (an enrollment whose one key is an RSA
key publishes that key bare instead). A link vouches for those keys. It's
either a chain link, signed by another enrollment of the same atSign (today,
the one that approved it), or a root link, signed by the atSign's signing root
at `public:pq_signing_root@<atSign>`. Walking from an enrollment's link to its
signer's, and on up to a root link, shows that the enrollment's keys belong to
the atSign, by the chain of approvals that admitted it.

Two things about today's links get in the way.

A link signs the whole `_apsk` value. When an enrollment adds a signing key or
retires one, the value changes, and the link stops vouching for the keys that
didn't change. Worse, an enrollment republishes its `_apsk` through
`enroll:update`, which leaves the old link on the record, so the walk then
reads it as broken (ruling 144.2 records this, seen in a test against a local
atServer).

And today the enrollment a link vouches for writes the link itself. Its signer
sends it in an envelope with a 7-day lifetime, and it waits there until that
enrollment runs, reads it and stamps it. A chain link whose enrollment doesn't
run within the 7 days is lost for good (a root link is sent again by the next
sweep of an enrollment holding the root), and mending a chain always takes a
round trip through the enrollment being mended.

Nothing in production walks a chain yet, so neither problem changes behaviour
today. They need fixing before something does.

## Goals

* A link vouches for one key, so keys can come and go without disturbing the
  links on the others.
* An enrollment that could approve another can write links for it directly,
  in one call, whether or not the other is online.
* An enrollment links a key it adds itself, using a key it has already linked,
  so key rotation needs nobody else.
* Every link traces to the signing root at the moment it's written.
* An approver can see whether each enrollment is anchored to the root.

### Non-goals

* Consulting the chain when verifying content: secret envelopes, key packages
  and namespace-key advertisements. That's a later decision.
* Changing who may approve or revoke an enrollment, or what an enrollment's
  grants let it write.
* Verifying links' signatures on the atServer.

## Considered Options

* ### Option 1 - Fix today's whole-value links

  Clear or re-sign a link after every `enroll:update` republish. Rejected, as
  it keeps the binding to the whole value, and links still have to wait for
  the enrollment to stamp them.

* ### Option 2 - Links carried by `enroll:approve`

  The approver signs one link per advertised key, and the atServer writes them
  as it publishes `_apsk` at approval. Superseded by option 5, since it covers
  approval only, and not a key added later or a chain that needs mending.

* ### Option 3 - A link inside each `_apsk` entry

  Rejected. The enrolling client composes the `_apsk` value before any approver
  exists, so a link could only reach it by rewriting the value after approval,
  and the entry format is at_auth's, none of which is marked experimental.

* ### Option 4 - Links in a record of their own

  A record only the atServer writes, beside `_apsk`, so no other write of
  `_apsk` could touch its links. Set aside in favour of
  keeping links on `_apsk`: one read per hop, and no new reserved key name,
  were judged worth one carry-over rule in each atServer implementation.

* ### Option 5 - The atServer writes a link for the voucher (chosen)

  A new `enroll` operation stores a link the caller has signed on another
  enrollment's `_apsk`, or on its own.

For option 5, the right to write links was weighed two ways. A superset of the
target's grants on its own was rejected in favour of the approve gate, which
`enroll:approve` and `enroll:revoke` both apply, so writing a link takes the
same authority over the target as approving or revoking it. A stored link is
still only a claim, which the walk checks.

## Proposal Summary

A new operation, `enroll:link`, lets an enrollment write per-key links onto
another enrollment's `_apsk`, or its own, with the atServer storing them in one
map keyed by `kid`. Links stop travelling by envelope, and the code that
conveys and stamps them goes.

## Proposal in Detail

### Links

A link names one key: `{v: 2, enrollmentId, kid, alg, pub}`. An enrollment's
links live in one map in its `_apsk` record's `appMetadata`, keyed by `kid`,
with one link per key. A bare `_apsk` counts as one `rsa2048` entry, whose
`kid` the atServer and the walk both derive from the key the same way every
other `kid` is derived. The exception is an `_apsk` that is the enrollment's
authentication key, as on the legacy posture. That key is dropped rather than
retired once the enrollment mints a signing key, so it takes no links and signs
none, and the atServer tells it apart by comparing it with the `apkamPublicKey`
the enrollment record holds. Such an enrollment reads as unsigned until it
publishes a signing key, which is linked like any other. For the same reason
an `enroll:update` can't make a signing key the authentication key: it's
refused when it would leave the `apkamPublicKey` as a key the `_apsk` lists
beside another, or one that carries a link, whether it installs that key,
republishes the `_apsk`, or both.

Whether a link is a root link or a chain link follows from its signer. Every
link names the `kid` of the key that signed it. If that `kid` is one of the
active or retired keys of `public:pq_signing_root@<atSign>`, the link is a root
link, and it's checked against that key only. Otherwise the link must name the
enrollment that signed it, and it's checked against that `kid` in that
enrollment's `_apsk`. A link that fails its check reads as broken, and it's
never tried again as the other kind. Root links keep their `at-root-link:`
prefix, and chain links stay typed JWS, so a signature made for one can't pass
as the other.

### The `enroll:link` operation

```text
enroll:link:{"enrollmentId": "<target>",
             "links": {"<kid>": {"link": <link>, "expect": <link or null>}}}
```

One call covers any number of the target's keys. The atServer accepts it from
the target enrollment itself, or from any caller `enroll:approve` would admit:
a CRAM connection, or an enrollment that holds `__manage` explicitly and covers
every namespace the target holds at the access the target holds it.

The atServer checks the structure only, and doesn't verify signatures. It
checks that:

* the target is approved;
* each `kid` is advertised in the target's current `_apsk`, its public key
  spelt as clients write it, in padded standard base64;
* each link's payload names the target and that `kid`, `alg` and public key;
* each link is at most 16 KiB encoded, and both the whole call and the
  target's `_apsk` record, its value and `appMetadata` with every link it
  would then hold, fit the atServer's existing 500 KiB limit on an enrollment
  record;
* the link stored for each `kid` is the one the call names as `expect`,
  compared as JSON, or there's none when `expect` is null.

The call is all or nothing, under the atServer's lock on enrollment writes,
and a refusal names what failed. The compare-and-set on `expect` is
what keeps two vouchers, or a voucher and a sweep, from losing each other's
writes, and it leaves the policy for replacing a link to the client.

Every atServer implementation carries the stored link map over on any other
write of `_apsk`, a put or an `enroll:update` republish alike, whatever that
write sends, and drops links for keys the new value no longer advertises.
Those writes, a client's delete of the record, and `enroll:link` are
serialised with each other.

### Client behaviour

* An approver calls `enroll:link` straight after `enroll:approve`, writing root
  links when it holds the signing root's private key, and chain links signed
  with its own linked keys when it doesn't. An approver with neither, such as
  an enrollment on the legacy posture holding only its authentication key,
  can't, and a root holder's sweep anchors the new enrollment instead.
* An enrollment that adds a signing key links it itself, signing with one of
  its keys that already has a link, and only then signs content with it. The
  old key's link keeps vouching for what that key signed.
* A voucher signs a chain link only with one of its keys that already has a
  link, and a root link is signed only with the root key. So by induction
  every link traces to the root when it's written, and a linked key is an
  anchored key, short of a later revocation or expiry in between.
* The client decides when a link replaces another, and says so through
  `expect`: a root link may replace a chain link, a chain link never replaces a
  root link, and a chain link is replaced only to mend it.
* An enrollment signs content with its linked keys while it has one, and
  otherwise as it does today.
* A fully privileged enrollment whose atSign publishes no signing root mints
  one when it starts, and links its own keys. Today a root is minted only at
  activation and when an older keyfile is retrofitted, so without this an
  older atSign could never be anchored.
* Each time an enrollment holding the root's private key starts, its sweep
  root-links any key on the atSign without a root link that passes its check,
  replacing a chain link, or a root link that fails its check.
* The walk follows pairs of enrollment and `kid`, and reads a cycle as broken.
  A voucher doesn't vouch for an enrollment its own key already chains
  through.
* `at_activate list` and at_client_flutter's `EnrollmentRequestList` show
  whether each enrollment is anchored.

### Expected Consequences

* at_commons gains `link` in the `enroll` grammar, and its parameters.
* Every atServer implementation adds `enroll:link`, the carry-over rule, the
  serialisation and the bounds above.
* at_client writes and reads the new links, calls `enroll:link`, mints a
  missing root and walks by key. It removes link envelopes, stamping, the
  startup's pending-link step, its own writes of link fields, and the version 1
  whole-value links with their `apskChainLink` and `apskRootLink` fields, all
  of which are marked experimental. The sweep stays, writing through
  `enroll:link`, and so does the conveyance of secrets at approval and of the
  signing root's private key to fully privileged enrollments.
* at_onboarding_cli and at_client_flutter show anchored status.
* An atServer without `enroll:link` gets no links at all, and its enrollments
  read as unsigned, which the walk already tolerates during the changeover.
  That's harmless while nothing in production walks a chain, so the first
  production code that does should ship after `enroll:link` is on every
  atServer, or else tolerate unsigned enrollments.

[design-chain]: https://github.com/atsign-foundation/at_client_sdk/blob/66bf122a3af81d47aaa0071fb47fe78b5ef74be7/docs/projects/pq/design.md#983-the-chain-and-why-a-link-is-bound-to-the-exact-string
[ruling-22-2]: https://github.com/atsign-foundation/at_client_sdk/blob/trunk/docs/projects/pq/detail/decisions.md#222-the-signing-root-chain-follows-the-approval-graph
[ruling-24-2]: https://github.com/atsign-foundation/at_client_sdk/blob/trunk/docs/projects/pq/detail/decisions.md#242-the-rulings
[ruling-144-2]: https://github.com/atsign-foundation/at_client_sdk/blob/trunk/docs/projects/pq/detail/decisions.md#1442-a-republish-clears-the-links-a-root-holder-re-anchors
[ruling-152]: https://github.com/atsign-foundation/at_client_sdk/blob/trunk/docs/projects/pq/detail/decisions.md#152-a-conveyed-link-is-stamped-as-it-arrives-and-its-envelope-kept-until-it-is-2026-10-08
