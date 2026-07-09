import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class AgentResult:
    success: bool
    output: dict
    feedback: Optional[str] = None
    error: Optional[str] = None


def parse_json_response(text: str) -> dict:
    """Extract JSON from LLM response, handling extra text or markdown wrapping."""
    text = text.strip()
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Try stripping markdown code fences
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass
    # Try progressively from first { to each } from right to left
    start = text.find("{")
    if start != -1:
        # Find all } positions
        end_positions = [i for i, c in enumerate(text) if c == "}"]
        # Try from rightmost } backwards until one parses
        for end in reversed(end_positions):
            if end <= start:
                break
            candidate = text[start:end + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue
        # None parsed cleanly — try fixing truncated JSON
        # Use the largest candidate (first { to last })
        if end_positions and end_positions[-1] > start:
            candidate = text[start:end_positions[-1] + 1]
        else:
            candidate = text[start:]
        fixed = _try_fix_truncated_json(candidate)
        if fixed:
            return fixed
        # Try with just text from { to end (fully truncated, no closing })
        fixed = _try_fix_truncated_json(text[start:])
        if fixed:
            return fixed
    raise ValueError(f"Could not parse JSON from response: {text[:200]}")


def _try_fix_truncated_json(text: str) -> dict | None:
    """Attempt to fix truncated JSON by closing open strings/braces."""
    # If the JSON was cut off mid-string, close the string and braces
    # Count open braces/brackets
    open_braces = text.count("{") - text.count("}")
    open_brackets = text.count("[") - text.count("]")
    # Check if we're inside a string (odd number of unescaped quotes)
    in_string = False
    i = 0
    while i < len(text):
        if text[i] == "\\" and i + 1 < len(text):
            i += 2
            continue
        if text[i] == '"':
            in_string = not in_string
        i += 1
    suffix = ""
    if in_string:
        suffix += '"'
    suffix += "]" * open_brackets
    suffix += "}" * open_braces
    if suffix:
        try:
            return json.loads(text + suffix)
        except json.JSONDecodeError:
            # Try truncating to last complete key-value pair
            last_comma = text.rfind(",")
            if last_comma > 0:
                truncated = text[:last_comma]
                truncated_braces = truncated.count("{") - truncated.count("}")
                truncated_brackets = truncated.count("[") - truncated.count("]")
                close = "]" * truncated_brackets + "}" * truncated_braces
                try:
                    return json.loads(truncated + close)
                except json.JSONDecodeError:
                    pass
    return None


class BaseAgent(ABC):
    name: str = "base"
    description: str = ""

    @abstractmethod
    async def execute(self, input_data: dict) -> AgentResult:
        pass

    async def validate_output(self, output: dict) -> bool:
        return True
