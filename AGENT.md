# Agent architecture and tools

This repository contains a CLI **agent** implemented in `agent.py`. The agent is designed to answer questions about the LMS project by combining three capabilities: reading documentation, inspecting source code and wiki files, and querying the running backend API. It uses an OpenAI-compatible LLM as the reasoning engine and wraps that model in an agentic loop with tool calling.

## Configuration and CLI

The agent is invoked from the project root with:

- `uv run agent.py "Your question"`

All configuration comes from environment variables (no hardcoded keys):

- `LLM_API_KEY`, `LLM_API_BASE`, `LLM_MODEL` for the LLM provider (from `.env.agent.secret`).
- `LMS_API_KEY` for authenticating requests to the backend API (from `.env.docker.secret`).
- `AGENT_API_BASE_URL` for the system API base URL, defaulting to `http://localhost:42002`.

The agent prints a single JSON object to stdout with fields:

- `answer`: final answer text.
- `source`: optional wiki/source reference (e.g. `wiki/git-workflow.md#resolving-merge-conflicts`).
- `tool_calls`: the sequence of tool calls made, including `tool`, `args`, and `result`.

## Tools

The agent exposes three tools as OpenAI function-calling schemas:

- `list_files(path: str)`: lists entries under a directory relative to the repo root.
- `read_file(path: str)`: reads a file from the repository with path safety checks.
- `query_api(method: str, path: str, body?: string)`: calls the deployed backend API with `LMS_API_KEY` authentication and returns a JSON string containing `status_code` and `body`.

All file paths are resolved relative to `REPO_ROOT` and validated to prevent escaping the project directory.

## Agentic loop and behavior

The agent builds an initial message list (system + user) and sends it to the LLM together with the tool schemas. When the LLM responds with `tool_calls`, the agent executes each tool, appends a `tool` role message with the result, and calls the LLM again. This loop repeats up to 10 iterations. When the LLM returns a normal assistant message without tool calls, the agent treats it as the final answer and returns the JSON structure.

The system prompt instructs the LLM to:

- Use `list_files` and `read_file` to explore the wiki and codebase for documentation questions and bug diagnosis.
- Use `query_api` to answer live system and data questions such as counts, completion rates, or item lists.
- Prefer documentation and source code for static facts like framework, ports, or status codes.
- Include a meaningful `source` reference when the answer is based on wiki or code, and clearly indicate when data comes from the live API.

## Lessons learned

While building this agent, several practical patterns emerged:

- Clear tool descriptions and parameter docs significantly improve the LLM’s choice of tools.
- Path security is important: resolving and validating paths prevents accidental access outside the repo.
- Separating LLM configuration from system API configuration (two types of keys, different base URLs) makes the agent easier to run under both local and autochecker environments.
- Iterating with a local benchmark (such as `run_eval.py`) is essential: it reveals where the agent underuses tools, misinterprets endpoints, or returns answers that fail keyword checks.
