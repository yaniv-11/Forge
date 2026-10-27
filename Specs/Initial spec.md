# Forge — AI Coding Agent Harness
## Project Specification

**Version:** 0.1.0  
**Status:** Initial specification  
**Language:** Python  
**Interface:** CLI  
**Model provider:** Openrouter API (initial implementation)  
**Project type:** Local AI coding agent harness

---

# 1. Project Overview

## 1.1 Project Name

Forge

## 1.2 Vision

Forge is a locally executed AI coding agent inspired by the core capabilities of Codex.

The purpose of Forge is not merely to create an AI chatbot that can generate code. Its purpose is to build a functional coding agent harness that demonstrates how an AI coding agent operates internally.

The project will be implemented from scratch, with a focus on understanding the architecture, design decisions, execution flow, failure handling, security, and trade-offs involved in building a reliable agent.

Forge will initially operate through a CLI and work within a local repository.

## 1.3 Primary Objective

Build a coding agent that can:

- Understand a user's coding task.
- Inspect an existing repository.
- Read and search source files.
- Plan and implement code changes.
- Modify multiple files.
- Execute commands and tests.
- Observe tool results.
- Recover from errors.
- Iterate until the task is completed or a limit is reached.
- Present a summary of changes to the user.

The long-term objective is to implement the fundamental harness capabilities found in sophisticated coding agents, including tool orchestration, persistent sessions, context management, sandboxing, approval policies, and recovery.

## 1.4 Learning Objective

The project must be developed as an engineering learning experience.

Every major component should be implemented with a clear understanding of:

- What problem it solves.
- Why the component is necessary.
- How it interacts with other components.
- What alternative approaches exist.
- Why a particular approach was selected.
- What its limitations are.
- How it can fail.
- How its behavior can be tested.

The project must not be developed through unstructured code generation or framework-first implementation.

---

# 2. Development Philosophy

Forge will be developed incrementally, brick by brick.

The following principles apply:

1. No large code dumps.
2. No implementation before the relevant design is understood.
3. No architectural decision without examining alternatives.
4. No framework abstraction without understanding the underlying mechanism.
5. No moving to the next milestone before the current milestone is tested.
6. No hidden tool execution.
7. No unbounded agent loops.
8. No unrestricted filesystem or shell access.
9. No pretending that an operation succeeded when it failed.
10. No unnecessary complexity before a requirement justifies it.

Each milestone should produce a working and testable system.

---

# 3. User Experience

## 3.1 Primary Interface

Forge will be a command-line application.

The user should be able to start Forge from the repository they want it to work on.

Example:

```bash
cd my-project
forge
```

Forge should initialize a session and identify the current repository as its initial workspace.

The user can then enter a coding task:

```text
forge> Add input validation to the registration endpoint.
```

Forge should inspect the project, determine which files are relevant, make appropriate changes, execute tests when necessary, and provide a final summary.

## 3.2 One-Shot Command

Forge should eventually support:

```bash
forge "Fix the failing tests"
```

This allows the user to provide a task directly from the shell.

## 3.3 Interactive Session

The interactive CLI should eventually support:

- Submitting tasks.
- Viewing progress.
- Cancelling execution.
- Approving or rejecting sensitive operations.
- Viewing tool execution results.
- Continuing an existing session.
- Exiting without losing persistent session data.

These capabilities will be implemented incrementally.

---

# 4. System Scope

## 4.1 Initial Scope

The initial implementation will focus on:

- Python.
- CLI interaction.
- Openrouter  API.
- Agent orchestration.
- Typed tool definitions.
- Tool registry and dispatcher.
- Basic file tools.
- A minimal agent execution loop.
- Unit and integration testing.

## 4.2 Long-Term Scope

The complete Forge project is expected to include:

- Tool management.
- Workspace management.
- Sandboxing.
- Persistence.
- Session recovery.
- Context management.
- Approval policies.
- Coding workflows.
- Git integration.
- Observability.
- Evaluation.
- MCP integration.
- Optional subagent support.

