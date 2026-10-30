Forge — Master Engineering Specification & Implementation Prompt

Project: Forge — AI Coding Agent Harness
Repository: https://github.com/yaniv-11/Forge
Language: Python
Primary goal: Build a reliable, secure, extensible coding agent from scratch while understanding every component and design decision.

Part 1 — Master Engineering Specification

1. Project vision

Forge is a local coding agent that operates inside a user-configured workspace.

It should be able to:

Understand a user's coding task.

Inspect the relevant parts of a codebase.

Create a plan and track its progress.

Read, create, and modify files.

Execute approved commands.

Run tests and other verification steps.

Diagnose failures and attempt bounded repairs.

Inspect its changes.

Report what it accomplished, what failed, and what remains.

Forge should not be a simple LLM wrapper that repeatedly calls tools. It should be a carefully designed agent runtime with explicit state, control flow, permissions, context management, and verification.

2. Engineering principles

All implementation must follow these principles:

Understand before modifying: Inspect the existing repository and architecture first.

Incremental development: Implement in small, independently testable slices.

Explicit control flow: The agent loop must be understandable and observable.

Typed interfaces: Prefer typed models and validated schemas over unstructured dictionaries.

Safety by design: Workspace restrictions and permission checks must be enforced by Forge's runtime, not merely instructed to the LLM.

Deterministic infrastructure: Filesystem, command execution, state management, and tool dispatch should behave predictably.

Provider independence: Model-provider-specific logic should be isolated behind an adapter.

Testability: Every core component should be testable without making real model calls.

Explainability: Tool calls, state transitions, and execution results should be inspectable.

No unnecessary complexity: Do not introduce frameworks or abstractions without a concrete need.

3. Scope

This specification covers the following feature areas:

Core agent runtime

Coding tools and patch support

Command execution and testing

Git integration and checkpoints

Agent planning and execution

Repository understanding

Context management

Workspace safety and permissions

Session persistence and recovery

Structured logging and tracing

Advanced capabilities such as MCP, subagents, browser automation, and parallel tool execution are outside this specification unless required by an existing dependency.

4. Core Agent Runtime

4.1 Explicit agent loop

Forge must implement a clear agent loop:

Receive a user task.

Build the initial conversation and task state.

Send the appropriate context to the model.

Parse and normalize the model response.

Determine whether the model:

Requests tool execution

Returns a final response

Returns an invalid or unexpected response

Validate each tool call.

Execute permitted tool calls.

Append results to the conversation.

Update task and execution state.

Continue until the task is complete or a termination condition is reached.

The loop must not rely on the model to manage its own execution limits or security boundaries.

4.2 Multiple tool calls

The runtime must support multiple tool calls in one model response.

Requirements:

Preserve each tool call's unique ID.

Preserve the correct assistant message structure.

Associate each tool result with its originating tool call ID.

Validate each call independently.

Handle one tool call failing without corrupting the others.

Ensure tool results are returned in the correct order.

Do not silently discard tool calls.

Initially, execute tool calls sequentially. Parallel execution can be introduced later after dependency and safety rules are designed.

4.3 Normalized model response

Create a provider-independent response representation.

Conceptually:

ModelResponse

message

tool_calls

finish_reason

usage

ToolCall

id

name

arguments

TokenUsage

input_tokens

output_tokens

total_tokens

The agent loop should consume this normalized representation rather than provider-specific response objects.

4.4 Typed agent state

The agent should maintain explicit state such as:

Current task

Conversation messages

Current plan

Plan progress

Iteration count

Tool-call count

Execution status

Workspace root

Current session ID

Last error

Cancellation state

Usage and cost metadata, when available

Avoid passing arbitrary dictionaries throughout the application.

4.5 Tool registry and dispatcher

The tool registry must define:

Tool name

Description

Argument schema

Handler

Permission category

Risk classification

Whether user approval is required

The dispatcher must:

Resolve the tool name.

Validate the arguments.

Check permissions.

Check whether approval is required.

Execute the handler.

Normalize the result.

Return a structured success or failure.

The dispatcher must not allow the model to bypass these steps.

4.6 Error handling

Use structured tool results.

A tool result should distinguish:

Success

Validation error

Permission denied

Tool not found

Execution error

Timeout

Cancelled

Errors should be informative enough for the agent to recover without exposing sensitive system information.

Do not catch all exceptions and return an empty string or generic success result.

4.7 Limits and cancellation

Implement configurable limits for:

Maximum agent iterations

Maximum tool calls

Maximum execution time

Per-tool timeout

Maximum command output

Maximum model response size

Support cancellation of a running task.

When a limit is reached:

Stop further execution.

Preserve relevant state.

Return a clear reason.

Report any partial changes already made.

5. Coding Capabilities

5.1 Filesystem tools

Maintain and improve the existing tools:

list_files

search_files

read_file

