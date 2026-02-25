import argparse
import datetime
import json
import os
import sys
from typing import Any, Dict, List, Tuple

import pandas as pd
from tqdm import tqdm

# Ensure we can import from D4C/* when running as a script.
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
D4C_DIR = os.path.abspath(os.path.join(THIS_DIR, ".."))
if D4C_DIR not in sys.path:
    sys.path.append(D4C_DIR)

from prompt import d4j as d4j_prompt  # noqa: E402
from ppl.ppl_geter import OpenAICompatiblePPLGeter, _extract_chat_completion_logprobs, compute_ppl_from_token_logprobs  # noqa: E402


def _load_config(config_path: str) -> Dict[str, Any]:
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        obj = json.load(f)
    if not isinstance(obj, dict):
        raise ValueError("config.json must be a JSON object")
    return obj


def _resolve_path(d4c_dir: str, path_val: str) -> str:
    if not path_val:
        return path_val
    if os.path.isabs(path_val):
        return path_val
    return os.path.abspath(os.path.join(d4c_dir, path_val))


def _extract_buggy_info_no_log(data: pd.DataFrame, msg: pd.DataFrame, slug: str) -> Dict[str, str]:
    datas = data[data["slug"] == slug]
    msg_filtered = msg[msg["slug"] == slug]

    buggy_codes = ""
    buggy_comments = ""
    for _, row in datas.iterrows():
        buggy_comment = row["comment"].strip() if pd.notna(row.get("comment")) else "This function has no comment."
        buggy_code = row["buggy_code"]
        if buggy_comment:
            buggy_comments += "   " + str(buggy_comment) + "\n"
        buggy_codes += "```java\n" + str(buggy_code) + "\n```\n"

    error_message = "\n".join(msg_filtered.get("exception_info", pd.Series([], dtype=str)).dropna().tolist()) if not msg_filtered.empty else "This function has no exception info."
    failed_tests = "\n".join(msg_filtered.get("test_method", pd.Series([], dtype=str)).dropna().tolist()) if not msg_filtered.empty else "This function has no failed test."

    return {
        "SLUG": slug,
        "BUGGY_COMMENT": buggy_comments,
        "ERROR_MESSAGE": error_message,
        "FAILED_TEST": failed_tests,
        "BUGGY_CODE": buggy_codes,
    }


def _safe_slug_dirname(slug: str) -> str:
    return (slug or "unknown").replace("/", "_").replace("\\", "_")


def _extract_assistant_text(resp: Dict[str, Any]) -> str:
    choices = resp.get("choices") or []
    if not choices:
        return ""
    c0 = choices[0] or {}

    msg = c0.get("message")
    if isinstance(msg, dict):
        content = msg.get("content")
        if content is not None:
            return str(content)

    text = c0.get("text")
    if text is not None:
        return str(text)

    return ""


def build_prompt_messages(buggy_info: Dict[str, str]) -> Tuple[List[Dict[str, str]], str]:
    query = d4j_prompt.AGENT_PROMPT_SR
    query = query.replace("{BUGGY_COMMENT}", buggy_info["BUGGY_COMMENT"])
    query = query.replace("{ERROR_MESSAGE}", buggy_info["ERROR_MESSAGE"].strip())
    query = query.replace("{FAILED_TEST}", buggy_info["FAILED_TEST"].strip())
    query = query.replace("{BUGGY_CODE}", buggy_info["BUGGY_CODE"].strip())

    prompt_messages = list(d4j_prompt.HISTORY_AGENT_D4J_SEARCH_REPLACE)
    prompt_messages.append({"role": "user", "content": query})
    return prompt_messages, query

