import json
import sys
from pathlib import Path

# Добавляем корень репо в sys.path, чтобы импортировать agent.py
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import agent  # noqa: E402


def test_format_result_shape():
    answer = "Test answer"
    result = agent.format_result(answer)

    assert isinstance(result, dict)
    assert "answer" in result
    assert "tool_calls" in result

    assert isinstance(result["answer"], str)
    assert isinstance(result["tool_calls"], list)

    json_str = json.dumps(result)
    parsed = json.loads(json_str)
    assert parsed["answer"] == answer
