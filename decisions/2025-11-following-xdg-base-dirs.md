# Following XDG Base Directory spec

<!-- This template is inspired by
https://github.com/GoogleCloudPlatform/emblem/tree/main/docs/decisions -->

* **Status:** Draft <!--/ Approved / Rejected / Superseded-->
* **Last Updated:** 2025-11-14
* **Objective:** Follow standard conventions in our software.

## Context & Problem Statement

For those that aren't familiar with the XDG Base Directories spec, please read
[this summary](https://wiki.archlinux.org/title/XDG_Base_Directory#System_directories)
first. It is also worth looking further down in that document at all of the
applications which had their own dot directory and moved to use the XDG base
directories conventions.

The use of the `~/.atsign` directory for everything mixes cache
(local secondary storage) data with .atKeys files (i.e. credentials), all under
the same directory.

## Goals

* Separate data storage by type, so that management by type is easy
  (e.g. delete all cache data, not just our software's, in one command).
* Minimize the amount of migration effort required.
* Follow standard conventions when it makes sense.

### Non-goals

* Following the spec for the sake of following the spec

## Other considerations <!-- optional -->

### What we presently store in `~/.atsign`

* `keys` - the canonical .atKeys file path.
* `sshnp/cached_pks` - a cache directory for other atSign's public keys
  (though, this one is planned for deletion altogether).
* `storage/<atsign>` - storage cache directory for an atSign.
* `at_onboarding_cli/storage/<atsign>` - another storage cache for an atSign.

## Proposal Summary

Two stages presented below, the first being a quickfix solution, to help create some
conventions for data storage, rather than the mess we have now.

The second stage being an extension on top of stage 1, which improves key
resolution by adding a new non-breaking standard for atKeys file storage.

## Proposal in Detail

### Stage 1 - Use XDG State Directory

1. Keep `~/.atsign/keys/` as is.
2. Leave `~/.atsign/sshnp/cached_pks/` as is, until it is removed later.
3. Standardize the storage path from `~/.atsign/**/storage` to
  `$XDG_STATE_HOME/<app>/<atsign>/storage`.
4. Set forth the practice to use a standard convention instead of choosing
something without giving it much thought.

Why `XDG_STATE_HOME` instead of `XDG_CACHE_HOME`?
I think that either is fine, but rebuilding a local secondary storage is
expensive enough that we should lean towards the more permanent side.

### Stage 2 - Multi-key Resolution System

A keys resolution system could be interesting and potentially useful when
working with APKAM keys that have been cut on a machine.

For example:

* `~/.atsign/keys/<app>/` for the primary set of keys, following the same file
  naming scheme.
* `~/.atsign/keys/` for the default/fallback keys path.

For example, with `app=noports` and `atsign=bob`:
1. Try `~/.atsign/keys/noports/@bob_key.atKeys`
2. Try `~/.atsign/keys/@bob_key.atKeys`

This would be really helpful for the new `noports` cli binary which seeks to
simplify apkam with its `activate` and `issue-keys` subcommands. It would be
helpful to have this standard in place and start using it in that release.

### Stages Footnotes

Notice that I used `<app>` in both options.

I think we need some clarity on how this is defined:

1. It could be a simple string. In which case it could be the primary
namespace of the application. Thus that app must own the atSign in order to
claim the directory via primary ownership of the namespace.

2. Alternatively, we could come up with some clever encoding mechanism to
associate all namespaces of an app with a directory. This is super complicated,
and noports already serves as an example of why this doesn't scale well: it
started with `sshnp` & `sshrvd`, then we later added `noports` for storing app
settings and profiles.

3. A uuid, but there's still risk of collision this way, so I think it's just a
worse version of option 1.
