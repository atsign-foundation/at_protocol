<!-- This template is inspired by https://github.com/GoogleCloudPlatform/emblem/tree/main/docs/decisions -->
## Remove Reverse SSH No Ports Client

* **Status:** Draft <!-- / Approved / Rejected / Superseded -->
* **Last Updated:** 2023-11-14
* **Objective:** To finalize the decision to remove reverse client support in SSH No Ports 4.0.0

## Context & Problem Statement

There are maintenance costs and edge cases created by supporting a reverse client as fallback when not using sshrvd with SSH No Ports.

[repo link](https://github.com/atsign-foundation/sshnoports)

## Goals

To establish whether we should support a reverse client or not, and how.

### Non-goals
N/A

## Considered Options <!-- optional -->
- ### Completely remove the reverse client
- ### Remove the reverse client and reintroduce as a completely separate implementation (later, as needed)
- ### Continue supporting the reverse client

## Proposal Summary

Recommendation: remove the reverse client for now, reintroduce it later as needed.

## Proposal in Detail

Supporting the reverse client creates a number of edge cases, and is useful for when we assume that there is no sshrvd mediating the connection.
The project is moving in the direction where sshrvd is the heart and soul of connectivity for sshnp, so there isn't a clear need for the reverse client.
Maintaining the reverse client leaves behind a bunch of additional maintenance work, since all forward clients would require either a fallback reverse 
client implementation, or in some cases, reverse clients can't be supported at all (such as in mobile/sandboxed applications).

My recommendation is that we remove the reverse client for now, and reintroduce it in isolation from the forward clients if
it is deemed as a necessary implementation for a particular use-case. 

### Expected Consequences <!-- optional -->
