# atProtocol Specification

\

| **Subject**   | atProtocol specification|
| ------------- | ------------------------|
| **Author(s)** | Colin Constable, Kevin Nickels, Jagannadh Vanghuri |
| | Gary Casey, Chris Swan |
| **Revision**  | v0.2.1 (draft) |
| **Date**      | Dec, 5, 2023  |

\

## atDirectory

The atDirectory provides a lookup of where an atServer for an atsign is
running. This is similar to a DNS server.

When asking an atDirectory for the lookup of a particular atSign the
atDirectory should respond with a null if the name does not exist and if the
name exists the DNS name or address of the atServer and the IP port number
for that atSign should be returned.

**Response:**

`<host>:<port>`

The atDirectory only has one verb - `@exit` and all other inputs are
considered to be lookup requests.

## atServer

An atServer is where an atSign user's personal data should be stored.
One interacts with an atServer using the verbs exposed by the protocol.

An atServer should have 4 major sub components:

1. Key Store
2. Commit Log
3. Access Log
4. Notification Log

Verbs described in the document should be used to create, update, delete,
and retrieve information from the above sub components.

### 1. Key Store

Key store is a place where user data in an atServer should be saved as key
and value pairs. Apart from the value, an atSign user should be able to add
certain metadata for a key.

#### **Key**

A key in the atProtocol can be formed by using any alphanumeric and special
characters (UTF-8) excluding "@", ":" and a white space (" "). A key in an
atServer can be any of the following 5 types:

1. Public Key

   * A public key is a key which can be looked up by any atSign owner.
   * A public key should be part of the _scan_ verb result.
   * Format of the public key should be **public::<@sign>**.

   **Example:**

   `public:location@alice`

   > The owner of the atServer should be allowed to update or delete the
   > value of a public key.

2. Shared Key

   * A user key can only be looked up by an atSign owner with whom the data
   has been shared.
   * A user key should be part of the _scan_ verb result only for the user
   who created it and the specific user it has been shared with.
   * Format of the key shared with someone else should be
   **\<Shared with @sign>::\<Created by @sign>**

   **Example:**

   `@bob:phone@alice`

   > Note: Above Key should be part of scan verb result for only @alice and
   > @bob
&nbsp;
   > The owner of the atServer should be allowed to update or delete the
   > value of a user key.

3. Internal Key

   * Internal keys start with an underscore(\_) and are not displayed in scan
   results. Internal keys can be looked up only by the owner of the atServer.

4. Cached Key

   * A cached key is a key that was originally created by another atSign user
   but is now cached on the atServer of another user's atSign as he/she was
   given permission to cache it.
   * A cached key should be listed in the _scan_ verb result for the atSign
   user who cached it.
   * Format of the key shared with someone else should be
   **cached:\<Shared with @sign>::\<Created by @sign>**

   **Example:**

   `cached:@bob:phone@alice`

   > The user who has cached the key should not be allowed to update the
   > cached key.
&nbsp;
   > An atSign owner who has created and shared the key should be allowed to
   > update a cached key, and if the "autoNotify" config parameters is set to
   > true, the updated value should be notified (please refer to the `notify`
   > verb) and the cached key updated with the new value.
&nbsp;
   > If the user who originally shared the keys set the CCD (Cascade delete)
   > to true, the cached key will be deleted when the original key is deleted.

#### **Value**

Text or binary values can be saved in an atServer. The size of the value saved
in an atServer is bound by the config parameter "maxBufferSize".

> A user should be made aware of this limitation by using the `stats` verb.
&nbsp;
> If a binary value is being saved on an atServer, the "isBinary" attribute
> on the metadata should be set to true by the convention.

1. Reference Value

   An atServer should support referencing another key's value.

   A reference value should be in the format "atsign://".

   For example, 'phone@bob(key)' is 1234 (value). Now another key called
   altPhone@bob can refer to phone@bob by referencing it as altPhone@bob = atsign://phone@bob.

   When the user does a lookup on the key that contains a reference, the
   atServer should return a fully resolved value.

