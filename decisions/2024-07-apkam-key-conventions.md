# Platform SDKs

* **Status:** Not Approved
* **Last Updated:** 2024-07-16
* **Objective:** Normalize the approach to creating APKAM keys for the user.

## Context & Problem Statement

Right now, we have no clear guidelines on how to name APKAM keys for the user.

If the keys are not named consistently, it will be difficult for users
 and apps to understand which keys are available and how to use them.

Introducing our `-k` flag in `at_activate enroll`.

Currently, we have the -k flag which allows the user to specify the key name
they want to use. This is useful for users who want to use a specific key
name, however for apps that read the keys is it not clear which is apkam
and which is a manager key.

## Goals

Create a consistent naming convention for APKAM keys.

### Non-goals

Specifying the key conventions as defaults in our documentation.

## Considered Options

* ### Remove the -k flag as a mandatory flag in at_activate enroll

Come up with default key name for APKAM keys. The user will still be able
to see which keys are for what using the `at_activate list` command

Such as:
* `@soccer0_{enrollment_id}_key.atKeys`
* `@soccer0_{hashed_namespace}_key.atKeys`

* ### Create a naming convention for APKAM keys in the documentation

Create a naming convention for APKAM keys in the documentation.

Right now the default is `@soccer0_key.atKeys`. Which is the same as
the manager key. However we are completely riding on the fact that
the user will get the prompt to NOT overwrite the key.

Leaving these decisions up to the user is not ideal. When a more
advanced user wishes to use a specific key name, they can use the `-k` flag.

## Proposal Summary

Remove the `-k` flag as a mandatory flag in `at_activate enroll` and come up
 with a default naming convention for APKAM keys in code.

## Proposal in Detail

I'm leaning towards the hashed namespace key name, we would be hashing using the enrollment_id. This would allow the user to see which keys are for what using the `at_activate list` command.

If we want we could instead include the hash inside of the json of the file.

### Expected Consequences

Rewriting the code to include the hashed namespace key name.

Which include:
* at_activate
* noports
* any other app that would use apkam keys
