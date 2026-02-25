from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .embedder import embed_items_to_jsonl, load_items_jsonl


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Embed bug_task_model_selection items.jsonl")
    p.add_argument("--config", default=None, type=str, help="Path to embed_config.json")
    p.add_argument("--items", default=None, type=str, help="Path to items.jsonl")
    p.add_argument("--out", default=None, type=str, help="Path to output embeddings.jsonl")
    p.add_argument("--api-key", default=None, type=str, help="API key (or config api_key_env)")
    p.add_argument("--model", default=None, type=str)
    p.add_argument("--proxy", default=None, type=str)
    p.add_argument("--base-url", default=None, type=str, help="Override embedding endpoint URL")
    p.add_argument("--limit", default=None, type=int)
    p.add_argument(
        "--no-resume",
        action="store_true",
        help="Do not resume from existing out file; overwrite instead of appending",
    )

    args = p.parse_args(argv)

    cfg: dict = {}
    if args.config:
        cfg_path = Path(args.config)
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))

    items_path = Path(args.items or cfg.get("items") or "")
    out_path = Path(args.out or cfg.get("out") or "")

    model = args.model or cfg.get("model") or "text-embedding-v4"
    proxy = args.proxy or cfg.get("proxy") or "bailian"
    base_url = args.base_url or cfg.get("base_url") or None
    if isinstance(base_url, str) and not base_url.strip():
        base_url = None

    api_key_env = cfg.get("api_key_env") or "BAILIAN_API_KEY"
    api_key = args.api_key or cfg.get("api_key") or os.environ.get(str(api_key_env))
    if not api_key:
        raise SystemExit("Missing api_key: set --api-key, or set config api_key/api_key_env")

    limit = args.limit
    if limit is None:
        raw_limit = cfg.get("limit")
        if isinstance(raw_limit, int) and raw_limit > 0:
            limit = raw_limit

    if not str(items_path):
        raise SystemExit("Missing --items (or config items)")
    if not str(out_path):
        raise SystemExit("Missing --out (or config out)")

    items = load_items_jsonl(items_path)
    if args.no_resume and out_path.exists():
        out_path.unlink()

    embed_items_to_jsonl(
        items=items,
        api_key=str(api_key),
        model=str(model),
        proxy=str(proxy),
        base_url=base_url,
        limit=limit,
        out_path=out_path,
        resume=(not args.no_resume),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