def main() -> int:
    parser = argparse.ArgumentParser(description="Run D4J SR (search/replace) task once per case, using API logprobs to compute output PPL.")

    parser.add_argument(
        "--config",
        default=os.path.join(THIS_DIR, "config.json"),
        type=str,
        help="Path to config JSON (default: D4C/ppl/config.json)",
    )

    # Optional CLI overrides (config.json is the primary source of truth)
    parser.add_argument("--base-url", default="", type=str)
    parser.add_argument("--model", default="", type=str)
    parser.add_argument("--api-key", default="", type=str)

    parser.add_argument("--data-path", default="", type=str)
    parser.add_argument("--msg-path", default="", type=str)

    parser.add_argument("--slug", default="", type=str, help="If set, only process this slug")
    parser.add_argument("--limit", default=0, type=int, help="If >0, limit number of slugs")

    parser.add_argument("--max-tokens", default=0, type=int)
    parser.add_argument("--temperature", default=-1.0, type=float)
    parser.add_argument("--top-logprobs", default=None, type=int)
    parser.add_argument(
        "--prompt-logprobs",
        default=-1,
        type=int,
        help="Whether to request vLLM prompt_logprobs (0/1). Default: disabled unless set in config.json.",
    )
    parser.add_argument("--qps", default=-1.0, type=float, help="请求速率上限；0 表示关闭限速")

    args = parser.parse_args()

    cfg = _load_config(args.config)
    base_url = args.base_url or str(cfg.get("base_url") or "").strip()
    model = args.model or str(cfg.get("model") or "").strip()

    api_key = args.api_key or str(cfg.get("api_key") or "").strip()
    if not api_key:
        env_name = str(cfg.get("api_key_env") or "D4C_API_KEY")
        api_key = os.environ.get(env_name, "")
    if not api_key:
        api_key = os.environ.get("D4C_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""
    if not api_key:
        raise SystemExit("api_key is empty (set in config.json, pass --api-key, or set env var)")

    data_path = _resolve_path(D4C_DIR, args.data_path or str(cfg.get("data_path") or "data/defects4j_code.csv"))
    msg_path = _resolve_path(D4C_DIR, args.msg_path or str(cfg.get("msg_path") or "data/defects4j_artifact.csv"))
    cache_path = str(cfg.get("cache_path_edit") or "").strip()
    if cache_path:
        cache_path = _resolve_path(D4C_DIR, cache_path)

    max_tokens = args.max_tokens if args.max_tokens and args.max_tokens > 0 else int(cfg.get("max_tokens") or 1024)
    temperature = args.temperature if args.temperature >= 0 else float(cfg.get("temperature") or 1.0)
    top_logprobs = args.top_logprobs
    if top_logprobs is None and "top_logprobs" in cfg:
        tlp = cfg.get("top_logprobs")
        top_logprobs = None if tlp is None else int(tlp)

    prompt_logprobs_req: int | None = None
    if args.prompt_logprobs >= 0:
        # Explicit CLI override
        prompt_logprobs_req = int(args.prompt_logprobs)
    else:
        # Optional config-driven default
        plp = cfg.get("prompt_logprobs")
        if plp is not None:
            prompt_logprobs_req = int(plp)
    qps_cfg = cfg.get("qps")
    qps = args.qps if args.qps >= 0 else (float(qps_cfg) if qps_cfg is not None else 0.0)

    slug_filter = args.slug or str(cfg.get("slug") or "")
    limit = args.limit if args.limit else int(cfg.get("limit") or 0)

    n_samples = int(cfg.get("n_samples") or 1)
    if n_samples <= 0:
        raise SystemExit("n_samples must be a positive integer")

    if not base_url:
        raise SystemExit("base_url is empty (set in config.json or pass --base-url)")
    if not model:
        raise SystemExit("model is empty (set in config.json or pass --model)")

    # Backward-compatible default: when using local vLLM, enable prompt_logprobs
    # unless explicitly overridden by CLI/config.
    if prompt_logprobs_req is None and ("localhost" in base_url or "127.0.0.1" in base_url):
        prompt_logprobs_req = 1

    # result/<timestamp>/<slug>/<n>/result.json
    result_root = os.path.join(THIS_DIR, "result")
    run_ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(result_root, run_ts)
    os.makedirs(run_dir, exist_ok=True)

    data = pd.read_csv(data_path, sep=",", encoding="utf-8", engine="python")
    msg = pd.read_csv(msg_path, sep=",", encoding="utf-8", engine="python")

    id_count = data["slug"].value_counts()
    all_slugs = id_count.index.tolist()
    all_slugs = sorted(all_slugs, key=lambda s: (s.split("_")[0].lower(), int(s.split("_")[1])))

    if slug_filter:
        all_slugs = [s for s in all_slugs if s == slug_filter]
    if limit and limit > 0:
        all_slugs = all_slugs[:limit]

    geter = OpenAICompatiblePPLGeter(base_url=base_url, api_key=api_key, model=model, qps=qps)
    
    skipped_samples = 0

    for i, slug in tqdm(enumerate(all_slugs), total=len(all_slugs), desc="Processing Slugs", unit="slug"):
        buggy_info = _extract_buggy_info_no_log(data, msg, slug)
        prompt_messages, query = build_prompt_messages(buggy_info)

        for sample_idx in range(1, n_samples + 1):
            # Check if sample already exists in cache
            if cache_path:
                cache_case_dir = os.path.join(cache_path, _safe_slug_dirname(slug))
                cache_result_path_new = os.path.join(cache_case_dir, str(sample_idx), "result.json")
                cache_result_path_old = os.path.join(cache_case_dir, "result.json")

                if os.path.exists(cache_result_path_new) or (sample_idx == 1 and os.path.exists(cache_result_path_old)):
                    tqdm.write(f"Skipping {slug} sample {sample_idx}/{n_samples} - found in cache")
                    skipped_samples += 1
                    continue

            resp = geter.chat_completion_with_logprobs(
                messages=prompt_messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_logprobs=top_logprobs,
                prompt_logprobs=prompt_logprobs_req,
            )

            model_output = _extract_assistant_text(resp)
            token_logprobs, tokens, prompt_token_logprobs, prompt_tokens = _extract_chat_completion_logprobs(resp)
            ppl_res = compute_ppl_from_token_logprobs(token_logprobs, prompt_token_logprobs)
            ppl_res.tokens = tokens
            ppl_res.prompt_tokens = prompt_tokens

            sample_dir = os.path.join(run_dir, _safe_slug_dirname(slug), str(sample_idx))
            os.makedirs(sample_dir, exist_ok=True)
            out_path = os.path.join(sample_dir, "result.json")
            query_path = os.path.join(sample_dir, "query.txt")
            model_output_path = os.path.join(sample_dir, "model_output.txt")

            out_obj: Dict[str, Any] = {
                "task": "d4j_edit",
                "slug": slug,
                "sample_idx": sample_idx,
                "n_samples": n_samples,
                "run_ts": run_ts,
                "model": model,
                "base_url": base_url,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "top_logprobs": top_logprobs,
                "prompt": prompt_messages,
                "query": query,
                "model_output": model_output,
                "avg_nll": ppl_res.avg_nll,
                "ppl": ppl_res.ppl,
                "n_tokens": ppl_res.n_tokens,
                "token_logprobs": ppl_res.token_logprobs,
            }
        
            if ppl_res.ppl_io is not None:
                out_obj["avg_nll_io"] = ppl_res.avg_nll_io
                out_obj["ppl_io"] = ppl_res.ppl_io
                out_obj["n_tokens_io"] = ppl_res.n_tokens_io
                out_obj["prompt_logprobs"] = ppl_res.prompt_logprobs

            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(out_obj, f, ensure_ascii=False, indent=2)

            with open(query_path, "w", encoding="utf-8") as f:
                f.write(query)

            with open(model_output_path, "w", encoding="utf-8") as f:
                f.write(model_output)

    print(f"Done. Results saved under: {run_dir}")
    if cache_path:
        print(f"Skipped {skipped_samples} samples (found in cache)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