## 4.3 Out of Scope Initially

The following will not be implemented in the first milestone:

- Web UI.
- GUI.
- Cloud-hosted execution.
- Multi-user collaboration.
- Distributed agent orchestration.
- Autonomous background operation.
- Complex multi-agent planning.

These may be reconsidered after the core harness is functional.

---

# 5. Architectural Overview

The initial conceptual architecture is:

```text
                    User
                     |
                     v
                  CLI Layer
                     |
                     v
                 Agent Loop
                     |
          +----------+----------+
          |                     |
          v                     v
     Model Client         Tool Dispatcher
          |                     |
          v                     v
      Openrouter API           Tool Registry
                                |
                                v
                         Execution Policy
                                |
                                v
                          Tool Runtime
                                |
              +-----------------+----------------+
              |                 |                |
              v                 v                v
          File Tools       Search Tools     Shell Tools
              |                 |                |
              +-----------------+----------------+
                                |
                                v
                         Local Workspace
```

Future components:

```text
             +-------------------------+
             | Persistence / Sessions  |
             +-------------------------+

             +-------------------------+
             | Context Management      |
             +-------------------------+

             +-------------------------+
             | Sandbox / Permissions  |
             +-------------------------+

             +-------------------------+
             | Approval Policies       |
             +-------------------------+

             +-------------------------+
             | Observability / Evals   |
             +-------------------------+
```

This is a conceptual architecture, not a finalized module structure.

The implementation structure may evolve as we learn more about the responsibilities and boundaries of each component.

---

# 6. Core Components

## 6.1 CLI Layer

Responsibilities:

- Accept user input.
- Identify the workspace.
- Start and manage sessions.
- Display model responses.
- Display tool activity.
- Handle cancellation.
- Handle user approvals.

The CLI should not contain the agent's reasoning or tool execution logic.

## 6.2 Model Client

Responsibilities:

- Communicate with the Openrouter API.
- Send conversation messages.
- Send tool definitions.
- Receive model responses.
- Parse tool calls.
- Handle API errors.
- Handle timeouts and rate limits.
- Track model usage where available.

The model client should be separated from the agent loop.

This separation will allow Forge to support additional model providers in the future.

## 6.3 Agent Orchestrator

Responsibilities:

- Manage the agent execution loop.
- Send messages to the model.
- Interpret model responses.
- Dispatch tool requests.
- Add tool results to the conversation.
- Determine when the agent has completed its task.
- Enforce execution limits.
- Handle errors and cancellation.

The initial implementation will use an explicit agent loop.

A state machine or graph-based orchestrator may be introduced later if the requirements justify it.

## 6.4 Tool Registry

Responsibilities:

- Register available tools.
- Store tool definitions.
- Expose tool metadata.
- Provide model-facing tool schemas.
- Retrieve tools by name.
- Prevent duplicate registrations.

## 6.5 Tool Dispatcher

Responsibilities:

- Receive a model-generated tool request.
- Validate the tool name.
- Validate tool arguments.
- Apply execution policies.
- Invoke the appropriate handler.
- Normalize tool results.
- Return errors in a consistent format.

The model must never directly execute Python code or operating system commands.

All tool execution must pass through the harness.

## 6.6 Tool Runtime

Responsibilities:

- Execute registered tool handlers.
- Manage execution timeouts.
- Handle subprocess lifecycle.
- Capture stdout and stderr.
- Return structured results.
- Enforce resource limits where supported.

## 6.7 Workspace Manager

Responsibilities:

- Identify the authorized workspace.
- Resolve file paths.
- Validate path access.
- Prevent unintended access outside the workspace.
- Manage file operations.
- Support repository-aware operations.

The workspace manager will become a central component of the security architecture.

## 6.8 Persistence Layer

Future responsibilities:

- Save sessions.
- Save conversation history.
- Save tool execution records.
- Save checkpoints.
- Resume interrupted sessions.
- Recover state after process crashes.

The persistence approach has not yet been finalized.

## 6.9 Context Manager

Future responsibilities:

