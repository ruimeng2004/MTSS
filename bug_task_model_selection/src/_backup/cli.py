from __future__ import annotations

import argparse
from pathlib import Path

from .artifact_builder import build_items_for_slug, export_items_jsonl, iter_slugs
from .views import BugView


def parse_views(raw: str | None) -> set[BugView]:
    if not raw:
        return {
            BugView.report,
            BugView.test,
            BugView.error,
            BugView.error_plus_test,
            BugView.buggy_code,
            BugView.buggy_code_obfuscated,
            BugView.buggy_code_mixed,
        }
    out: set[BugView] = set()
    for part in raw.split(","):
        v = part.strip()
        if not v:
            continue
        out.add(BugView(v))
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Build multi-view bug artifact items from prompt_list/<slug>/")
    p.add_argument("--prompt-list-dir", default="prompt_list", type=str)
    p.add_argument("--out", default="bug_task_model_selection/data/artifacts/items.jsonl", type=str)
    p.add_argument("--views", default=None, type=str, help="comma-separated view names")
    p.add_argument("--limit", default=None, type=int)

    args = p.parse_args(argv)

    prompt_list_dir = Path(args.prompt_list_dir)
    enabled_views = parse_views(args.views)

    all_items = []
    for i, slug in enumerate(iter_slugs(prompt_list_dir)):
        if args.limit is not None and i >= args.limit:
            break
        all_items.extend(
            build_items_for_slug(
                prompt_list_dir=prompt_list_dir,
                slug=slug,
                enabled_views=enabled_views,
            )
        )

    export_items_jsonl(all_items, Path(args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