write_file

edit_file

Add:

create_directory

apply_patch

get_file_diff

The filesystem tool layer must remain independent of the model provider.

5.2 Patch support

Implement a patching capability that supports controlled file modifications.

Requirements:

Validate patch structure.

Validate target paths.

Detect when expected source content does not match.

Detect ambiguous patch application.

Avoid silently applying a patch to the wrong location.

Return a clear summary of applied changes.

Preserve file content when a patch fails.

Provide a diff before and after modification.

Do not implement a patch tool that blindly replaces arbitrary text without validating the intended target.

5.3 Directory creation

create_directory must:

Resolve the path inside the workspace.

Reject paths outside the workspace.

Handle existing directories predictably.

Avoid modifying unrelated paths.

Return a structured result.

5.4 Command execution

Implement a run_command tool.

It should support:

Executable and argument list

Working directory

Environment configuration

Timeout

Output size limit

Exit code

Standard output

Standard error

Cancellation

Execution duration

Prefer passing commands as an executable plus argument list instead of constructing shell command strings.

If shell execution is supported, treat it as a separate, higher-risk capability.

The command execution layer must not allow the model to choose an arbitrary working directory outside the configured workspace.

5.5 Testing tools

Forge should be able to run:

Unit tests

Integration tests

Project-specific test commands

Linting

Formatting

Type checking

The agent should inspect the repository to determine which commands are appropriate.

It must not assume every project uses pytest, npm, or a particular tool.

5.6 Change verification

After modifying files, Forge should:

Identify the changed files.

Inspect the resulting diff.

Verify that intended modifications were applied.

Run relevant tests when permitted.

Check command exit codes.

Report any remaining failures.

A model's statement that a change is successful is not sufficient verification.

6. Git Integration

Implement Git-aware tools:

git_status

git_diff

git_diff_file

git_create_checkpoint

git_restore_checkpoint

Requirements:

Detect whether the workspace is a Git repository.

Inspect changes before and after task execution.

Identify files modified by Forge.

Preserve unrelated user changes.

Avoid destructive Git commands by default.

Require approval for potentially destructive actions.

Checkpoint behavior

A checkpoint should provide a recoverable state for Forge's changes.

The implementation must consider:

Existing uncommitted user changes

Untracked files

Newly created files

Modified files

Deleted files

Recovery after a failed task

Do not assume that resetting the entire repository is a safe rollback strategy.

Initially, Forge should not automatically commit changes.

7. Agent Intelligence

7.1 Planning

Before making significant modifications, Forge should create a structured plan.

A plan should contain:

Task objective

Steps

Status of each step

Relevant files

Expected result

Verification strategy

Example:

Inspect project structure.

Identify the relevant module.

Read the implementation and tests.

Plan the change.

Modify the necessary files.

Run relevant tests.

Inspect the final diff.

Report the result.

The plan should be adaptable rather than rigid.

7.2 Plan tracking

Maintain plan state:

Pending

In progress

Completed

Failed

Blocked

Plan state must be stored in the agent's state model.

7.3 Replanning

Forge should replan when:

A required file is missing.

A command fails.

A test reveals an unexpected issue.

The current approach is no longer valid.

New information changes the task.

Replanning must not discard useful prior context.

7.4 Bounded self-correction

Forge may attempt to repair failures.

Example:

Modify a function.

Run tests.

Observe a failure.

Diagnose the failure.

Apply a correction.

Run the relevant test again.

Set configurable limits for repair attempts.

Do not allow infinite test-fix loops.

Forge must stop and report when it cannot make progress.

8. Repository Understanding

Forge must improve its ability to understand an unfamiliar codebase.

Initial repository inspection

Build a repository inspection capability that can identify:

Root directory

Project files

Source directories

Test directories

Configuration files

Dependency files

Entry points

README and documentation

Relevant Git metadata

Repository map

Create a lightweight repository map.

The map may include:

File tree

Main modules

Entry points

Dependencies

Tests

Important configuration

Known commands

The map should be generated on demand or cached with invalidation.

Relevant-file selection

Forge should select relevant files based on the task.

It should consider:

User task

Search results

Imports and dependencies

Tests

Configuration

Related symbols

Avoid reading the entire repository into the model context by default.

Future extensibility

Keep the architecture extensible for future:

AST-based inspection

Symbol navigation

Import graph

Semantic code search

Hybrid retrieval

These do not need to be implemented unless they materially improve the current version.

9. Context Management

Implement a dedicated context-building layer.

The context builder should determine what information is sent to the model.

Responsibilities

Assemble system instructions

Include the current user task

Include the current plan

Include relevant conversation history

Include relevant repository information

Include tool results

Include relevant errors and test output

Track context/token limits

Context budgeting

Forge must account for the model's context window.

Implement:

Configurable context budget

Relevant-file prioritization

Truncation of oversized tool results

