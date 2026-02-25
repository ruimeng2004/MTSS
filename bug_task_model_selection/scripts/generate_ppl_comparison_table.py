#!/usr/bin/env python3
"""Generate detailed PPL comparison table for all bugs."""

import json
from pathlib import Path
from typing import Dict

import pandas as pd


def load_ppl_scores(path: Path) -> Dict[str, float]:
    """Load PPL scores from JSONL file."""
    scores = {}
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            obj = json.loads(line)
            slug = obj.get('slug')
            value = obj.get('value')
            if slug and value is not None:
                scores[slug] = float(value)
    return scores


def generate_comparison_table(model_name: str, edit_ppl: Dict[str, float], 
                              gen_ppl: Dict[str, float]) -> pd.DataFrame:
    """Generate comparison table for a model."""
    data = []
    
    for slug in sorted(edit_ppl.keys()):
        if slug not in gen_ppl:
            continue
        
        edit_val = edit_ppl[slug]
        gen_val = gen_ppl[slug]
        
        # Which is better
        better = 'edit' if edit_val < gen_val else 'gen'
        
        # Absolute difference
        abs_diff = abs(edit_val - gen_val)
        
        # Relative difference (percentage)
        min_val = min(edit_val, gen_val)
        max_val = max(edit_val, gen_val)
        rel_diff = (max_val - min_val) / min_val if min_val > 0 else 0
        
        data.append({
            'slug': slug,
            'edit_ppl': edit_val,
            'gen_ppl': gen_val,
            'better': better,
            'abs_diff': abs_diff,
            'rel_diff_pct': rel_diff * 100
        })
    
    return pd.DataFrame(data)


def main():
    """Main function."""
    data_dir = Path("bug_task_model_selection/data/ppl")
    output_dir = Path("bug_task_model_selection/data/analysis")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    models = [
        ('qwen3_coder', 'qwen3_coder_edit.jsonl', 'qwen3_coder_gen.jsonl'),
        ('qwen3_30b', 'qwen3_30b_edit.jsonl', 'qwen3_30b_gen.jsonl')
    ]
    
    for model_name, edit_file, gen_file in models:
        print(f"Processing {model_name}...")
        
        # Load PPL scores
        edit_ppl = load_ppl_scores(data_dir / edit_file)
        gen_ppl = load_ppl_scores(data_dir / gen_file)
        
        # Generate comparison table
        df = generate_comparison_table(model_name, edit_ppl, gen_ppl)
        
        # Save to CSV
        output_file = output_dir / f"ppl_comparison_{model_name}.csv"
        df.to_csv(output_file, index=False, float_format='%.6f')
        print(f"  Saved to: {output_file}")
        print(f"  Total bugs: {len(df)}")
        
        # Generate markdown table (first 50 rows for preview)
        md_file = output_dir / f"ppl_comparison_{model_name}.md"
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(f"# PPL Comparison Table - {model_name}\n\n")
            f.write(f"**Total bugs**: {len(df)}\n\n")
            f.write("## 说明\n\n")
            f.write("- **slug**: Bug 标识符\n")
            f.write("- **edit_ppl**: Edit 任务建模的 PPL\n")
            f.write("- **gen_ppl**: Gen 任务建模的 PPL\n")
            f.write("- **better**: 哪个策略更好（PPL 更低）\n")
            f.write("- **abs_diff**: 绝对差距\n")
            f.write("- **rel_diff_pct**: 相对差距（百分比）\n\n")
            
            f.write("## 完整数据\n\n")
            f.write("完整数据请查看 CSV 文件: `ppl_comparison_{}.csv`\n\n".format(model_name))
            
            f.write("## 前 50 个 bugs（按 slug 排序）\n\n")
            f.write("| Slug | Edit PPL | Gen PPL | Better | Abs Diff | Rel Diff (%) |\n")
            f.write("|------|----------|---------|--------|----------|-------------|\n")
            
            for _, row in df.head(50).iterrows():
                f.write(f"| {row['slug']} | {row['edit_ppl']:.6f} | "
                       f"{row['gen_ppl']:.6f} | {row['better']} | "
                       f"{row['abs_diff']:.6f} | {row['rel_diff_pct']:.2f}% |\n")
            
            f.write("\n## 差距最大的 20 个 bugs\n\n")
            f.write("| Rank | Slug | Edit PPL | Gen PPL | Better | Abs Diff | Rel Diff (%) |\n")
            f.write("|------|------|----------|---------|--------|----------|-------------|\n")
            
            top20 = df.nlargest(20, 'rel_diff_pct')
            for i, (_, row) in enumerate(top20.iterrows(), 1):
                f.write(f"| {i} | {row['slug']} | {row['edit_ppl']:.6f} | "
                       f"{row['gen_ppl']:.6f} | {row['better']} | "
                       f"{row['abs_diff']:.6f} | {row['rel_diff_pct']:.2f}% |\n")
            
            f.write("\n## 差距最小的 20 个 bugs\n\n")
            f.write("| Rank | Slug | Edit PPL | Gen PPL | Better | Abs Diff | Rel Diff (%) |\n")
            f.write("|------|------|----------|---------|--------|----------|-------------|\n")
            
            bottom20 = df.nsmallest(20, 'rel_diff_pct')
            for i, (_, row) in enumerate(bottom20.iterrows(), 1):
                f.write(f"| {i} | {row['slug']} | {row['edit_ppl']:.6f} | "
                       f"{row['gen_ppl']:.6f} | {row['better']} | "
                       f"{row['abs_diff']:.6f} | {row['rel_diff_pct']:.2f}% |\n")
        
        print(f"  Markdown preview saved to: {md_file}")
    
    print("\n✓ All tables generated successfully!")
    print(f"\nOutput directory: {output_dir}")


if __name__ == "__main__":
    main()