2. Metadata

   Metadata of a key should describe the following properties of the value
   being inserted.

   | **Meta Attribute** | **Auto create?** | **Description**                                                                                                                |
   | ------------------ | ---------------- | ------------------------------------------------------------------------------------------------------------------------------ |
   | createdOn          | Yes              | Date and time when the key has been created.                                                                                   |
   | createdBy          | Yes              | atSign that has created the key                                                                                                |
   | updatedOn          | Yes              | Date and time when the key has been last updated.                                                                              |
   | sharedWith         | No               | atSign of the user with whom the key has been shared. Can be null if not shared with anyone.                                   |
   | ttl                | No               | Time to live in milliseconds.                                                                                                  |
   | expiresOn          | Yes              | A Date and Time derived from the ttl (now + ttl). A Key should be auto deleted once it expires.                                |
   | ttb                | No               | Time to birth in milliseconds.                                                                                                 |
   | availableFrom      | Yes              | A Date and Time derived from the ttb (now + ttb). A Key should be only available after availableFrom.                          |
   | isCached           | No               | True if the key can be cached by another atSign user.                                                                          |
   | ttr                | No               | Time in milliseconds after which the cached key needs to be refreshed. Ttr of -1 indicates that the key can be cached forever. |
   | refreshAt          | No               | A Date and Time derived from the ttr. The time at which the key gets refreshed.                                                |
   | ccd                | No               | Indicates if a cached key needs to be deleted when the atSign user who has originally shared it deletes it.                    |
   | isBinary           | No               | True if the value is a binary value.                                                                                           |
   | isEncrypted        | No               | True if the value is encrypted                                                                                                 |

### 2. Commit Log

An atServer should record any create, update and delete operations in a
commit log. The Commit Log should record these operations with a unique commit
id so that users of the atServer can lookup operations that happened on or
after a given commit id.

An atServer should provide a way to compact the Commit Log based on time and
size.

### 3. Access Log

An atServer should record the following user actions: user login, user
authentication, and lookup. The Access Log should record these operations so
that users of the atServer can retrieve various statistics such as the most
visited atSign or most visited keys.

An atServer should provide a way to compact the Access Log based on time and
size.

### 4. Notification Log

An atServer should record any notifications that have been received and sent.
Please check the `notify` verb specification for details on how a notification
should be sent.

An atServer should provide a way to compact the Notification Log based on time
and size.

## Standard Keys

An atServer should have the following standard keys:

| **Key**                    | **Description**                                               |
| -------------------------- | ------------------------------------------------------------- |
| public:publickey@          | Public key used by other atSigns for encryption.              |
| public:signing\_publickey@ | Public key used on a pol handler to verify a signed challenge |
| @signing\_privatekey@      | Private key used to sign a challenge on a pol request         |
| :shared\_key@              | Symmetric key used to encrypt/decrypt self atSign data        |

## Configuration Parameters

An atServer should honor the following configuration parameters.

| **Key**                          | **Valid Values**     | **Description**                                                                                                                                                          |
| -------------------------------- | -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **autoNotify**                   | true/false           | If set to true, an atServer should automatically notify another atSign user when a key has been shared with them. Please refer to the _notify_ verb spec for details. |
| **bufferLimit**                  | Number of bytes      | Maximum size of a value for a key that can be transferred to an atServer                                                                                                 |
| **inbound\_max\_limit**          | An Integer           | Maximum number of inbound connections that an atServer can accept                                                                                                         |
| **outbound\_max\_limit**         | An Integer           | Maximum number of outbound connections that an atServer can make to another atServer                                                                                     |
| **inbound\_idle\_time\_millis**  | Time in milliseconds | Maximum time the inbound connection can be active                                                                                                                        |
| **outbound\_idle\_time\_millis** | Time in milliseconds | Maximum time the outbound connection can be active.                                                                                                                      |

## Block List

A user of the atServer should be able to decide who is allowed to connect to
an atServer. The `config` verb should be used to configure this. Once added,
an atServer should honor the list at the time of accepting new connections from
an atSign owner using the `from` verb.

## Verbs

### The `from` verb

**Synopsis:**

The `from` verb is used to tell an atServer whom you claim to be.

**Syntax:**

Following regex represents the syntax of the `from` verb:

`r'^from:(?<@sign>@?[^@\s]+$)'`

**Example:**

`from:alice`

**Response:**

If the user who is trying to connect is the owner of the atServer, then the
`from` verb should respond with the following response.

`data:<sessionId@atSign:uuid>`

e.g:

`data:_4af24c03-d732-48f8-a9a2-570e8fb6a01c@alice:d6cac849-9c29-42b0-b0c5-493db62728b9`

If the user who is trying to connect is not the owner of the atServer, then the
`from` verb should respond with the following response.

`proof:<sessionid>@<@sign>:<UUID>`

If the user is not allowed to connect to the atServer, then it should respond
back with the following error and close the connection to the server.

`error:AT0013-Connection Exception`

**Description:**

The `from` verb is used to tell the atServer what atSign you claim to be. With
the `from` verb, one can connect to one's own atServer or someone else's
atServer. In both cases, the atServer responds back with a challenge to prove
that you are who you claim to be. This is part of the authentication mechanism
of the atProtocol.

This authentication mechanism varies based on whether you are connecting to
your own atServer (cram) or someone else's atServer (pol).

