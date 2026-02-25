import argparse
import csv
import datetime
import os
import sys
from typing import Dict, List

import pandas as pd
from tqdm import tqdm

# Ensure we can import from D4C/* when running as a script.
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
D4C_DIR = os.path.abspath(os.path.join(THIS_DIR, ".."))
if D4C_DIR not in sys.path:
    sys.path.append(D4C_DIR)


def get_processed_slugs(csv_file_path: str) -> set:
    processed_slugs = set()
    if not os.path.exists(csv_file_path):
        return processed_slugs
    with open(csv_file_path, "r", encoding="utf-8") as csv_file:
        reader = csv.reader(csv_file)
        try:
            header = next(reader)
        except StopIteration:
            return processed_slugs

        # Prefer a "slug" column if present.
        slug_idx = None
        for idx, name in enumerate(header):
            if name.strip().lower() == "slug":
                slug_idx = idx
                break
        if slug_idx is None:
            slug_idx = 1  # legacy default

        for row in reader:
            if len(row) > slug_idx:
                processed_slugs.add(row[slug_idx])
    return processed_slugs


def build_query(mode: str, buggy_info: Dict[str, str]) -> str:
    from prompt import d4j as d4j_prompt

    if mode == "agent":
        query = d4j_prompt.AGENT_PROMPT_MUTI
        query = query.replace("{BUGGY_COMMENT}", buggy_info["BUGGY_COMMENT"])
        query = query.replace("{ERROR_MESSAGE}", buggy_info["ERROR_MESSAGE"].strip())
        query = query.replace("{FAILED_TEST}", buggy_info["FAILED_TEST"].strip())
        query = query.replace("{BUGGY_CODE}", buggy_info["BUGGY_CODE"].strip())
        return query

    if mode == "no_comment":
        query = d4j_prompt.AGENT_PROMPT_MUTI_NO_COMMENT
        query = query.replace("{ERROR_MESSAGE}", buggy_info["ERROR_MESSAGE"].strip())
        query = query.replace("{FAILED_TEST}", buggy_info["FAILED_TEST"].strip())
        query = query.replace("{BUGGY_CODE}", buggy_info["BUGGY_CODE"].strip())
        return query

    if mode == "no_test":
        query = d4j_prompt.AGENT_PROMPT_MUTI_NO_TEST
        query = query.replace("{BUGGY_COMMENT}", buggy_info["BUGGY_COMMENT"])
        query = query.replace("{ERROR_MESSAGE}", buggy_info["ERROR_MESSAGE"].strip())
        query = query.replace("{BUGGY_CODE}", buggy_info["BUGGY_CODE"].strip())
        return query

    if mode == "no_test_message":
        query = d4j_prompt.AGENT_PROMPT_MUTI_NO_MESSAGE
        query = query.replace("{BUGGY_COMMENT}", buggy_info["BUGGY_COMMENT"])
        query = query.replace("{FAILED_TEST}", buggy_info["FAILED_TEST"].strip())
        query = query.replace("{BUGGY_CODE}", buggy_info["BUGGY_CODE"].strip())
        return query

    if mode == "pure":
        query = d4j_prompt.USER_PROMPT
        query = query.replace("{BUGGY_CODE}", buggy_info["BUGGY_CODE"].strip())
        return query

    raise ValueError("mode must be one of: agent, no_comment, no_test, no_test_message, pure")


def resolve_history(history_name: str) -> List[Dict[str, str]]:
    from prompt import d4j as d4j_prompt

    if not hasattr(d4j_prompt, history_name):
        raise ValueError(f"Unknown history_name: {history_name}. Must be defined in prompt/d4j.py")
    history = getattr(d4j_prompt, history_name)
    if not isinstance(history, list):
        raise ValueError(f"History {history_name} is not a list")
    return history


def resolve_debugger(args):
    if args.chat_mode == "remote":
        from utils.chat_remote import RemoteChat
        return RemoteChat(args.api_key, args.remote_model, args.remote_proxy)
    if args.chat_mode == "local":
        from utils.chat_local import LocalChat
        return LocalChat(args.cp_path, args.local_model, args.local_proxy)
    raise ValueError("chat_mode must be 'remote' or 'local'")


def _safe_slug_dirname(slug: str) -> str:
    # Keep it simple; slugs are typically like "Closure_126".
    return (slug or "unknown").replace("/", "_").replace("\\", "_")


