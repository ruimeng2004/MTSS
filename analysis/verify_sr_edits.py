#!/usr/bin/env python3
"""批量或单个检查：sr edit 块数量是否与 query 中的 Buggy functions 数量一致，并输出报告。"""

import argparse
import datetime
import re
import sys
from pathlib import Path

DEFAULT_OUTPUT = Path("/home/base/APR/D4C/analysis/result/sr_edit_verification.txt")


def count_buggy_functions(query_path: Path) -> int:
    """Count code blocks in the Buggy functions section of the query file."""
    text = query_path.read_text(encoding="utf-8")
    if "### Buggy functions" not in text:
        raise ValueError("Could not find '### Buggy functions' section in query file")
    section = text.split("### Buggy functions", 1)[1]
    # Each buggy function is provided as a code block that starts with ```java
    return len(re.findall(r"```\w+", section))


def count_sr_edits(model_output_path: Path) -> int:
    """Count search/replace edits in the model output."""
    text = model_output_path.read_text(encoding="utf-8")
    # Each edit block starts with the marker <<<<<<< SEARCH
    return len(re.findall(r"<<<<<<<\s+SEARCH", text))


def check_pair(query_path: Path, model_output_path: Path) -> tuple[int, int, bool]:
    """Return (buggy_count, sr_count, is_match) for a single pair."""
    buggy_count = count_buggy_functions(query_path)
    sr_count = count_sr_edits(model_output_path)
    return buggy_count, sr_count, buggy_count == sr_count


def iter_pairs(result_dir: Path):
    """Yield (name, query_path, model_output_path) for each valid subdirectory."""
    for subdir in sorted(result_dir.iterdir()):
        if not subdir.is_dir():
            continue
        query_path = subdir / "query.txt"
        model_output_path = subdir / "model_output.txt"
        if query_path.exists() and model_output_path.exists():
            yield subdir.name, query_path, model_output_path


def write_report(lines: list[str], output_path: Path, title: str) -> None:
    """Write report lines to file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().isoformat(timespec="seconds")
    header = [
        title,
        f"生成时间: {timestamp}",
        "",
    ]
    output_path.write_text("\n".join(header + lines), encoding="utf-8")


def run_single(query: Path, model_output: Path, output: Path | None) -> int:
    """Run the check on a single pair."""
    try:
        buggy_count, sr_count, is_match = check_pair(query, model_output)
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    lines = [
        f"Buggy functions: {buggy_count}",
        f"sr edits:       {sr_count}",
    ]

    for line in lines:
        print(line)

    if is_match:
        print("PASS: sr edit count matches buggy function count.")
        status_line = "PASS: sr edit count matches buggy function count."
        if output:
            write_report(lines + [status_line], output, "单文件 sr edit 校验")
        return 0

    fail_line = "FAIL: sr edit count does not match buggy function count."
    print(fail_line)
    if output:
        write_report(lines + [fail_line], output, "单文件 sr edit 校验")
    return 1


def run_batch(result_dir: Path, fail_only: bool, output: Path | None) -> int:
    """Run the check across all subdirectories under result_dir."""
    pairs = list(iter_pairs(result_dir))
    if not pairs:
        print("Error: 未找到包含 query.txt 和 model_output.txt 的子目录。", file=sys.stderr)
        return 2

    failures = 0
    errors = 0
    report_lines: list[str] = [f"输入目录: {result_dir}"]

    for name, query_path, model_output_path in pairs:
        try:
            buggy_count, sr_count, is_match = check_pair(query_path, model_output_path)
        except (OSError, ValueError) as exc:
            errors += 1
            print(f"{name}: ERROR ({exc})")
            report_lines.append(f"{name}: ERROR ({exc})")
            continue

        if not fail_only or not is_match:
            status = "OK" if is_match else "FAIL"
            line = f"{name}: buggy={buggy_count}, sr={sr_count}, status={status}"
            print(line)
            report_lines.append(line)

        if not is_match:
            failures += 1

    total = len(pairs)
    summary = f"Total: {total}, Failures: {failures}, Errors: {errors}"
    print(f"\n{summary}")
    report_lines.append("")
    report_lines.append(summary)

    if output:
        write_report(report_lines, output, "批量 sr edit 校验报告")
    if errors:
        return 2
    return 0 if failures == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "校验 sr edit 块数量是否与 Buggy functions 数量一致。"
        )
    )
    parser.add_argument(
        "--result-dir",
        type=Path,
        help="result 目录路径（包含多个子目录，每个子目录有 query.txt 和 model_output.txt）",
    )
    parser.add_argument(
        "--query",
        default="query.txt",
        type=Path,
        help="Path to the query.txt file (default: query.txt in the current directory)",
    )
    parser.add_argument(
        "--model-output",
        default="model_output.txt",
        type=Path,
        help="Path to the model_output.txt file (default: model_output.txt in the current directory)",
    )
    parser.add_argument(
        "--fail-only",
        action="store_true",
        help="批量模式下仅输出不匹配或出错的条目",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"结果输出文件路径（默认: {DEFAULT_OUTPUT})",
    )
    args = parser.parse_args()

    if args.result_dir:
        return run_batch(args.result_dir, args.fail_only, args.output)
    return run_single(args.query, args.model_output, args.output)


if __name__ == "__main__":
    sys.exit(main())
