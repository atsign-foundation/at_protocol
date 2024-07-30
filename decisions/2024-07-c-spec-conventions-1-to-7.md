# C SDK Specification

- **Status:** Draft
- **Last Updated:** 2024-07-29
- **Objective:** Define conventions for contributing to the C SDK

## Context & Problem Statement

Establish conventions 1 through 8 for the C SDK. Outlined in this document are conventions 1 through 8. More conventions may be introduced in the futuer.

## Goals

- Establish conventions for contributing to the C SDK
- Provide a clear path for contributors to follow
- Ensure consistency in the C SDK
- Make it easy for contributors to understand how to contribute to the C SDK

### Non-goals

N/A

## Proposal Summary

The goal of this document is to establish the following conventions when contributing to the C SDK. We expect future contributors to follow these conventions to ensure consistency and maintainability of the codebase.

## Proposal in Detail

Conventions are listed below:

# Convention 1. Snake Case

## Description

We're using snake case instead of camel case because MbedTLS happens to be snake case. Since MbedTLS is one of our core libraries seen everywhere, we may as well follow their naming convention. Most C programs are also generally known to be in snake_case.

When using snake case, we separate each **word** with an underscore.

## Examples

Good:

```c
aes_pkam_public_key
value_encrypted_for_us_base64
atclient
atsign
```

Bad:

```c
aespkampublickey
skeencalgo
at_client
at_key
HelloWorld
helloWorld
```

## Exceptions

Some exceptions that you may find throughout the code base:

- We consider `base64` as one word because "64" isn't really a word
- When we use the `at` prefix, we do not consider it as a word which is why we have `atclient` instead of `at_client`. There are just too many ats that an extra underscore would be too much.

# Convention 2. Function Signature Format

## Description

Functions should return an `int` to hand off an error code to the caller of the function. If an error is not possible, `void` should be used. Some exceptions on this will be emphasized.

Example of a function:

```c
int calculate_length(const atclient_atkey *atkey, int *output_length);
```

Generally, function signatures should follow this format:

```c
<return_type> <function_name>(<context>, <input,...>, <output,...>, <optional,...>);
```

- <return_type> - generally an `int` to give an error code, or may be any other return type as long as a complex error is not possible 
- <function_name> - the name of the function (example 'foo_bar') should be in snake_case
- <context> - typically this is a struct pointer that is the core object meant to be used in the function (i.e. this function LIVES and BREATHES because of the object that the caller is passing), this should be set to `const` if it is meant to be read-only
- <input,..> - any input function arguments, any values that are not editable or should not be edited, should be set to `const`.
- <output,..> - any output function arguments, typically we have pointers or double pointers to give the caller some complex values, any const inputs that are related to the output should be put in this section (for example, buffer size is related to the buffer, which is an output).
- <optional,...> - any optional inputs or outputs or any kind of optional arguments should be at the end. An argument is considered "optional" when NULL can be passed to it and the function will expect it to be either NULL or NON-NULL.

Here are some examples:

```c
// function signature
int atclient_put(atclient *ctx, const char *value, int *commit_id);
```

```c
// usage
atclient ctx;
atclient_init(&ctx);
int error_code;
int commit_id;
if((error_code = atclient_put(&ctx, "foo_bar", &commit_id)) != 0) {
    // handle error
}
printf("%d\n", commit_id); // outputs "37", for example
```

# Convention 3. Function Input

Related discussions have been made in : #341

## Description

This section is regarding the `<input,...>` section of the function signature.

When receiving input in a function signature, when is it appropriate to pass the length of the buffer and when is it not?

Take the following example

```c
// method 1 - assume it is null-terminated
int do_something1(const char *value);

// method 2 - expect value length as input
int do_something(const char *value, const size_t value_len);
```

## Method 1

In method 1, take the input and expect it to be null-terminated

Use method 1 when:
- Working with strings (chars)
- You specify that the input should be null-terminated and it is the caller's responsibility to pass in a null-terminated string

## Method 2

In method 2, take both the input and length

Use method 2 when:

- Working with bytes (unsigned chars) - a null-terminator cannot be dependent to act as the end of the data
- Working with files or standard input - when the caller is most likely passing in this data from a file, it will be a lot easier for them to pass the length as opposed to having to make a completely separate string and null-terminate it.


# Convention 4. Function Output

