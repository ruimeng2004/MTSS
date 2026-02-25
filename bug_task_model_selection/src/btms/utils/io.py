"""I/O utility functions for BTMS pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator


def iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    """Iterate over lines in a JSONL file.
    
    Args:
        path: Path to JSONL file
        
    Yields:
        Parsed JSON objects
    """
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            yield json.loads(s)


def write_jsonl(path: Path, items: list[dict[str, Any]]) -> None:
    """Write items to a JSONL file.
    
    Args:
        path: Output path
        items: List of dictionaries to write
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def read_json(path: Path) -> dict[str, Any]:
    """Read a JSON file.
    
    Args:
        path: Path to JSON file
        
    Returns:
        Parsed JSON object
    """
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: dict[str, Any], indent: int = 2) -> None:
    """Write data to a JSON file.
    
    Args:
        path: Output path
        data: Dictionary to write
        indent: Indentation level
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)
