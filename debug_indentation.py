#!/usr/bin/env python3
"""Debug indentation normalization."""

def normalize_indentation(text: str) -> str:
    """Normalize indentation."""
    lines = text.split('\n')
    normalized_lines = []
    
    for line in lines:
        stripped = line.lstrip()
        if not stripped:
            normalized_lines.append('')
            continue
        
        leading_ws = len(line) - len(stripped)
        indent_level = leading_ws // 4
        normalized_line = (' ' * indent_level) + stripped
        normalized_lines.append(normalized_line)
    
    return '\n'.join(normalized_lines)

# Test with model output (8 spaces)
model_line = "        h[1] = size.height;"
print(f"Model line: '{model_line}'")
print(f"  Leading spaces: {len(model_line) - len(model_line.lstrip())}")
print(f"  Normalized: '{normalize_indentation(model_line)}'")
print()

# Test with source (12 spaces)
source_line = "            h[1] = size.height;"
print(f"Source line: '{source_line}'")
print(f"  Leading spaces: {len(source_line) - len(source_line.lstrip())}")
print(f"  Normalized: '{normalize_indentation(source_line)}'")
print()

# Check if they match after normalization
model_norm = normalize_indentation(model_line)
source_norm = normalize_indentation(source_line)
print(f"Match: {model_norm == source_norm}")
