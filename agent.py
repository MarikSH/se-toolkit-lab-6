import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

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
                "You are a documentation agent that answers questions using the project wiki. "
                "Use the `list_files` tool to discover files (for example under the 'wiki' directory), "
                "then use the `read_file` tool to read relevant files. "
                "When you answer, always include a source path with section anchor like "
                "'wiki/git-workflow.md#resolving-merge-conflicts'."
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

        # финальный ответ без tool_calls
        answer_text = message.get("content", "")
        # LLM должен явно указать source в тексте; здесь просто оставляем поле,
        # модель может вернуть его отдельным ключом в message, но это зависит от настройки
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
