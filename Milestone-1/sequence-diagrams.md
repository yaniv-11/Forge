# Sequence Diagrams for Milestone 1

## 1. Basic task flow

```text
User->CLI: enters task
CLI->AgentLoop: run(task)
AgentLoop->ModelClient: send_messages(messages, tools)
ModelClient->Groq API: POST chat completion
Groq API-->ModelClient: model response
ModelClient-->AgentLoop: { final_answer } or { tool_call }

alt tool call present
    AgentLoop->ToolDispatcher: execute(tool_call)
    ToolDispatcher->ToolRegistry: get(name)
    ToolRegistry-->ToolDispatcher: tool definition
    ToolDispatcher->ToolHandler: invoke(**kwargs)
    ToolHandler-->ToolDispatcher: structured result
    ToolDispatcher-->AgentLoop: {status, result}
    AgentLoop->AgentLoop: append result to messages
    AgentLoop->ModelClient: send_messages(updated_messages)
else final answer present
    AgentLoop-->CLI: final answer
end
CLI-->User: present result
```

## 2. Failure path

```text
AgentLoop->ModelClient: request
ModelClient-->AgentLoop: failure / timeout / malformed output
AgentLoop->AgentLoop: record last_error
AgentLoop-->CLI: stop with failure summary
CLI-->User: explain what failed and why
```

## 3. Tool validation path

```text
Model response->ToolDispatcher: tool_call
ToolDispatcher->ToolDispatcher: check name format
ToolDispatcher->ToolRegistry: resolve tool by name
ToolRegistry-->ToolDispatcher: ToolDefinition or KeyError
ToolDispatcher->ToolDispatcher: validate arguments schema
alt valid
    ToolDispatcher->ToolHandler: execute
    ToolHandler-->ToolDispatcher: output
    ToolDispatcher-->AgentLoop: success payload
else invalid
    ToolDispatcher-->AgentLoop: error payload
end
```

## 4. Loop limit path

```text
AgentLoop->AgentLoop: increment steps and tool_calls
AgentLoop->AgentLoop: compare against configured maximums
alt limit reached
    AgentLoop-->CLI: final answer with stop reason
else continue loop
    AgentLoop->ModelClient: next iteration
end
```

## 5. Design interpretation

These diagrams show the actual shape of the harness: the agent loop is the coordinator, the model client is the provider boundary, and the tool dispatcher is the enforcement boundary. This is the critical architectural pattern that makes the system safe, observable, and testable.
