import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urljoin

import requests


REPO_ROOT = Path(__file__).resolve().parent


def load_llm_config() -> Dict[str, str]:
    api_key = os.getenv("LLM_API_KEY")
    api_base = os.getenv("LLM_API_BASE")
    model = os.getenv("LLM_MODEL")

    if not api_key or not api_base or not model:
        print(
            "Missing LLM_API_KEY, LLM_API_BASE, or LLM_MODEL in environment",
            file=sys.stderr,
        )
        sys.exit(1)

    return {"api_key": api_key, "api_base": api_base, "model": model}


def load_api_config() -> Dict[str, str]:
    base_url = os.getenv("AGENT_API_BASE_URL", "http://localhost:42002")
    api_key = os.getenv("LMS_API_KEY")
    if not api_key:
        print("Missing LMS_API_KEY in environment", file=sys.stderr)
        sys.exit(1)
    return {"base_url": base_url.rstrip("/"), "api_key": api_key}


def safe_resolve(path: str) -> Path:
    candidate = (REPO_ROOT / path).resolve()
    try:
        candidate.relative_to(REPO_ROOT)
    except ValueError:
        raise ValueError("Access outside project root is not allowed")
    return candidate


def tool_list_files(path: str) -> str:
    try:
        target = safe_resolve(path)
    except ValueError as exc:
        return f"Error: {exc}"

    if not target.exists():
        return f"Error: path '{path}' does not exist"
    if not target.is_dir():
        return f"Error: path '{path}' is not a directory"

    entries = sorted(p.name for p in target.iterdir())
    return "\n".join(entries)


def tool_read_file(path: str) -> str:
    try:
        target = safe_resolve(path)
    except ValueError as exc:
        return f"Error: {exc}"

    if not target.exists():
        return f"Error: file '{path}' does not exist"
    if not target.is_file():
        return f"Error: path '{path}' is not a file"

    return target.read_text(encoding="utf-8", errors="replace")


def tool_query_api(method: str, path: str, body: str | None = None) -> str:
    cfg = load_api_config()
    url = urljoin(cfg["base_url"] + "/", path.lstrip("/"))

    headers = {
        "Authorization": f"Bearer {cfg['api_key']}",
        "Content-Type": "application/json",
    }

    data = None
    if body:
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            return json.dumps(
                {
                    "status_code": 0,
                    "body": f"Error: invalid JSON body: {body}",
                }
            )

    try:
        resp = requests.request(
            method=method.upper(),
            url=url,
            headers=headers,
            json=data,
            timeout=10,
        )
    except requests.RequestException as exc:
        return json.dumps(
            {
                "status_code": 0,
                "body": f"Error: request failed: {exc}",
            }
        )

    try:
        if resp.headers.get("content-type", "").startswith("application/json"):
            parsed_body: Any = resp.json()
        else:
            parsed_body = resp.text
    except Exception:
        parsed_body = resp.text

    return json.dumps(
        {
            "status_code": resp.status_code,
            "body": parsed_body,
        }
    )


def get_tool_schemas() -> List[Dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "list_files",
                "description": "List files and directories at a given path from the project root.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative directory path from the project root.",
                        }
                    },
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read a file from the project repository.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative file path from the project root.",
                        }
                    },
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "query_api",
                "description": (
                    "Call the deployed backend HTTP API. Use this for live data questions "
                    "(counts, scores, analytics, statuses). Returns JSON with status_code and body."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "method": {
                            "type": "string",
                            "description": "HTTP method such as GET, POST, etc.",
                        },
                        "path": {
                            "type": "string",
                            "description": "Relative API path such as '/items/' or '/analytics/completion-rate'.",
                        },
                        "body": {
                            "type": "string",
                            "description": "Optional JSON request body as a string.",
                        },
                    },
                    "required": ["method", "path"],
                },
            },
        },
    ]


def call_llm_raw(
    messages: List[Dict[str, Any]], tools: List[Dict[str, Any]] | None = None
) -> Dict[str, Any]:
    cfg = load_llm_config()
    url = cfg["api_base"].rstrip("/") + "/chat/completions"

    payload: Dict[str, Any] = {
        "model": cfg["model"],
        "messages": messages,
        "temperature": 0.2,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    headers = {
        "Authorization": f"Bearer {cfg['api_key']}",
        "Content-Type": "application/json",
    }

    response = requests.post(url, headers=headers, json=payload, timeout=50)
    response.raise_for_status()
    return response.json()


def run_doc_agent(question: str) -> Dict[str, Any]:
    tools = get_tool_schemas()
    messages: List[Dict[str, Any]] = [
        {
            "role": "system",
            "content": (
                "You are a documentation and system agent for this LMS project. "
                "Use list_files and read_file to navigate the wiki and source code. "
                "Use query_api to call the deployed backend for live data (counts, analytics, statuses). "
                "For static framework/port/status-code questions, prefer reading the wiki or source code. "
                "When you answer, include a source path with section anchor when it comes from docs, "
                "or mention that the answer comes from the live API when using query_api."
            ),
        },
        {"role": "user", "content": question},
    ]

    all_tool_calls: List[Dict[str, Any]] = []

    for _ in range(10):
        data = call_llm_raw(messages, tools=tools)
        choice = data["choices"][0]
        message = choice["message"]

        tool_calls = message.get("tool_calls") or []
        if tool_calls:
            for tc in tool_calls:
                func_name = tc["function"]["name"]
                args_str = tc["function"].get("arguments") or "{}"
                try:
                    args = json.loads(args_str)
                except json.JSONDecodeError:
                    args = {}

                if func_name == "list_files":
                    result_text = tool_list_files(args.get("path", ""))
                elif func_name == "read_file":
                    result_text = tool_read_file(args.get("path", ""))
                elif func_name == "query_api":
                    result_text = tool_query_api(
                        method=args.get("method", "GET"),
                        path=args.get("path", "/"),
                        body=args.get("body"),
                    )
                else:
                    result_text = f"Error: unknown tool '{func_name}'"

                all_tool_calls.append(
                    {
                        "tool": func_name,
                        "args": args,
                        "result": result_text,
                    }
                )

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "name": func_name,
                        "content": result_text,
                    }
                )

            continue

        answer_text = message.get("content") or ""
        source = ""
        if isinstance(message.get("source"), str):
            source = message["source"]

        return {
            "answer": answer_text,
            "source": source,
            "tool_calls": all_tool_calls,
        }

    return {
        "answer": "Stopped after 10 tool calls without final answer.",
        "source": "",
        "tool_calls": all_tool_calls,
    }


def main() -> None:
    if len(sys.argv) < 2:
        print('Usage: uv run agent.py "your question"', file=sys.stderr)
        sys.exit(1)

    question = sys.argv[1]
    result = run_doc_agent(question)

    json.dump(result, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
