# bug_task_model_selection

This folder contains an **opt-in**, self-contained pipeline for the "Cluster-Guided Task Modeling Selection for Bug Repair" change.

It is designed to be run on artifacts under `prompt_list/<slug>/` and produce:

- multi-view `(slug, view)` items (`items.jsonl`)
- embeddings per item with stable IDs + rich metadata (`embeddings.jsonl`)

## 1) Build multi-view bug artifacts

Input layout:

- `prompt_list/<slug>/query.txt`
- `prompt_list/<slug>/FAILED_TEST.txt`
- `prompt_list/<slug>/ERROR_MESSAGE.txt`
- `prompt_list/<slug>/BUGGY_CODE.txt`

Default views:

- `report`
- `test`
- `error`
- `error_plus_test` (derived; error + failed test)
- `buggy_code`
- `buggy_code_obfuscated` (derived)
- `buggy_code_mixed` (derived)

Generate JSONL items:

```bash
python -m bug_task_model_selection.src.cli \
  --prompt-list-dir prompt_list \
  --out bug_task_model_selection/data/artifacts/items.jsonl
```

Optional flags:

- `--views report,test,error,buggy_code,buggy_code_obfuscated,buggy_code_mixed`
- `--limit 100`

## 2) Embed each (slug, view) item

This step reads `items.jsonl`, calls the repo's existing `utils.chat_remote.RemoteChat.get_embedding`, and writes one JSONL record per embedded item.

```bash
python -m bug_task_model_selection.src.embed_cli \
  --config bug_task_model_selection/embed_config.json
```

Optional flags:

- `--proxy bailian|OpenAI|...`
- `--model text-embedding-v4`
- `--base-url https://.../v1/embeddings` (override embedding endpoint)
- `--api-key <YOUR_KEY>` (recommended; do not hardcode)
- `--limit 100`

Notes:

- Stable identifier: `item_id = "{slug}__{view}"`
- Each embedding record stores the item metadata (slug/view/source_file/tokens/transform_config) for traceability.
