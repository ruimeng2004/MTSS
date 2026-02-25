from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .io_utils import read_text, strip_code_fences
from .models import BugItem
from .tokenization import approximate_tokens
from .transforms import IdentifierHashObfuscator, mixed_code_variant
from .views import BugView
from .ids import stable_item_id


_DEFAULT_OBFUSCATOR = IdentifierHashObfuscator()


def build_items_for_slug(
    *,
    prompt_list_dir: Path,
    slug: str,
    enabled_views: set[BugView],
    include_text: bool = True,
) -> list[BugItem]:
    slug_dir = prompt_list_dir / slug
    items: list[BugItem] = []

    def add_item(
        *,
        view: BugView,
        source_file: str | None,
        text: str,
        transform_config: dict | None = None,
    ) -> None:
        item_id = stable_item_id(slug, view)
        items.append(
            BugItem(
                item_id=item_id,
                slug=slug,
                view=view.value,
                source_file=source_file,
                text=text if include_text else "",
                tokens=approximate_tokens(text),
                transform_config=transform_config,
            )
        )

    if BugView.report in enabled_views:
        p = slug_dir / "query.txt"
        if p.exists():
            add_item(view=BugView.report, source_file="query.txt", text=read_text(p).strip())

    if BugView.test in enabled_views:
        p = slug_dir / "FAILED_TEST.txt"
        if p.exists():
            add_item(view=BugView.test, source_file="FAILED_TEST.txt", text=read_text(p).strip())

    if BugView.error in enabled_views:
        p = slug_dir / "ERROR_MESSAGE.txt"
        if p.exists():
            add_item(view=BugView.error, source_file="ERROR_MESSAGE.txt", text=read_text(p).strip())

    if BugView.error_plus_test in enabled_views:
        p_err = slug_dir / "ERROR_MESSAGE.txt"
        p_test = slug_dir / "FAILED_TEST.txt"
        parts: list[str] = []
        if p_err.exists():
            parts.append("### Error message\n" + read_text(p_err).strip())
        if p_test.exists():
            parts.append("### Failed test\n" + read_text(p_test).strip())
        if parts:
            add_item(
                view=BugView.error_plus_test,
                source_file=None,
                text="\n\n".join(parts).strip(),
                transform_config={"type": "concat", "parts": ["error", "test"]},
            )

    buggy_code_text: str | None = None
    if BugView.buggy_code in enabled_views or BugView.buggy_code_obfuscated in enabled_views or BugView.buggy_code_mixed in enabled_views:
        p = slug_dir / "BUGGY_CODE.txt"
        if p.exists():
            buggy_code_text = strip_code_fences(read_text(p)).strip()

    if BugView.buggy_code in enabled_views and buggy_code_text is not None:
        add_item(view=BugView.buggy_code, source_file="BUGGY_CODE.txt", text=buggy_code_text)

    if BugView.buggy_code_obfuscated in enabled_views and buggy_code_text is not None:
        obf, cfg = _DEFAULT_OBFUSCATOR.obfuscate(buggy_code_text)
        add_item(
            view=BugView.buggy_code_obfuscated,
            source_file="BUGGY_CODE.txt",
            text=obf,
            transform_config=cfg,
        )

    if BugView.buggy_code_mixed in enabled_views and buggy_code_text is not None:
        mixed, cfg = mixed_code_variant(buggy_code_text)
        add_item(view=BugView.buggy_code_mixed, source_file="BUGGY_CODE.txt", text=mixed, transform_config=cfg)

    return items


def iter_slugs(prompt_list_dir: Path) -> Iterable[str]:
    for p in sorted(prompt_list_dir.iterdir()):
        if p.is_dir():
            yield p.name


def export_items_jsonl(items: Iterable[BugItem], out_path: Path) -> None:
    from .export import export_items_jsonl as _export

    _export(items, out_path)