- Track context usage.
- Select relevant conversation history.
- Manage tool result sizes.
- Reduce context when necessary.
- Summarize earlier interaction.
- Preserve important task information.

The context manager should be introduced after the basic agent loop is understood.

---

# 7. Functional Requirements

## FR-01: Start a session

The user must be able to launch Forge from a repository directory.

## FR-02: Submit a task

The user must be able to provide a coding task through the CLI.

## FR-03: Communicate with the model

Forge must send the task and relevant context to the configured model provider.

## FR-04: Request tools

The model must be able to request tools through structured tool calls.

## FR-05: Execute tools

Forge must validate and execute tool requests.

## FR-06: Return tool results

Tool results must be returned to the model in a structured form.

## FR-07: Continue execution

Forge must support repeated model/tool interactions until the task is completed or an execution limit is reached.

## FR-08: Inspect a repository

Forge must be able to list files, read files, and search repository contents.

## FR-09: Modify files

Forge must be able to create and modify files within the authorized workspace.

## FR-10: Execute commands

Forge must eventually be able to execute tests, linters, and other project commands under defined execution policies.

## FR-11: Handle failures

Forge must capture and handle model errors, tool errors, timeouts, and execution failures.

## FR-12: Present a result

Forge must provide a final response describing the outcome of the task.

## FR-13: Preserve sessions

Forge must eventually support persistent sessions and recovery.

---

# 8. Non-Functional Requirements

## NFR-01: Security

Forge must not allow model-generated tool requests to bypass harness policies.

## NFR-02: Reliability

Tool failures must not silently corrupt the agent state.

## NFR-03: Observability

The user and developer must be able to understand what the agent is doing.

## NFR-04: Testability

The core harness must be testable without making real model API calls.

## NFR-05: Extensibility

New tools and model providers should be addable without rewriting the core agent loop.

## NFR-06: Maintainability

Components should have clear responsibilities and explicit interfaces.

## NFR-07: Resource Limits

Agent execution must have configurable limits on:

- Number of model iterations.
- Tool execution duration.
- Tool output size.
- Total execution time.
- Model usage where supported.

---

# 9. Initial Design Decisions and Alternatives

## ADR-001: Interface

**Decision:** CLI.

Rationale:

- Natural for local coding workflows.
- Supports repository-based execution.
- Keeps the initial scope focused on the harness.
- Allows later integration with editors and development tools.

## ADR-002: Orchestration

**Initial approach:** Explicit agent loop.

Alternatives:

- Explicit loop.
- State machine.
- Graph-based orchestration.

The explicit loop is selected for the initial implementation because it exposes the fundamentals of agent execution.

The architecture must remain open to introducing a state machine as execution complexity increases.

## ADR-003: Tool Management

**Initial approach:** Typed tool schemas, central registry, and dispatcher.

Alternatives:

- Direct function calls.
- Central registry and dispatcher.
- Plugin-based runtime.

The registry and dispatcher provide a balance between simplicity and extensibility.

## ADR-004: Agent State

**Initial approach:** Typed state object.

Alternatives:

- Mutable dictionary.
- Typed state object.
- Event-sourced state.

A typed state object makes the execution state explicit and easier to validate.

## ADR-005: Persistence

**Decision:** Deferred.

Candidates:

- JSON.
- JSONL event log.
- SQLite.

SQLite is a candidate for the long-term implementation, but the final decision will be made after examining persistence requirements and failure scenarios.

## ADR-006: Model Provider

**Initial approach:** Open Router API.

The model client should be isolated behind a provider interface so that other providers can be added later.

## ADR-007: Workspace

**Initial approach:** Current repository directory.

The workspace must be explicitly authorized and enforced by the harness.

## ADR-008: Sandbox

**Decision:** Deferred implementation.

The sandbox design must be finalized before unrestricted shell execution is exposed.

Potential approaches include:

- Restricted subprocess execution.
- Operating-system-level restrictions.
- Container-based execution.

The choice must account for security, usability, portability, and complexity.

---

# 10. Security Requirements