**Options:**

| Option    | Required | Description                       |
| --------- | -------- | --------------------------------- |
| `<@sign>` | Yes      | The atSign you are claiming to be |

Required: Yes

Description: atSign with which you are connecting to an atServer.

### The `cram` verb

**Synopsis:**

The `cram` verb is used to boostrap authenticate one's own self as an owner
of an atServer. It is intended to be used once until a set of PKI keys are
cut on the owner's mobile device and from then on we use the `pkam` verb.

**Syntax:**

The following regex represents the syntax of the `cram` verb:

`r'^cram:(?<digest>.+$)'`

**Example:**

`cram:<digest>`

**Response:**

If the user gets the challenge right, the prompt should change to the atSign
of the user.

`<@sign>@`

If the user gets the cram authentication wrong, then it should respond back
with the following error and close the connection to the server.

`error:AT0401-Client authentication failed`

**Description:**

The `cram` verb follows the `from` verb. As an owner of the atServer, you
should be able to take the challenge thrown by the `from` verb and encrypt
using the shared key that the server has been bound with. Upon receiving the
`cram` verb along with the digest, the server decrypts the digest using the
shared key and matches it with the challenge. If they are the same, then the
atServer lets you connect to the atServer and changes the prompt to your
atSign.

**Options:**

| Option     | Required | Description         |
| ---------- | -------- | ------------------- |
| `<digest>` | Yes      | encrypted challenge |

### The `pkam` verb

**Synopsis:**

The `pkam` verb is used to authenticate one's own self as an owner of an
atServer using a PKI style authentication.

**Syntax:**

Following regex represents the syntax of the `pkam` verb:

`^pkam:(?<signature>.+$)`

**Response:**

If the user gets the challenge right, the prompt should change to the atSign
of the user.

`<@sign>@`

If the user gets the pkam authentication wrong then it should respond back
with the following error and close the connection to the server.

`error:AT0401-Client authentication failed`

**Description:**

The `pkam` verb follows the `from` verb. As an owner of the atServer, you
should be able to take the challenge thrown by the `from` verb and encrypt
using the private key of the RSA key pair with what the server has been bound
with. Upon receiving the `cram` verb along with the digest, the server
decrypts the digest using the public key and matches it with the challenge.
If they are the same then the atServer lets you connect to the atServer and
changes the prompt to your atSign.

**Options:**

| Option     | Required | Description         |
| ---------- | -------- | ------------------- |
| `<digest>` | Yes      | encrypted challenge |

### The `pol` verb

**Synopsis:**

The `pol` verb is part of the `pkam` process to authenticate oneself while
connecting to someone else's atServer. The term 'pol' means 'proof of life'
as it provides a near realtime assurance that the requestor is who it claims
to be.

**Syntax:**

Following regex represents the syntax of the `pol` verb:

`r'^pol$'`

**Response:**

If the user gets the challenge right the prompt should change to the atSign
of the user.

`<@sign>@`

If the user gets the cram authentication wrong then it should respond back
with the following error and close the connection to the server.

`error:AT0401-Client authentication failed`

**Description:**

The `pol` verb follows the `from` verb. 'pol' indicates another atServer that
the user who is trying to connect is ready to authenticate themself. For
example, if @bob is trying to connect to @alice, @bob would take the key and
value from the proof response of the verb and create a public key and value
which then can be looked up by @alice. After @alice looks up @bob's atServer
@alice's atServer should change the prompt to @bob.

**Options:**

NA

### The `scan` verb

**Synopsis:**

The scan verb is used to see the keys in an atSign's secondary server.

**Syntax:**

Following regex represents the syntax of the `scan` verb:

`r'^scan$|scan(:showhidden:(?<showhidden>true|false))?(:(?<forAtSign>@[^:@\s]+))?( (?<regex>\S+))?$'`

**Response:**

`data:[<keys>]`

**Description:**

The atServer should return the keys within the atServer if the scan verb
executed succesfully.

The atServer will respond accordingly to whether the atSign is authenticated
or not.

**Options:**

| Option         | Required | Description                                |
| -------------- | -------- | ------------------------------------------ |
| `<showhidden`> | No       | If true, will show hidden internal keys    |
| `<forAtSign>`  | No       | Filter keys that are created by the atSign |

### The `update` verb

**Synopsis:**

The `update` verb is used to insert key/value pairs into a Key Store. An
update can only be run by the owner of an atServer on his/her own atServer.

**Syntax:**

Following regex represents the syntax of the `update` verb:

