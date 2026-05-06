# Atsign Protocol app developer guide

A pointer document for **app developers** building on the Atsign
Protocol via the Dart `at_client_sdk`. If you are implementing an
atServer or atClient in another language, you want
[`atsign_protocol_specification.md`](./atsign_protocol_specification.md)
instead.

<!-- pyml disable-num-lines 999 md013-->

## Pick the right SDK package

| If you're building…                            | Start with                                                                                                                                                                                                                                                                   |
|------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| A Flutter app (mobile / desktop / IoT)         | [`at_client_flutter`](https://github.com/atsign-foundation/at_client_sdk/tree/trunk/packages/at_client_flutter): ships pre-built onboarding and APKAM widgets.                                                                                                               |
| A Dart CLI or server app                       | [`at_cli_commons`](https://github.com/atsign-foundation/at_client_sdk/tree/trunk/packages/at_cli_commons) for boilerplate, plus [`at_onboarding_cli`](https://github.com/atsign-foundation/at_client_sdk/tree/trunk/packages/at_onboarding_cli) for first-time provisioning. |
| Custom onboarding tooling                      | [`at_auth`](https://github.com/atsign-foundation/at_client_sdk/tree/trunk/packages/at_auth): platform-neutral lifecycle core.                                                                                                                                                |
| Shared types (`AtKey`, `Metadata`, exceptions) | [`at_commons`](https://github.com/atsign-foundation/at_client_sdk/tree/trunk/packages/at_commons)                                                                                                                                                                            |

Web is **not** a supported target. Flutter web has no implementations
of the platform plugins onboarding and local storage depend on.

## The atSign lifecycle

There are 3 phases between "I don't own an atSign" and "my app is
talking to the atServer". The
[`at_auth` README](https://github.com/atsign-foundation/at_client_sdk/tree/trunk/packages/at_auth#the-atsign-lifecycle)
has the full writeup; the short version:

1. **Register** an atSign, free at
   [my.noports.com/no-ports-plans](https://my.noports.com/no-ports-plans),
   paid / custom at [my.atsign.com](https://my.atsign.com). You receive
   a **CRAM secret** by email.
2. **Onboard** the atSign exactly once: CRAM-authenticate, generate
   the master keypairs, store private halves in `.atKeys` (CLI) or the
   device keychain (Flutter). **Master keys are root of trust. Back
   them up.**
3. **Authenticate** subsequent apps via **APKAM enrollment**: request
   a namespace-scoped keypair (`{'todos': 'rw'}`), the master-keys
   holder approves, and the atServer issues new revocable credentials.

CLI tools that ship with `at_onboarding_cli`:

```sh
dart pub global activate at_onboarding_cli
at_register -e your_email@example.com   # Phase 1+2 in one shot
at_activate -a @alice                   # Phase 2 with email OTP
at_activate -a @alice -c <cram_secret>  # Phase 2 with explicit CRAM
```

For the APKAM flow, see
[`at_onboarding_cli/example/apkam_examples/`](https://github.com/atsign-foundation/at_client_sdk/tree/trunk/packages/at_onboarding_cli/example/apkam_examples).

## Day-to-day API: prefer `AtCollection<T>`

For app code, the recommended surface is
[`AtCollection<T>`](https://github.com/atsign-foundation/at_client_sdk/tree/trunk/packages/at_client#collections),
a typed, shareable, locally-indexed collection of records with a
query builder and event streams. AtCollection hides the AtKey,
metadata, notification-regex, and sync ceremony that the low-level
`AtClient.put/get/delete` API exposes.

The low-level API still exists, see
[The escape hatch](#the-escape-hatch-low-level-atclientputgetdelete)
below, but for everything that resembles "CRUD on typed records",
`AtCollection<T>` is the right tool.

### Sketch

```dart
final todos = await atClient.collection<Todo>(
  'todos.my_app',                // fully-qualified namespace
  const Duration(days: 7),       // default expiration
  fromJson: Todo.fromJson,       // (de)serialiser
  typeTag: 'Todo',               // required: discriminator for polymorphic types
  eventsFromLocalSecondary: true,// required: event-driven (true) vs notification-driven (false)
);

// Create + share
final item = await todos.create(
  obj: Todo('write readme'),
  sharedWith: {'@bob'.toAtsign()},
);

// Update
item.obj.done = true;
await todos.update(item);

// Diff-shared-with — preferred over update() when only changing recipients
await todos.updateSharedWith(
  item,
  sharedWith: {'@bob'.toAtsign(), '@carol'.toAtsign()},
);

// Delete (cascade-deletes sub-collections if any)
await todos.delete(item, cascade: true);

// Existence probe (cheap; uses plookup, not scan)
final exists = await todos.exists(item.id, item.owner);
```

### Queries

Build immutable, composable queries that fetch one-shot or watch live:

```dart
final overdue = todos.query()
    .where((t) => !t.obj.done)
    .wherePath($TodoFields.due.lt(DateTime.now()))   // typed AST predicate
    .orderBy((t) => t.obj.due)
    .thenBy((t) => t.id)
    .limit(20);

final list  = await overdue.get();              // one-shot List<CItem<Todo>>
final live  = overdue.watch();                  // Stream<List<CItem<Todo>>>
final count = await todos.query().where((t) => !t.obj.done).count();
final byOwner = await todos.query().groupBy<Atsign>((t) => t.owner);
```

For the common parent + children pattern (e.g. blog posts + comments,
invoices + line items):

```dart
final tree = posts.query().watchWithSub<Comment>(
  subName: 'comments',
  subFromJson: Comment.fromJson,
  subTypeTag: 'Comment',
);
// Stream<List<WithChildren<Post, Comment>>>
```

For arbitrary-depth hierarchies, use `watchWithTree`.

### Read receipts

Built into `CItem<T>`; idempotent on both sides.

```dart
// Reader side
await incomingItem.markReadByMe();

// Owner side
final readers = await myItem.readBy;            // Future<Set<Atsign>>
todos.readReceipts.listen((e) => print('${e.from} read ${e.id}'));
```

### Lifecycle event streams

```dart
// Items entering visibility (when their availableAt passes)
todos.availableEvents.listen((e) => doSomething(e));

// Items about to expire
todos.expiringSoonEvents(leadTime: Duration(hours: 1))
     .listen((e) => doSomething(e));

// All updates / deletes
todos.events.listen((e) => switch (e) {
  CItemUpdated()    => onUpdated(e),
  CItemDeleted()    => onDeleted(e),
  CSubItemUpdated() => onSubUpdated(e),
  // ...
});
```

### Sub-collections

Children scoped to a parent `CItem`, with opt-in cascade-delete:

```dart
final comments = posts.subCollection<Comment>(
  parent: post,
  subName: 'comments',
  defaultExpiration: const Duration(days: 30),
  fromJson: Comment.fromJson,
  typeTag: 'Comment',
);
await comments.create(
  obj: Comment('nice one'),
  sharedWith: {/* … */},
);

await posts.delete(post, cascade: true);   // removes its comments too
```

### Worked examples

Code worth opening rather than reading about. The Dart and CLI
examples live under
[`at_client/example/bin/`](https://github.com/atsign-foundation/at_client_sdk/tree/trunk/packages/at_client/example/bin):

- `collections_primitives.dart`: basic CRUD and sharing
- `collections_domain_objects.dart`: typed domain objects and `fromJson`
- `collections_generic.dart`: polymorphic types (single role)
- `collections_binary.dart`: `Uint8List` storage
- `collections_subcollections.dart`: parent and children with cascade
- `collections_invoices.dart`: concurrent typed-predicate watches with
  `PathField` range bucketing and a 10k-item create/delete cycle
- `collections_todos.dart`: full interactive TUI (shared todos)

The canonical Flutter reference app is
[`at_client_flutter/examples/todos`](https://github.com/atsign-foundation/at_client_sdk/tree/trunk/packages/at_client_flutter/examples/todos).
It has the same feature set as `collections_todos.dart`, rendered
through the mobile and desktop widget stack the way a shipping app
would use it.

## The escape hatch, low-level `AtClient.put/get/delete`

For the rare cases AtCollection doesn't fit, bespoke key shapes,
non-record-shaped values, integration with legacy data, the raw SDK
surface is still available:

```dart
await atClient.put(atKey, value);
final value = await atClient.get(atKey);
await atClient.delete(atKey);
```

You should almost never need this if you are using AtCollection.

## How the protocol relates to the SDK

The SDK's public API does not map 1:1 to wire verbs. The AtCollection
API in particular synthesises multiple verbs per call.

| App-level call                                                 | Underlying verb(s)                                                                      |
|----------------------------------------------------------------|-----------------------------------------------------------------------------------------|
| `collection.create(obj: …, sharedWith: …)`                     | `update` (self copy) + `update` per recipient + `notify` per recipient                  |
| `collection.update(item)`                                      | `update` (self copy) + `update` per recipient + `notify` per recipient                  |
| `collection.updateSharedWith(item, …)`                         | `update` per added/removed recipient + `notify` (no self-key rewrite)                   |
| `collection.delete(item, cascade: …)`                          | `delete` (self) + `delete` per recipient + `notify:delete` per recipient + cascade walk |
| `collection.exists(id, owner)`                                 | `plookup` (own atSign) or local cache lookup (other atSigns)                            |
| `collection.query().get()`                                     | local store read; one-time `sync:from` if stale                                         |
| `collection.query().watch()`                                   | local store subscription; `monitor` underneath for cross-atSign updates                 |
| `collection.events` / `availableEvents` / `expiringSoonEvents` | local-store `DataEvent` stream + client-side scheduled timers                           |
| `markReadByMe()` / `readBy`                                    | `update` / `llookup` against the reserved `__rr` sub-collection                         |
| `atClient.put(atKey, value)`                                   | `update`                                                                                |
| `atClient.get(atKey)` (own atSign)                             | `llookup`                                                                               |
| `atClient.get(atKey)` (other atSign)                           | `lookup`                                                                                |
| `atClient.delete(atKey)`                                       | `delete`                                                                                |
| `atClient.getAtKeys(regex: …)`                                 | `scan`                                                                                  |
| `notificationService.notify(...)`                              | `notify`                                                                                |
| `notificationService.subscribe(...)`                           | `monitor`                                                                               |
| `syncService.sync()` / `waitUntilCaughtUp()`                   | `sync:from` (paginated)                                                                 |
| `AtOnboardingService.onboard()`                                | `from` + `cram` + `update` (×N)                                                         |
| `AtOnboardingService.authenticate()`                           | `from` + `pkam`                                                                         |
| `AtEnrollment.submit(...)`                                     | `from` + `enroll:request`                                                               |
| `AtEnrollment.approve(...)`                                    | `enroll:approve`                                                                        |

If you find yourself reaching for something neither AtCollection nor
the high-level AtClient API exposes, drop down to
[`at_lookup`](https://github.com/atsign-foundation/at_client_sdk/tree/trunk/packages/at_lookup),
which is the verb-level transport, and consult the full
[Atsign Protocol Specification](./atsign_protocol_specification.md).

## Upcoming changes

Several active workstreams will materially change parts of the
protocol surface, post-quantum encryption, fast sync ("fsync"), a new
on-disk AtKeys structure, a canonical conformance test suite, and
others. See
[Appendix C of the specification](./atsign_protocol_specification.md#appendix-c-significant-near-term-projects)
for the current snapshot.

## Further reading

- [Atsign Protocol Specification](./atsign_protocol_specification.md):
  wire-level reference
- [atPlatform docs](https://docs.atsign.com/), high-level concepts
- [pub.dev: at_client](https://pub.dev/packages/at_client), the main
  SDK package
- [`at_client` README, Collections section](https://github.com/atsign-foundation/at_client_sdk/tree/trunk/packages/at_client#collections)
 , authoritative on the AtCollection API
