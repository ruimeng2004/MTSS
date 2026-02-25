#!/usr/bin/env python3
"""Analyze BTMS routing evaluation results.

This script:
1. loads all routing results from evaluation_output/
2. compares success rates against the Fixed 50-50 Baseline
3. calculates correlation between confidence scores and actual success
4. generates a summary report
"""

import json
import math
import argparse
from pathlib import Path
from typing import Dict, List, Any
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def calculate_correlation(x: List[float], y: List[float]) -> float:
    """Calculate Pearson correlation coefficient."""
    if len(x) != len(y) or len(x) == 0:
        return 0.0
    
    n = len(x)
    sum_x = sum(x)
    sum_y = sum(y)
    sum_xy = sum(xi * yi for xi, yi in zip(x, y))
    sum_x2 = sum(xi ** 2 for xi in x)
    sum_y2 = sum(yi ** 2 for yi in y)
    
    numerator = n * sum_xy - sum_x * sum_y
    denominator = math.sqrt((n * sum_x2 - sum_x ** 2) * (n * sum_y2 - sum_y ** 2))
    
    if denominator == 0:
        return 0.0
        
    return numerator / denominator

def analyze_calibration(results_data: List[Dict[str, Any]]) -> Dict[str, float]:
    """Analyze calibration: correlation between confidence and success."""
    confidences = []
    outcomes = []
    
    for r in results_data:
        conf = r.get('confidence', 0.0)
        # Outcome is 1 if successful_attempt is not None, else 0
        outcome = 1.0 if r.get('successful_attempt') is not None else 0.0
        
        if conf is not None:
            confidences.append(float(conf))
            outcomes.append(outcome)
            
    correlation = calculate_correlation(confidences, outcomes)
    
    # Binning analysis (e.g., avg success rate per confidence bin)
    # This is more complex to return as single value, so sticking to correlation for now
    
    return correlation

def load_results(base_output_dir: Path) -> Dict[str, Any]:
    """Load all btms_routing_results.json files."""
    summary = {}
    
    for results_file in base_output_dir.glob('**/btms_routing_results.json'):
        # Extract config name from parent directory name
        # e.g., btms_routing_exp2-hybrid-balanced -> exp2-hybrid-balanced
        parent_name = results_file.parent.name
        if parent_name.startswith('btms_routing_'):
            config_name = parent_name.replace('btms_routing_', '')
        else:
            config_name = parent_name
            
        try:
            with open(results_file, 'r') as f:
                data = json.load(f)
                
            # Basic stats already in json
            stats = {
                'total_bugs': data.get('total_bugs', 0),
                'fixed_bugs': data.get('fixed_bugs', 0),
                'success_rate': data.get('success_rate', 0.0),
                'edit_success': data.get('edit_success', 0),
                'gen_success': data.get('gen_success', 0),
                'avg_time': data.get('average_time_per_bug', 0.0)
            }
            
            # Additional analysis
            bug_results = data.get('bug_results', [])
            stats['confidence_correlation'] = analyze_calibration(bug_results)
            
            summary[config_name] = stats
            logger.info(f"Loaded results for {config_name}: {stats['fixed_bugs']} fixed")
            
        except Exception as e:
            logger.error(f"Error loading {results_file}: {e}")
            
    return summary

def generate_report(summary: Dict[str, Any], output_md: Path):
    """Generate comparative report in Markdown."""
    
    # Identify baseline (fixed-50-50)
    baseline_key = 'fixed-50-50'
    baseline_fixed = 0
    if baseline_key in summary:
        baseline_fixed = summary[baseline_key]['fixed_bugs']
    
    # Sort configs by fixed bugs descending
    sorted_configs = sorted(summary.items(), key=lambda x: x[1]['fixed_bugs'], reverse=True)
    
    with open(output_md, 'w') as f:
        f.write("# BTMS Routing Evaluation Result Summary\n\n")
        f.write(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        
        # 1. Performance Table
        f.write("## 1. Overall Performance\n\n")
        f.write("| Configuration | Fixed Bugs | Success Rate | vs. Baseline | Edit Fixed | Gen Fixed | Confidence Corr |\n")
        f.write("|---|---|---|---|---|---|---|\n")
        
        for name, stats in sorted_configs:
            fixed = stats['fixed_bugs']
            rate = stats['success_rate'] * 100
            
            # Diff vs baseline
            diff = fixed - baseline_fixed
            diff_str = f"{diff:+d}" if baseline_key in summary else "N/A"
            if name == baseline_key:
                diff_str = "-"
            
            edit = stats['edit_success']
            gen = stats['gen_success']
            corr = stats['confidence_correlation']
            
            # Format
            row = f"| **{name}** | {fixed} | {rate:.1f}% | {diff_str} | {edit} | {gen} | {corr:.3f} |\n"
            f.write(row)
            
        f.write("\n")
        
        # 2. Key Findings
        f.write("## 2. Key Findings\n\n")
        
        best_config = sorted_configs[0][0] if sorted_configs else "None"
        best_fixed = sorted_configs[0][1]['fixed_bugs'] if sorted_configs else 0
        
        f.write(f"- **Best Performer**: `{best_config}` with {best_fixed} fixed bugs.\n")
        
        if baseline_key in summary:
            f.write(f"- **Baseline (Fixed 50-50)**: Fixed {baseline_fixed} bugs.\n")
            if best_fixed > baseline_fixed:
                gain = best_fixed - baseline_fixed
                f.write(f"- **Improvement**: Dynamic routing improved success by +{gain} bugs (+{gain/baseline_fixed*100:.1f}%).\n")
            elif best_fixed < baseline_fixed:
                 f.write(f"- **Regression**: Dynamic routing performed worse than baseline ({best_fixed - baseline_fixed} bugs).\n")
            else:
                 f.write(f"- **Neutral**: Dynamic routing matched baseline performance.\n")
        else:
            f.write("- **Baseline Missing**: Comparison against fixed strategy not possible yet.\n")
            
        # Calibration insight
        corrs = [s['confidence_correlation'] for _, s in summary.items() if s['confidence_correlation'] != 0]
        if corrs:
            avg_corr = sum(corrs) / len(corrs)
            f.write(f"- **Calibration**: Average correlation between confidence and success is {avg_corr:.3f}.\n")
            if avg_corr > 0.1:
                f.write("  - This suggests the confidence score is a valid predictor of fix success.\n")
            else:
                f.write("  - The confidence score shows weak or no correlation with success.\n")
        
        f.write("\n")

def main():
    parser = argparse.ArgumentParser(description='Analyze BTMS routing results')
    parser.add_argument('--output-dir', type=str, default='/home/base/mengrui/MTSS/evaluation_output',
                        help='Base directory containing evaluation results')
    parser.add_argument('--report', type=str, default='ROUTING_EVALUATION_SUMMARY.md',
                        help='Output report filename')
    args = parser.parse_args()
    
    base_dir = Path(args.output_dir)
    results = load_results(base_dir)
    
    if not results:
        print("No results found.")
        return
        
    report_path = base_dir / args.report
    generate_report(results, report_path)
    print(f"Report generated: {report_path}")

if __name__ == '__main__':
    main()
