# PKAMs per app per device

* **Status:** Draft
* **Created:** 2023-01
* **Changelog:**
  * 2023-04-03 Added mermaid sequence diagrams of current and proposed new flows
* **Objective:** Define protocol interactions required to have different PKAMs
  per app+device

<!-- TOC -->
* [PKAMs per app per device](#pkams-per-app-per-device)
  * [Context & Problem Statement](#context--problem-statement)
  * [Goals](#goals)
    * [Non-goals](#non-goals)
  * [Other considerations](#other-considerations)
  * [Proposal Summary](#proposal-summary)
  * [Proposal In Detail](#proposal-in-detail)
    * [Initial bootstrap enrollment](#initial-bootstrap-enrollment)
      * [Overview](#overview)
      * [Description](#description)
      * [Sequence diagram](#sequence-diagram)
    * [All subsequent enrollments](#all-subsequent-enrollments)
      * [Overview](#overview-1)
      * [Description](#description-1)
      * [Sequence diagram](#sequence-diagram-1)
    * [Other details](#other-details)
  * [Appendix - current flows](#appendix---current-flows)
    * [First client onboarding](#first-client-onboarding)
    * [Subsequent client onboarding](#subsequent-client-onboarding)
<!-- TOC -->

## Context & Problem Statement
Current PKAM (Public Key Authentication Method) supports only a single keypair.
- Key pairs are created by first device/app on the edge.
- Device/app holds the private key; the public key is placed on the secondary server
- Access is “all or nothing” - access to the private key delivers access to everything
- atSign owners are asked to manage/store keys, safely.
  - This is always tricky
  - Inevitable that atSign owners will sometimes accidentally leak keys
- Apps require the atSign owner to give the keys to the app
- Authentication flow, given an existing PKAM keypair, is
  - App sends `from:@alice` to `@alice`'s atServer
  - atServer responds with a challenge `data:<challenge>`
  - App signs the challenge with its PKAM private key, sends `pkam:<signature>`
  - atServer verifies the signature against the PKAM public key which it knows

## Goals
- Limit likelihood of compromise of private keys
  - Limit private keys required by apps to the bare minimum - a single keypair whose
    private key may be held on a TPM / secure element
  - No more exporting of keys files for import by other apps+devices
  - Easy-to-use management of app access and app namespace permissions
- Limit blast radius if private keys are compromised
  - Apply access controls to apps' use of the atSign's namespace
  - Easy-to-use modification / revocation of app access and app namespace permissions

### Non-goals

## Other considerations

## Proposal Summary
This proposal is based upon, and expands upon, [this summary proposal](https://docs.google.com/presentation/d/1Yo30hVGfasBEZqeYGNlhhuqLbLLE-l6Qm8RpbBGvNBs/edit#slide=id.gd1dd4acffa_0_5)
- APKAM (Application PKAM) - a keypair per app+device
- MPKAM - an APKAM which has access to the `.__manage` namespace
- APKAM enrollment requests can be approved only by apps which have an MPKAM
- Device/app stores the minimum amount of information
  - unique enrollment ID
  - keys
    - the APKAM keypair
      - the private key may be held on a TPM
    - an APKAM symmetric key specific to this enrollment
      - This is required because
        - the approving app needs to be able to send private key(s) to the
          enrolling app
        - the APKAM private key may be on a TPM which does not support
          using the private key for decryption but only for signing
- An enrollment interaction flow will
  - Allow new apps to request that their app+device be approved and have
    their APKAM public key stored on the atServer
  - Allow requests to be approved or denied by another existing app with the
    appropriate authority
  - Make encryption keypairs' private keys and symmetric keys available as
    appropriate to the newly enrolled app by encrypting with the APKAM
    **symmetric** key
- After enrollment, an app needs to be able to
  - Authenticate with APKAM keypair and enrollment id
  - Fetch all keys which have been shared with this enrollment id
    - And decrypt those keys using the APKAM **symmetric** key
- There must be a way to revoke enrollment of a given APKAM
  - an enrolled app should be able to revoke its own enrollment
- Additions to `pkam` verb syntax
- New verb `enroll` for enrollment management
- New verb `keys` for management of (1) encryption keypairs (2) 'self' encryption keys

## Proposal In Detail
### Initial bootstrap enrollment
#### Overview
- Do CRAM and PKAM as done prior to APKAM
- Then follow up with an `enroll` request

#### Description
In addition to what is done now (CRAM auth, PKAM auth, cutting default 
encryption keypair and default 'self' encryption key), the client 
also
- generates an 'APKAM symmetric key' and encrypts it with default encryption 
  public key
- client stores two keys on the server via `enroll` request
  - default self encryption key - encrypted with APKAM symmetric key
  - default encryption private key - encrypted with APKAM symmetric key
- client only need to store their enrollmentID, APKAM private key and APKAM
  symmetric key - however, for backwards compatibility will store 
  those things in addition to everything that is in the current atKeys file 
  format

#### Sequence diagram
```mermaid
sequenceDiagram
    participant FirstClient
    participant Server

    note over FirstClient,Server: CRAM Authentication

    FirstClient->>Server: from:@alice
    Server->>Server: store digest <SHA512(${cramSecret}${serverChallenge})>
    Server-->>FirstClient: ${serverChallenge}
    FirstClient->>Server: cram:<SHA512(${cramSecret}${serverChallenge})>
    Server->>Server: fetch stored digest
    Server->>Server: Compare digests
    alt digests do not match
        Server-->>FirstClient: Authentication failed
        FirstClient->>FirstClient: Exit
    else digests match
        Server-->>FirstClient: Success
    end

    note over FirstClient,Server: Onboarding
    FirstClient->>FirstClient: Generate PKAM keypair (ideally on a secure element of some sort)
    FirstClient->>Server: Store PKAM public key
    Server->>Server: Store PKAM public key
    note over Server: New - mark this PKAM key as privileged to enrol subsequent clients
    Server->>Server: Mark this PKAM public key as privileged
    FirstClient->>FirstClient: Generate default encryption keypair    
    FirstClient->>FirstClient: Generate symmetric self encryption key (e.g AES key)
    note over FirstClient,Server: New
    FirstClient->>FirstClient: Generate APKAM symmetric key     
    FirstClient->>FirstClient: Encrypt default encryption private key with APKAM symmetric key - $encryptedDefaultPrivateEncryptionKey
    FirstClient->>FirstClient: Encrypt self encryption key with APKAM symmetric key - $encryptedDefaultSelfEncryptionKey
    FirstClient->>Server: enroll:request:$encryptedDefaultPrivateEncryptionKey:$encryptedDefaultSelfEncryptionKey         
    Server->>Server: Store encrypted default encryption private key e.g $enrollmentId.default_enc_private_key.__manage@alice
    Server->>Server: Store encrypted default self encryption keys e.g $enrollmentId.default_self_enc_key.__manage@alice
    FirstClient->>Server: Disconnect and attempt pkam with enrollmentId
    Server-->>FirstClient: Auth passed
    FirstClient->>Server: Store default encryption public key
    Server->>Server: Store default encryption public key
    FirstClient->>FirstClient: Store enrollmentId and apkam symmetric key(unencrypted) in atKeysFile
    FirstClient->>Server: Delete CRAM secret
    Server->>Server: Delete CRAM secret
    note over FirstClient: Client now only needs access to the enrollmentId,<br/>APKAM private key and APKAM symmetric key<br/> and may store them in atKeys file<br/> or keychain as appropriate 
```

### All subsequent enrollments
This is _**substantially**_ different from how things are now.

#### Overview
- An `enroll:request` command results in a keyStore entry being created in the
  `__manage` namespace and a notification being generated on the server and  
  delivered to apps which have permission to approve or deny the request
- Apps which have access can approve or deny the request

#### Description
- NewApp sends enroll request
  - atServer creates a private keyStore entry in the `.__manage` namespace. The key for
    the entry is `<enrollmentId>.new.enrollments.__manage@atSign`, where `<enrollmentId>` is
    some random id and the data stored is something like
      ```json
        {
          "sessionID": "<the session ID of the NewApp connection>",
          "appName":"<appName>",
          "deviceName":"<deviceName>",
          "namespaces": [
            {"ns":"one","ac": "r"},
            {"ns":"two","ac": "rw"},
            {"ns":"three","ac": "r"}
            ],
          "APKAMPublicKey":"APKAMPublicKey",
          "requestType": "newEnrollment",
          "approval": {"state":"requested"}
        }
      ```
  - atServer generates a notification for this keyStore entry. Only apps which have
    access to the `.__manage` namespace will receive this notification.
  - atServer responds to NewApp with the usual PKAM challenge `data:<challenge>`
  - NewApp tries `pkam`
    - If the enrollment has not yet been approved, get an error code for "Enrollment request not yet approved"
      and can retry `pkam` again
    - If the enrollment has been denied, get a fatal error code for "Enrollment request denied",
      and NewApp may no longer retry the `pkam`
    - Once the enrollment has been approved, then the response will be accepted
    - NewApp may then retrieve encryption private keys and self encryption keys
      - `keys:get:private`
      - `keys:get:self`
  - An already-enrolled app ('ExistingApp') with access to the `.__manage` namespace
    - Receives and decrypts the notification.
    - Display the request details, and ask the user to approve or deny it
    - **Approve:**
      - `enroll:approve:<enrollmentId>:<encryptedDefaultEncPrivateKey:<encryptedDefaultSelfEncryptionKey>`
      - atServer marks the enrollment request as `approved`
    - **Deny:**
      - `enroll:deny:<approvalID>`
      - atServer marks the enrollment request as `denied`
  - atServer will set timers to expire approval requests after a suitable configurable
    interval (e.g. 90 seconds). Expired approval requests will be deleted.
  - Upon startup, atServer will load all approval requests with approval state "requested",
    delete them if they have already passed the expiry interval, and set an appropriate expiry
    timer otherwise
  - When a request is approved, atServer stores the APKAMPublicKey in an entry with
    key name `public:appName.deviceName.pkam.__pkams.__public_keys`

#### Sequence diagram
```mermaid
sequenceDiagram
    participant NewClient
    participant Server
    participant ExistingPrivilegedClient

    note over NewClient,ExistingPrivilegedClient: Subsequent client onboarding
    NewClient->>NewClient: Generate APKAM keypair (ideally on a secure element of some sort)
    NewClient->>NewClient: Generate new APKAM symmetric key - $apkamSymmetricKey
    NewClient->>NewClient: Encrypt APKAM symmetric key with default encryption public key - $encryptedApkamSymmetricKey
    NewClient->>Server: from:@alice
    Server-->>NewClient: ${serverChallenge}
    NewClient->>Server: enroll:request<br/>:app:<appName><br/>:device:<deviceName><br/>:namespaces:<...><br/>:apkamPublicKey:<apkamPublicKey>:<br/>apkamSymmetricKey<encryptedApkamSymmetricKey<br/>
    Server->>ExistingPrivilegedClient: Send notification with enrollmentID and  $encryptedApkamSymmetricKey
    Server->>Server: Mark enrolment request PENDING
    Server->>ExistingPrivilegedClient: Approve or deny
    note over NewClient: Meanwhile, NewClient will try periodically to authenticate
    alt Pending
        note over NewClient,Server: While pending but not timed out, authentication will fail <br/>but may be reattempted
        NewClient->>Server: pkam:enrollmentId:<enrollmentId>:<PKAM private key SHA256Signature of ${serverChallenge}>
        Server->>NewClient: Authentication failed - approval PENDING
    else Denied
        note over NewClient,Server: If explicitly denied, authentication will fail permanently <br/>until a new enrolment request is sent
        ExistingPrivilegedClient->>Server: Denied
        Server->>Server: Mark enrolment request DENIED
        NewClient->>Server: pkam:enrollmentId:<enrollmentId>:<PKAM private key SHA256Signature of ${serverChallenge}>
        Server->>NewClient: Authentication failed - approval DENIED
    else Timeout
        note over NewClient,Server: If the approval request times out, authentication will fail permanently <br/>until a new enrolment request is sent
        NewClient->>Server: pkam:enrollmentId:<enrollmentId>:<PKAM private key SHA256Signature of ${serverChallenge}>
        Server->>Server: If timeout has expired, Mark enrolment request TIMED OUT
        Server->>NewClient: Authentication failed - approval request TIMED OUT
    else Approved
        note over NewClient,Server: If approved, authentication will succeed
        ExistingPrivilegedClient->>ExistingPrivilegedClient: Decrypt $encryptedApkamSymmetricKey <br/>with default encryption private key<br/> - $apkamSymmetricKey
        ExistingPrivilegedClient->>ExistingPrivilegedClient: Encrypt default encryption private key<br/> and default self encryption key<br/> with $apkamSymmetricKey
        ExistingPrivilegedClient->>Server: enroll:approve:<enrollmentId>:<encryptedDefaultEncPrivateKey>:<encryptedDefaultSelfEncryptionKey>
        Server->>Server: Mark enrolment request APPROVED
        NewClient->>Server: pkam:enrollmentId:<enrollmentId>:<PKAM private key SHA256Signature of ${serverChallenge}>
        Server->>Server: Verify signature using the PKAM public key presented in the enroll request earlier
        alt Verified
            Server->>NewClient: Authentication SUCCESS
            NewClient->>Server: keys:get:private
            NewClient->>NewClient: decrypt encryption private key with $apkamSymmetricKey
            NewClient->>Server: keys:get:self
            NewClient->>NewClient: decrypt self encryption key with $apkamSymmetricKey
            NewClient->>NewClient: write to atKeysFile - enrollmentId, APKAM public and private key, APKAM symmetric key
            
        else Not verified
            Server->>NewClient: Authentication FAILED
        end
    end
```

### Other details
- `info` verb will additionally include details of the APKAM's namespace access
- All existing verb implementations must change to respect APKAM namespace access controls
- `enroll` verb should be rate-limited
- `__global` namespace is ONLY used for storing globally accessible keys. It is
  not usable by any other verb lookup/update/delete/notify/etc
- Types of enrollment requests. Types are determined by the server
  - newEnrollment
  - overrideEnrollment (app wanting to enroll a new public key)
  - changeNamespaceAccess
  - revokeEnrollment
- MPKAM apps need access to all encryption private keys
  - If an app being enrolled requires __manage access, then share all encryption private keys with them
  - So they can share the relevant subset with other apps as they enroll
  - Corollary: When an encryption keypair is created in a namespace, it must be shared (1) with all apps which
    have access to the namespace (2) with all apps who have the MPKAM access (__shared namespace)

## Appendix - current flows

### First client onboarding
```mermaid
sequenceDiagram
    participant Client
    participant Server

    note over Client,Server: CRAM Authentication

    Client->>Server: from:@alice
    Server->>Server: store digest <SHA512(${cramSecret}${serverChallenge})>
    Server-->>Client: ${serverChallenge}
    Client->>Server: cram:<SHA512(${cramSecret}${serverChallenge})>
    Server->>Server: fetch stored digest
    Server->>Server: Compare digests
    alt digests do not match
        Server-->>Client: Authentication failed
        Client->>Client: Exit
    else digests match
        Server-->>Client: Success
    end

    note over Client,Server: Onboarding
    Client->>Client: Generate PKAM keypair
    Client->>Server: Store PKAM public key
    Server->>Server: Store PKAM public key
    Client->>Server: PKAM authentication
    Server-->>Client: Auth passed
    Client->>Server: Delete CRAM secret
    Server->>Server: Delete CRAM secret
    Client->>Client: Generate encryption keypair
    Client->>Server: Store encryption public key
    Server->>Server: Store encryption public key
    Client->>Client: Generate AES key for private data
    Client->>Client: Generate and store atKeys file
```
### Subsequent client onboarding
Use the PKAM keys from the atKeys file which was generated during first client onboarding

```mermaid
sequenceDiagram
    participant NewClient
    participant Server

    NewClient->>Server: from:@alice
    Server-->>NewClient: ${serverChallenge}
    NewClient->>Server: pkam:<PKAM private key SHA256Signature of ${serverChallenge}>
    Server->>Server: Verify signature using the stored PKAM public key
    alt Verified
        Server->>NewClient: Authentication SUCCESS
    else Not verified
        Server->>NewClient: Authentication FAILED
    end
```