Related discussions have been made in : #335

## Description

This section is regarding the `<output,...>` section of the function signature.

There are two ways to give back an array of data back to the caller of the function. The first way is **double pointer method** and the second way is **buffer and length**. 

In the first way, the **function** is responsible for allocating the memory and the **caller** is responsible for freeing. In the second way, the **caller** is responsible for both allocating and freeing the memory.

The third way is very similar to the second method, but the function does not return the length.

## Double Pointer Method

In this first method, you pass a double pointer so that the function can allocate **just enough** memory for you, making your life easier while also optimally using your memory.

```c
// function signature
int atclient_atkey_to_string(const atclient_atkey *atkey, char **return_string);
```

```c
// usage
char *string = NULL;

atclient_atkey_to_string(&atkey, &string);

printf("%s\n", string); // outputs "foo.bar@bob"

free(string);
```

You should use this method when:

- Returning a string (this is most optimal for strings because a null-terminator can be used to avoid passing a length)
- Output is calculable (if we know how long the string is going to be, we know where to put the null-terminator !)
- The returned data is a substring of a superior buffer (example, I want to return "foo" from "foo_bar", "foo" is trivial to extract from the string and should be simplified for the caller).

## Buffer And Length Method

In this second method, the caller has more control over the memory usage (e.g. they could allocate it statically or dynamically if they would like!), but is a lot harder to use. In the example below, the caller has to go through and allocate the memory, reset the buffer, and make a variable to hold the length.

```c
// function signature
int atclient_atkey_to_string(const atclient_atkey *atkey, char *return_buffer, const size_t return_buffer_size, size_t *return_buffer_len);
```

Sometimes, `size_t *return_buffer_len` is an optional buffer and NULL can be passed here if the caller doesn't want to receive the length. This is useful for when the caller null-terminates the buffer themselves and can trust that the buffer will be null-terminated and safe for string usage.

```c
// usage
const size_t string_size = 100;
char string[string_size];
memset(string, 0, sizeof(char) * string_size);
size_t string_len = 0;

atclient_atkey_to_string(&atkey, string, string_size, &string_len);

printf("[%d]: %.*s\n", (int) string_len, (int) string_len, string); // outputs "[11]: foo.bar@bob"
```

You should use this method when:

