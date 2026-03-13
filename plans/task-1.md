# Task 1 plan

- LLM provider: Qwen Code API (OpenAI-compatible chat completions).
- Model: qwen3-coder-plus.
- Read config from env vars: LLM_API_KEY, LLM_API_BASE, LLM_MODEL.
- agent.py:
  - Parse question from argv[1].
  - Build a chat completion request with a short system prompt.
  - Call LLM via HTTP (openai client или requests+json).
  - Print JSON: {"answer": "...", "tool_calls": []} to stdout.
  - All debug prints go to stderr.
- Tests:
  - Run `uv run agent.py "test question"` via subprocess.
  - Parse stdout as JSON.
  - Assert keys "answer" (non-empty string) and "tool_calls" (list) exist.
