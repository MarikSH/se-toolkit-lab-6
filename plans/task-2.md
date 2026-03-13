# Task 2 plan — Documentation Agent

## Tools and schemas

- Implement two tools in `agent.py`:
  - `list_files(path: str)` → newline-separated list of entries.
  - `read_file(path: str)` → file contents or error string.
- Define OpenAI-style tool schemas in the LLM request:
  - `{"type": "function", "function": {"name": "list_files", "parameters": {...}}}`
  - `{"type": "function", "function": {"name": "read_file", "parameters": {...}}}`

## Agentic loop

- Send initial messages: system + user, plus tool definitions.
- While tool calls exist and count < 10:
  - Parse `tool_calls` from LLM response.
  - For each tool call:
    - Execute `list_files` or `read_file`.
    - Append a `tool` role message with the result.
  - Call the LLM again with updated messages.
- When response has only a normal `assistant` message:
  - Extract `answer` text and `source` (path + section anchor).
  - Return JSON with `answer`, `source`, `tool_calls`.

## Path security

- Resolve all paths relative to repo root with `Path().resolve()`.
- Reject any path that escapes the project root:
  - If `resolved_path.is_relative_to(repo_root)` is false → return an error string.
- For `list_files`, if path is a file or missing → return a readable error string instead of raising.

