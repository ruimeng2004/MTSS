#!/usr/bin/env python3
"""Anonymize patches by replacing project-specific identifiers."""

import re
import json
import argparse
from pathlib import Path
from typing import Dict, Set, Tuple, List
from collections import defaultdict


class PatchAnonymizer:
    """Anonymize patches by replacing identifiers with abstract tokens."""
    
    # Common Java/programming keywords to preserve
    KEYWORDS = {
        'if', 'else', 'for', 'while', 'do', 'switch', 'case', 'break',
        'continue', 'return', 'throw', 'try', 'catch', 'finally',
        'public', 'private', 'protected', 'static', 'final', 'abstract',
        'class', 'interface', 'extends', 'implements', 'new', 'this',
        'super', 'null', 'true', 'false', 'void', 'int', 'long', 'float',
        'double', 'boolean', 'char', 'byte', 'short', 'String', 'Object',
        'import', 'package', 'throws', 'synchronized', 'volatile',
        'transient', 'native', 'strictfp', 'assert', 'enum', 'const',
        'goto', 'instanceof'
    }
    
    # Common method prefixes to preserve semantic meaning
    SEMANTIC_PREFIXES = {
        'get', 'set', 'is', 'has', 'add', 'remove', 'delete', 'update',
        'create', 'find', 'search', 'check', 'validate', 'parse',
        'format', 'convert', 'calculate', 'compute', 'process',
        'init', 'initialize', 'start', 'stop', 'close', 'open',
        'read', 'write', 'load', 'save', 'clear', 'reset'
    }
    
    def __init__(self, preserve_semantics: bool = True):
        """Initialize anonymizer.
        
        Args:
            preserve_semantics: If True, preserve common semantic prefixes.
        """
        self.preserve_semantics = preserve_semantics
        self.identifier_map: Dict[str, str] = {}
        self.class_counter = 0
        self.method_counter = 0
        self.var_counter = 0
        self.package_counter = 0
    
    def _is_keyword(self, token: str) -> bool:
        """Check if token is a keyword to preserve."""
        return token.lower() in self.KEYWORDS
    
    def _has_semantic_prefix(self, token: str) -> bool:
        """Check if token has a semantic prefix to preserve."""
        if not self.preserve_semantics:
            return False
        
        token_lower = token.lower()
        for prefix in self.SEMANTIC_PREFIXES:
            if token_lower.startswith(prefix):
                return True
        return False
    
    def _get_identifier_type(self, token: str, context: str) -> str:
        """Determine identifier type from context.
        
        Args:
            token: The identifier token.
            context: Surrounding text for context.
        
        Returns:
            Type: 'CLASS', 'METHOD', 'VAR', or 'PACKAGE'.
        """
        # Check if it's a class (starts with uppercase)
        if token[0].isupper():
            return 'CLASS'
        
        # Check if it's a method (followed by parenthesis)
        if '(' in context:
            return 'METHOD'
        
        # Check if it's a package (contains dots)
        if '.' in token:
            return 'PACKAGE'
        
        # Default to variable
        return 'VAR'
    
    def _anonymize_identifier(
        self,
        token: str,
        id_type: str
    ) -> str:
        """Anonymize a single identifier.
        
        Args:
            token: The identifier to anonymize.
            id_type: Type of identifier (CLASS, METHOD, VAR, PACKAGE).
        
        Returns:
            Anonymized token.
        """
        if token in self.identifier_map:
            return self.identifier_map[token]
        
        # Preserve semantic prefix if enabled
        if self._has_semantic_prefix(token):
            prefix = next(
                p for p in self.SEMANTIC_PREFIXES
                if token.lower().startswith(p)
            )
            suffix_start = len(prefix)
            suffix = token[suffix_start:]
            
            # Anonymize the suffix part
            if id_type == 'CLASS':
                anon = f"{prefix}Class{self.class_counter}"
                self.class_counter += 1
            elif id_type == 'METHOD':
                anon = f"{prefix}Method{self.method_counter}"
                self.method_counter += 1
            else:
                anon = f"{prefix}Var{self.var_counter}"
                self.var_counter += 1
        else:
            # Full anonymization
            if id_type == 'CLASS':
                anon = f"CLASS_{self.class_counter}"
                self.class_counter += 1
            elif id_type == 'METHOD':
                anon = f"METHOD_{self.method_counter}"
                self.method_counter += 1
            elif id_type == 'PACKAGE':
                anon = f"PACKAGE_{self.package_counter}"
                self.package_counter += 1
            else:
                anon = f"VAR_{self.var_counter}"
                self.var_counter += 1
        
        self.identifier_map[token] = anon
        return anon
    
    def anonymize_patch(self, patch_text: str) -> Tuple[str, Dict[str, str]]:
        """Anonymize a patch by replacing identifiers.
        
        Args:
            patch_text: Original patch text.
        
        Returns:
            Tuple of (anonymized_patch, identifier_mapping).
        """
        # Reset counters for each patch
        self.identifier_map = {}
        self.class_counter = 0
        self.method_counter = 0
        self.var_counter = 0
        self.package_counter = 0
        
        lines = patch_text.split('\n')
        anonymized_lines = []
        
        for line in lines:
            # Skip diff headers and metadata
            if (line.startswith('diff ') or
                line.startswith('index ') or
                line.startswith('---') or
                line.startswith('+++') or
                line.startswith('@@')):
                anonymized_lines.append(line)
                continue
            
            # Process code lines
            anonymized_line = self._anonymize_line(line)
            anonymized_lines.append(anonymized_line)
        
        return '\n'.join(anonymized_lines), self.identifier_map
    
    def _anonymize_line(self, line: str) -> str:
        """Anonymize identifiers in a single line.
        
        Args:
            line: Original line of code.
        
        Returns:
            Anonymized line.
        """
        # Preserve leading whitespace and diff markers
        prefix = ''
        if line and line[0] in [' ', '+', '-']:
            prefix = line[0]
            line = line[1:]
        
        # Find all identifiers (simplified: alphanumeric + underscore)
        # This regex matches Java identifiers
        pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b'
        
        def replace_identifier(match):
            token = match.group(1)
            
            # Preserve keywords
            if self._is_keyword(token):
                return token
            
            # Determine type and anonymize
            context = line[max(0, match.start()-10):match.end()+10]
            id_type = self._get_identifier_type(token, context)
            return self._anonymize_identifier(token, id_type)
        
        anonymized = re.sub(pattern, replace_identifier, line)
        return prefix + anonymized