`r'^update:(?:ttl:(?<ttl>\d+):)?(?:ttb:(?<ttb>\d+):)?(?:ttr:(?<ttr>(-?)\d+):)?(ccd:(?<ccd>true|false):)?((?:public:)|(@(?<for@sign>[^@:\s]-):))?(?<atKey>[^:@]((?!:{2})[^@])+)(?:@(?<@sign>[^@\s]-))? (?<value>.+$)'`

**Example:**

Put a key/value pair into the atServer with key location@bob and value bob's
location value. This operation will create a new key if it does not already
exist. If it already exists, it will overwrite the existing value.

`update:location@bob bob's location value`

Put a key/value pair into the atServer with key location@bob and value bob's
location value but key expires in 10 minutes. The time to live of this key is
10 minutes.

`update:ttl:600000:location@bob bob's location value but key expires in 10 minutes`

Put a shared key/value pair into the atServer with key @alice:phone@bob
(shared with @alice and shared by @bob) with value bob's phone number shared
to @alice.

`update:@alice:phone@bob bob's phone number shared to @alice`

**Response:**

The atServer should return the commit id from Commit Log if the update is
successful.

`data:<CommitId>`

If the user provides the invalid update command, then it should respond with
the following error and close the connection to the server.

`error:AT0003-Invalid Syntax`

**Description:**

The `update` verb should be used to perform create/update operations on the
atServer. The `update` verb requires the owner of the atServer to authenticate
themself to the atServer using `from` and `cram` verbs.

If a key has been created for another atSign user, the atServer should honor
"autoNotify" configuration parameter.

**Options:**

| Option       | Required                                                      | Description                                                                                                                                                                                     |
| ------------ | ------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `<ttl>`      | No                                                            | Time to live in milliseconds                                                                                                                                                                    |
| `<ttb>`      | No                                                            | Time to birth in milliseconds                                                                                                                                                                   |
| `<ttr>`      | No                                                            | Time to refresh in milliseconds. ttr > -1 is a valid value which indicates that the user with whom the key has been shared can keep it forever and the value for this key won't change forever. |
| `<ccd>`      | No                                                            | A value of "true" indicates that the cached key needs to be deleted when the atSign user who has originally shared it deletes it.                                                               |
| `<for@sign>` | Yes (Not required when the key is a public key or a self key) | atSign of the user with whom the key has been shared                                                                                                                                            |
| `<@sign>`    | Yes                                                           | atSign of the owner of the key                                                                                                                                                                  |
| `<value>`    | Yes                                                           | Value for the key                                                                                                                                                                               |

### The `update:meta` verb

**Synopsis:**

The `update:meta` verb should be used to update the metadata of a key atSign
user without having to send or save the value again.

**Syntax:**

Following is the regex for the `update:meta` verb

`^update:meta:((?:public:)|((?<forAtSign>@?[^@\s]-):))?(?<atKey>((?!:{2})[^@])+)@(?<atSign>[^@:\s]-)(:ttl:(?<ttl>\d+))?(:ttb:(?<ttb>\d+))?(:ttr:(?<ttr>\d+))?(:ccd:(?<ccd>true|false))?(:isBinary:(?<isBinary>true|false))?(:isEncrypted:(?<isEncrypted>true|false))?$`

**Example:**

Update the metadata of key `phone@bob` setting `isBinary:true` while keeping
all other metadata as it is.

`update:meta:phone@bob:isBinary:true`

Update the metadata of the shared key `@alicephone@bob` (shared with `@alice`
& shared by `@bob`) setting `ttl:600000`, setting `isBinary:true` and
`isEncrypted:true` while keeping all other metadata as it is.

`update:meta:@alice:phone@bob:ttl:600000:isBinary:true:isEncrypted:true`

**Response:**

The atServer should return the commit id from Commit Log if the update is
successful.

`data:<CommitId>`

If the user provides the invalid update meta command, then it should respond
with the following error and close the connection to the server

`error:AT0003-Invalid Syntax`

**Description:**

The `update:meta` verb should be used to perform create/update operations on
the atServer. The `update:meta` verb requires the owner of the atServer to
authenticate themself to the atServer using `from` and `cram` verbs.

The atServer should allow creation of keys with null values. If a key has
been created for another atSign user, the atServer should honor "autoNotify"
configuration parameter.

**OPTIONS:**

| Option       | Required                                        | Description                                                                                                                       |
| ------------ | ----------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `<ttl>`      | No                                              | Time to live in milliseconds                                                                                                      |
| `<ttb>`      | No                                              | Time to birth in milliseconds                                                                                                     |
| `<ttr>`      | No                                              | Time to refresh in milliseconds                                                                                                   |
| `<ccd>`      | No                                              | A value of "true" indicates that the cached key needs to be deleted when the atSign user who has originally shared it deletes it. |
| `<for@sign>` | Yes (Not required when the key is a public key) | atSign of the user with whom the key has been shared                                                                              |
| `<@sign>`    | Yes                                             | atSign of the owner                                                                                                               |

