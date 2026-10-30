# Execution flow for Milestone 2

## 1. Normal create flow

```text
User task: create a new config file
  |
  v
Agent chooses create_file
  |
  v
Tool validator checks path and existence
  |
  +--> file does not exist -> allow write
  +--> file already exists -> reject
  |
  v
File is created within the workspace root
```

## 2. Explicit replace flow

```text
User task: overwrite an existing configuration file
  |
  v
Agent chooses replace_file
  |
  v
Tool validator checks whether the file exists
  |
  +--> file exists -> allow replacement
  +--> file missing -> reject
  |
  v
File contents are replaced intentionally and atomically
```

## 3. Edit flow

```text
User task: update a specific snippet in a file
  |
  v
Agent chooses edit_file with old/new text
  |
  v
Tool reads current file contents
  |
  v
Count occurrences of old text
  |
  +--> 0 matches -> reject as not found
  +--> >1 match -> reject as ambiguous
  +--> exactly 1 match -> replace that unique occurrence
  |
  v
Updated file is written back to disk
```

## 4. Safety principle

Milestone 2 keeps the runtime model simple but introduces a crucial rule: destructive operations require explicit intent.

No broad write path should quietly overwrite existing files in the workspace.
