# Agent instructions

This repository includes a simple CLI **agent** implemented in `agent.py`.

## How to run

- From the project root:
  - `uv run agent.py "Your question"`
- The agent reads LLM configuration from environment variables:
  - `LLM_API_KEY`
  - `LLM_API_BASE`
  - `LLM_MODEL`

## Output format

- Prints a single JSON object to stdout:
  - `{"answer": "<string>", "tool_calls": []}`
- No extra logs on stdout; errors go to stderr.
