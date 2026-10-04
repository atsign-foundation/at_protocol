# An ordered batch that can stop at its first failure

* **Status:** Draft
* **Last Updated:** 2026-10-04
* **Objective:** Make `batch` run a fixed set of verbs in order, and let a
client ask it to stop at the first command that fails.

## Context & Problem Statement

`batch` carries a list of commands in one request:

```text
batch:[{"id":1,"command":"update:..."},{"id":2,"command":"delete:..."}]
```

and answers with one entry per command:

```text
data:[{"id":1,"response":{...}},{"id":2,"response":{...}}]
```

Today at_client uses it only to push sync changes, which are updates and
deletes. What else a batch may carry isn't specified, so a client can't rely
on a `lookup` or a `notify` working inside one on every atServer
implementation. A failed command is recorded and the batch carries on, and a
command that matches no verb, or fails with no error code, gets no entry in
the reply at all.

Some of what at_client does needs one write to succeed before the next is
made. To mint a namespace key, a client first takes a lock, a short-lived
immutable record that the atServer refuses to create twice, and only then
publishes. That takes a round trip per step, and the lock only narrows the
window in which two enrollments can collide.

## Goals

* A batch can carry `lookup`, `llookup`, `plookup`, `notify`, `update` and
  `delete`, on every atServer implementation that advertises it.
* Its commands run in the order given.
* A client can ask a batch to stop at the first command that fails, so one
  request can take a lock and act under it.
* Every command in a batch gets an entry in the reply.
* `notify:all` is deprecated in favour of a batch of `notify` commands.

### Non-goals

* Transactions. Commands that ran before a failure stay done.
* Any other verb in a batch, including the other `notify` variants.

## Considered Options

* ### Option 1 - Keep sending one request per step

  Rejected, as it keeps the round trip per step and the window between taking
  a lock and acting under it.

* ### Option 2 - Specify batch, and add a flag to stop at the first failure

  Fix what a batch can carry and the order it runs in, add a bare flag that
  stops it at the first failure, and advertise both in `info`.

## Proposal Summary

Option 2. A batch carries `lookup`, `llookup`, `plookup`, `notify`, `update`
and `delete`, and runs them in order. A bare `abortOnFailure` flag stops it at
the first command that fails, and the commands after that one are not run.
An atServer advertises this as `batch.abortOnFailure` in the `features` list
described in
[Ephemeral notifications and explicit expiry](2026-10-ephemeral-notifications-and-explicit-expiry.md).
`notify:all`, which nothing uses, is deprecated in favour of a batch of
`notify` commands.

## Proposal in Detail

### Grammar

```text
batch[:abortOnFailure]:<json>
```

`abortOnFailure` is a bare flag: present means stop at the first failure,
absent means run every command. `<json>` is the list of
`{"id": <int>, "command": "<command>"}` objects that `batch` takes today.

### What a batch may carry

`lookup`, `llookup`, `plookup`, `notify` (the plain verb, not `notify:list`,
`notify:status`, `notify:fetch`, `notify:remove` or `notify:all`), `update` and
`delete`. The atServer checks every command before running any, and refuses
the whole batch, naming the first command it won't run, when one is outside
that set. Each command is authorized as it would be if sent on its own over
the same connection.

### Order

Commands run one at a time, in the order of the list. Each finishes, its
write included, before the next starts.

### Stopping at the first failure

A command fails when its reply is an error. With `abortOnFailure`, the batch
stops after the first failure, and the commands after it are not run. Without
it, the batch runs every command, as today.

### The reply

The reply has one entry per command, in the order of the list. A command that
ran has its reply, data or error, under `response`. A command that was not run
because an earlier one failed has `"skipped": true` and no `response`:

```text
data:[{"id":1,"response":{...error...}},{"id":2,"skipped":true}]
```

### Taking a lock in one request

A client puts the lock first and the writes it guards after it (shown wrapped;
on the wire it's one line):

```text
batch:abortOnFailure:[
  {"id":1,"command":"update:ttl:30000:immutable:true:_lock.ns@alice <holder>"},
  {"id":2,"command":"update:..."}]
```

When another enrollment holds the lock, the first command fails and nothing
else runs. When it succeeds, the guarded writes follow in the same request,
with no round trip between taking the lock and acting under it.

### notify:all

`notify:all` is unused legacy. A batch of `notify` commands does what it was
for, carrying a notification to each of many recipients in one request, and
gives each recipient its own metadata, which `notify:all` can't. So
`notify:all` is deprecated: an atServer lists it in `info` as `notify.all` with
status `Deprecated` while it still accepts it, and as `Retired` once it
refuses it.

### Expected Consequences

* at_commons carries the flag in the grammar and the builder, and the reply's
  `skipped` field.
* Every atServer implementation checks a batch against the six verbs before
  running it, runs it in order, honours `abortOnFailure`, gives every command
  an entry, and lists `batch.abortOnFailure` in `info`.
* at_client uses the flag only where its atServer lists the feature. Its
  namespace-key and signing-root mint locks, and any other step that must
  succeed before the next, can each become one request.
* One request can carry a notification to each of many recipients, as a batch
  of `notify` commands.
* at_commons marks `notify:all`'s grammar and builder deprecated, and every
  atServer implementation lists `notify.all` as `Deprecated`, then `Retired`
  when it stops accepting the verb.
