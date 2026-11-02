# Forge

Forge is a local, workspace-constrained coding agent written in Python. It runs a model-powered agent loop from the terminal, gives the model a controlled set of repository tools, persists task state across sessions, and keeps filesystem and command activity inside an explicitly selected workspace.

The project is designed to make the important agent boundaries visible:

- the CLI controls task execution;
- the agent loop controls reasoning and tool iterations;
- a registry describes the tools exposed to the model;
- a dispatcher validates and executes tool calls;
- workspace guards constrain reads and writes;
- local JSON, SQLite, traces, and repository indexes provide memory and recovery.

## Table of contents

- [Highlights](#highlights)
- [How Forge works](#how-forge-works)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running Forge](#running-forge)
- [Interactive commands](#interactive-commands)
- [Agent tools](#agent-tools)
- [Execution flow](#execution-flow)
- [Safety model](#safety-model)
- [Memory and persistence](#memory-and-persistence)
- [Repository indexing and context](#repository-indexing-and-context)
- [Project structure](#project-structure)
- [Testing](#testing)
- [Observability](#observability)
- [Limitations and roadmap](#limitations-and-roadmap)
- [Troubleshooting](#troubleshooting)
- [License](#license)

## Highlights

- Explicit and inspectable agent loop
- OpenRouter-compatible chat-completions client
- Interactive multi-turn REPL or one-shot execution
- Workspace selection with `--workspace`
- Typed tool definitions and JSON-style argument schemas
- Parallel execution of independent tool calls
- Required-field and argument-type validation
- Prompt-injection sanitization
- Workspace, path-traversal, directory, and symlink protection
- Separate create, replace, and exact-snippet edit operations
- Allowlisted and approval-protected command execution
- Git status, diff, checkpoint, and restore helpers
- Incremental JSON session persistence
- Session summaries and recent-message restoration
- Workspace-specific JSON memory
- SQLite sessions, episodes, files, and Python symbols
- Estimated token-budget context compaction
- Structured JSONL runtime traces
- Unit coverage for the core loop and file safety behavior

## How Forge works

Forge is not a framework wrapper with hidden agent behavior. The runtime is split into small components with deliberate interfaces.

```text
User task
    |
    v
CLI / REPL
    |
    +--> settings and environment
    +--> workspace selection
    +--> memory initialization
    |
    v
AgentLoop
    |
    +--> prompt construction
    +--> repository and session context
    +--> model request
    |
    v
OpenRouterClient
    |
    +--> normalized final answer
    +--> one or more tool calls
    +--> usage metadata
    |
    v
ToolDispatcher
    |
    +--> schema validation
    +--> approval policy
    +--> retry policy
    |
    v
ToolRegistry --> registered tool handlers
    |
    v
Workspace filesystem / process / Git boundaries
    |
    v
Tool results
    |
    v
Agent loop repeats until a final answer or execution limit
```

### Agent state

Each agent run tracks:

- the sanitized user task;
- conversation messages;
- agent iteration count;
- tool-call count;
- retry count;
- final answer;
- last error;
- accumulated token usage;
- elapsed execution time;
- current plan data.

### Stop conditions

A run ends when:

- the model returns a final answer;
- the model returns no usable result;
- the maximum step count is reached;
- the maximum tool-call count is reached;
- protected execution is denied.

## Installation

### Requirements

- Windows PowerShell or another terminal
- Python 3.10 or newer
- Git, for checkpoint and repository operations
- An OpenRouter API key for live model requests

### Install the project

From the repository root:

```powershell
python -m venv .venv
. .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e .
```

Confirm that the command is available:

```powershell
forge --help
```

If PowerShell does not allow activation scripts, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
. .venv\Scripts\Activate.ps1
```

Forge has no third-party runtime dependencies declared in `pyproject.toml`; the implementation uses the Python standard library and the installed Forge package.

## Configuration

Copy the example environment file:

```powershell
Copy-Item .env.example .env
```

Then configure:

```dotenv
OPENROUTER_API_KEY=your_openrouter_api_key_here
FORGE_MODEL=openai/gpt-4o-mini
FORGE_SITE_URL=
FORGE_APP_NAME=Forge
FORGE_PROVIDER=openrouter
```

| Variable | Purpose | Default |
|---|---|---|
| `OPENROUTER_API_KEY` | OpenRouter API credential | none |
| `FORGE_MODEL` | OpenRouter model identifier | `openai/gpt-4o-mini` |
| `FORGE_SITE_URL` | Optional HTTP-Referer attribution | none |
| `FORGE_APP_NAME` | Optional OpenRouter application name | `Forge` |
| `FORGE_PROVIDER` | Provider setting reserved for future provider selection | `openrouter` |
| `FORGE_DEBUG` | Enables `[TRACE]` output when set to `1`, `true`, `yes`, or `on` | `false` |

Forge searches for `.env` in the selected workspace, the current directory, and the package repository location. A real API key enables live OpenRouter requests. Without a key, the model client returns deterministic mock responses for local loop testing.

Keep `.env`, API credentials, and private memory outside source control.

## Running Forge

### Interactive REPL

Start Forge in the current directory:

```powershell
forge
```

Example:

```text
Forge workspace: C:\Users\you\Desktop\project
Commands: /help, /status, /sessions, /history, /exit
forge> fix the failing calculator tests
```

Each task creates or continues the active in-process session. The REPL remains available until `/exit`, `/quit`, EOF, or an interrupt is received.

### One-shot task

```powershell
forge "Fix the failing tests"
```

Arguments after the command are joined into a single task string.

### Select a workspace

```powershell
forge --workspace C:\path\to\project "Inspect the repository"
```

Short form:

```powershell
forge -w C:\path\to\project "Inspect the repository"
```

The workspace must exist. Filesystem tools, repository indexing, session storage, traces, memory, and workspace-relative command working directories are associated with this root.

### Resume a JSON session

```powershell
forge -w C:\path\to\project --resume session-0
```

Resume loads the stored summary and recent messages, then runs the original saved task again with that context.

### Disable parallel tools

```powershell
forge --no-parallel-tools "Inspect the repository"
```

Parallel tool execution is enabled by default and limited to four workers per model response.

## Interactive commands

| Command | Behavior |
|---|---|
| `/help` | Lists the available REPL commands |
| `/status` | Shows concise Git branch and working-tree status |
| `/sessions` | Lists persisted JSON session IDs |
| `/history` | Lists tasks submitted during the current REPL process |
| `/exit` | Exits Forge |
| `/quit` | Alias for `/exit` |

## Agent tools

Tools are registered centrally in `forge.cli.build_registry()`.

### Repository discovery

| Tool | Description |
|---|---|
| `list_files` | Lists child names in a workspace directory |
| `inspect_repo` | Scores files by task keywords and returns relevant paths |
| `search_files` | Runs a case-insensitive regular-expression search and returns file-and-line matches |
| `read_file` | Reads a UTF-8 text file |

### Planning and memory

| Tool | Description |
|---|---|
| `plan_task` | Creates a three-step inspect, fix, and verify plan |
| `resume_session` | Loads a JSON session only if no destructive side effects are recorded |

### Safe file mutation

| Tool | Description |
|---|---|
| `create_file` | Creates a file only when it does not already exist |
| `replace_file` | Replaces content only after verifying that an existing target exists |
| `edit_file` | Replaces an exact snippet only when it occurs exactly once |

There is no generic unrestricted `write_file` tool exposed to the model.

### Command execution

| Tool | Description |
|---|---|
| `run_command` | Executes an allowlisted executable with a workspace-scoped working directory and timeout |

The default executable allowlist includes:

- Python interpreters: `python`, `python3`, `py`
- Testing: `pytest`
- Git: `git`
- JavaScript: `npm`, `npx`, `node`
- Other common toolchains: `dotnet`, `cargo`, `go`
- Windows shells: `cmd`, `powershell`, `pwsh`

Despite the allowlist, commands can still execute powerful interpreters and shells. Approval prompts are therefore an important additional boundary.

### Git operations

| Tool | Description |
|---|---|
| `git_status` | Returns concise branch and working-tree status |
| `git_diff` | Returns staged or unstaged diff output |
| `create_checkpoint` | Creates an annotated Git tag checkpoint |

## Execution flow

### Normal agent turn

1. The user task is sanitized.
2. The default plan is attached to the task.
3. System rules and the task become model messages.
4. Recent session context and summaries are injected when available.
5. The model receives the registered tool schemas.
6. The response is classified as a final answer or a set of tool calls.
7. Tool calls are validated and dispatched.
8. Tool results are appended to the conversation.
9. Transient tool failures are retried according to the configured retry policy.
10. The loop returns to the model until it answers or reaches a limit.

### Tool-call flow

```text
Model response
    |
    +--> final_answer --> return result
    |
    +--> tool_calls
            |
            +--> validate tool name
            +--> validate required arguments
            +--> validate primitive argument types
            +--> check approval policy
            +--> invoke handler
            +--> normalize result
            +--> append tool message
```

Tool results use structured outcomes such as:

- `ok`
- `validation_error`
- `tool_not_found`
- `permission_denied`
- `execution_error`

### Parallel tool execution

Independent tool calls from one model response are scheduled in a bounded thread pool. Results are collected back in call order and then appended as tool messages, preserving the IDs expected by the model protocol.

Potentially mutating calls should not be assumed independent. Parallel execution should be disabled with `--no-parallel-tools` when simultaneous writes or Git operations could conflict.

## Safety model

Forge combines several independent layers. Each layer closes a different class of error.

### Prompt constraints

The prompt builder:

- identifies user content as untrusted;
- adds workspace and permission rules;
- removes common jailbreak phrases before model submission;
- asks the model not to claim completion without verification.

Prompt filtering is defensive but is not a substitute for tool-level enforcement.

### Workspace path enforcement

The filesystem boundary:

- resolves relative paths against the selected workspace root;
- rejects absolute paths outside the workspace;
- rejects path traversal;
- detects symlink components;
- prevents directory targets from being used as files;
- rejects symlinks when they are directly present in a write path.

### Mutation semantics

| Operation | Existing file | Missing file |
|---|---|---|
| `create_file` | rejected | created |
| `replace_file` | overwritten | rejected |
| `edit_file` | exact unique match required | rejected |

An edit with zero matches or multiple matches is rejected rather than applying a guessed replacement.

### Approval system

Tools marked as approval-required are not executed automatically.

At an approval prompt:

- `y` or `yes` approves the request;
- `n`, `no`, or Enter denies it.

Tool calls denied at the approval boundary return `permission_denied`. Retry logic does not repeatedly execute a denied approval request.

### Command allowlisting

`run_command` restricts the executable name and working directory, but the allowlist does not replace OS-level sandboxing. Python and shell entry points can run arbitrary subcommands depending on arguments.

### Important safety boundary

Forge currently implements a workspace-aware application boundary, not a hardened operating-system container. It does not provide:

- a dedicated subprocess/container sandbox;
- syscall isolation;
- per-process network rules;
- memory or CPU cgroups;
- OS-level secret filtering;
- guaranteed protection against approved malicious commands.

Run Forge only in workspaces and environments you trust, and review approval prompts carefully.

## Memory and persistence

Forge separates persistent memory into several forms.

### Working memory

Working memory is the active `AgentState.messages` list plus the plan and loop counters. It represents what the current agent run can reason about.

### Short-term JSON sessions

JSON sessions are stored under:

```text
.forge_sessions/
├── session-0.json
├── session-1.json
└── ...
```

Each payload includes:

- task;
- summary;
- recent messages;
- plan;
- usage;
- elapsed time;
- retry count;
- side-effect metadata.

Writes use temporary files and atomic replacement to reduce partial-session corruption.

Incremental updates are supported through `SessionStore.update_session()`.

### Workspace memory

Workspace memory is stored separately at:

```text
.forge/workspace_memory.json
```

The initial structure contains:

- project facts;
- coding conventions;
- entry points;
- test commands;
- known failures.

Workspace memory should contain non-secret project knowledge. Forge excludes the `.forge` directory from repository indexing.

### SQLite memory

Forge also stores agent and repository data in:

```text
.forge/memory.sqlite3
```

SQLite tables include:

- `sessions`;
- `episodes`;
- `repository_files`;
- `symbols`.

An episode records a completed task, its outcome, summary, session, file list, and command list.

### Session restore

On resume, Forge:

1. loads the JSON session;
2. rejects sessions marked with destructive side effects;
3. selects recent messages;
4. restores the human-readable summary;
5. injects summary and recent context before running the saved task.

### Context compaction

Before a model request, messages are estimated in approximate four-character token chunks.

When estimated context exceeds the configured budget:

- one system message is retained;
- recent non-system messages are retained;
- older messages are represented by a compaction summary.

Raw persisted history remains separate from the compacted prompt view.

## Repository indexing and context

On CLI startup Forge rebuilds a bounded repository index.

### Indexed files

The index scans supported source and configuration formats:

```text
.py  .js  .ts  .tsx  .jsx  .java  .go  .rs  .cs
.md  .json  .toml
```

Ignored locations include:

- `.git`
- `.forge`
- `.forge_sessions`
- `.venv`
- `__pycache__`
- `node_modules`

The default rebuild limit is 2,000 files.

### Indexed symbols

Python files are parsed with the standard-library AST. Forge records:

- classes;
- functions;
- asynchronous functions;
- source paths;
- source line numbers;
- basic signatures and names.

Symbol lookup is currently exact-case-insensitive substring lookup against indexed names. It is repository local, does not use embeddings, and does not create a call graph.

## Project structure

```text
Forge/
├── src/forge/
│   ├── agent.py              # Agent loop and execution state
│   ├── cli.py                # Entry point, REPL, registry assembly
│   ├── config.py             # Environment and runtime settings
│   ├── git_tools.py          # Git status, diff, checkpoint, restore
│   ├── memory.py             # Workspace memory, SQLite, indexing, compaction
│   ├── model_client.py       # OpenRouter API adapter and response parsing
│   ├── observability.py      # Structured JSONL traces
│   ├── persistence.py        # Atomic JSON session persistence
│   ├── planning.py           # Plan and retry state
│   ├── prompts.py            # System prompt and prompt sanitization
│   ├── repo_inspector.py     # Lightweight repository relevance scoring
│   ├── tool_dispatcher.py    # Schema validation and approval enforcement
│   ├── tool_registry.py      # Tool metadata and provider schemas
│   └── tools/
│       └── filesystem.py     # Path guards, files, search, command execution
├── tests/
│   └── test_file_operations.py
├── Milestone-1/
├── Milestone-2/
├── Specs/
├── pyproject.toml
└── README.md
```

## Testing

Run the complete test suite from the repository root:

```powershell
python -m pytest -q
```

Compile all Python sources:

```powershell
python -m compileall src tests -q
```

The suite covers:

- multiple tool calls and call-ID preservation;
- required argument validation;
- create/replace/edit file semantics;
- unique snippet edits;
- workspace escape prevention;
- command working-directory boundaries;
- permission metadata;
- command output;
- plans and retry budgets;
- repository relevance;
- prompt sanitization;
- session persistence;
- Git checkpoint creation;
- parallel tool-call ordering;
- workspace memory;
- SQLite sessions;
- repository symbol indexing;
- context compaction.

## Observability

### Structured traces

Runtime events are appended as JSON Lines to:

```text
.forge/traces.jsonl
```

Events include:

- task start;
- model responses;
- tool retries;
- tool results;
- task completion;
- elapsed time.

Trace output is local and append-only. Each event is timestamped.

### CLI progress

The CLI prints:

- tool names and statuses;
- retry attempts and reasons;
- completion time;
- session ID;
- aggregated token count;
- final answer or error.

Debug mode adds detailed `[TRACE]` messages:

```powershell
$env:FORGE_DEBUG="true"
forge "Inspect the repository"
```

## Limitations and roadmap

Forge is a compact coding-agent foundation rather than a complete IDE replacement.

### Current limitations

- Repository relevance uses keyword and path scoring rather than embeddings.
- Python indexing is AST-based; JavaScript and other language symbols are not semantically parsed.
- Indexed context is not yet injected automatically into every relevant model turn.
- There is no call graph, type index, or language-server integration.
- Approval is prompted per tool call and not persisted as a trusted session policy.
- Parallel writes are not dependency-aware.
- Session resume reruns the stored task rather than offering a new follow-up task.
- Model usage parsing depends on the provider response format.
- Context estimation uses a character heuristic rather than a tokenizer-specific count.
- Model context has no provider-specific context-window configuration.
- Provider requests do not yet expose retry and cancellation controls.
- File operations are text-only.
- There is no OS-level sandbox.
- There is no checkpoint UI for reviewing individual changes before restoration.
- Streaming output and interruption handling are not implemented.

### Recommended next work

1. Add approval policies and persistent approval scopes.
2. Add cancellation and provider retry/backoff.
3. Add explicit follow-up tasks after session resume.
4. Add tokenizer-aware context budgeting.
5. Inject relevant symbol and file context into model prompts.
6. Add semantic retrieval using local embeddings.
7. Add language-server and cross-file symbol navigation.
8. Add unified diff preview before writes.
9. Add patch-level rollback and change tracking.
10. Add test and build command discovery.
11. Add subprocess resource limits and isolated execution.
12. Add streaming model output.
13. Add memory management commands for facts, episodes, and forgetting.

## Troubleshooting

### The CLI is not found

Ensure the virtual environment is active and the package is installed editable:

```powershell
.venv\Scripts\Activate.ps1
python -m pip install -e .
```

Then run:

```powershell
where.exe forge
forge --help
```

### Live requests are returned as mock responses

Check that `OPENROUTER_API_KEY` is set in the workspace `.env`, the current `.env`, or a supported parent location:

```powershell
$env:OPENROUTER_API_KEY = "your_key"
forge "Inspect the repository"
```

### A command is denied

A registered protected command requires approval. Confirm the prompt with `y`, or review the command arguments and deny it with `n`.

Executable names outside the default allowlist are rejected before process creation.

### A file operation is denied

Check that:

- the path is inside the selected workspace;
- the path contains no symlink component;
- create targets do not already exist;
- replace targets already exist;
- edit snippets occur exactly once.

### SQLite is busy or locked

Stop other Forge processes accessing the same workspace. If it remains locked after all processes exit, inspect the workspace for stale processes rather than deleting an active database.

### Resume reports destructive side effects

The session contains recorded side-effect state and is intentionally blocked from normal resume. Review the JSON session manually and start a new session if the history should not be replayed.

## License

License information has not yet been declared in `pyproject.toml` or the repository. Add a license only after choosing the appropriate license for the project and its dependencies.