def process_patches(
    input_file: Path,
    output_file: Path,
    preserve_semantics: bool = True,
    save_mapping: bool = True
) -> None:
    """Process all patches and save anonymized versions.
    
    Args:
        input_file: Path to input patches JSONL file.
        output_file: Path to output anonymized patches JSONL file.
        preserve_semantics: If True, preserve semantic prefixes.
        save_mapping: If True, save identifier mappings.
    """
    anonymizer = PatchAnonymizer(preserve_semantics=preserve_semantics)
    
    anonymized_patches = []
    all_mappings = {}
    
    print(f"Processing patches from: {input_file}")
    print(f"Preserve semantics: {preserve_semantics}")
    print()
    
    with open(input_file, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if not line.strip():
                continue
            
            patch = json.loads(line)
            original_text = patch['text']
            
            # Anonymize the patch
            anonymized_text, mapping = anonymizer.anonymize_patch(
                original_text
            )
            
            # Create new patch item
            anon_patch = patch.copy()
            anon_patch['text'] = anonymized_text
            anon_patch['original_text'] = original_text
            anon_patch['anonymized'] = True
            
            anonymized_patches.append(anon_patch)
            all_mappings[patch['item_id']] = mapping
            
            if (i + 1) % 100 == 0:
                print(f"  Processed {i + 1} patches...")
    
    # Save anonymized patches
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        for patch in anonymized_patches:
            f.write(json.dumps(patch, ensure_ascii=False) + '\n')
    
    print()
    print(f"Saved {len(anonymized_patches)} anonymized patches to:")
    print(f"  {output_file}")
    
    # Save mappings if requested
    if save_mapping:
        mapping_file = output_file.parent / (output_file.stem + '_mappings.json')
        with open(mapping_file, 'w', encoding='utf-8') as f:
            json.dump(all_mappings, f, indent=2, ensure_ascii=False)
        print(f"Saved identifier mappings to:")
        print(f"  {mapping_file}")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Anonymize patches by replacing project-specific identifiers'
    )
    parser.add_argument(
        '--input',
        type=str,
        default='bug_task_model_selection/data/artifacts/patches_filtered.jsonl',
        help='Path to input patches JSONL file'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='bug_task_model_selection/data/artifacts/patches_anonymized.jsonl',
        help='Path to output anonymized patches JSONL file'
    )
    parser.add_argument(
        '--no-semantics',
        action='store_true',
        help='Do not preserve semantic prefixes (full anonymization)'
    )
    parser.add_argument(
        '--no-mapping',
        action='store_true',
        help='Do not save identifier mappings'
    )
    
    args = parser.parse_args()
    
    try:
        process_patches(
            input_file=Path(args.input),
            output_file=Path(args.output),
            preserve_semantics=not args.no_semantics,
            save_mapping=not args.no_mapping
        )
        return 0
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
