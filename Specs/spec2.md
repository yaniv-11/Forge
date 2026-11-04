# Forge — Milestone 2 Specification
## Coding Tools

**Status:** Proposed  
**Milestone:** 2  
**Objective:** Enable Forge to make controlled, verifiable changes to files inside its configured workspace.

---

## 1. Goal

Milestone 2 extends Forge from a file-reading agent into a basic coding agent.

Forge should be able to:
- Explore the workspace.
- Search for relevant code.
- Read file contents.
- Create files.
- Edit existing files.
- Verify its changes.
- Explain what it changed.

The user should be able to give Forge tasks such as:

- "Add a new function to this Python file."
- "Fix the bug in this function."
- "Create a README for this project."
- "Update the configuration to support a new option."
- "Find all usages of this function and update them."

Forge must not be allowed to read or modify files outside its configured workspace.

---

## 2. Workspace Boundary and Safety

### 2.1 Workspace definition

Forge operates within one configured workspace directory.

For the initial implementation:
- The workspace is the project folder supplied to Forge.
- All file tools must resolve paths relative to that workspace.
- Relative paths are preferred.
- Absolute paths are rejected unless explicitly supported and verified to remain inside the workspace.

### 2.2 Path restrictions

The following paths must be rejected:

- Paths that escape the workspace using `..`.
- Paths that resolve outside the workspace.
- Symlinks that point outside the workspace.
- Unsupported special files such as device files.

### 2.3 Safety requirements

Every filesystem tool must:
1. Resolve and validate the requested path.
2. Check that the operation is permitted.
3. Perform the operation only after validation.
4. Return a clear error if validation fails.

Path validation must not be implemented separately and inconsistently inside each tool. A shared workspace/path validation component should be used.

**Important:** Path resolution alone is not a complete defense against symlink races. The initial implementation should reject symlinks for write operations and avoid following them outside the workspace. Stronger OS-level sandboxing is deferred.

---

## 3. Tool Inventory

### Existing tools

| Tool | Purpose | Status |
|---|---|---|
| `list_files` | List files and directories | Existing |
| `read_file` | Read file contents | Existing |
| `search_files` | Search file contents | Existing |

These tools should be retained and tested against the workspace safety requirements.

### New tools

| Tool | Purpose | Priority |
|---|---|---|
| `edit_file` | Make a targeted edit to an existing file | First |
| `write_file` | Create a new file or explicitly overwrite an existing file | Second |

### Deferred tools

| Tool | Reason for deferral |
|---|---|
| `delete_file` | Destructive operation; requires additional safety controls |
| `run_command` | Requires command execution policy and isolation |
| `run_tests` | Depends on safe command execution |
| `apply_patch` | More advanced edit mechanism; can be added after the first edit tool |

---

## 4. Tool: edit_file

### 4.1 Purpose

Modify a specific part of an existing file without replacing the entire file.

### 4.2 Input schema

```json
{
  "path": "src/main.py",
  "old