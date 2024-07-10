# Platform SDKs

* **Status:** Approved
* **Last Updated:** 2024-07-10
* **Objective:** Set out a policy for our approach to providing software
development kits (SDKs) for various languages and platforms.

## Context & Problem Statement

We have (over the span of five years) created a variety of
[SDKs](https://github.com/atsign-foundation#available-sdks):

* Dart
* Java
* Python
* Micropython
* C
* C++
* Rust
* Go

With the C SDK we could potentially use it as a library, and wrap it using
foreign function interface (FFI) bindings, which can often be automatically
generated for other languages. This would potentially save time in providing
an SDK for new languages/platforms when they are requested by customers.

The problem is that generating an SDK like that would require the C library
to be maintained, shipped and bundled with its wrapper. It would also provide
a non native developer experience.

## Goals

Have a clear understanding of how we will approach the creation of additional
SDKs.

### Non-goals

To specify the SDK implementation.

## Considered Options

* ### Wrap a C library using generated FFI bindings

This was proposed ahead of an architecture call on 4 Jul 2024 in the hope
that it might speed up the process of providing additional SDKs.

* ### Create a native SDK for each new language/platform

After some discussion in the 4 Jul 2024 architecture call it was decided
that the drawbacks of wrapping a C library outweighed the potential benefits,
and thus we would continue to create native SDKs.

## Proposal Summary

Additional SDKs will be crafted in their native language.

## Proposal in Detail

When targeting a broader platform (e.g. .Net) we can choose the most
appropriate language in that platform (e.g. C#) to create the SDK.

An atSDK specification will be created based on the Dart & Java
implementations in order to speed the development of future SDKs.

### Expected Consequences

We shall have to continue to learn new platforms or hire team members with
the language skills required.

In some cases we may be able to collaborate with the customer requesting
an SDK to help co-develop it.
