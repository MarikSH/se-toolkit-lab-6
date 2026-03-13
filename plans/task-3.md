# Task 3 plan — System Agent

## query_api tool

- Implement `query_api` in `agent.py` to call the deployed backend.
- Read configuration from env vars:
  - `AGENT_API_BASE_URL` (default: `http://localhost:42002`).
  - `LMS_API_KEY` for auth (from `.env.docker.secret`).
- Parameters:
  - `method: string` (GET, POST, etc.).
  - `path: string` (e.g. `/items/`).
  - `body: string` (optional JSON request body).
- Return a JSON string with:
  - `status_code` and `body` fields.

## Tool schemas and routing

- Extend the existing tool schemas from Task 2:
  - Add `query_api` to the `tools` list for function calling.
- Update the system prompt so the LLM:
  - Uses wiki tools for documentation questions.
  - Uses `query_api` for live data or system status.
  - Uses `read_file` on source code when debugging errors.

## Eval and iteration

- After the first implementation:
  - Run `uv run run_eval.py` to get an initial score.
  - Note the first failing questions and their feedback in this file.
- Iteration strategy:
  - For each failing question, inspect:
    - Which tools are used in `tool_calls`.
    - API responses (status codes, error messages).
  - Improve tool descriptions and prompt wording.
  - Fix bugs in tools or code paths revealed by the benchmark.