- Returning bytes (a null-terminator cannot be depended on to act as a stopping point in the buffer)
- Output is not calculable (let the caller decide how much memory is enough to not cause a segfault, this is typically found in something like RSA decryption)
- When the input is most likely coming from a file (makes it easier to pass in strings so that the caller doesn't have to make separately null-terminated strings and easily do something like foo_bar(string[3], 10, string[14], 5, string[20], 3); )

## Buffer and No Length

This third method is very similar to the second way, except there is no need to pass a `size` and `output_length` pointer. It should be specified in **function documentation** the assumed size of the allocated buffer as well as the expected output.

```c
// function signature

/**
 * @param shared_with - shared with atSign, null-terminated and non-null
 * @param shared_encryption_key - assumed to be at least 32 bytes allocated (representing an AES256 key)
 */
int get_shared_encryption_key(const char *shared_with, unsigned char *shared_encryption_key);
```

```c
// usage
const char *shared_with = "@bob";
unsigned char shared_encryption_key[32];
if((ret = get_shared_encryption_key(shared_with, shared_encryption_key)) == 0) {
    // at this point, shared_encryption_key was successfully populated with 32 bytes to the brim
}
```

You should use this method when
- You wanted to use Method 2 but the size and length are always the same (in the example above, the size always == length and is always 32, assuming that the return exit code was 0 which means successful).
- You're not returning a string, you're returning bytes (unsigned chars)

# Convention 5. Validating Arguments

It is important to validate arguments in functions to avoid common pitfalls such as null pointers, negative values, etc. The first thing in every function should be similar to the following:

```c
int foo_bar(atclient *ctx, atclient_atkey *atkey) {
    int ret = 1;
    /*
     * 1. Validate arguments
     */
    if(ctx == NULL) {
        ret = 1;
        return ret;
    }

    if(atkey == NULL) {
        ret = 1;
        return ret;
    }
}
```

Another thing to note is that in the validating section of the function uses `return` and never uses `goto`. This is because the next part of the function is usually variable allocation where dynamic and static memory is allocated. If we were to use `goto`, then we would have to free the memory that was allocated before the `goto` statement. This is a common pitfall in C programming and should be avoided.

Example of how this practice should be executed:

```c
int foo_bar(atclient *ctx, atclient_atkey *atkey) {
    int ret = 1;
    /*
     * 1. Validate arguments
     */
    if(ctx == NULL) {
        ret = 1;
        return ret; // use return
    }

    if(atkey == NULL) {
        ret = 1;
        return ret; // use return
    }

    /*
     * 2. Variables
     */
    char *buffer = NULL;
    unsigned char recv[4096];
    char *xyz = malloc(sizeof(char) * 45);

    /*
     * 3. Do stuff
     */
    if((ret = foo_bar()) != 0) {
        goto exit; // use goto
    }

    if((ret = foo_bar()) != 0) {
        goto exit; // use goto
    }

    if((ret = foo_bar()) != 0) {
        goto exit; // use goto
    }

    goto exit;
exit: {
    free(xyz);
    return ret;
}
}
```

In the above example, if it is important to note that we use `goto` only once `xyz` is declared. That is because we `free(xyz)` in the `exit` block. We use `return` in the validating section because we do not want to allocate memory if the arguments are invalid. If we were to use `goto` in the validating section, then we would have to free the memory that was allocated before the `goto` statement.

# Convention 6. Error Handling

Rule 1: The first statement in any function that is returning `int` (with the intent of returning an exit code) should be declaring what the default error code is.

For example,

```c
int foo_bar() {
    int ret = 1;

    // do stuff

    return ret;
}
```

The reason for this rule is to make it easier to make any changes to our error handling in the future.

Rule 2: Try to avoid non-nested if statements.

If an error occurs, then set the error code if it is not already set by the function, log, then either exit or return.

For example,

Bad

```c
if((ret = foo_bar()) == 0 ) {
    if((ret = foo_baz()) == 0) {
        if((ret = foo_bat()) == 0) {
            // code
        } else {
            // error
            return ret;
        }
    } else {
        // error
        return ret;
    }
} else {
    // error
    return ret;
}
```

Good

```c
if((ret = foo_bar()) != 0 ) {
    // log
    return ret;
}

if((ret = foo_baz()) != 0) {
    // log
    return ret;
}

if((ret = foo_bat()) != 0) {
    // log
    return ret;
}

// code
```

Rule 3: If an error code isn't returned by a function and an error occurs, explicitly set it as the first as soon as the error occurs.

For example,

Bad

```c
int exit_code;
unsigned char *x = NULL;
if((x = malloc(sizeof(unsigned char) * 45)) == NULL) {
    printf("Error occurred\n");
    exit_code = 5; // the exit_code should be the FIRST thing set AS SOON AS the error occurs. This is wrong !
    return exit_code;
}
```

Good

```c
int exit_code;
unsigned char *x = NULL;
if((x = malloc(sizeof(unsigned char) * 45)) == NULL) {
    exit_code = 5; // first thing ! :))
    printf("Error occurred\n");
    return exit_code;
}
```

The reason for this rule is to limit things that could go wrong. It is important that the error code is set as soon as the error occurs to avoid any potential issues. For example, if printf for some reason caused an error, then the exit code could potentially not have been set and an exit code 0 could somehow be mistakenly `returned. The reason for this rule is also because of Rule 1, and it helps us in the future if we ever want to change our error handling.

Rule 4: Function return types should be `int` and should return an error code. If an error is not possible, then the return type should be `void`. With the exception of types like `bool` or `size_t` where the error code is not complex.

Example

```c
bool atclient_connection_is_connected(atclient *ctx) {
    int erro_code = 0;
    if((ret = atclient_connection_send(ctx, "noop:0\r\n")) != 0) {
        return false;
    }
    return true;
}
```

In the above example, since the function returned a failure, it is safe to assume that the connection is not connected. If the function returned a success, then it is safe to assume that the connection is connected.

Another example:

```c
size_t calculate_length(atclient_atkey *atkey) {
    size_t length = 0;
    if(atkey == NULL) {
        return length;
    }
}
```

Since atkey was null, then it is pretty obvious that the length is 0. The length is truly 0 beacuse nothing exists and there was nothing to calculate. This is why the return type need not be `int` in this scenario. There is *always* an answer to the question "what is the length of this atkey?" that fits the return type `size_t`.