# Format and Lint Tooling

<!-- This template is inspired by
https://github.com/GoogleCloudPlatform/emblem/tree/main/docs/decisions -->

- **Status:** Draft
- **Last Updated:** 2024-09-05
- **Objective:** Standardize formatting and linting to consistent code styles

## Context & Problem Statement

Members of the team use various markup / code styles / formatters outside of
Dart which results in some problematic code reviews containing lots of quote
changes, white space changes, etc.

## Goals

- Create a list of formatters for common file types we use to format and lint
  code to ensure consistency across the team
- Try to keep the list short and reasonable
- Try to pick tools formatters which are widely available

### Non-goals

## Other considerations <!-- optional -->

- It is typically a wise and sane choice to pick the native option whenever
  available.
- Do the same for linters, and lint ignores.

> Note: I have brought linters into the equation because they can be affected by
> formatters. For example, I have yet to find a formatter that works with the
> linter we use for the at_protocol specification... thus I think we should
> change that to markdownlint or something that follows the same rules as
> markdownlint. The reason that the linter for the at_protocol specification
> fails is due to whitespace around comments. The linter ignores comments, but
> not whitespace around comments. Every formatter that I've seen pads all
> comments with whitespace, thus the linter sees a double blank line and doesn't
> like it. - @xavierchanth

## Considered Options <!-- optional -->

- ### Option 1 (@xavierchanth's proposal)

> Not tied to any of these, but these are what I am using as they work well and
> seem to be popular.

<!-- pyml disable-num-lines 11 md013-->

| Formatter                                   | Description                                                            | Language(s)                                             |
| ------------------------------------------- | ---------------------------------------------------------------------- | ------------------------------------------------------- |
| dart format                                 | Native                                                                 | Dart                                                    |
| rustfmt                                     | Native                                                                 | Rust                                                    |
| [gofumpt](https://github.com/mvdan/gofumpt) | Native gofmt with some stricter rules                                  | Go                                                      |
| markdownlint-cli2                           | Linter with the same rules as at_protocol spec, has built-in formatter | Markdown                                                |
| shfmt                                       | Shell formatter                                                        | shell                                                   |
| gersemi                                     | Cmake formatter                                                        | cmake                                                   |
| clangd                                      | C family formatter, which supports configuration                       | C                                                       |
| prettier                                    | A formatter for webdev which supports several file types               | HTML, CSS, JavaScript, JSON, YAML, (Markdown available) |

> Note on clangd: we currently have at_c configured to be more like dart format
>
> Note on prettier: I think it is a good catch-all for languages where we don't
> care very much about styling but should have something.
>
> Note on missing languages: I don't have a Java or C# formatter currently
> installed, thus I have not recommended formatters for them, but we do have
> some code written in these languages so it would be nice to have
> recommendations. We could also use clangd, but there are probably better
> options.

- ### Option 2

## Proposal Summary

Proposed a list of formatters for the team to use for various languages.

## Proposal in Detail

- To be completed after further discussion

### Expected Consequences <!-- optional -->

Less styling changes in our Pull Requests, easier times reviewing.