### The `lookup` verb

**Synopsis:**

The `lookup` verb should be used to lookup the value shared by another atSign
user.

**Syntax:**

The following is the regex of the `lookup` verb:

`lookup:((?<operation>meta|all):)?(?<atKey>(?:[^:]).+)@(?<@sign>[^@\s]+)$`

**Example:**

Look up the value of the key `@<you>:phone@alice` (the key is created and
shared by @alice and lives on their atServer where the key is intentionally
shared with you).

`lookup:phone@alice`

Look up the metadata of the key `@<you>:phone@alice` (key shared by `@alice`
and shared with you).

`lookup:meta:phone@alice`

Look up both the value and the metadata of the key `@<you>:phone@alice`
(key shared by `@alice` and shared with you).

`lookup:all:phone@alice`

**Response:**

```json
data: 
{
    "createdBy":"@bob",
    "updatedBy":"@bob",
    "createdAt":"2020-10-21 09:46:48.982Z",
    "updatedAt":"2020-10-21 09:46:48.982Z",
    "availableAt":"null",
    "expiresAt":"null",
    "refreshAt":"2020-10-21 09:46:58.982Z",
    "status":"active",
    "version":0,
    "ttl":null,
    "ttb":null,
    "ttr":10000,
    "ccd":false,
    "isBinary":false,
    "isEncrypted":false
 }
```

If the operation is to lookup the metadata and the data together then the
result should be wrapped in a JSON in the following format:

`data:<Value and Metadata in a JSON>`

```json
data:
{
    "key":"@alice:country@bob",
    "data":"USA",
    "metaData":
    {
        "createdBy":"@bob",
        "updatedBy":"@bob",
        "createdAt":"2020-10-21 09:46:48.982Z",
        "updatedAt":"2020-10-21 09:46:48.982Z",
        "availableAt":"null",
        "expiresAt":"null",
        "refreshAt":"2020-10-21 09:46:58.982Z",
        "status":"active",
        "version":0,
        "ttl":null,
        "ttb":null,
        "ttr":10000,
        "ccd":false,
        "isBinary":false,
        "isEncrypted":false
    }
}
```

If the other atServer on which the lookup needs to be performed is down then
the atServer should return the following error and keep the connection alive.

`error:AT0007-atServer not found.`

If the lookup command is not valid, then the atServer should return the
following error and close the connection:

`error:AT0003-Invalid Syntax`

For whatever reasons, If the handshake with another atServer fails, then the
atServer should return the following error:

`data:AT0008-Handshake failure`

If the operation is not specified the atServer should just respond back with
the value saved by the user as is.

`data:<value>`

If the operation is to lookup the metadata only then the result should be
wrapped in a JSON in the following format:

`data:<Metadata in a JSON>`

**Description:**

The `lookup` verb should be used to fetch the value of the key shared by
another atSign user. If there is a public and user key with the same name
then the result should be based on whether the user is trying to lookup is
authenticated or not. If the user is authenticated then the user key has to
be returned, otherwise the public key has to be returned.

**Options:**

| Option        | Required | Description                                                                                             |
| ------------- | -------- | ------------------------------------------------------------------------------------------------------- |
| `<operation>` | No       | `meta` - returns the metadata of the AtKey, `all` - returns both the data and the metadata of the AtKey |
| `<atKey>`     | Yes      | the key to be looked up                                                                                 |
| `<@sign>`     | Yes      | the atSign owner of the key                                                                             |

### The `plookup` verb

**Synopsis:**

The `plookup` verb enables to lookup the value of the public key shared by
another atSign user.

**Syntax:**

Following is the regex of the `plookup` verb:

`^plookup:((?<operation>meta|all):)?(?<atKey>[^@\s]+)@(?<@sign>[^@\s]+)$`

**Example:**

Look up the value of the key `public:publickey@alice` (the key is created and
shared by `@alice` and lives on their atServer where the key is public).

`plookup:publickey@alice`

Look up the metadata of the public key

`plookup:meta:publickey@alice`

Look up both the value and the metadata of the public key

`plookup:all:publickey@alice`

Look up the value and metadata of the public key while bypassing the cache
(i.e. the value will be fetched directly from the atServer instead of first
checking for a cached key on your secondary).

`plookup:bypassCache:true:all:publickey@alice`

**Response:**

The atServer should return the value or metadata or the value and metadata
together based on the option specified.

The response structure should be exactly the same as the `lookup` verb.

