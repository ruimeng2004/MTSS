from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Iterable

from tqdm import tqdm
import tiktoken

from utils.chat_remote import RemoteChat

from .embedding_models import EmbeddedItem
from .models import BugItem


def load_items_jsonl(path: Path) -> list[BugItem]:
    items: list[BugItem] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            obj = json.loads(s)
            items.append(
                BugItem(
                    item_id=obj["item_id"],
                    slug=obj["slug"],
                    view=obj["view"],
                    source_file=obj.get("source_file"),
                    text=obj.get("text", ""),
                    tokens=int(obj.get("tokens", 0)),
                    transform_config=obj.get("transform_config"),
                )
            )
    return items


def export_embeddings_jsonl(items: Iterable[EmbeddedItem], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(asdict(item), ensure_ascii=False) + "\n")


def _load_existing_item_ids(out_path: Path) -> set[str]:
    if not out_path.exists():
        return set()
    done: set[str] = set()
    with out_path.open("r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            try:
                obj = json.loads(s)
            except Exception:
                continue
            item_id = obj.get("item_id")
            if not (isinstance(item_id, str) and item_id):
                continue

            # Only mark as done if we have a successful embedding.
            # Failed records (embedding is None or with an error field) should be retried on resume.
            if obj.get("embedding") is None:
                continue
            if "error" in obj and obj.get("error"):
                continue
            done.add(item_id)
    return done


def _prune_failed_records_for_item(*, out_path: Path, errors_path: Path, item_id: str) -> None:
    if not out_path.exists():
        return

    tmp_path = out_path.with_suffix(out_path.suffix + ".tmp")
    moved_any = False

    with out_path.open("r", encoding="utf-8") as src, tmp_path.open("w", encoding="utf-8") as dst:
        for line in src:
            s = line.strip()
            if not s:
                continue
            try:
                obj = json.loads(s)
            except Exception:
                # Keep unparseable lines in-place
                dst.write(line)
                continue

            if obj.get("item_id") != item_id:
                dst.write(line)
                continue

            # For this item_id, keep only successful embeddings in main file.
            is_failed = (obj.get("embedding") is None) or ("error" in obj and obj.get("error"))
            if is_failed:
                errors_path.parent.mkdir(parents=True, exist_ok=True)
                with errors_path.open("a", encoding="utf-8") as ef:
                    ef.write(json.dumps(obj, ensure_ascii=False) + "\n")
                moved_any = True
                continue

            dst.write(line)

    if moved_any:
        tmp_path.replace(out_path)
    else:
        try:
            tmp_path.unlink()
        except Exception:
            pass


def embed_items_to_jsonl(
    *,
    items: list[BugItem],
    api_key: str,
    model: str,
    proxy: str,
    out_path: Path,
    base_url: str | None = None,
    limit: int | None = None,
    resume: bool = True,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    done_ids: set[str] = _load_existing_item_ids(out_path) if resume else set()

    errors_path = out_path.with_name(out_path.stem + "_errors" + out_path.suffix)

    client = RemoteChat(api_key=api_key, model=model, proxy=proxy, base_url=base_url)
    total = min(len(items), limit) if isinstance(limit, int) and limit >= 0 else len(items)

    # Tokenizer for chunk sizing + weighting (approximate; model-dependent).
    _enc = tiktoken.get_encoding("cl100k_base")

    def _num_tokens(s: str) -> int:
        try:
            return len(_enc.encode(s))
        except Exception:
            return max(1, len(s) // 4)

    def _chunk_text(s: str, *, max_tokens: int = 7500, overlap_tokens: int = 200) -> list[str]:
        if not s:
            return [""]
        toks = _enc.encode(s)
        if len(toks) <= max_tokens:
            return [s]

        chunks: list[str] = []
        start = 0
        step = max(1, max_tokens - max(0, overlap_tokens))
        while start < len(toks):
            end = min(len(toks), start + max_tokens)
            chunk = _enc.decode(toks[start:end])
            chunks.append(chunk)
            if end >= len(toks):
                break
            start += step
        return chunks

    def _split_in_half(ch: str) -> list[str]:
        toks = _enc.encode(ch)
        if len(toks) <= 1:
            return [ch]
        mid = max(1, len(toks) // 2)
        return [_enc.decode(toks[:mid]), _enc.decode(toks[mid:])]

    def _weighted_mean_pool(vectors: list[list[float]], weights: list[int]) -> list[float]:
        if not vectors:
            return []
        dim = len(vectors[0])
        total_w = float(sum(max(0, w) for w in weights))
        if total_w <= 0:
            total_w = float(len(vectors))
            weights = [1 for _ in vectors]

        out = [0.0] * dim
        for vec, w in zip(vectors, weights):
            ww = float(max(0, w))
            if len(vec) != dim:
                continue
            for i in range(dim):
                out[i] += vec[i] * ww
        for i in range(dim):
            out[i] /= total_w
        return out

    # Append mode so interrupted runs can continue without losing progress.
    with out_path.open("a", encoding="utf-8") as f:
        for i, item in enumerate(tqdm(items, total=total, desc="Embedding", unit="item")):
            if limit is not None and i >= limit:
                break
            if item.item_id in done_ids:
                continue

            text = item.text or ""
            # Keep a comfortable margin under the server limit (8192).
            # cl100k_base is an approximation; a smaller chunk size avoids mismatch.
            chunks = _chunk_text(text, max_tokens=6000, overlap_tokens=200)

            try:
                if len(chunks) == 1:
                    emb, emb_tokens = client.get_embedding(chunks[0], ID=item.item_id)
                else:
                    chunk_vecs: list[list[float]] = []
                    chunk_weights: list[int] = []
                    total_usage_tokens = 0
                    chunk_errors: list[str] = []

                    # Adaptive chunk embedding: if the provider complains about length,
                    # split the chunk further and retry a few times.
                    worklist: list[tuple[str, str]] = []
                    for ci, ch in enumerate(chunks):
                        worklist.append((f"{item.item_id}__chunk{ci+1}of{len(chunks)}", ch))

                    while worklist:
                        cid, ch = worklist.pop(0)
                        try:
                            vec, usage = client.get_embedding(ch, ID=cid)
                            if isinstance(vec, list):
                                chunk_vecs.append(vec)
                                chunk_weights.append(_num_tokens(ch))
                            u = usage if isinstance(usage, int) else None
                            if u is not None:
                                total_usage_tokens += int(u)
                        except KeyboardInterrupt:
                            raise
                        except Exception as e:
                            msg = str(e)
                            # Special-case the server length error to split further.
                            if "Range of input length" in msg and "8192" in msg:
                                parts = _split_in_half(ch)
                                # If we can't split further, record error.
                                if len(parts) <= 1 or parts[0] == ch:
                                    chunk_errors.append(f"{cid}: {msg}")
                                else:
                                    worklist.insert(0, (cid + "a", parts[0]))
                                    worklist.insert(1, (cid + "b", parts[1]))
                                continue
                            chunk_errors.append(f"{cid}: {msg}")
                            continue

                    emb = _weighted_mean_pool(chunk_vecs, chunk_weights) if chunk_vecs else None
                    emb_tokens = total_usage_tokens if total_usage_tokens > 0 else None
                    if emb is None and chunk_errors:
                        raise RuntimeError("; ".join(chunk_errors[:3]))
            except KeyboardInterrupt:
                raise
            except Exception as e:
                rec = EmbeddedItem(
                    item_id=item.item_id,
                    slug=item.slug,
                    view=item.view,
                    embedding=None,
                    embedding_dim=None,
                    embedding_model=model,
                    embedding_proxy=proxy,
                    tokens=None,
                    source_file=item.source_file,
                    transform_config=item.transform_config,
                )
                f.write(json.dumps({**asdict(rec), "error": str(e)}, ensure_ascii=False) + "\n")
                f.flush()
                continue

            dim: int | None
            if isinstance(emb, list):
                dim = len(emb)
            else:
                dim = None

            rec = EmbeddedItem(
                item_id=item.item_id,
                slug=item.slug,
                view=item.view,
                embedding=emb,
                embedding_dim=dim,
                embedding_model=model,
                embedding_proxy=proxy,
                tokens=emb_tokens,
                source_file=item.source_file,
                transform_config=item.transform_config,
            )

            # If this item had previous failed records, keep main file clean by
            # moving those failures to a sidecar *_errors.jsonl.
            if resume:
                _prune_failed_records_for_item(
                    out_path=out_path,
                    errors_path=errors_path,
                    item_id=item.item_id,
                )

            f.write(json.dumps(asdict(rec), ensure_ascii=False) + "\n")
            f.flush()


def embed_items(
    *,
    items: Iterable[BugItem],
    api_key: str,
    model: str,
    proxy: str,
    base_url: str | None = None,
    limit: int | None = None,
) -> list[EmbeddedItem]:
    client = RemoteChat(api_key=api_key, model=model, proxy=proxy, base_url=base_url)

    out: list[EmbeddedItem] = []
    for i, item in enumerate(tqdm(list(items), desc="Embedding", unit="item")):
        if limit is not None and i >= limit:
            break

        emb, emb_tokens = client.get_embedding(item.text, ID=item.item_id)

        dim: int | None
        if isinstance(emb, list):
            dim = len(emb)
        else:
            dim = None

        out.append(
            EmbeddedItem(
                item_id=item.item_id,
                slug=item.slug,
                view=item.view,
                embedding=emb,
                embedding_dim=dim,
                embedding_model=model,
                embedding_proxy=proxy,
                tokens=emb_tokens,
                source_file=item.source_file,
                transform_config=item.transform_config,
            )
        )

    return out
