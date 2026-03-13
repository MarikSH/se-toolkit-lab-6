# Task 2 plan — Documentation Agent

## Tools

- Implement two tools in `agent.py`:
  - `list_files(path: str)` → newline-separated listing.
  - `read_file(path: str)` → file contents or error string.
- Expose them as OpenAI function-calling tools:
  - `tools = [{"type": "function", "function": {"name": "list_files", ...}}, ...]`.

## Agentic loop

- Build initial messages: system prompt + user question.
- Call the LLM with tools enabled.
- If response has `tool_calls`:
  - Execute each tool.
  - Append `tool` role messages with results.
  - Repeat up to 10 iterations.
- If response has only assistant message:
  - Treat it as final answer, extract `answer` and `source`.

## Path security

- Resolve all paths relative to repo root.
- Forbid paths that escape the repo (no `..` outside root).
- Return readable error messages instead of raising exceptions.
