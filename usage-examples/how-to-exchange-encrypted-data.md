# How to exchange encrypted data

* **Status:** **Draft** / Approved / Rejected / Superseded
* **Last Updated:** 2023-01-25
* **Objective:** Explain how an authenticated atSign client exchanges data with another atSign

## Context & Problem Statement

Some details of how the atPlatform works are not specified in detail by the atProtocol itself, but are
usage conventions which are embedded in the client SDKs. As a result, building new client software, be
it in a new language or building alternative client software for a language for which client software
is already available, requires the engineer to base their efforts upon existing client libraries rather
than a language-agnostic specification of the minimum functionality required.

## Goals

Given a client which has access to keys from a completed onboarding, provide a detailed specification
of how the client can securely exchange data with another atSign.

### Non-goals

This document does not cover client onboarding.

* TODO: Create such a document

## Specification Summary

## Specification in Detail
### Core prerequisites
Ability to
- create RSA encryption public/private keypairs and use them to do encryption and decryption
- cryptographically sign data using a private key, and verify signatures using a public key
- create AES encryption keys and use them to do encryption and decryption
- establish a TLS socket connection, and be able to use it to send and receive data

### Flow
Given an already-onboarded client (i.e. access to authentication private key and encryption private key) for atsign 
`@alice`
- Lookup address of the `@alice` atServer
  - Establish TLS connection to root.atsign.org:64
  - Send `alice\n`
  - Expect response in form `<someDomain.example.com>:<port>`
- Authenticate to `@alice` atServer
  - Establish TLS connection 
  - do PKAM authentication
    - Send `from:@alice`
    - Expect response in form `data:<challengeText>`
    - Create a base64-encoded SHA256 signature of `challengeText` using the client's PKAM private key
      - Dart code example
      ```dart
        var key = RSAPrivateKey.fromString(privateKey);
        var sha256signature =
            key.createSHA256Signature(utf8.encode(challengeText) as Uint8List);
        var signature = base64Encode(sha256signature);
      ```
    - Send `pkam:<signature>`
    - Expect response `data:success` (or `error:<errorMessage>` if the signature could not be verified by the atServer
      using the corresponding PKAM public key)

TODO Clean up the rest of this and add diagrams

- share an AES key with another atSign. Assuming you are alice and you want to talk to bob this is: (1) cut an AES
key, (2) lookup bob's public key (3) encrypt the AES key (4) use
update verb to save it as @bob:shared_key@alice (5) encrypt the AES key with your own encryption private key for your
own use, and (6) use update verb to save it as
shared_key.bob@alice 
- share data encrypted with that AES key. Encrypt your data with the AES key, use update verb to save it as @bob:
some.key_name.in.some.namespace@alice

And conversely an already-onboarded client which wants to receive data needs to be able to (1) PKAM authenticate (2)
lookup some data e.g. @bob:
some.key_name.in.some.namespace@alice (3) retrieve the AES key by looking up @bob:shared_key@alice (4) decrypt the data
using the AES key