## How to exchange encrypted data

* **Status:** **Draft** / Approved / Rejected / Superseded
* **Last Updated:** 2023-01-25
* **Objective:** Explain how an authenticated atSign client exchanges data with another atSign

**TODO**: Add diagrams

<!-- TOC -->
  * [How to exchange encrypted data](#how-to-exchange-encrypted-data)
  * [Context & Problem Statement](#context--problem-statement)
  * [Goals](#goals)
    * [Non-goals](#non-goals)
  * [Specification](#specification)
    * [Core prerequisites](#core-prerequisites)
    * ["Sending" atSign](#-sending--atsign)
      * [- Lookup address of the `@alice` atServer](#--lookup-address-of-the-alice-atserver)
      * [- Authenticate to `@alice` atServer](#--authenticate-to-alice-atserver)
      * [- Fetch existing shared symmetric key if it has already been created](#--fetch-existing-shared-symmetric-key-if-it-has-already-been-created)
      * [- Or create a new shared symmetric key](#--or-create-a-new-shared-symmetric-key)
      * [- Encrypt and share some data](#--encrypt-and-share-some-data)
    * ["Receiving" atSign](#-receiving--atsign)
  * [Other resources](#other-resources)
<!-- TOC -->

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
- This document does not cover client onboarding. 
  - TODO: Create such a document

## Technical prerequisites
Ability to
- create RSA encryption public/private keypairs and use them to do encryption and decryption
- cryptographically sign data using a private key, and verify signatures using a public key
- create AES encryption keys and use them to do encryption and decryption
- establish a TLS socket connection, and be able to use it to send and receive data
- base64 encoding/decoding

## Specification
### "Sending" atSign
Given an already-onboarded client (i.e. access to authentication private key and encryption private key) for atsign 
`@alice`
#### - Lookup address of the `@alice` atServer
  - Establish TLS connection to root.atsign.org:64
  - Send `alice\n`
  - Expect response in form `<someDomain.example.com>:<port>`
#### - Authenticate to `@alice` atServer
  - Establish TLS connection 
  - do PKAM authentication
    - Send `from:@alice`
    - Expect response in form `data:<challengeText>`
    - Create a base64-encoded SHA256 signature of `challengeText` using the client's PKAM private key
      - Dart code example
      ```dart
        var key = RSAPrivateKey.fromString(privateKey);
        var sha256signature = key.createSHA256Signature(utf8.encode(challengeText) as Uint8List);
        var signature = base64Encode(sha256signature);
      ```
    - Send `pkam:<signature>`
    - Expect response `data:success` (or `error:<errorMessage>` if the signature could not be verified by the atServer
      using the corresponding PKAM public key)
#### - Fetch existing shared symmetric key if it has already been created
  - Send `llookup:shared_key.bob@alice` // This is a copy of the symmetric key which is encrypted with `@alice`'s 
    public encryption key
  - If response like `data:<base64EncodedEncryptedSharedKey>`
    - Decode from bas64, then decrypt using our private encryption key. The result will be a symmetric key, 
      base64-encoded. **NB** _Currently we use RSA asymmetric keypairs, and AES-256 symmetric keys. We will be 
      supporting other ciphers and modes in future._
    - base64-decode the symmetric key => $sharedAESKey
  - Else if response like `error:error:AT0015-key not found : @bob:shared_key@alice does not exist in keystore` we
    need to create a symmetric key and share it wih `@bob`
#### - Or create a new shared symmetric key
  - Create a new AES-256 symmetric key => $sharedAESKey and base64-encode it => $base64EncodedSharedAESKey
  - Save for our own use in future
    - Encrypt $base64EncodedSharedAESKey with our public encryption key and base64-encode the result => 
      $base64EncodedEncryptedForAliceSharedAESKey
    - Store in the atServer
      - Send `update:shared_key.bob@alice $base64EncodedEncryptedForAliceSharedAESKey` and handle the response
  - Share with `@bob`
    - Fetch `@bob`'s public encryption key
      - Send `plookup:publickey@bob`
      - Successful response `data:<bobsBase64EncodedPublicKey>`
    - Encrypt $base64EncodedSharedAESKey with bobsBase64EncodedPublicKey and base64-encode the result =>
      $base64EncodedEncryptedForBobSharedAESKey
    - Store in the atServer
      - Send `update:ttr:86400:@bob:shared_key@alice $base64EncodedEncryptedForBobSharedAESKey` and handle the 
        response
#### - Encrypt and share some data
  - Encrypt your $data with $sharedAESKey and base64-encode the result => $base64EncodedEncryptedData
    - We currently use the CTR (aka SIC) mode of the AES cipher, with PKCS7Padding. Java example:
      ```java
      public String aesEncryptToBase64(String clearText, String keyBase64, byte[] iv) {
          SecretKey key = _aesKeyFromBase64(keyBase64);
          Cipher cipher = Cipher.getInstance("AES/SIC/PKCS7Padding", "BC");
          cipher.init(Cipher.ENCRYPT_MODE, key, iv);
          byte[] encrypted = cipher.doFinal(clearText.getBytes());
          return Base64.getEncoder().encodeToString(encrypted);
      }
      ```
  - Send `update:<optional metadata attributes:>@bob:some.key_name.in.some.namespace@alice $base64EncodedEncryptedData` 
    and handle the response

### "Receiving" atSign
- PKAM authenticate
- lookup the data which `@alice` stored above at `@bob:some.key_name.in.some.namespace@alice`
  - Send `lookup:some.key_name.in.some.namespace@alice` // NB do not include `@bob:`
  - Successful response will be `data:$base64EncodedEncryptedData`
- retrieve the base64-encoded shared symmetric key by looking up `@bob:shared_key@alice`
  - Send `lookup:shared_key@alice` // NB do not include `@bob:`
  - Successful response will be `data:$base64EncodedEncryptedForBobSharedAESKey`
  - base64-decode $base64EncodedEncryptedForBobSharedAESKey => $encryptedForBobSharedAESKey
  - decrypt $encryptedForBobSharedAESKey using Bob's private encryption key
  - base64-decode the result, and construct an AES key
- base64-decode the $base64EncodedEncryptedData, and decrypt it using the shared symmetric key. Java example:
  ```java
  public static String aesDecryptFromBase64(String cipherTextBase64, String keyBase64, byte[] iv) {
      SecretKey key = _aesKeyFromBase64(keyBase64);
      Cipher cipher = Cipher.getInstance("AES/SIC/PKCS7Padding", "BC");
      cipher.init(Cipher.DECRYPT_MODE, key, iv);
      byte[] decrypted = cipher.doFinal(Base64.getDecoder().decode(cipherTextBase64));
      return new String(decrypted);
  }
  ```
## Other resources