Security is a fundamental part of the harness, not a feature to add at the end.

## 10.1 Workspace Isolation

File operations must be restricted to the authorized workspace.

Forge must defend against:

- Path traversal.
- Absolute paths outside the workspace.
- Symlink escapes.
- Unexpected working-directory changes.

## 10.2 Shell Execution

Shell execution must not be unrestricted by default.

The design must address:

- Command authorization.
- Working directory.
- Environment variables.
- Timeouts.
- Output limits.
- Process termination.
- Network access.
- Filesystem access.

## 10.3 Tool Validation

All tool arguments must be validated before execution.

Tool schemas must not be treated as a security boundary by themselves.

The runtime must independently enforce the relevant restrictions.

## 10.4 Approval Policies

Future approval policies should allow the user to:

- Approve a sensitive action.
- Reject an action.
- Allow a category of actions.
- Configure permissions for a session.

The approval system must be enforced by the harness, not by the model's instructions.

## 10.5 Secrets

API keys and other secrets must not be:

- Hardcoded in source code.
- Exposed to the model unnecessarily.
- Written into logs.
- Included in tool outputs without a reason.

---

# 11. Milestone Roadmap

## Milestone 0 — Specification and Architecture

Objectives:

- Finalize the project specification.
- Establish the development workflow.
- Define the architecture.
- Record initial ADRs.
- Define module boundaries.
- Define testing principles.

Deliverables:

- FORGE_SPEC.md
- Initial architecture diagram.
- Initial ADRs.
- Project setup plan.

Acceptance criteria:

- Responsibilities of the main components are understood.
- Initial decisions are documented.
- Open decisions are clearly identified.

## Milestone 1 — Minimal Agent Loop

Objectives:

- Set up the Python project.
- Implement the model client.
- Define typed tool schemas.
- Implement the tool registry.
- Implement the dispatcher.
- Implement the explicit agent loop.
- Add a minimal CLI.
- Add unit tests and integration tests.

Initial tools may include:

- list_files
- read_file

Acceptance criteria:

- Forge can accept a task.
- Forge can communicate with the model.
- The model can request a registered tool.
- The harness executes the tool.
- The result is returned to the model.
- The model can continue and produce a final answer.
- Execution limits are enforced.
- Tests pass without requiring a live API call for every test.

## Milestone 2 — Coding Tools

Objectives:

- Implement file searching.
- Implement file writing.
- Implement structured patch application.
- Implement file creation and deletion.
- Standardize tool results.

Acceptance criteria:

- Forge can inspect and modify a small repository.
- Tool failures are surfaced correctly.
- File changes can be verified through tests.

## Milestone 3 — Workspace and Sandbox

Objectives:

- Implement workspace management.
- Restrict filesystem access.
- Design command execution.
- Introduce execution policies.
- Implement process timeouts.
- Handle subprocess output and termination.

Acceptance criteria:

- File operations cannot escape the authorized workspace under tested conditions.
- Shell commands execute under explicit policies.
- Timeouts and failures are handled safely.
- Security tests cover known attack paths.

## Milestone 4 — Persistence and Recovery

Objectives:

- Implement session storage.
- Store messages and tool execution records.
- Implement checkpoints.
- Support session resumption.
- Handle interrupted execution.

Acceptance criteria:

- A session can be resumed after the CLI exits.
- Session history can be reconstructed.
- Interrupted operations are represented accurately.
- Recovery behavior is tested.

## Milestone 5 — Context Management

Objectives:

- Implement context tracking.
- Measure token usage where possible.
- Manage large tool outputs.
- Introduce history reduction.
- Preserve important task information.

Acceptance criteria:

- Long sessions do not grow context without limits.
- Context reduction preserves task-relevant information.
- The system handles context-limit errors.

## Milestone 6 — Coding Workflow

Objectives:

- Implement task planning.
- Implement iterative code changes.
- Run tests.
- Observe failures.
- Fix errors.
- Summarize modifications.

Acceptance criteria:

