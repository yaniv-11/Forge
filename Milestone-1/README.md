# Milestone 1 — Minimal Agent Loop

This folder captures the first working milestone for Forge as described in the project specification.

## Goal

Build the smallest viable coding-agent harness that can:

- accept a task from the CLI,
- talk to a model provider,
- request registered tools,
- execute those tools safely through a dispatcher,
- loop until completion or a limit is reached,
- return a final answer to the user.

## Scope included in this milestone

- Python project skeleton
- typed agent state and tool contract
- Groq client abstraction
- tool registry and dispatcher
- CLI entry point
- initial file tools
- execution-limit enforcement
- test coverage for core behavior

## Core design decisions

1. The model client is isolated behind an interface so provider swaps remain possible.
2. The agent loop is explicit rather than hidden in framework magic.
3. Tool execution always passes through a registry and dispatcher.
4. The workspace is explicitly constrained and validated.
5. The system is structured so it can be tested without a live model call in every unit test.

## Folder structure

- `architecture.md` — component responsibilities and boundaries
- `execution-flow.md` — the precise user and agent runtime flow
- `sequence-diagrams.md` — end-to-end system interactions
- `../src/forge` — Python implementation skeleton
- `../tests` — unit tests for the initial loop

## Milestone acceptance criteria mapped to this implementation

- Forge accepts a task through a minimal CLI.
- The model client is separate from orchestration logic.
- Registered tools can be requested and dispatched.
- Tool results are returned in a structured format.
- The loop supports iteration with limits.
- The harness remains testable without living on a real API call during every test.