Removal or summarization of obsolete information

Preservation of important instructions and state

Never silently truncate the user's task or critical tool-call history.

Context compaction

When the context becomes too large:

Preserve task instructions.

Preserve current plan.

Preserve relevant findings.

Preserve recent tool interactions.

Summarize older history.

Preserve important errors and unresolved issues.

Compaction should be explicit and testable.

10. Reliability and Safety

10.1 Workspace boundary

All filesystem operations must remain inside the configured workspace.

This includes:

Listing

Searching

Reading

Writing

Editing

Patching

Creating directories

File diff operations

10.2 Path validation

The path safety layer must handle:

Absolute paths

Relative paths

Parent traversal

Symbolic links

Existing and non-existing targets

Nested directories

Path normalization

Do not rely solely on checking whether a path string begins with the workspace path.

Consider symlink escapes and filesystem race conditions.

Use the strongest practical containment mechanisms available on the target platform.

10.3 Command permissions

Command execution must have a permission system.

Classify commands into risk categories.

Examples:

Read-only inspection

Local build/test

File modification

Network access

Destructive operation

Allow configurable policies:

Deny

Allow

Ask user

The model must not be able to grant itself permissions.

10.4 User approval

Require explicit approval for risky operations such as:

Destructive filesystem changes

Potentially destructive Git actions

Commands with broad system impact

Operations outside the default permitted scope

Network access when restricted

Approval must be enforced by Forge's runtime.

10.5 Sandboxing

Design command execution to support sandboxing.

The sandbox should constrain:

Filesystem access

Process execution

Network access

Environment variables

Resource usage

Use an appropriate OS-level isolation mechanism when available.

A workspace path check alone is not a sandbox.

10.6 Secrets

Avoid exposing:

API keys

Tokens

Credentials

Sensitive environment variables

Do not include secrets in logs or model context unless strictly necessary.

11. Session Persistence and Recovery

Implement persistent sessions.

A session should store:

Session ID

User task

Conversation history

Plan

Execution state

Tool-call records

Relevant errors

Changed-file information

Checkpoint metadata

Resume

Forge should be able to resume a previously interrupted task.

It must:

Load the session.

Validate the saved state.

Restore the plan and conversation.

Inspect the current workspace.

Detect changes made since the interruption.

Continue safely or ask the user to resolve conflicts.

Do not blindly replay previous tool calls.

Prefer replay-safe state restoration over replaying side-effecting commands.

SQLite is a suitable candidate for local session storage, but the final choice should be based on the existing architecture and requirements.

12. Structured Logging and Tracing

Implement structured observability.

Record:

Session ID

Task ID

Agent iteration

Model request

Tool call

Tool result

Tool duration

Command exit code

Error details

State transition

Token usage, when available

Use structured logs rather than scattered print statements.

Traceability

A user should be able to understand:

What Forge attempted

Which tools it called

Why a command failed

What files were changed

Whether tests passed

Why Forge stopped

Do not log secrets or unnecessarily large file contents.

13. Testing Requirements

Implement tests throughout development.

Unit tests

Cover:

Model response parsing

Multiple tool calls

Tool schema validation

Tool dispatch

Agent state transitions

Path validation

File editing

Patch application

Command execution

Context building

Plan tracking

Persistence

Permission enforcement

Integration tests

Cover realistic workflows:

Workflow A — Modify existing code

User asks for a code change.

Forge inspects the repository.

Forge plans the change.

Forge edits files.

Forge runs tests.

Forge inspects the diff.

Forge reports the outcome.

Workflow B — Create a new file

User asks to create a module.

Forge determines the correct location.

Forge creates the file.

Forge runs relevant validation.

Forge reports the new file.

Workflow C — Repair a failing test

Forge runs tests.

Test fails.

Forge diagnoses the failure.

Forge applies a bounded repair.

Forge reruns tests.

Forge reports whether the repair succeeded.

Workflow D — Security boundary

User or model attempts to access a path outside the workspace.

Forge rejects the operation.

No external file is modified.

Workflow E — Interrupted task

Forge starts a task.

Execution is interrupted.

The session is restored.

Forge inspects the current workspace.

Forge resumes safely.

14. Acceptance Criteria

Forge is considered ready for practical coding tasks when:

It can handle multiple tool calls correctly.

Tool arguments are validated before execution.

Tool-call IDs and message structure are preserved.

It can inspect, edit, and patch files.

It can execute permitted commands.

It can run tests and interpret exit codes.

It can plan and track a coding task.

It can recover from ordinary tool and test failures.

It can stop when limits are reached.

It can inspect its own changes.

All filesystem operations are workspace-restricted.

Command execution is permission-controlled.

Risky operations require approval.

Sessions can be saved and resumed safely.

Execution is observable through structured logs.

Automated tests cover the core behavior.

It reports incomplete or failed work honestly.