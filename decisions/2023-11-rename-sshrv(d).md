<!-- This template is inspired by https://github.com/GoogleCloudPlatform/emblem/tree/main/docs/decisions -->
## Rename sshrv(d)

* **Status:** Draft <!-- / Approved / Rejected / Superseded -->
* **Last Updated:** 2023-11-14
* **Objective:** To rename sshrvd and sshrv to something more technically accurate

## Context & Problem Statement

sshrvd and sshrv are actually tcp socket rendezvous, and are not ssh specific.

## Goals

- Deem if a new name is necessary
- Make the rename as part of 4.0.0's breaking changes if we decide to follow through with the rename

## Considered Options <!-- optional -->
- ### Keep them the same
- ### tcprv(d)
- ### sr(d)

## Proposal Summary

To rename sshrvd and sshrv to something without "ssh" and possibly with "tcp" in the name.

## Proposal in Detail

The two new options are either tcprv(d) or sr(d) which stand for tcp rendezvous (daemon) and socket rendezvous (daemon).

The choice for naming depends entirely on how we decide to proceed with future implementations.

If we want to support a single, universal daemon & client then we should use a name which doesn't contain "tcp"
since that client could eventually support udp and other socket types.

If we want separate daemon and clients for each socket type, then we should use a name which does contain "tcp"
so that we can be specific to that particular implementation.

### Update: Friday, December 1, 2023

We held a secondary vote in [a PR](https://github.com/atsign-foundation/at_protocol/pull/112) and established that the naming should be generic (option 3 won):

1. Keep the same name - sshrv(d)
2. Something specifically tcp related - e.g. tcprv(d), tcpsr(d), etc...
3. Something generic to sockets - e.g. srv(d), sr(d), etc... 
