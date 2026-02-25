"""Output parser for model-generated fix outputs.

This module provides the OutputParser class for parsing different formats
of model-generated bug fixes (Edit and Rewrite formats).
"""

import logging
import re
from typing import List, Optional, Tuple

from evaluation.core.data_structures import (
    SearchReplace,
    RewritePatch,
    ParsedPatch
)

logger = logging.getLogger(__name__)


class OutputParser:
    """Parses model output to extract fix patches.
    
    Supports two formats:
    1. Edit format: SEARCH/REPLACE blocks with targeted changes
    2. Rewrite format: Complete method rewrites
    """
    
    # Regex patterns for parsing
    METHOD_SIGNATURE_PATTERN = r'###(.+?)(?:\n|$)'
    SEARCH_REPLACE_PATTERN = (
        r'<<<<<<< SEARCH\s*\n'
        r'(.*?)'
        r'\n=======\s*\n'
        r'(.*?)'
        r'\n>>>>>>> REPLACE'
    )
    CODE_BLOCK_PATTERN = r'```(?:java)?\s*\n(.*?)\n```'
    
    def __init__(self):
        """Initialize OutputParser."""
        self.search_replace_regex = re.compile(
            self.SEARCH_REPLACE_PATTERN,
            re.DOTALL
        )
        self.method_signature_regex = re.compile(
            self.METHOD_SIGNATURE_PATTERN
        )
        self.code_block_regex = re.compile(
            self.CODE_BLOCK_PATTERN,
            re.DOTALL
        )
    
    def parse(
        self,
        model_output: str,
        bug_slug: str,
        attempt_num: int,
        modeling_type: Optional[str] = None,
        query: Optional[str] = None
    ) -> ParsedPatch:
        """Parse model output to extract patches.
        
        Args:
            model_output: Content of model_output.txt file.
            bug_slug: Bug identifier.
            attempt_num: Attempt number.
            modeling_type: Type of modeling ('edit' or 'rewrite').
                          If None, will be auto-detected.
            query: Optional query content for extracting method signatures.
        
        Returns:
            ParsedPatch object containing extracted patches.
        """
        try:
            # Auto-detect format if not specified
            if modeling_type is None:
                modeling_type = self.detect_format(model_output)
            
            logger.info(
                f"Parsing {bug_slug}/{attempt_num} "
                f"(format: {modeling_type})"
            )
            
            if modeling_type == 'edit':
                search_replaces = self.parse_edit_format(model_output)
                return ParsedPatch(
                    bug_slug=bug_slug,
                    attempt_num=attempt_num,
                    modeling_type='edit',
                    search_replaces=search_replaces,
                    parse_success=True
                )
            elif modeling_type == 'rewrite':
                rewrites = self.parse_rewrite_format(model_output, query)
                return ParsedPatch(
                    bug_slug=bug_slug,
                    attempt_num=attempt_num,
                    modeling_type='rewrite',
                    rewrites=rewrites,
                    parse_success=True
                )
            else:
                raise ValueError(f"Unknown modeling type: {modeling_type}")
                
        except Exception as e:
            logger.error(
                f"Failed to parse {bug_slug}/{attempt_num}: {e}"
            )
            return ParsedPatch(
                bug_slug=bug_slug,
                attempt_num=attempt_num,
                modeling_type=modeling_type or 'unknown',
                parse_success=False,
                parse_error=str(e)
            )
    
    def detect_format(self, model_output: str) -> str:
        """Detect the format of model output.
        
        Args:
            model_output: Model output content.
            
        Returns:
            'edit' or 'rewrite'.
        """
        # Check for SEARCH/REPLACE markers (Edit format)
        if '<<<<<<< SEARCH' in model_output and '>>>>>>> REPLACE' in model_output:
            return 'edit'
        
        # Check for method signature without SEARCH/REPLACE (Rewrite format)
        if '###' in model_output and '<<<<<<< SEARCH' not in model_output:
            return 'rewrite'
        
        # Default to edit if unclear
        logger.warning(
            "Could not clearly detect format, defaulting to 'edit'"
        )
        return 'edit'
    
    def parse_edit_format(self, model_output: str) -> List[SearchReplace]:
        """Parse Edit format (SEARCH/REPLACE blocks).
        
        Args:
            model_output: Model output content.
            
        Returns:
            List of SearchReplace objects.
        """
        search_replaces = []
        
        # Extract code from markdown code blocks if present
        code_content = self._extract_code_blocks(model_output)
        if not code_content:
            code_content = model_output
        
        # Find all method signatures
        method_signatures = self._extract_method_signatures(code_content)
        
        # Find all SEARCH/REPLACE blocks
        matches = self.search_replace_regex.finditer(code_content)
        
        for i, match in enumerate(matches):
            search_block = match.group(1)
            replace_block = match.group(2)
            raw_text = match.group(0)
            
            # Get corresponding method signature
            method_sig = method_signatures[i] if i < len(method_signatures) else ""
            
            search_replace = SearchReplace(
                method_signature=method_sig.strip(),
                search_block=search_block,
                replace_block=replace_block,
                raw_text=raw_text
            )
            
            search_replaces.append(search_replace)
            logger.debug(
                f"Extracted SEARCH/REPLACE block {i+1}: "
                f"method='{method_sig.strip()}'"
            )
        
        if not search_replaces:
            logger.warning("No SEARCH/REPLACE blocks found in edit format")
        
        return search_replaces
    
    def parse_rewrite_format(
        self,
        model_output: str,
        query: Optional[str] = None
    ) -> List[RewritePatch]:
        """Parse Rewrite format (complete method rewrites).
        
        Args:
            model_output: Model output content.
            query: Optional query content for extracting method signatures.
            
        Returns:
            List of RewritePatch objects.
        """
        rewrites = []
        
        # Extract code from markdown code blocks if present
        code_content = self._extract_code_blocks(model_output)
        if not code_content:
            code_content = model_output
        
        # Fix truncated lines in Gen format output
        code_content = self._fix_truncated_lines(code_content)
        
        # Split by method signatures (###method_sig format)
        parts = re.split(self.METHOD_SIGNATURE_PATTERN, code_content)
        
        # Check if we found any ### markers
        if len(parts) > 1:
            # parts[0] is text before first signature
            # parts[1] is first signature, parts[2] is first code
            # parts[3] is second signature, parts[4] is second code, etc.
            
            for i in range(1, len(parts), 2):
                if i + 1 < len(parts):
                    method_sig = parts[i].strip()
                    full_code = parts[i + 1].strip()
                    
                    rewrite = RewritePatch(
                        method_signature=method_sig,
                        full_code=full_code,
                        raw_text=f"###{method_sig}\n{full_code}"
                    )
                    
                    rewrites.append(rewrite)
                    logger.debug(
                        f"Extracted rewrite: method='{method_sig}'"
                    )
        else:
            # No ### markers found - treat entire code as single rewrite
            # This handles Gen format where model_output is just the code
            if code_content.strip():
                # Try to extract method signature from query first
                method_sig = ""
                if query:
                    method_sig = self._extract_method_signature_from_query(
                        query
                    )
                
                # Fallback to extracting from code if query didn't work
                if not method_sig:
                    method_sig = self._extract_method_signature_from_code(
                        code_content
                    )
                
                rewrite = RewritePatch(
                    method_signature=method_sig,
                    full_code=code_content.strip(),
                    raw_text=code_content.strip()
                )
                
                rewrites.append(rewrite)
                logger.debug(
                    f"Extracted rewrite (no ### marker): method='{method_sig}'"
                )
        
        if not rewrites:
            logger.warning("No method rewrites found in rewrite format")
        
        return rewrites
    
    def _extract_code_blocks(self, content: str) -> str:
        """Extract code from markdown code blocks.
        
        Args:
            content: Content that may contain markdown code blocks.
            
        Returns:
            Extracted code, or empty string if no code blocks found.
        """
        matches = self.code_block_regex.findall(content)
        
        if matches:
            # Join all code blocks
            return '\n\n'.join(matches)
        
        return ""
    
    def _extract_method_signatures(self, content: str) -> List[str]:
        """Extract all method signatures from content.
        
        Args:
            content: Content containing method signatures.
            
        Returns:
            List of method signatures.
        """
        matches = self.method_signature_regex.findall(content)
        return [m.strip() for m in matches]
    
    def _extract_method_signature_from_code(self, code: str) -> str:
        """Extract method signature from Java code.
        
        Args:
            code: Java code containing a method.
            
        Returns:
            Method signature string, or empty string if not found.
        """
        # Pattern to match Java method signatures
        # Matches: [modifiers] returnType methodName(parameters)
        pattern = r'((?:public|private|protected|static|final|synchronized|abstract|native|\s)+)[\w<>\[\]]+\s+(\w+)\s*\([^)]*\)'
        
        match = re.search(pattern, code)
        if match:
            return match.group(0).strip()
        
        return ""
    
    def _extract_method_signature_from_query(self, query: str) -> str:
        """Extract method signature from query content.
        
        For Gen format, the query.txt contains the buggy function with
        the signature inside a code block after "### Buggy functions".
        
        Args:
            query: Query content from query.txt.
            
        Returns:
            Method signature string, or empty string if not found.
        """
        # Look for the "### Buggy functions" section
        buggy_section_match = re.search(
            r'###\s*Buggy functions.*?```java\s*(.*?)```',
            query,
            re.DOTALL | re.IGNORECASE
        )
        
        if buggy_section_match:
            buggy_code = buggy_section_match.group(1).strip()
            
            # Use regex to find method signature
            # Pattern matches: [modifiers] returnType methodName(params)
            # This handles multi-line signatures
            pattern = r'((?:public|private|protected|static|final|synchronized|abstract|\s)+)([\w<>\[\]]+)\s+(\w+)\s*\(((?:[^)]|\n)*?)\)'
            
            match = re.search(pattern, buggy_code)
            if match:
                # Reconstruct the signature from captured groups
                modifiers = ' '.join(match.group(1).split())  # Normalize whitespace
                return_type = match.group(2).strip()
                method_name = match.group(3).strip()
                params = ' '.join(match.group(4).split())  # Normalize whitespace
                
                signature = f"{modifiers} {return_type} {method_name}({params})"
                return signature
        
        return ""
    
    def validate_search_replace(
        self,
        search_replace: SearchReplace
    ) -> Tuple[bool, Optional[str]]:
        """Validate a SearchReplace object.
        
        Args:
            search_replace: SearchReplace to validate.
            
        Returns:
            Tuple of (is_valid, error_message).
        """
        if not search_replace.method_signature:
            return False, "Missing method signature"
        
        if not search_replace.search_block:
            return False, "Empty SEARCH block"
        
        if not search_replace.replace_block:
            return False, "Empty REPLACE block"
        
        # Check that search and replace are different
        if search_replace.search_block.strip() == search_replace.replace_block.strip():
            return False, "SEARCH and REPLACE blocks are identical"
        
        return True, None
    
    def validate_rewrite(
        self,
        rewrite: RewritePatch
    ) -> Tuple[bool, Optional[str]]:
        """Validate a RewritePatch object.
        
        Args:
            rewrite: RewritePatch to validate.
            
        Returns:
            Tuple of (is_valid, error_message).
        """
        if not rewrite.method_signature:
            return False, "Missing method signature"
        
        if not rewrite.full_code:
            return False, "Empty code"
        
        # Check that code looks like valid Java
        if '{' not in rewrite.full_code or '}' not in rewrite.full_code:
            return False, "Code doesn't appear to be a complete method"
        
        return True, None

    def _fix_truncated_lines(self, code: str) -> str:
        """Fix truncated lines in Gen format output.
        
        Gen format outputs sometimes have lines truncated at ~80 characters,
        causing syntax errors. This method joins truncated lines back together.
        
        Args:
            code: Code content that may have truncated lines.
            
        Returns:
            Code with truncated lines fixed.
        """
        lines = code.split('\n')
        fixed_lines = []
        i = 0
        
        while i < len(lines):
            current = lines[i]
            
            # Check if this line might be truncated
            # Criteria: line is long (>75 chars), doesn't end with typical
            # line-ending characters, and next line exists
            if (i + 1 < len(lines) and
                len(current.rstrip()) > 75 and
                current.rstrip() and
                not current.rstrip()[-1] in ';,{})]:' and
                lines[i + 1].strip() and
                not lines[i + 1].strip()[0] in '{'):
                
                # Check if next line starts without proper indentation
                # (suggesting it's a continuation)
                next_line = lines[i + 1]
                current_indent = len(current) - len(current.lstrip())
                next_indent = len(next_line) - len(next_line.lstrip())
                
                # If next line has less or equal indentation and starts
                # with a lowercase letter or continues a word, it's likely
                # a truncated continuation
                if (next_indent <= current_indent and
                    next_line.strip() and
                    (next_line.strip()[0].islower() or
                     not current.rstrip()[-1].isspace())):
                    # Join the lines
                    fixed_lines.append(current.rstrip() + next_line.lstrip())
                    i += 2
                    continue
            
            fixed_lines.append(current)
            i += 1
        
        return '\n'.join(fixed_lines)
