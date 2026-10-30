# Milestone 2 — Safe file operations and explicit write semantics

This milestone closes the main safety gaps identified in the initial implementation pass for Forge.

## Goal

Harden the file tool layer so the model cannot accidentally destroy existing content by calling a broad overwrite operation when it actually intended a narrow edit.

## Scope included in this milestone

- separate file creation from file replacement,
- require explicit replacement intent for existing files,
- reject ambiguous edit targets before writing,
- enforce exact-match replacement semantics,
- keep the dispatch layer aligned with the safer tool contract,
- add regression tests for unsafe file-operation behavior.

## Core design decisions

1. File creation and file replacement are distinct operations with different semantics.
2. Overwriting an existing file is never implicit.
3. Edit operations must target a unique, exact snippet or fail.
4. Tool safety is enforced in the filesystem boundary, not just in the model prompt.
5. The agent loop remains small and testable while the safety constraints become stricter.

## Key corrections from Milestone 1

The initial implementation allowed a broad write path that could overwrite an existing file. That is unsafe for an agent that may mistake a create action for a replace action.

Milestone 2 resolves this by introducing a clear distinction between:

- `create_file`: create a new file only if it does not already exist,
- `replace_file`: replace the contents of an existing file only when the caller explicitly chooses replacement,
- `edit_file`: modify a unique snippet in place without touching unrelated content.

## Planned implementation

The tool layer should enforce the following rules:

- creating an existing file is a validation error,
- replacing a missing file is a validation error,
- editing a file requires a unique match,
- no silent “first match wins” behavior is allowed,
- all write operations must stay within the workspace root.

## Milestone acceptance criteria

- The agent can create a new file without risking overwrite of an existing file.
- Replacing an existing file requires an explicit replacement call.
- Editing a file fails fast when the target is missing or ambiguous.
- The filesystem boundary rejects unsafe paths and symlinks.
- Tests cover create-vs-replace-vs-edit behavior.