If the other atServer on which the `lookup` needs to be performed is not
available, then the atServer should return the following error and keep the
connection alive.

`error:AT0007- Secondary Server not found.`

If the `lookup` command is not valid, then the atServer should return the
following error and close the connection:

`error:AT0003-Invalid Syntax`

**Description:**

The `plookup` verb should be used to fetch the value of the public key shared
by another atSign user.

**Options:**

| Option        | Required | Description                                                                                             |
| ------------- | -------- | ------------------------------------------------------------------------------------------------------- |
| `<operation>` | No       | `meta` - returns the metadata of the AtKey, `all` - returns both the data and the metadata of the AtKey |
| `<atKey>`     | Yes      | the key to be looked up                                                                                 |
| `<@sign>`     | Yes      | the atSign owner of the key                                                                             |

### The `llookup` verb

**Synopsis:**

The `llookup` verb should be used to look up one's own atServer and this
should return the value as is (i.e. without any resolution).

**Syntax:**

The Following is the regex of the `llookup` verb:

`^llookup:((?<operation>meta|all):)?(?:cached:)?((?:public:)|(@(?<for@sign>[^@:\s]-):))?(?<atKey>[^:]((?!:{2})[^@])+)@(?<@sign>[^@\s]+)$`

**Example:**

Lookup the value of a public key that lives on your atServer

`llookup:public:publickey@<you>`

Lookup both the value and the metadata of a self key that lives on your
atServer

`llookup:all:phone@<you>`

Lookup both the value and the metadata of a shared key (that is shared with
`@alice` and created by `@<you>`)

`llookup:all:@alice:phone@<you>`

**Response:**

The atServer should return the value or metadata or the value and metadata
together based on the option specified.

The response structure should be exactly the same as the `lookup` verb.

If the other atServer on which the lookup needs to be performed is down then
the atServer should return the following error and keep the connection alive.

`error:AT0007- Secondary Server not found.`

> If the lookup command is not valid, then the atServer should return the
> following error and close the connection:

`error:AT0003-Invalid Syntax`

**Description:**:

The `llookup` verb should be used to fetch the value of the key in the owners
atServer store as is without resolving it. For example if a key contains a
reference as a value, the `lookup` verb should resolve it to a value whereas
llookup should return the value as is.

**Options:**

| Option        | Required | Description                                                                                             |
| ------------- | -------- | ------------------------------------------------------------------------------------------------------- |
| `<operation>` | No       | `meta` - returns the metadata of the AtKey, `all` - returns both the data and the metadata of the AtKey |
| `<atKey>`     | Yes      | the key to be looked up                                                                                 |
| `<@sign>`     | Yes      | the atSign owner of the key                                                                             |

### The `delete` verb

**Synopsis:**

The `delete` verb should be used to delete an atKey in the atServer. Only
authenticated atSigns can use the `delete` verb.

**Syntax:**

The following is the regex of the `delete` verb:

`^delete(:priority:(?<priority>low|medium|high))?(:cached)?(:((?<publicScope>public)|(@(?<forAtSign>[^:@\s]+))))?:(?<atKey>(([^:@\s]+)|(at_secret)))(@(?<atSign>[^:@\s]+))?$`

**Example:**

`delete:@alice:test.namespace@bob`

Deletes an atKey named "@alice:test.namespace@bob" from the atServer.

**Response:**

The atServer should return the commit id.

```text
data:<commitId>
```

**Description:**

The `delete` verb only can be used for AtKeys you own. Deleting a cached key
will not delete the original copy of the AtKey. Deleting an AtKey that does
not exist will still respond with a commit id.

**Options:**

| Option       | Required | Description                                                               |
| ------------ | -------- | ------------------------------------------------------------------------- |
| `:cached:`   | No       | Include `:cached:` if the key you are deleting is cached in your atServer |
| `:public:`   | No       | Include `:public:` if the key you are deleting is a public key            |
| `<for@sign>` | No       | The key's sharedWith atSign                                               |
| `<atKey>`    | Yes      | Key name of the AtKey                                                     |
| `<@sign>`    | Yes      | The key's sharedBy atSign                                                 |

### The `stats` verb

**Synopsis:**

The `stats` verb should be used to get the statistics of an atSign.

**Syntax:**

Following is the regex of the `stats` verb

`stats(?<statId>:((?!0)\d+)?(,(\d+))-)?`

**Example:**

`stats`

**Response:**

If the user gives stats all the statistics will be returned as JSON. Following
statistics are provided:

1. `activeInboundConnections`
2. `activeOutboundConnections`
3. `lastCommitId`
4. `secondaryStorageSize`
5. `topAtSigns`
6. `topKeys`

**Example:**