- Forge can complete a representative coding task in a small repository.
- The task can involve multiple files.
- Tests can be executed and their results observed.
- The final result reflects actual changes.

## Milestone 7 — Advanced Harness Capabilities

Potential features:

- Approval policies.
- Parallel tool execution.
- MCP tool integration.
- Subagents.
- Git-aware workflows.
- Advanced context management.
- Observability.
- Evaluation framework.
- More robust recovery.
- Additional model providers.

These features will be prioritized after the core harness is functional.

---

# 12. Testing Strategy

Testing must be implemented alongside each component.

## Unit Tests

Test individual components:

- Model client request construction.
- Tool schema validation.
- Tool registry behavior.
- Dispatcher behavior.
- Workspace path validation.
- Agent state transitions.
- Persistence operations.

## Integration Tests

Test interactions between components:

- Agent loop with mocked model responses.
- Model tool call to dispatcher.
- Tool result returned to model.
- Multiple tool calls in a single session.
- Error handling and retries.

## Security Tests

Test:

- Path traversal.
- Symlink escapes.
- Unauthorized file access.
- Invalid tool arguments.
- Command execution restrictions.
- Timeout handling.
- Output limits.

## End-to-End Tests

Eventually, test Forge against small repositories containing predefined tasks.

Measure:

- Task completion.
- Correctness of changes.
- Test outcomes.
- Tool failures.
- Number of model iterations.
- Token usage.
- Execution duration.

---

# 13. Proposed Initial Project Structure

This structure is a starting proposal and may change after the architecture is finalized.

```text
forge/
├── pyproject.toml
├── README.md
├── FORGE_SPEC.md
├── .env.example
│
├── docs/
│   ├── architecture.md
│   └── adr/
│
├── src/
│   └── forge/
│       ├── __init__.py
│       ├── cli.py
│       │
│       ├── agent/
│       │   ├── loop.py
│       │   └── state.py
│       │
│       ├── model/
│       │   ├── client.py
│       │   └── schemas.py
│       │
│       ├── tools/
│       │   ├── registry.py
│       │   ├── dispatcher.py
│       │   └── definitions.py
│       │
│       ├── workspace/
│       │   └── manager.py
│       │
│       ├── runtime/
│       │   └── executor.py
│       │
│       └── persistence/
│           └── ...
│
└── tests/
    ├── unit/
    ├── integration/
    └── security/
```

The actual module boundaries will be finalized during Milestone 0 and refined during implementation.

---

# 14. Development Workflow

For each component:

1. Identify the problem.
2. Explore alternative approaches.
3. Discuss trade-offs.
4. Select an approach.
5. Write its interface and requirements.
6. Implement the smallest useful version.
7. Write tests.
8. Run tests.
9. Review the implementation.
10. Record any architectural decisions.
11. Move to the next component.

The developer should understand the code before proceeding to the next component.

---

# 15. Definition of Project Success

Forge will be considered successful when it demonstrates a reliable local coding agent harness capable of:

- Operating from a repository through a CLI.
- Interacting with a model through structured requests.
- Managing and executing tools.
- Inspecting and modifying code.
- Running commands within defined restrictions.
- Handling tool failures and execution limits.
- Maintaining persistent sessions.
- Recovering from interruptions.
- Managing context across longer tasks.
- Providing observable and testable behavior.

The primary success criterion is not merely that Forge can generate code.

The primary success criterion is that the developer understands how the harness works internally and can explain the design, execution flow, trade-offs, and failure modes of each major component.

---

# 16. Immediate Next Step

Begin with **Milestone 0: Specification and Architecture**.

The next tasks are:

1. Create the Python project in VS Code.
2. Add this specification as `FORGE_SPEC.md`.
3. Finalize the initial architectural decisions.
4. Define the minimal agent loop contract.
5. Define the model client interface.
6. Define the tool schema and dispatcher interface.
7. Define the initial test plan.
8. Begin Milestone 1 only after the interfaces are understood.

Forge will be built incrementally, with each component designed, implemented, tested, and reviewed before moving forward.
