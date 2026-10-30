# Architecture for Milestone 2

## 1. Architectural goal

Milestone 2 continues the small, explicit architecture of Forge, but sharpens the operational boundary around file mutation.

```text
User
  |
  v
CLI
  |
  v
AgentLoop
  |       \_
  |        \_ tool intent selection
  |            |
  v            v
ToolRegistry  FileSafetyLayer
  |            |
  |            v
  |        create_file / replace_file / edit_file
  |            |
  v            v
Filesystem boundary
  |
  v
Workspace root
```

The point of this milestone is not to add complexity for its own sake. It is to ensure that file mutations are intentional, auditable, and impossible to trigger accidentally through a broad write API.

## 2. Component responsibilities

### 2.1 Tool registry

The registry must expose separate operations for:

- creating a file,
- replacing an existing file,
- editing a specific snippet.

This removes the ambiguous ergonomics that made `write_file` too dangerous.

### 2.2 File safety layer

This layer enforces all mutation rules before the write is accepted.

Rules include:

- do not overwrite an existing file during create,
- do not create a missing file during replace,
- fail if `old` is empty,
- fail if the edit target is not unique,
- fail if the target escapes the allowed workspace.

### 2.3 Filesystem boundary

The filesystem boundary is the enforcement point for all path checks and writes.

It continues to guard against:

- directory targets,
- symlink escapes,
- path traversal,
- unexpected file mutation outside the project root.

## 3. Why this matters

The original `write_file` behavior was too permissive for an agentic tool. An agent can make mistakes. The system should not magnify those errors by allowing silent destructive writes.

This milestone forces the agent to operate in a safer, more explicit contract:

- create new files with explicit intent,
- replace only when replacement is explicitly requested,
- edit only when the target is exact and unambiguous.

## 4. Safety guarantees

Milestone 2 aims for the following guarantees:

1. No accidental overwrite from a generic write call.
2. No silent choice of the first matching edit target.
3. No unsafe path escape through the tool layer.
4. Clear errors for invalid or ambiguous operations.

## 5. Relationship to Milestone 1

Milestone 1 established the minimal loop and tool system. Milestone 2 tightens the safety contract around file mutation without redesigning the overall agent architecture.

The core loop remains the same; the improvement is in the boundary rules.