def save_repair_output(repair_out_dir: str, run_ts: str, slug: str, response: str) -> str:
    """Persist model output to D4C/ppl/repair_output/<run_ts>/<slug>/<timestamp>.txt"""
    if not response:
        return ""
    slug_dir = os.path.join(repair_out_dir, run_ts, _safe_slug_dirname(slug))
    os.makedirs(slug_dir, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    out_path = os.path.join(slug_dir, f"{ts}.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(response)
    return out_path


def main():
    from generator.generator_utils import extract_buggy_info
    from ppl.perplexity import compute_ppl_o_io, load_scorer

    parser = argparse.ArgumentParser(description="Generate outputs via API and compute O/IO perplexity with a local CLM scorer.")

    # Generation
    parser.add_argument("--chat_mode", default="remote", type=str, choices=["remote", "local"])
    parser.add_argument("--api_key", default=os.environ.get("D4C_API_KEY", ""), type=str)
    parser.add_argument("--remote_model", default="deepseek-chat", type=str)
    parser.add_argument("--remote_proxy", default="DeepSeek", type=str)
    parser.add_argument("--temperature", default=1.0, type=float)
    parser.add_argument("--max_try", default=1, type=int)

    parser.add_argument("--cp_path", default="~/.cache/huggingface/hub", type=str)
    parser.add_argument("--local_model", default="models--mistralai--Mixtral-8x7B-Instruct-v0.1", type=str)
    parser.add_argument("--local_proxy", default="batch", type=str)

    # Prompting
    parser.add_argument("--history_name", default="HISTORY_AGENT_D4J_MUTI", type=str)
    parser.add_argument("--mode", default="agent", type=str)

    # Data
    parser.add_argument("--data_path", required=True, type=str)
    parser.add_argument("--msg_path", required=True, type=str)
    parser.add_argument("--log_path", default=os.path.join(D4C_DIR, "log"), type=str)
    parser.add_argument("--slug", default="", type=str, help="If set, only process this slug")
    parser.add_argument("--limit", default=0, type=int, help="If >0, limit number of slugs")

    # Scorer (white-box)
    parser.add_argument("--scorer_model", required=True, type=str, help="HF model name/path used to compute perplexity (e.g., Mixtral)")
    parser.add_argument("--scorer_device", default="auto", type=str)
    parser.add_argument("--scorer_dtype", default="auto", type=str, help="torch dtype: auto|float16|bfloat16|float32")
    parser.add_argument("--max_length", default=0, type=int, help="Override scorer max_length (0 means model default)")
    parser.add_argument("--stride", default=512, type=int)

    # Output
    parser.add_argument("--out_csv", required=True, type=str)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--repair_out_dir",
        default=os.path.join(THIS_DIR, "repair_output"),
        type=str,
        help="Directory to save raw model outputs (stored under a per-slug subfolder).",
    )

    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.out_csv) or ".", exist_ok=True)
    os.makedirs(args.log_path, exist_ok=True)
    os.makedirs(args.repair_out_dir, exist_ok=True)

    run_ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    data = pd.read_csv(args.data_path, sep=",", encoding="utf-8", engine="python")
    msg = pd.read_csv(args.msg_path, sep=",", encoding="utf-8", engine="python")

    id_count = data["slug"].value_counts()
    all_slugs = id_count.index.tolist()
    all_slugs = sorted(all_slugs, key=lambda s: (s.split("_")[0].lower(), int(s.split("_")[1])))

    if args.slug:
        all_slugs = [s for s in all_slugs if s == args.slug]

    if args.limit and args.limit > 0:
        all_slugs = all_slugs[: args.limit]

    history = resolve_history(args.history_name)
    debugger = resolve_debugger(args)

    model, tokenizer, device = load_scorer(args.scorer_model, device=args.scorer_device, torch_dtype=args.scorer_dtype)
    max_length = args.max_length if args.max_length and args.max_length > 0 else None

    processed_slugs = set()
    if args.resume and os.path.exists(args.out_csv):
        processed_slugs = get_processed_slugs(args.out_csv)

    rows = []
    for i, slug in tqdm(enumerate(all_slugs), total=len(all_slugs), desc="Processing Slugs", unit="slug"):
        if slug in processed_slugs:
            continue

        buggy_info = extract_buggy_info(data, msg, slug, args.log_path)
        query = build_query(args.mode, buggy_info)

        prompt_messages = history.copy()
        prompt_messages.append({"role": "user", "content": query})

        for t in range(args.max_try):
            try:
                chat_ret = debugger.chat(prompt_messages, i, temperature=args.temperature)
                if isinstance(chat_ret, tuple) and len(chat_ret) == 2:
                    response, api_total_tokens = chat_ret
                else:
                    response, api_total_tokens = chat_ret, ""
                if response is None:
                    continue

                # Save raw model output alongside PPL results.
                repair_file = save_repair_output(args.repair_out_dir, run_ts, slug, response)

                ppl = compute_ppl_o_io(
                    model=model,
                    tokenizer=tokenizer,
                    prompt_messages=prompt_messages,
                    assistant_output=response,
                    device=device,
                    max_length=max_length,
                    stride=args.stride,
                )

                rows.append(
                    {
                        "ID": i,
                        "slug": slug,
                        "history_name": args.history_name,
                        "mode": args.mode,
                        "chat_mode": args.chat_mode,
                        "remote_model": args.remote_model if args.chat_mode == "remote" else "",
                        "remote_proxy": args.remote_proxy if args.chat_mode == "remote" else "",
                        "temperature": args.temperature,
                        "try": t,
                        "api_total_tokens": api_total_tokens,
                        "avg_nll_o": ppl.avg_nll_o,
                        "ppl_o": ppl.ppl_o,
                        "n_tokens_o": ppl.n_tokens_o,
                        "avg_nll_io": ppl.avg_nll_io,
                        "ppl_io": ppl.ppl_io,
                        "n_tokens_io": ppl.n_tokens_io,
                        "response": response,
                        "repair_output_file": repair_file,
                    }
                )

            except Exception as e:
                rows.append(
                    {
                        "ID": i,
                        "slug": slug,
                        "history_name": args.history_name,
                        "mode": args.mode,
                        "chat_mode": args.chat_mode,
                        "remote_model": args.remote_model if args.chat_mode == "remote" else "",
                        "remote_proxy": args.remote_proxy if args.chat_mode == "remote" else "",
                        "temperature": args.temperature,
                        "try": t,
                        "api_total_tokens": "",
                        "avg_nll_o": "",
                        "ppl_o": "",
                        "n_tokens_o": "",
                        "avg_nll_io": "",
                        "ppl_io": "",
                        "n_tokens_io": "",
                        "response": "",
                        "repair_output_file": "",
                        "error": str(e),
                    }
                )

        # Write incrementally to avoid losing progress on long runs.
        if rows:
            df = pd.DataFrame(rows)
            if os.path.exists(args.out_csv):
                df.to_csv(args.out_csv, mode="a", header=False, index=False)
            else:
                df.to_csv(args.out_csv, index=False)
            rows = []


if __name__ == "__main__":
    main()