`data: [{"id":"1","name":"activeInboundConnections","value":"1"}, {"id":"2","name":"activeOutboundConnections","value":"0"}, {"id":"3","name":"lastCommitID","value":"1"}, {"id":"4","name":"secondaryStorageSize","value":12560}, {"id":"5","name":"topAtSigns","value":{"@bob":1}}, {"id":"6","name":"topKeys","value":{"publickey@alice":1}}]`

Individual statistics can be retrieved using the respective Id.

```json
@alice@stats:1
data: [{"id":"1","name":"activeInboundConnections","value":"1"}]
```

### The `sync` verb

**Synopsis:**

The `sync` verb enables to synchronize the keys between the local atServer
and remote atServer.

**Syntax:**

Following is the regex:

`sync:(?<from_commit_seq>[0-9]+$|-1)`

**Response:**

The `sync` verb returns a json array of the commit entries from the given
commit id to the current commit id. Further, The `sync` verb accepts -1 as
argument which returns all the commit entries.

```json
data:[{"atKey":"@bob:phone@alice","operation":"+","opTime":"2020-10-26 11:57:43.732","commitId":0,"value":"12345","metadata":{"ttr":"36000000","ccd":"false"}},
{"atKey":"@bob:shared_key@alice","operation":"-","opTime":"2020-10-26 09:44:54.382219Z","commitId":1}]
```

### The `notify` verb

**Synopsis:**

The `notify` verb enables us to notify the atSign user of some data event.

**Syntax:**

The Following is the regex for the `notify` verb

```text
notify:((?<operation>update|delete):)?(ttl:(?<ttl>\d+):)?(ttb:(?<ttb>\d+):)?(ttr:(?<ttr>(-)?\d+):)?(ccd:(?<ccd>true|false):)?(@(?<forAtSign>[^@:\s]-)):(?<atKey>[^:]((?!:{2})[^@])+)@(?<atSign>[^@:\s]+)(:(?<value>.+))?
```

**Example:**

```json
notify:update:ttr:-1:@{RECIPIENT}:{KEY}.{NAMESPACE}@{SENDER}:{BASE64ENCODED_CYPHERTEXT}
```

**Example:**

Notify @alice that you have a shared key `@alice:test@<you>` with an updated
value waiting for them to lookup.

`notify:update:@alice:test@<you>`

Notify @alice that you have a shared key `@alice:test@<you>` that was deleted.

`notify:delete:@alice:test@<you>`

Notify @alice with a message my sample message to bob.

`notify:messageType:text:@<you>:my sample message to bob`

**Response:**

When a key is notified successfully, returns `data:{ID}` e.g.

```text
data:fccf2ddc-9316-4302-a11b-3dd214857431
```

**Description:**

When an atSign owner notifies the key to another atSign owner, an entry has to
be created in received notifications list on the user who has shared the key
and an entry has to be created in sent notifications list on the user to whom
the key is to be notified. When auto notify is set to true, when a key is
created/updated and deleted notification is triggered to another atSign user.

### The `notify:list` verb

**Synopsis:**

Notify list returns a list of notifications.

**Syntax:**

Following is the regex

`notify:(list (?<regex>.-)|list$)`

**Example:**

`notify:list`

**Response:**

If the user is the owner, returns a list of received notifications. If a user
is pol authenticated user, returns a list of sent notifications

`data:[{"id":"0e5e9e89-c9cb-423b-8972-8c5487215990","from":"@alice","to":"@bob","key":"@bob:phone@alice","value":12345,"operation":"update","epochMillis":1603714122636}]`

### The `notify:remove` verb

**Synopsis:**

Notify remove removes a notification from the notification log.

**Syntax:**

Following is the regex

`notify:(remove:(?<notificationId>[^:]+$))`

**Example:**

Remove a notification that you received that has id
`0e5e9e89-c9cb-423b-8972-8c5487215990`.

`notify:remove:0e5e9e89-c9cb-423b-8972-8c5487215990`

**Response:**

If successful, returns

`data:success`

**Description:**

Deletes a notification from the notificaiton log. Note that this is different
from `notify:delete`, which sends a notification relating to the deletion of
a key.

**Options:**

| Option             | Required | Description                |
| ------------------ | -------- | -------------------------- |
| `<notificationId>` | Yes      | The id of the notification |

### The `monitor` Verb

**Synopsis:**

The `monitor` verb streams received notifications.

**Syntax:**

Following is the regex

`^monitor$|^monitor ?(?<regex>.-)?)$`

**Example:**

`monitor`

`monitor @bob`

**Response:**

Returns a stream of notifications.

