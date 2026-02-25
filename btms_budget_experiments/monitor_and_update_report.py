#!/usr/bin/env python3
import os
import glob
import re
import time
from datetime import datetime

# Configuration
BASE_DIR = "/home/base/mengrui/MTSS/evaluation_output"
REPORT_FILE = "/home/base/mengrui/MTSS/btms_budget_experiments/EVALUATION_METRICS_REPORT.md"
TOTAL_BUGS = 698

CONFIGS = [
    ("Fixed 50-50 (Baseline)", "btms_routing_fixed-50-50"),
    ("Exp 2 - Balanced", "btms_routing_exp2-hybrid-balanced"),
    ("Exp 5 - Size Heavy", "btms_routing_exp5-size-heavy"),
    ("Exp 1 - Default", "btms_routing_exp1-hybrid-default"),
    ("Exp 3 - PPL Heavy", "btms_routing_exp3-ppl-heavy"),
    ("Exp 4 - Vote Heavy", "btms_routing_exp4-vote-heavy"),
    ("Baseline 1 - PPL", "btms_routing_baseline1-ppl-only"),
    ("Baseline 2 - Vote", "btms_routing_baseline2-vote-only"),
    ("Baseline 3 - Size", "btms_routing_baseline3-size-adjusted")
]

def get_latest_log(config_dir_name):
    dir_path = os.path.join(BASE_DIR, config_dir_name)
    if not os.path.exists(dir_path):
        return None
    
    logs = glob.glob(os.path.join(dir_path, "eval_log_*.txt"))
    if not logs:
        return None
    
    # Sort by modification time
    return max(logs, key=os.path.getmtime)

def parse_log(log_path):
    fixed = 0
    failed = 0
    
    try:
        with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                if "[Worker" in line:
                    if "✓" in line:
                        fixed += 1
                    elif "✗" in line:
                        failed += 1
    except Exception as e:
        print(f"Error reading {log_path}: {e}")
        
    return fixed, failed

def generate_table_row(name, fixed, failed):
    total = fixed + failed
    progress = (total / TOTAL_BUGS) * 100
    
    if total > 0:
        rate = (fixed / total) * 100
        rate_str = f"{rate:.1f}%"
    else:
        rate_str = "-"
        
    term_icon = "🟢" if total < TOTAL_BUGS and total > 0 else ("✅" if total >= TOTAL_BUGS else "⚪")
    
    return f"| {name} | {total}/{TOTAL_BUGS} ({progress:.1f}%) | {fixed} | {failed} | {rate_str} |"

def update_report():
    rows = []
    
    any_running = False
    
    for name, dir_name in CONFIGS:
        log_path = get_latest_log(dir_name)
        if log_path:
            fixed, failed = parse_log(log_path)
            rows.append(generate_table_row(name, fixed, failed))
            if (fixed + failed) < TOTAL_BUGS and (fixed + failed) > 0:
                any_running = True
        else:
            rows.append(f"| {name} | 0/{TOTAL_BUGS} (0.0%) | 0 | 0 | - |")

    # Construct the new section content
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status_icon = "🟢" if any_running else "✅"
    status_text = "评测进行中" if any_running else "评测已完成"
    
    new_section = f"""### 4. 修复成功率 ({status_text} {status_icon})

**目标**: 在给定budget下的实际修复成功率

**当前状态**: {status_icon} **{status_text}** (上次更新: {timestamp})

| 配置 | 进度 | 已修复 (Fixed) | 失败 (Failed) | 当前成功率 |
|------|------|---------------|---------------|------------|
"""
    for row in rows:
        new_section += row + "\n"
        
    new_section += "\n"

    # Read existing report
    with open(REPORT_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    # Regex to replace the section
    # Matches starting from ### 4. 修复成功率 until the end of file (or next section if I were safer, but it seems to be the last one)
    # The original header was "### 4. 修复成功率 ❌"
    # Actually, looking at the file content, it ends with that section. 
    # But to be safe, let's match specifically the header and consume lines until end or next header.
    
    # Pattern: ### 4. 修复成功率.*?(?=\n#|$) - this is risky if new sections are added.
    # Let's match specific old header "### 4. 修复成功率 ❌"
    
    pattern = r"### 4\. 修复成功率 [❌⚠️🟢✅].*?(\n#|\Z)"
    
    # Check if the header exists with specific icon, otherwise try generic
    if re.search(pattern, content, re.DOTALL):
        # We need to preserve the trailing newline or next header if we matched it
        # NOTE: re.sub with a group reference is tricky if we don't capture it perfectly.
        
        # Simpler approach: Find the start index of "### 4. 修复成功率"
        start_idx = content.find("### 4. 修复成功率")
        if start_idx != -1:
             # Just truncate and append? No, there might be footers (though unlikely here).
             # Let's assume it's the last section for now based on read_file output.
             # The read_file showed it as the last section.
             
             updated_content = content[:start_idx] + new_section
             
             with open(REPORT_FILE, 'w', encoding='utf-8') as f:
                 f.write(updated_content)
             print(f"Updated report at {timestamp}")
        else:
             print("Could not find section header")
    else:
        print("Regex match failed")
        # Fallback using string search
        start_idx = content.find("### 4. 修复成功率")
        if start_idx != -1:
             updated_content = content[:start_idx] + new_section
             with open(REPORT_FILE, 'w', encoding='utf-8') as f:
                 f.write(updated_content)
             print(f"Updated report at {timestamp} (Fallback)")

if __name__ == "__main__":
    update_report()
