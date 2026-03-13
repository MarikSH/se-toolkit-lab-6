import json
import os
import sys
from typing import Any, Dict

import requests


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


def call_llm(question: str) -> str:
    cfg = load_llm_config()
    url = cfg["api_base"].rstrip("/") + "/chat/completions"

    payload: Dict[str, Any] = {
        "model": cfg["model"],
        "messages": [
            {
                "role": "system",
                "content": "You are a concise assistant. Answer clearly in one or two sentences.",
            },
            {"role": "user", "content": question},
        ],
        "temperature": 0.2,
    }

    headers = {
        "Authorization": f"Bearer {cfg['api_key']}",
        "Content-Type": "application/json",
    }

    response = requests.post(url, headers=headers, json=payload, timeout=50)
    response.raise_for_status()
    data = response.json()

    # OpenAI/Qwen-style response
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        print(f"Unexpected LLM response format: {exc}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    if len(sys.argv) < 2:
        print('Usage: uv run agent.py "your question"', file=sys.stderr)
        sys.exit(1)

    question = sys.argv[1]
    answer_text = call_llm(question)

    result: Dict[str, Any] = {
        "answer": answer_text,
        "tool_calls": [],
    }

    json.dump(result, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