```json
@alice@monitor
notification: {"id":"773e226d-dac2-4269-b1ee-64d7ce93a42f","from":"@bob","to":"@alice","key":"@alice:phone@bob","value":null,"operation":"update","epochMillis":1603714720965}
```

**Description:**

The `monitor` verb accepts an optional parameter to filter the notifications
by passing filter criteria as regex to `monitor` verb.

**Options:**

| Option    | Required | Description                                                      |
| --------- | -------- | ---------------------------------------------------------------- |
| `<regex>` | No       | The regex to filter the notificaitons during the monitor session |

## Beta verbs

### The `info` Verb

**Synopsis:**

The `info` verb provides runtime information about the atServer.

Regex: `^info(:brief)?$`

**Examples:**

`info`

```json
data:{"version":"3.0.28","uptimeAsWords":"1 hours 35 minutes 29 seconds","features":[{"name":"noop:","status":"Beta","description":"The No-Op verb simply does nothing for the requested number of milliseconds. The requested number of milliseconds may not be greater than 5000. Upon completion, the noop verb sends 'ok' as a response to the client.","syntax":"^noop:(?<delayMillis>\\d+)$"},{"name":"info:","status":"Beta","description":"The Info verb returns some information about the server including uptime and some info about available features. ","syntax":"^info(:brief)?$"}]}
```

`info:brief`

```json
data:{"version":"3.0.28","uptimeAsMillis":5855295}
```

### The `noop` Verb

**Synopsis:**

The `noop` verb does nothing for up to 5 seconds before returning a
`data:ok` response.

Regex: `^noop:(?<delayMillis>\\d+)$`

**Examples:**

`noop:123`

After 123ms:

`data:ok`

`noop:5001`

```text
error:AT0022-Exception: noop:<durationInMillis> where the duration maximum is 5000 milliseconds
```

## Error Codes

| **Error Code** | **Error Message**                                     | **Description**                                                                                                                                         |
| -------------- | ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| AT0001         | Server exception                                      | Exception occurs when there is an issue while starting the server.                                                                                      |
| AT0002         | DataStore exception                                   | Exception occurs during keystore operations (GET/PUT/DELETE).                                                                                           |
| AT0003         | Invalid syntax                                        | Exception occurs if we give any invalid command to the server.                                                                                          |
| AT0004         | Socket error                                          | Exception occurs when socket connection to secondary cannot be established.                                                                             |
| AT0005         | Buffer limit exceeded                                 | This exception occurs when input/output message size reaches the maximum limit configured in the server.                                                |
| AT0006         | Outbound connection limit exceeded                    | Exception occurs when the number of open connections to other atServers reaches the maximum limit configured.                                           |
| AT0007         | atServer not found                                    | Exception occurs when an atServer tries to connect to another atServer which is not available in the atDirectory or not yet instantiated.               |
| AT0008         | Handshake failure                                     | This exception is for any exception during the handshake process of two atServers.                                                                      |
| AT0009         | UnAuthorized client in the request                    | UnAuthorized Exception will occur when an unsuccessful handshake happens between two atServers.                                            |
| AT0010         | Internal server error                                 | This is for any server related errors.                                                                                                                  |
| AT0011         | Internal server exception                             | This exception is used for any server related exceptions.                                                                                               |
| AT0012         | Inbound connection limit exceeded                     | This exception will occur when the number of active clients reaches the maximum limit configured.                                                       |
| AT0401         | Client authentication failed                          | This exception occurs when client authentication fails or client tries to execute any verb which needs authentication before successful authentication. |
| AT0013         | Connection Exception                                  | This will occur when a blocked user tries to connect to the atServer.                                                                                   |
| AT0014         | Unknown AtClient exception                            | This exception will be thrown while performing any operations(Get/update/delete) using AtClient SDK.                                                    |
| AT0015         | Key not found                                         | This exception will be thrown when the key is not available for encryption/decryption.                                                                  |
| AT0021         | Unable to connect to atServer                         | This exception will occur when we are unable to connect to an atServer.                                                                                 |
| AT0022         | noop: where the duration maximum is 5000 milliseconds | A noop command has been issued with a duration outside of 0-5000ms                                                                                      |

Glossary

> atProtocol (Pronounced, at protocol)
&nbsp;
> atSign (Pronounced, at sign) atSign is a unique name that a user gets when
> enrolled with atsign.com
&nbsp;
> atDirectory
&nbsp;
> atServer
&nbsp;
> Verb
&nbsp;
> Public Key
&nbsp;
> Private Key
&nbsp;
> Shared Secret
&nbsp;
> Default Keys
&nbsp;
> Key
&nbsp;
> Value
&nbsp;
> Metadata
&nbsp;
> Commit Log
&nbsp;
> Access Log
&nbsp;
