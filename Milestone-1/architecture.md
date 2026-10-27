# Architecture for Milestone 1

## 1. Architectural overview

Forge at this stage is intentionally small but composed around clear layers.

```text
User
  |
  v
CLI
  |
  v
AgentLoop
  |        \_
  |         \_ calls model
  |            |
  v            v
ModelClient   ToolDispatcher
  |            |
  |            v
  |       ToolRegistry
  |            |
  |            v
  |        ToolRuntime
  v
Groq API

Local workspace
```

The important design idea is not the exact package layout, but the separation of concerns:

- the CLI is only an entry point,
- the orchestration logic owns the execution loop,
- the model client owns provider communication,
- tools are defined in a registry and executed by a dispatcher,
- the workspace is a security boundary,
- tests validate the harness without depending on live API calls.

## 2. Component responsibilities

### 2.1 CLI layer

The CLI is responsible for:

- collecting the task,
- identifying the active repository or workspace,
- instantiating the agent,
- printing final output,
- surfacing error messages and loop limits.

It does not decide tool logic or model reasoning.

### 2.2 Agent loop

This is the orchestration heart of the system. It keeps the sequence:

1. receive task,
2. send messages with tool schema to the model,
3. inspect the model response,
4. dispatch any tool call,
5. append tool output,
6. continue until final answer or stop condition.

This loop is explicit and stateful. It is easier to understand, debug, and test than a more implicit framework-driven approach.

### 2.3 Model client

The model client has one main purpose: communicate with the configured provider. It should handle:

- request construction,
- JSON payload formatting,
- response parsing,
- tool-call extraction,
- API errors and retryable conditions.

This component is intentionally separated so the system can later support OpenAI, Anthropic, or Groq without rewriting the orchestration layer.

### 2.4 Tool registry

The registry owns the definition of which tools are available to the agent.

Each tool is described by:

- a unique name,
- argument schema,
- a Python callable,
- metadata such as description and safety constraints.

This central registry keeps all tools discoverable and prevents duplicates.

### 2.5 Tool dispatcher

The dispatcher does the runtime enforcement step.

It takes a model-generated tool call and performs:

- tool name validation,
- argument validation,
- execution policy checks,
- callable invocation,
- result normalization,
- consistent error reporting.

This is the security checkpoint between AI output and actual system operations.

### 2.6 Workspace boundary

The workspace boundary is not yet a full sandbox, but its core principle is clear: the system may operate on only the authorized repository root.

This is where path normalization, allowed directory checks, and symlink protections begin.

## 3. Why this architecture

This design was selected because it balances simplicity and extensibility.

### Benefits

- clear responsibilities,
- easier testing,
- fewer hidden side effects,
- safer tool execution,
- straightforward provider swap-out.

### Trade-offs

- the loop is deliberately simple and not yet highly adaptive,
- tool calls are not yet persisted,
- the system is still local and single-process,
- sandboxing is intentionally deferred.

## 4. Failure boundaries

There are a few major places where things can fail:

1. model request or response failure,
2. invalid tool call from the model,
3. execution policy rejection,
4. runtime tool error,
5. loop exhaustion.

Each failure is surfaced as structured data and must not silently mutate the agent state.

## 5. Testability

The design allows unit tests to validate:

- registry behavior,
- schema validation,
- tool dispatch decisions,
- loop stop conditions,
- final summarization output,
- failure modes without real model calls.

This is a core requirement from the project specification.

## 6. Milestone 1 design principle

The goal of this milestone is not to create a perfect autonomous coder. It is to create a small but honest harness that demonstrates how an agent loop, tool registry, dispatcher, and provider boundary fit together in a real system.
