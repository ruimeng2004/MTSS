#!/usr/bin/env python3
"""Analyze line truncation issues in Gen format outputs."""

import re
from pathlib import Path

def check_truncation(file_path):
    """Check if a file has truncated lines.
    
    Args:
        file_path: Path to model_output.txt file.
    
    Returns:
        Tuple of (has_truncation, truncated_lines).
    """
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()
        
        truncated = []
        for i, line in enumerate(lines, 1):
            # Check if line ends mid-word (no space before newline)
            # and next line starts without indentation
            if i < len(lines):
                current = line.rstrip('\n')
                next_line = lines[i].lstrip() if i < len(lines) else ""
                
                # Detect truncation: line ends without space/punctuation
                # and is very long (>80 chars)
                if (len(current) > 75 and 
                    current and 
                    not current[-1] in ' \t;,{})]:' and
                    next_line and
                    not next_line[0] in ' \t'):
                    truncated.append((i, current[-20:]))
        
        return len(truncated) > 0, truncated
    except Exception as e:
        return False, []

def main():
    """Analyze truncation in Gen format outputs."""
    input_dir = Path("ppl/result/20260106_030425")
    
    total_bugs = 0
    truncated_bugs = 0
    truncation_details = []
    
    for bug_dir in sorted(input_dir.iterdir()):
        if not bug_dir.is_dir() or bug_dir.name.startswith('.'):
            continue
        
        bug_slug = bug_dir.name
        
        for attempt_dir in sorted(bug_dir.iterdir()):
            if not attempt_dir.is_dir():
                continue
            
            model_output = attempt_dir / "model_output.txt"
            if not model_output.exists():
                continue
            
            total_bugs += 1
            has_trunc, trunc_lines = check_truncation(model_output)
            
            if has_trunc:
                truncated_bugs += 1
                truncation_details.append({
                    'bug': bug_slug,
                    'attempt': attempt_dir.name,
                    'lines': trunc_lines
                })
    
    print("="*60)
    print("GEN FORMAT TRUNCATION ANALYSIS")
    print("="*60)
    print(f"Total attempts analyzed: {total_bugs}")
    print(f"Attempts with truncation: {truncated_bugs}")
    print(f"Truncation rate: {truncated_bugs/total_bugs*100:.1f}%")
    print()
    
    if truncation_details:
        print("Sample truncated outputs (first 10):")
        for detail in truncation_details[:10]:
            print(f"  {detail['bug']}/{detail['attempt']}: "
                  f"{len(detail['lines'])} truncated lines")
            if detail['lines']:
                line_num, text = detail['lines'][0]
                print(f"    Line {line_num}: ...{text}")

if __name__ == "__main__":
    main()
