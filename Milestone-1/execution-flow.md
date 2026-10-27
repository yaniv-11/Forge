# Execution Flow for Milestone 1

## 1. User flow

A user starts Forge from a repository directory and enters a task.

```text
user -> CLI -> AgentLoop -> ModelClient -> Groq API
```

The CLI starts the session, resolves the workspace, and passes the user task to the orchestrator.

## 2. Agent execution loop

The agent loop runs in a controlled sequence:

1. Initialize state.
2. Build the system prompt and conversation history.
3. Send a request to the model, including available tools.
4. Receive a model response.
5. If the response includes a tool call, validate and dispatch it.
6. Add tool output back into the conversation.
7. Repeat until the model produces a final answer or the limit is reached.
8. Return a final summary to the user.

## 3. Tool-call flow

```text
Model response -> Tool call payload -> ToolRegistry lookup -> Dispatcher validation -> Tool runtime -> result -> conversation
```

Important details:

- the model does not directly call Python objects,
- the dispatcher enforces validation before execution,
- tool output is normalized and included in the next model request,
- repeated tool execution is bounded by a step limit.

## 4. Failure flow

When a tool or model call fails, the system does not continue blindly.

```text
error event -> capture error -> append to state -> decide retry vs stop -> return structured failure information
```

Examples:

- malformed tool arguments,
- tool not found,
- model API timeout,
- unexpected exception in a tool,
- execution limit reached.

## 5. Loop limits

Milestone 1 includes an explicit execution cap. This is essential to prevent agent loops from running forever.

The loop guard can enforce:

- maximum tool calls,
- maximum model turns,
- maximum total runtime,
- final answer fallback if the model keeps looping.

## 6. Final answer flow

The system ends in a final result phase:

```text
agent decides task complete -> final response generated -> user sees summary -> tool trace remains available for debugging
```

This final response should include:

- what was completed,
- which tool results influenced the outcome,
- whether a limit or error interrupted the run,
- what remains unresolved if execution stopped early.

## 7. Design implication

This sequence is intentionally simple, but it mirrors the real core of a coding agent. The important milestone is not autonomous intelligence; it is a trustworthy and observable loop with safe tool execution and structured feedback.
