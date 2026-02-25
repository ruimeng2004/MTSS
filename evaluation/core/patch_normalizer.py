"""Patch normalizer for converting parsed patches to unified diff format.

This module provides the PatchNormalizer class for normalizing both Edit and
Rewrite format patches into standard unified diff format that can be applied
with git apply or patch command.
"""

import difflib
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from tree_sitter import Language, Parser
import tree_sitter_java

from evaluation.core.data_structures import (
    ParsedPatch,
    SearchReplace,
    RewritePatch,
    NormalizedPatch,
    MatchResult,
    MatchQuality,
    NormalizationStrategy,
    NormalizationError,
    SearchBlockNotFoundError,
    AmbiguousMatchError,
    MethodNotFoundError
)

logger = logging.getLogger(__name__)


class PatchNormalizer:
    """Normalizes parsed patches to unified diff format.
    
    This class handles the conversion of both Edit format (SEARCH/REPLACE)
    and Rewrite format patches into standard unified diff format. It uses
    tree-sitter for method location and implements exact matching strategies.
    
    Attributes:
        context_lines: Number of context lines to include in diffs.
        java_parser: Tree-sitter parser for Java code.
        reporter: Optional reporter for tracking normalization issues.
    """
    
    def __init__(
        self,
        context_lines: int = 3,
        reporter: Optional[Any] = None
    ):
        """Initialize PatchNormalizer.
        
        Args:
            context_lines: Number of context lines for unified diff.
            reporter: Optional NormalizationReporter for tracking issues.
        """
        self.context_lines = context_lines
        self.reporter = reporter
        
        # Initialize tree-sitter parser for Java
        self.java_language = Language(tree_sitter_java.language())
        self.java_parser = Parser(self.java_language)
        
        logger.info(
            f"Initialized PatchNormalizer with {context_lines} context lines"
        )
    
    def _extract_relative_path(self, filepath: Path, bug_slug: str = None) -> str:
        """Extract repository-relative path from absolute path.
        
        Args:
            filepath: Absolute or relative path to source file.
            bug_slug: Bug identifier (e.g., "Gson_12") for project-specific handling.
            
        Returns:
            Repository-relative path (e.g., 'source/org/package/File.java').
        """
        filepath_str = str(filepath)
        
        # Look for common Java source directories and extract from there
        for part in ['source/', 'src/main/java/', 'src/']:
            if part in filepath_str:
                # Extract everything from this directory onwards
                idx = filepath_str.find(part)
                relative_path = filepath_str[idx:]
                
                # Special handling for Gson project
                # Gson has a gson/ subdirectory that needs to be included
                if bug_slug and bug_slug.startswith('Gson_'):
                    if 'gson/src' in filepath_str and not relative_path.startswith('gson/'):
                        # Add gson/ prefix if the file is in gson/ subdirectory
                        relative_path = 'gson/' + relative_path
                
                return relative_path
        
        # If no standard directory found, return just the filename
        return filepath.name
    
    def find_source_file_for_method(
        self,
        repo_path: Path,
        method_signature: str,
        search_block: Optional[str] = None
    ) -> Optional[Path]:
        """Find source file containing a specific method using tree-sitter.
        
        Searches all Java files in the repository to find the one containing
        the method with the given signature. If search_block is provided and
        multiple files contain the method, uses the search_block content to
        disambiguate.
        
        Args:
            repo_path: Path to repository root.
            method_signature: Method signature to search for.
            search_block: Optional SEARCH block content for disambiguation.
            
        Returns:
            Path to source file containing the method, or None if not found.
        """
        # Extract method name from signature
        method_name = self._extract_method_name(method_signature)
        
        if not method_name:
            logger.warning(
                f"Could not extract method name from: {method_signature}"
            )
            return None
        
        logger.debug(
            f"Searching for method '{method_name}' in repository: {repo_path}"
        )
        
        # Find all Java files
        java_files = list(repo_path.rglob("*.java"))
        logger.debug(f"Found {len(java_files)} Java files to search")
        
        # Collect all matching files
        matching_files = []
        
        # Search each file
        for java_file in java_files:
            try:
                with open(java_file, 'r', encoding='utf-8') as f:
                    source_content = f.read()
                
                # Try to locate method in this file
                method_node = self._locate_method_with_treesitter(
                    source_content=source_content,
                    method_signature=method_signature
                )
                
                if method_node:
                    matching_files.append((java_file, source_content, method_node))
                    
            except Exception as e:
                # Skip files that can't be read or parsed
                logger.debug(f"Error searching {java_file}: {e}")
                continue
        
        if not matching_files:
            logger.warning(
                f"Method '{method_name}' not found in any Java file"
            )
            return None
        
        # If only one match, return it
        if len(matching_files) == 1:
            logger.info(
                f"Found method '{method_name}' in: {matching_files[0][0]}"
            )
            return matching_files[0][0]
        
        # Multiple matches - use search_block to disambiguate
        logger.info(
            f"Found {len(matching_files)} files with method '{method_name}'"
        )
        
        if search_block:
            logger.debug("Using SEARCH block content for disambiguation")
            
            # Normalize search block for comparison
            search_normalized = self._normalize_indentation(
                self._normalize_newlines(search_block)
            )
            search_lines_filtered = [
                line for line in search_normalized.split('\n')
                if line.strip() and line.strip() not in ['{', '}']
            ]
            
            # Check each matching file
            for java_file, source_content, method_node in matching_files:
                method_text = method_node['text']
                method_normalized = self._normalize_indentation(
                    self._normalize_newlines(method_text)
                )
                method_lines_filtered = [
                    line for line in method_normalized.split('\n')
                    if line.strip() and line.strip() not in ['{', '}']
                ]
                
                # Try to match search lines in method
                match_found, _ = self._fuzzy_match_lines(
                    search_lines_filtered,
                    method_normalized.split('\n'),
                    search_normalized.split('\n')
                )
                
                if match_found:
                    logger.info(
                        f"Found method '{method_name}' with matching SEARCH "
                        f"block in: {java_file}"
                    )
                    return java_file
            
            logger.warning(
                f"SEARCH block not found in any of the {len(matching_files)} "
                f"files containing method '{method_name}'"
            )
        
        # Fallback: return first match (interface or abstract class likely)
        logger.warning(
            f"Returning first match for '{method_name}': {matching_files[0][0]}"
        )
        return matching_files[0][0]
    
    def normalize(
        self,
        parsed_patch: ParsedPatch,
        source_file: Path
    ) -> NormalizedPatch:
        """Normalize a parsed patch to unified diff format.
        
        Args:
            parsed_patch: ParsedPatch object from OutputParser.
            source_file: Path to the source file to be patched.
                        Can be a repository root path, in which case the
                        correct source file will be searched automatically.
            
        Returns:
            NormalizedPatch object containing unified diff.
            
        Raises:
            FileNotFoundError: If source file doesn't exist and can't be found.
            ValueError: If patch format is unknown.
        """
        # If source_file is a directory (repository root), search for the file
        if source_file.is_dir():
            logger.info(
                f"Source file is a directory, searching for method in repository"
            )
            
            # Get method signature and search block from first search/replace or rewrite
            method_sig = None
            search_block = None
            
            if parsed_patch.modeling_type == 'edit' and parsed_patch.search_replaces:
                method_sig = parsed_patch.search_replaces[0].method_signature
                search_block = parsed_patch.search_replaces[0].search_block
            elif parsed_patch.modeling_type == 'rewrite' and parsed_patch.rewrites:
                method_sig = parsed_patch.rewrites[0].method_signature
                # For rewrite, we don't have a search block, but we have the full code
                # We can use part of it for disambiguation
                search_block = None
            
            if method_sig:
                found_file = self.find_source_file_for_method(
                    repo_path=source_file,
                    method_signature=method_sig,
                    search_block=search_block
                )
                
                if found_file:
                    source_file = found_file
                else:
                    raise FileNotFoundError(
                        f"Could not find source file for method: {method_sig}"
                    )
            else:
                raise ValueError(
                    "Cannot search for source file without method signature"
                )
        
        if not source_file.exists():
            raise FileNotFoundError(f"Source file not found: {source_file}")
        
        logger.info(
            f"Normalizing {parsed_patch.bug_slug}/{parsed_patch.attempt_num} "
            f"(format: {parsed_patch.modeling_type})"
        )
        
        if parsed_patch.modeling_type == 'edit':
            return self._normalize_edit_patches(parsed_patch, source_file)
        elif parsed_patch.modeling_type == 'rewrite':
            return self._normalize_rewrite_patches(parsed_patch, source_file)
        else:
            raise ValueError(
                f"Unknown modeling type: {parsed_patch.modeling_type}"
            )
    
    def normalize_with_fallback(
        self,
        parsed_patch: ParsedPatch,
        source_file: Path
    ) -> Tuple[NormalizedPatch, NormalizationStrategy]:
        """Normalize patch with fallback strategies.
        
        Tries multiple strategies in order:
        1. METHOD_SCOPED_EXACT: Exact match within method scope
        2. FILE_SCOPED_EXACT: Exact match within entire file
        3. MANUAL_REVIEW: All strategies failed, needs manual review
        
        Args:
            parsed_patch: ParsedPatch object from OutputParser.
            source_file: Path to the source file to be patched.
            
        Returns:
            Tuple of (NormalizedPatch, NormalizationStrategy used).
            
        Raises:
            NormalizationError: If all strategies fail.
        """
        if not source_file.exists():
            raise FileNotFoundError(f"Source file not found: {source_file}")
        
        logger.info(
            f"Normalizing with fallback: {parsed_patch.bug_slug}/"
            f"{parsed_patch.attempt_num}"
        )
        
        # Read source file once
        with open(source_file, 'r', encoding='utf-8') as f:
            source_content = f.read()
        
        # Define strategies to try
        strategies = [
            NormalizationStrategy.METHOD_SCOPED_EXACT,
            NormalizationStrategy.FILE_SCOPED_EXACT,
        ]
        
        last_match_result = None
        
        # Try each strategy
        for strategy in strategies:
            logger.debug(f"Trying strategy: {strategy.value}")
            
            try:
                # For edit format, try to locate and normalize
                if parsed_patch.modeling_type == 'edit':
                    success, result = self._try_strategy_for_edit(
                        parsed_patch,
                        source_file,
                        source_content,
                        strategy
                    )
                    
                    if success:
                        logger.info(
                            f"Normalization succeeded with strategy: "
                            f"{strategy.value}"
                        )
                        # Add strategy to metadata
                        result.normalization_strategy = strategy.value
                        return result, strategy
                    else:
                        last_match_result = result
                        continue
                
                # For rewrite format, method location is required
                elif parsed_patch.modeling_type == 'rewrite':
                    # Rewrite always uses method-scoped strategy
                    if strategy == NormalizationStrategy.METHOD_SCOPED_EXACT:
                        result = self._normalize_rewrite_patches(
                            parsed_patch,
                            source_file
                        )
                        result.normalization_strategy = strategy.value
                        return result, strategy
                    else:
                        # Skip file-scoped for rewrite
                        continue
                
            except Exception as e:
                logger.warning(
                    f"Strategy {strategy.value} raised exception: {e}"
                )
                continue
        
        # All strategies failed - generate failure report
        logger.error(
            f"All normalization strategies failed for "
            f"{parsed_patch.bug_slug}/{parsed_patch.attempt_num}"
        )
        
        failure_report_path = self._generate_failure_report(
            parsed_patch,
            source_file,
            last_match_result
        )
        
        raise NormalizationError(
            f"Failed to normalize patch - requires manual review. "
            f"See failure report: {failure_report_path}"
        )
    
    def _try_strategy_for_edit(
        self,
        parsed_patch: ParsedPatch,
        source_file: Path,
        source_content: str,
        strategy: NormalizationStrategy
    ) -> Tuple[bool, Any]:
        """Try a specific strategy for edit format patches.
        
        Args:
            parsed_patch: ParsedPatch with search_replaces.
            source_file: Path to source file.
            source_content: Source file content.
            strategy: Strategy to try.
            
        Returns:
            Tuple of (success: bool, result: NormalizedPatch or MatchResult).
        """
        all_diffs = []
        all_metadata = []
        overall_quality = MatchQuality.EXACT_UNIQUE
        
        for i, sr in enumerate(parsed_patch.search_replaces):
            try:
                # Try to locate search block with this strategy
                if strategy == NormalizationStrategy.METHOD_SCOPED_EXACT:
                    match_result = self.locate_search_block_with_method_context(
                        source_content=source_content,
                        method_signature=sr.method_signature,
                        search_text=sr.search_block
                    )
                elif strategy == NormalizationStrategy.FILE_SCOPED_EXACT:
                    match_result = self.locate_search_block_in_file(
                        source_content=source_content,
                        search_text=sr.search_block
                    )
                else:
                    return False, None
                
                # Check match quality
                if not match_result.found:
                    logger.debug(
                        f"Block {i+1}: Not found with {strategy.value}"
                    )
                    return False, match_result
                
                if match_result.is_ambiguous:
                    logger.debug(
                        f"Block {i+1}: Ambiguous match with {strategy.value}"
                    )
                    overall_quality = MatchQuality.EXACT_AMBIGUOUS
                    return False, match_result
                
                # Generate diff for this block
                match = match_result.matches[0]
                diff = self._generate_diff_for_search_replace(
                    sr=sr,
                    source_file=source_file,
                    source_content=source_content,
                    match_start_line=match['start_line'],
                    match_end_line=match['end_line'],
                    bug_slug=parsed_patch.bug_slug
                )
                
                all_diffs.append(diff)
                all_metadata.append({
                    'method_signature': sr.method_signature,
                    'start_line': match['start_line'],
                    'end_line': match['end_line'],
                    'match_quality': match_result.quality.value,
                    'strategy': strategy.value
                })
                
            except Exception as e:
                logger.debug(f"Block {i+1}: Exception with {strategy.value}: {e}")
                return False, None
        
        # All blocks successfully normalized
        combined_diff = '\n'.join(all_diffs)
        
        normalized_patch = NormalizedPatch(
            bug_slug=parsed_patch.bug_slug,
            attempt_num=parsed_patch.attempt_num,
            modeling_type='edit',
            diff_content=combined_diff,
            target_files=[str(source_file)],
            metadata={
                'blocks': all_metadata,
                'total_blocks': len(parsed_patch.search_replaces),
                'successful_blocks': len(all_diffs),
                'strategy': strategy.value
            },
            match_quality=overall_quality,
            normalization_strategy=strategy.value
        )
        
        return True, normalized_patch

    
    def _normalize_edit_patches(
        self,
        parsed_patch: ParsedPatch,
        source_file: Path
    ) -> NormalizedPatch:
        """Normalize Edit format patches.
        
        Args:
            parsed_patch: ParsedPatch with search_replaces.
            source_file: Path to source file.
            
        Returns:
            NormalizedPatch with unified diff.
        """
        # Read source file
        with open(source_file, 'r', encoding='utf-8') as f:
            source_content = f.read()
        
        all_changes = []
        all_metadata = []
        overall_quality = MatchQuality.EXACT_UNIQUE
        
        for i, sr in enumerate(parsed_patch.search_replaces):
            logger.debug(
                f"Processing SEARCH/REPLACE block {i+1}/{len(parsed_patch.search_replaces)}: "
                f"method='{sr.method_signature}'"
            )
            
            try:
                # Locate the search block in source file
                match_result = self.locate_search_block_with_method_context(
                    source_content=source_content,
                    method_signature=sr.method_signature,
                    search_text=sr.search_block
                )
                
                if not match_result.found:
                    logger.warning(
                        f"Search block not found for {sr.method_signature}"
                    )
                    overall_quality = MatchQuality.NOT_FOUND
                    continue
                
                if match_result.is_ambiguous:
                    logger.warning(
                        f"Ambiguous match for {sr.method_signature}: "
                        f"{match_result.match_count} locations"
                    )
                    overall_quality = MatchQuality.EXACT_AMBIGUOUS
                
                # Store the change information
                match = match_result.matches[0]  # Use first match
                all_changes.append({
                    'start_line': match['start_line'],
                    'end_line': match['end_line'],
                    'replace_lines': sr.replace_block.split('\n'),
                    'search_replace': sr
                })
                
                all_metadata.append({
                    'method_signature': sr.method_signature,
                    'start_line': match['start_line'],
                    'end_line': match['end_line'],
                    'match_quality': match_result.quality.value
                })
                
            except Exception as e:
                logger.error(
                    f"Failed to normalize SEARCH/REPLACE block {i+1}: {e}"
                )
                overall_quality = MatchQuality.PARSE_ERROR
                continue
        
        # Check if any changes were found
        if len(all_changes) == 0:
            # No SEARCH blocks matched - raise error instead of returning empty
            error_msg = (
                f"No SEARCH blocks found in source file. "
                f"Attempted {len(parsed_patch.search_replaces)} blocks, "
                f"0 matched. This likely indicates a mismatch between "
                f"model training data and actual Defects4J source code."
            )
            logger.error(error_msg)
            raise SearchBlockNotFoundError(error_msg)
        
        # Generate unified diff
        if len(all_changes) == 1:
            # Single change, generate diff directly
            change = all_changes[0]
            source_lines = source_content.split('\n')
            matched_lines = source_lines[change['start_line'] - 1:change['end_line']]
            
            combined_diff = self.generate_unified_diff(
                original_lines=matched_lines,
                modified_lines=change['replace_lines'],
                filepath=str(source_file),
                start_line=change['start_line'],
                context_lines=self.context_lines,
                bug_slug=parsed_patch.bug_slug
            )
        else:
            # Multiple changes, merge them
            combined_diff = self._merge_multiple_changes(
                all_changes,
                source_file,
                source_content,
                parsed_patch.bug_slug
            )
        
        # Extract relative path for target_files
        relative_path = self._extract_relative_path(source_file, parsed_patch.bug_slug)
        
        return NormalizedPatch(
            bug_slug=parsed_patch.bug_slug,
            attempt_num=parsed_patch.attempt_num,
            modeling_type='edit',
            diff_content=combined_diff,
            target_files=[relative_path],
            metadata={
                'blocks': all_metadata,
                'total_blocks': len(parsed_patch.search_replaces),
                'successful_blocks': len(all_changes)
            },
            match_quality=overall_quality
        )
    
    def _normalize_rewrite_patches(
        self,
        parsed_patch: ParsedPatch,
        source_file: Path
    ) -> NormalizedPatch:
        """Normalize Rewrite format patches.
        
        Args:
            parsed_patch: ParsedPatch with rewrites.
            source_file: Path to source file.
            
        Returns:
            NormalizedPatch with unified diff.
        """
        # Read source file
        with open(source_file, 'r', encoding='utf-8') as f:
            source_content = f.read()
        
        all_diffs = []
        all_metadata = []
        
        for i, rewrite in enumerate(parsed_patch.rewrites):
            logger.debug(
                f"Processing rewrite {i+1}/{len(parsed_patch.rewrites)}: "
                f"method='{rewrite.method_signature}'"
            )
            
            try:
                # Locate method using tree-sitter
                method_node = self._locate_method_with_treesitter(
                    source_content=source_content,
                    method_signature=rewrite.method_signature
                )
                
                if not method_node:
                    logger.warning(
                        f"Method not found: {rewrite.method_signature}"
                    )
                    continue
                
                # Generate unified diff for method replacement
                diff = self._generate_diff_for_rewrite(
                    rewrite=rewrite,
                    source_file=source_file,
                    source_content=source_content,
                    method_node=method_node,
                    bug_slug=parsed_patch.bug_slug
                )
                
                all_diffs.append(diff)
                all_metadata.append({
                    'method_signature': rewrite.method_signature,
                    'start_line': method_node['start_line'],
                    'end_line': method_node['end_line']
                })
                
            except Exception as e:
                logger.error(f"Failed to normalize rewrite {i+1}: {e}")
                continue
        
        # Combine all diffs
        combined_diff = '\n'.join(all_diffs)
        
        # Extract relative path for target_files
        relative_path = self._extract_relative_path(source_file, parsed_patch.bug_slug)
        
        return NormalizedPatch(
            bug_slug=parsed_patch.bug_slug,
            attempt_num=parsed_patch.attempt_num,
            modeling_type='rewrite',
            diff_content=combined_diff,
            target_files=[relative_path],
            metadata={
                'methods': all_metadata,
                'total_methods': len(parsed_patch.rewrites),
                'successful_methods': len(all_diffs)
            }
        )
    
    def locate_search_block_with_method_context(
        self,
        source_content: str,
        method_signature: str,
        search_text: str
    ) -> MatchResult:
        """Locate search block within method context.
        
        This is the primary strategy: locate the method first using tree-sitter,
        then search for the SEARCH block within that method's scope.
        
        Args:
            source_content: Complete source file content.
            method_signature: Method signature to locate.
            search_text: SEARCH block text to find.
            
        Returns:
            MatchResult indicating match quality and locations.
        """
        # Step 1: Locate method using tree-sitter
        method_node = self._locate_method_with_treesitter(
            source_content=source_content,
            method_signature=method_signature
        )
        
        if not method_node:
            return MatchResult(
                quality=MatchQuality.METHOD_NOT_FOUND,
                found=False,
                metadata={
                    'method_signature': method_signature,
                    'error': 'Method not found in source file'
                }
            )
        
        # Step 2: Search within method body
        method_text = method_node['text']
        method_start_line = method_node['start_line']
        
        # Normalize newlines only
        normalized_search = self._normalize_newlines(search_text)
        normalized_method = self._normalize_newlines(method_text)
        
        # Step 3: Find exact matches
        matches = self._find_exact_matches(
            search_text=normalized_search,
            target_text=normalized_method,
            base_line=method_start_line
        )
        
        # Step 4: Return result based on match count
        if len(matches) == 0:
            return MatchResult(
                quality=MatchQuality.NOT_FOUND,
                found=False,
                metadata={
                    'method_signature': method_signature,
                    'method_range': (method_start_line, method_node['end_line']),
                    'search_text_preview': search_text[:200]
                }
            )
        elif len(matches) == 1:
            return MatchResult(
                quality=MatchQuality.EXACT_UNIQUE,
                found=True,
                matches=matches,
                metadata={
                    'method_signature': method_signature,
                    'method_range': (method_start_line, method_node['end_line'])
                }
            )
        else:
            return MatchResult(
                quality=MatchQuality.EXACT_AMBIGUOUS,
                found=True,
                matches=matches,
                metadata={
                    'method_signature': method_signature,
                    'method_range': (method_start_line, method_node['end_line']),
                    'match_count': len(matches)
                }
            )
    
    def locate_search_block_in_file(
        self,
        source_content: str,
        search_text: str
    ) -> MatchResult:
        """Locate search block in entire file (fallback strategy).
        
        This is a fallback when method-scoped search fails. Searches the
        entire file for the SEARCH block.
        
        Args:
            source_content: Complete source file content.
            search_text: SEARCH block text to find.
            
        Returns:
            MatchResult indicating match quality and locations.
        """
        logger.debug("Using file-scoped search (fallback strategy)")
        
        # Normalize newlines
        normalized_search = self._normalize_newlines(search_text)
        normalized_content = self._normalize_newlines(source_content)
        
        # Find exact matches in entire file
        matches = self._find_exact_matches(
            search_text=normalized_search,
            target_text=normalized_content,
            base_line=1  # File starts at line 1
        )
        
        if len(matches) == 0:
            return MatchResult(
                quality=MatchQuality.NOT_FOUND,
                found=False,
                metadata={
                    'strategy': 'file_scoped',
                    'search_text_preview': search_text[:200]
                }
            )
        elif len(matches) == 1:
            return MatchResult(
                quality=MatchQuality.EXACT_UNIQUE,
                found=True,
                matches=matches,
                metadata={
                    'strategy': 'file_scoped'
                }
            )
        else:
            return MatchResult(
                quality=MatchQuality.EXACT_AMBIGUOUS,
                found=True,
                matches=matches,
                metadata={
                    'strategy': 'file_scoped',
                    'match_count': len(matches)
                }
            )

    
    def _generate_diff_for_search_replace(
        self,
        sr: SearchReplace,
        source_file: Path,
        source_content: str,
        match_start_line: int,
        match_end_line: int,
        bug_slug: str = None
    ) -> str:
        """Generate unified diff for a SEARCH/REPLACE block.
        
        Args:
            sr: SearchReplace object.
            source_file: Path to source file.
            source_content: Source file content.
            match_start_line: Start line of match (1-based).
            match_end_line: End line of match (1-based).
            bug_slug: Bug identifier for project-specific handling.
            
        Returns:
            Unified diff string.
        """
        # Get the actual matched lines from source
        source_lines = source_content.split('\n')
        matched_lines = source_lines[match_start_line - 1:match_end_line]
        
        # Split REPLACE block into lines
        replace_lines = sr.replace_block.split('\n')
        
        # Generate unified diff using actual matched content
        diff = self.generate_unified_diff(
            original_lines=matched_lines,
            modified_lines=replace_lines,
            filepath=str(source_file),
            start_line=match_start_line,
            context_lines=self.context_lines,
            bug_slug=bug_slug
        )
        
        return diff
    
    def _merge_multiple_changes(
        self,
        all_changes: List[Dict[str, Any]],
        source_file: Path,
        source_content: str,
        bug_slug: str
    ) -> str:
        """Merge multiple changes into a single unified patch.
        
        When there are multiple SEARCH/REPLACE blocks for the same file,
        we need to apply all changes and generate a single unified diff.
        
        Args:
            all_changes: List of change dictionaries with start_line, end_line, replace_lines.
            source_file: Path to source file.
            source_content: Original source file content.
            bug_slug: Bug identifier for project-specific handling.
            
        Returns:
            Merged unified diff string.
        """
        logger.debug(
            f"Merging {len(all_changes)} changes into a single unified patch"
        )
        
        # Sort changes by start line
        sorted_changes = sorted(all_changes, key=lambda x: x['start_line'])
        
        # Apply all changes to create the modified content
        source_lines = source_content.split('\n')
        modified_lines = source_lines.copy()
        
        # Apply changes in reverse order to maintain line numbers
        for change in reversed(sorted_changes):
            start_idx = change['start_line'] - 1
            end_idx = change['end_line']
            
            # Replace the lines
            modified_lines[start_idx:end_idx] = change['replace_lines']
            
            logger.debug(
                f"Applied change at lines {change['start_line']}-{change['end_line']}: "
                f"{end_idx - start_idx} -> {len(change['replace_lines'])} lines"
            )
        
        # Generate a single unified diff for the entire file
        relative_path = self._extract_relative_path(source_file, bug_slug)
        
        # Use difflib to generate the unified diff
        diff_lines = list(difflib.unified_diff(
            [line + '\n' for line in source_lines],
            [line + '\n' for line in modified_lines],
            fromfile=f'a/{relative_path}',
            tofile=f'b/{relative_path}',
            n=self.context_lines,
            lineterm=''
        ))
        
        if not diff_lines:
            logger.warning("Generated diff is empty")
            return ''
        
        # Strip newlines and join
        diff_lines_stripped = [line.rstrip('\n') for line in diff_lines]
        merged_diff = '\n'.join(diff_lines_stripped) + '\n'
        
        logger.debug(
            f"Merged diff generated: {len(merged_diff)} chars, "
            f"1 unified patch"
        )
        
        return merged_diff
    
    def generate_unified_diff(
        self,
        original_lines: List[str],
        modified_lines: List[str],
        filepath: str,
        start_line: int,
        context_lines: int = 3,
        bug_slug: str = None
    ) -> str:
        """Generate precise unified diff.
        
        Args:
            original_lines: Original code lines (SEARCH block).
            modified_lines: Modified code lines (REPLACE block).
            filepath: File path (can be absolute or relative).
            start_line: Start line of SEARCH block in source (1-based).
            context_lines: Number of context lines.
            bug_slug: Bug identifier for project-specific handling.
            
        Returns:
            Unified diff format string.
        """
        # Read source file with universal newlines to handle CRLF
        with open(filepath, 'r', encoding='utf-8', newline='') as f:
            content = f.read()
        
        # Normalize to LF for processing
        content_normalized = content.replace('\r\n', '\n').replace('\r', '\n')
        all_lines = content_normalized.splitlines(keepends=True)
        
        # Extract relative path for diff header
        relative_path = self._extract_relative_path(Path(filepath), bug_slug)
        
        # Convert to 0-based index
        start_idx = start_line - 1
        end_idx = start_idx + len(original_lines)
        
        # Get context before
        context_before_start = max(0, start_idx - context_lines)
        context_before = all_lines[context_before_start:start_idx]
        
        # Get context after
        context_after_end = min(len(all_lines), end_idx + context_lines)
        context_after = all_lines[end_idx:context_after_end]
        
        # Build complete before/after with context
        # Note: context lines from file already have newlines
        # But original/modified lines from SEARCH/REPLACE may not
        original_with_newlines = [
            line if line.endswith('\n') else line + '\n'
            for line in original_lines
        ]
        modified_with_newlines = [
            line if line.endswith('\n') else line + '\n'
            for line in modified_lines
        ]
        
        before_lines = context_before + original_with_newlines + context_after
        after_lines = context_before + modified_with_newlines + context_after
        
        # Generate diff using difflib
        # Use lineterm='' to avoid double newlines
        diff_lines = list(difflib.unified_diff(
            before_lines,
            after_lines,
            fromfile=f'a/{relative_path}',
            tofile=f'b/{relative_path}',
            fromfiledate='',
            tofiledate='',
            n=context_lines,
            lineterm=''
        ))
        
        # Adjust line numbers in hunk header
        if len(diff_lines) >= 3:
            # Third line is the @@ hunk header
            hunk_header = diff_lines[2]
            # Calculate actual start line (1-based)
            actual_start = context_before_start + 1
            diff_lines[2] = self._adjust_hunk_header(hunk_header, actual_start)
        
        # difflib preserves newlines from input lines when lineterm=''
        # So we need to strip them before joining
        diff_lines_stripped = [line.rstrip('\n') for line in diff_lines]
        return '\n'.join(diff_lines_stripped) + '\n' if diff_lines_stripped else ''
    
    def _adjust_hunk_header(self, header: str, actual_start: int) -> str:
        """Adjust line numbers in hunk header.
        
        Args:
            header: Original hunk header (e.g., "@@ -1,10 +1,10 @@").
            actual_start: Actual start line number (1-based).
            
        Returns:
            Adjusted hunk header with correct line numbers.
        """
        # Parse original header
        match = re.match(r'@@ -(\d+),(\d+) \+(\d+),(\d+) @@', header)
        
        if not match:
            # Try single-line format: @@ -1 +1 @@
            match = re.match(r'@@ -(\d+) \+(\d+) @@', header)
            if match:
                return f'@@ -{actual_start} +{actual_start} @@'
            # Return original if can't parse
            return header
        
        old_count = match.group(2)
        new_count = match.group(4)
        
        # Generate new header with actual line numbers
        return f'@@ -{actual_start},{old_count} +{actual_start},{new_count} @@'
    
    def _generate_diff_for_rewrite(
        self,
        rewrite: RewritePatch,
        source_file: Path,
        source_content: str,
        method_node: Dict[str, Any],
        bug_slug: str = None
    ) -> str:
        """Generate unified diff for a method rewrite.
        
        Args:
            rewrite: RewritePatch object.
            source_file: Path to source file.
            source_content: Source file content.
            method_node: Method node from tree-sitter.
            bug_slug: Bug identifier for project-specific handling.
            
        Returns:
            Unified diff string.
        """
        # Extract original method lines
        start_line = method_node['start_line']
        end_line = method_node['end_line']
        
        # Get original method text and split into lines
        original_method_text = method_node['text']
        original_lines = original_method_text.split('\n')
        
        # Get new method code and split into lines
        new_method_lines = rewrite.full_code.split('\n')
        
        # Fix indentation mismatch between original and rewrite code
        # This is critical for patch application to succeed
        new_method_lines = self._adjust_indentation(
            original_lines=original_lines,
            new_lines=new_method_lines
        )
        
        # Generate unified diff
        diff = self.generate_unified_diff(
            original_lines=original_lines,
            modified_lines=new_method_lines,
            filepath=str(source_file),
            start_line=start_line,
            context_lines=self.context_lines,
            bug_slug=bug_slug
        )
        
        return diff
    
    def _adjust_indentation(
        self,
        original_lines: List[str],
        new_lines: List[str]
    ) -> List[str]:
        """Adjust indentation of new_lines to match original_lines.
        
        This fixes a critical issue where model-generated rewrite code
        may have different (often missing) indentation compared to the
        original method in the source file. Without this adjustment,
        patch application fails with "can't find file to patch" errors.
        
        Algorithm:
        1. Detect base indentation from original method's first line
        2. Detect base indentation from new code's first line
        3. Adjust all new lines by the indentation difference
        
        Args:
            original_lines: Lines from the original source method.
            new_lines: Lines from the model-generated rewrite code.
            
        Returns:
            Adjusted new_lines with correct indentation.
        """
        if not original_lines or not new_lines:
            return new_lines
        
        # Find the base indentation from original method
        # Look for the first non-empty line
        original_indent = 0
        for line in original_lines:
            if line.strip():  # Skip empty lines
                # Count leading spaces
                original_indent = len(line) - len(line.lstrip(' '))
                break
        
        # Find the base indentation from new code
        new_indent = 0
        for line in new_lines:
            if line.strip():  # Skip empty lines
                new_indent = len(line) - len(line.lstrip(' '))
                break
        
        # Calculate the indentation difference
        indent_diff = original_indent - new_indent
        
        if indent_diff == 0:
            # No adjustment needed
            return new_lines
        
        # Adjust indentation for all lines
        adjusted_lines = []
        for line in new_lines:
            if not line.strip():
                # Keep empty lines as-is
                adjusted_lines.append(line)
            else:
                if indent_diff > 0:
                    # Add indentation
                    adjusted_lines.append(' ' * indent_diff + line)
                else:
                    # Remove indentation (be careful not to remove too much)
                    spaces_to_remove = -indent_diff
                    if line.startswith(' ' * spaces_to_remove):
                        adjusted_lines.append(line[spaces_to_remove:])
                    else:
                        # Can't remove that many spaces, keep as-is
                        adjusted_lines.append(line)
        
        logger.debug(
            f"Adjusted indentation: original={original_indent} spaces, "
            f"new={new_indent} spaces, diff={indent_diff}"
        )
        
        return adjusted_lines
    
    def _locate_method_with_treesitter(
        self,
        source_content: str,
        method_signature: str
    ) -> Optional[Dict[str, Any]]:
        """Locate method using tree-sitter AST parsing.
        
        Args:
            source_content: Java source code.
            method_signature: Method signature to find.
            
        Returns:
            Dict with method location info, or None if not found.
            Contains: start_line, end_line, start_byte, end_byte, text, node
        """
        try:
            # Parse source code
            tree = self.java_parser.parse(bytes(source_content, 'utf8'))
            root_node = tree.root_node
            
            # Extract method name from signature
            method_name = self._extract_method_name(method_signature)
            
            if not method_name:
                logger.warning(
                    f"Could not extract method name from: {method_signature}"
                )
                return None
            
            logger.debug(f"Searching for method: {method_name}")
            
            # Search for method in AST with full signature for disambiguation
            method_node = self._find_method_in_ast(
                root_node,
                method_name,
                source_content,
                method_signature=method_signature
            )
            
            if method_node:
                logger.debug(
                    f"Found method {method_name} at lines "
                    f"{method_node['start_line']}-{method_node['end_line']}"
                )
            else:
                logger.debug(f"Method {method_name} not found in AST")
            
            return method_node
            
        except Exception as e:
            logger.error(f"Error parsing Java code with tree-sitter: {e}")
            return None
    
    def _find_method_in_ast(
        self,
        node: Any,
        method_name: str,
        source_content: str,
        method_signature: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Recursively search AST for method or constructor declaration.
        
        Args:
            node: Current AST node.
            method_name: Method name to find.
            source_content: Source code content.
            method_signature: Full method signature for disambiguation (optional).
            
        Returns:
            Dict with method info, or None if not found.
        """
        # Check if current node is a method or constructor declaration
        if node.type in ['method_declaration', 'constructor_declaration']:
            # Look for identifier child node (method/constructor name)
            for child in node.children:
                if child.type == 'identifier':
                    node_method_name = child.text.decode('utf8')
                    if node_method_name == method_name:
                        # Found matching method name
                        # If signature provided, verify parameters match
                        if method_signature:
                            node_signature = self._extract_signature_from_node(
                                node, source_content
                            )
                            if not self._signatures_match(
                                method_signature, node_signature
                            ):
                                # Name matches but signature doesn't (overloaded method)
                                break
                        
                        # Found matching method/constructor
                        start_point = node.start_point
                        end_point = node.end_point
                        start_byte = node.start_byte
                        end_byte = node.end_byte
                        
                        return {
                            'start_line': start_point[0] + 1,  # Convert to 1-based
                            'end_line': end_point[0] + 1,
                            'start_byte': start_byte,
                            'end_byte': end_byte,
                            'text': source_content[start_byte:end_byte],
                            'node': node
                        }
        
        # Recursively search children
        for child in node.children:
            result = self._find_method_in_ast(
                child, method_name, source_content, method_signature
            )
            if result:
                return result
        
        return None
    
    def _extract_method_name(self, method_signature: str) -> str:
        """Extract method name from method signature.
        
        Examples:
            "public LegendItemCollection getLegendItems()" -> "getLegendItems"
            "private void calculate(int x, int y)" -> "calculate"
            "static <T> List<T> sort(List<T> items)" -> "sort"
        
        Args:
            method_signature: Full method signature.
            
        Returns:
            Method name, or empty string if extraction fails.
        """
        # Match method name (identifier before opening parenthesis)
        # This handles generics, return types, modifiers, etc.
        match = re.search(r'\b(\w+)\s*\(', method_signature)
        
        if match:
            return match.group(1)
        
        # Fallback: try to get last word before any special characters
        # Remove generics first
        cleaned = re.sub(r'<[^>]+>', '', method_signature)
        words = cleaned.split()
        
        if words:
            # Get last word that looks like an identifier
            for word in reversed(words):
                if re.match(r'^\w+$', word):
                    return word
        
        logger.warning(
            f"Could not extract method name from signature: {method_signature}"
        )
        return ""
    
    def _extract_signature_from_node(
        self,
        node: Any,
        source_content: str
    ) -> str:
        """Extract method signature from AST node.
        
        Args:
            node: Method or constructor declaration node.
            source_content: Source code content.
            
        Returns:
            Method signature string (e.g., "equal(GeneralPath, GeneralPath)").
        """
        # Get method name
        method_name = ""
        for child in node.children:
            if child.type == 'identifier':
                method_name = child.text.decode('utf8')
                break
        
        # Get formal parameters
        params = []
        for child in node.children:
            if child.type == 'formal_parameters':
                # Extract parameter types
                params = self._extract_parameter_types(child, source_content)
                break
        
        # Build signature
        return f"{method_name}({', '.join(params)})"
    
    def _extract_parameter_types(
        self,
        formal_params_node: Any,
        source_content: str
    ) -> List[str]:
        """Extract parameter types from formal_parameters node.
        
        Args:
            formal_params_node: formal_parameters AST node.
            source_content: Source code content.
            
        Returns:
            List of parameter type names.
        """
        param_types = []
        
        for child in formal_params_node.children:
            if child.type == 'formal_parameter':
                # Find the type node - it could be nested in modifiers
                type_found = False
                for param_child in child.children:
                    # Skip modifiers like 'final'
                    if param_child.type == 'modifiers':
                        continue
                    
                    # Check for type nodes
                    if param_child.type in ['type_identifier', 'integral_type',
                                            'floating_point_type', 'boolean_type',
                                            'generic_type', 'array_type', 'void_type']:
                        # Get the type text
                        type_text = param_child.text.decode('utf8')
                        # Simplify type (remove package names)
                        simple_type = type_text.split('.')[-1]
                        param_types.append(simple_type)
                        type_found = True
                        break
                
                # If no direct type found, try to extract from text
                if not type_found:
                    param_text = child.text.decode('utf8')
                    # Remove 'final' and other modifiers
                    param_text = re.sub(r'\b(final|static|volatile)\s+', '', param_text)
                    # Extract type (first word before variable name)
                    match = re.match(r'([\w<>\[\]\.]+)\s+\w+', param_text)
                    if match:
                        type_text = match.group(1)
                        simple_type = type_text.split('.')[-1]
                        param_types.append(simple_type)
        
        return param_types
    
    def _signatures_match(
        self,
        signature1: str,
        signature2: str
    ) -> bool:
        """Check if two method signatures match.
        
        Compares method names and parameter types, ignoring modifiers,
        return types, and parameter names.
        
        Args:
            signature1: First signature (from model output).
            signature2: Second signature (from AST).
            
        Returns:
            True if signatures match, False otherwise.
        """
        # Normalize signatures by removing 'final' and extra whitespace
        sig1_normalized = re.sub(r'\bfinal\s+', '', signature1)
        sig2_normalized = re.sub(r'\bfinal\s+', '', signature2)
        
        # Extract method name and parameters from both signatures
        # signature1 format: "public static boolean equal(GeneralPath p1, GeneralPath p2)"
        # signature2 format: "equal(GeneralPath, GeneralPath)"
        
        # Extract from signature1
        match1 = re.search(r'\b(\w+)\s*\((.*?)\)', sig1_normalized)
        if not match1:
            return False
        
        name1 = match1.group(1)
        params1_str = match1.group(2).strip()
        
        # Extract from signature2
        match2 = re.search(r'\b(\w+)\s*\((.*?)\)', sig2_normalized)
        if not match2:
            return False
        
        name2 = match2.group(1)
        params2_str = match2.group(2).strip()
        
        # Check method names match
        if name1 != name2:
            return False
        
        # Parse parameter types from signature1
        # Format: "Type1 name1, Type2 name2" -> ["Type1", "Type2"]
        params1 = []
        if params1_str:
            for param in params1_str.split(','):
                param = param.strip()
                if param:
                    # Get type (first word, handling generics)
                    # Remove generics for comparison
                    param_no_generics = re.sub(r'<[^>]+>', '', param)
                    parts = param_no_generics.split()
                    if parts:
                        # Get simple type name (without package)
                        type_name = parts[0].split('.')[-1]
                        params1.append(type_name)
        
        # Parse parameter types from signature2
        # Format: "Type1, Type2" -> ["Type1", "Type2"]
        params2 = []
        if params2_str:
            for param in params2_str.split(','):
                param = param.strip()
                if param:
                    # Remove generics for comparison
                    param_no_generics = re.sub(r'<[^>]+>', '', param)
                    # Get simple type name (without package)
                    type_name = param_no_generics.split('.')[-1]
                    params2.append(type_name)
        
        # Check parameter counts match
        if len(params1) != len(params2):
            return False
        
        # Check each parameter type matches
        for p1, p2 in zip(params1, params2):
            if p1 != p2:
                return False
        
        return True
    
    def _normalize_newlines(self, text: str) -> str:
        """Normalize newlines only, preserve all other whitespace.
        
        This is the only normalization operation to ensure strict matching.
        
        Args:
            text: Text to normalize.
            
        Returns:
            Text with normalized newlines.
        """
        # Unify all newline types to \n
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        return text
    
    def _normalize_indentation(self, text: str) -> str:
        """Normalize indentation to allow flexible matching.
        
        Strips all leading whitespace and preserves only the code content,
        allowing matching regardless of indentation differences.
        
        Args:
            text: Text to normalize.
            
        Returns:
            Text with all leading whitespace removed from each line.
        """
        lines = text.split('\n')
        normalized_lines = []
        
        for line in lines:
            # Strip leading whitespace, keep the code
            stripped = line.lstrip()
            normalized_lines.append(stripped)
        
        return '\n'.join(normalized_lines)
    
    def _find_exact_matches(
        self,
        search_text: str,
        target_text: str,
        base_line: int
    ) -> List[Dict[str, Any]]:
        """Find all exact matches of search text in target text.
        
        Uses a sliding window approach with flexible indentation matching
        and structural tolerance (ignores standalone braces) to find all
        locations where the search text appears in the target.
        
        Args:
            search_text: Text to search for (already normalized).
            target_text: Text to search in (already normalized).
            base_line: Base line number for target text (1-based).
            
        Returns:
            List of match dictionaries with start_line, end_line, matched_text.
        """
        matches = []
        
        search_lines = search_text.split('\n')
        target_lines = target_text.split('\n')
        
        search_line_count = len(search_lines)
        target_line_count = len(target_lines)
        
        # Normalize indentation for flexible matching
        search_normalized = self._normalize_indentation(search_text)
        search_lines_norm = search_normalized.split('\n')
        
        # Filter out empty lines and standalone braces from search
        search_lines_filtered = [
            line for line in search_lines_norm
            if line.strip() and line.strip() not in ['{', '}']
        ]
        
        # Sliding window to find matches
        # We need a larger window to account for extra braces in target
        max_window_size = search_line_count + 10
        
        for i in range(target_line_count):
            # Try to match search lines starting from position i
            window_end = min(i + max_window_size, target_line_count)
            window = target_lines[i:window_end]
            window_text = '\n'.join(window)
            window_normalized = self._normalize_indentation(window_text)
            window_lines_norm = window_normalized.split('\n')
            
            # Filter out empty lines and standalone braces from window
            window_lines_filtered = [
                line for line in window_lines_norm
                if line.strip() and line.strip() not in ['{', '}']
            ]
            
            # Check if we can match all search lines within this window
            if len(window_lines_filtered) >= len(search_lines_filtered):
                # Try to match search lines against window lines
                match_found, actual_end_idx = self._fuzzy_match_lines(
                    search_lines_filtered,
                    window_lines_norm,
                    search_lines_norm
                )
                
                if match_found:
                    # Calculate actual end line in original target
                    actual_end_line = i + actual_end_idx
                    
                    matches.append({
                        'start_line': base_line + i,
                        'end_line': base_line + actual_end_line,
                        'matched_text': '\n'.join(target_lines[i:actual_end_line + 1]),
                        'window_index': i
                    })
                    
                    logger.debug(
                        f"Found match at lines {base_line + i} to "
                        f"{base_line + actual_end_line}"
                    )
        
        return matches
    
    def _fuzzy_match_lines(
        self,
        search_lines_filtered: List[str],
        window_lines_norm: List[str],
        search_lines_norm: List[str]
    ) -> Tuple[bool, int]:
        """Try to match search lines against window lines with tolerance.
        
        Matches all non-brace, non-empty lines from search against window,
        allowing for extra braces and empty lines in the window.
        
        Args:
            search_lines_filtered: Search lines without braces/empty lines.
            window_lines_norm: Normalized window lines (may include braces).
            search_lines_norm: Original normalized search lines.
            
        Returns:
            Tuple of (match_found, end_index_in_window).
        """
        if not search_lines_filtered:
            return False, 0
        
        search_idx = 0
        window_idx = 0
        last_matched_idx = 0
        
        while search_idx < len(search_lines_filtered) and window_idx < len(window_lines_norm):
            window_line = window_lines_norm[window_idx]
            search_line = search_lines_filtered[search_idx]
            
            # Skip empty lines and standalone braces in window
            if not window_line.strip() or window_line.strip() in ['{', '}']:
                window_idx += 1
                continue
            
            # Check if lines match
            if window_line == search_line:
                search_idx += 1
                last_matched_idx = window_idx
                window_idx += 1
            else:
                # No match
                return False, 0
        
        # Check if we matched all search lines
        if search_idx == len(search_lines_filtered):
            return True, last_matched_idx
        
        return False, 0
    
    def _exact_match(self, lines1: List[str], lines2: List[str]) -> bool:
        """Check if two line lists match exactly.
        
        Args:
            lines1: First list of lines.
            lines2: Second list of lines.
            
        Returns:
            True if lists match exactly, False otherwise.
        """
        if len(lines1) != len(lines2):
            return False
        
        for l1, l2 in zip(lines1, lines2):
            if l1 != l2:
                return False
        
        return True
    
    def _generate_failure_report(
        self,
        parsed_patch: ParsedPatch,
        source_file: Path,
        last_match_result: Optional[MatchResult]
    ) -> Optional[Path]:
        """Generate detailed failure report for manual review.
        
        Args:
            parsed_patch: ParsedPatch that failed to normalize.
            source_file: Source file path.
            last_match_result: Last MatchResult from failed strategies.
            
        Returns:
            Path to generated failure report, or None if reporter not configured.
        """
        if not self.reporter:
            logger.warning(
                "No reporter configured, skipping failure report generation"
            )
            return None
        
        # Generate report content
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("PATCH NORMALIZATION FAILURE REPORT")
        report_lines.append("=" * 80)
        report_lines.append("")
        report_lines.append(f"Bug: {parsed_patch.bug_slug}")
        report_lines.append(f"Attempt: {parsed_patch.attempt_num}")
        report_lines.append(f"Modeling Type: {parsed_patch.modeling_type}")
        report_lines.append(f"Source File: {source_file}")
        report_lines.append("")
        
        if last_match_result:
            report_lines.append(f"Last Match Quality: {last_match_result.quality.value}")
            report_lines.append(f"Matches Found: {last_match_result.match_count}")
            report_lines.append("")
            
            if last_match_result.quality == MatchQuality.EXACT_AMBIGUOUS:
                report_lines.append("ISSUE: Multiple exact matches found")
                report_lines.append("")
                report_lines.append("Match Locations:")
                for i, match in enumerate(last_match_result.matches, 1):
                    report_lines.append(
                        f"  {i}. Lines {match['start_line']}-{match['end_line']}"
                    )
                report_lines.append("")
                report_lines.append("ACTION REQUIRED:")
                report_lines.append("  - Review all match locations")
                report_lines.append("  - Manually select the correct location")
                report_lines.append("  - Update the patch with specific line numbers")
                
            elif last_match_result.quality == MatchQuality.NOT_FOUND:
                report_lines.append("ISSUE: Search block not found in source")
                report_lines.append("")
                report_lines.append("Possible reasons:")
                report_lines.append("  - Code has been modified since patch generation")
                report_lines.append("  - Whitespace differences")
                report_lines.append("  - Search block is incorrect")
                report_lines.append("")
                report_lines.append("ACTION REQUIRED:")
                report_lines.append("  - Verify source file is correct version")
                report_lines.append("  - Check for whitespace differences")
                report_lines.append("  - Manually locate the code to be changed")
                
            elif last_match_result.quality == MatchQuality.METHOD_NOT_FOUND:
                report_lines.append("ISSUE: Method not found in source")
                report_lines.append("")
                method_sig = last_match_result.metadata.get('method_signature', 'N/A')
                report_lines.append(f"Method Signature: {method_sig}")
                report_lines.append("")
                report_lines.append("Possible reasons:")
                report_lines.append("  - Method name is incorrect")
                report_lines.append("  - Method signature doesn't match")
                report_lines.append("  - Method is in a different class")
                report_lines.append("")
                report_lines.append("ACTION REQUIRED:")
                report_lines.append("  - Verify method name and signature")
                report_lines.append("  - Check if method exists in source file")
                report_lines.append("  - Update method signature if needed")
        
        report_lines.append("")
        report_lines.append("=" * 80)
        report_lines.append("SEARCH BLOCKS")
        report_lines.append("=" * 80)
        report_lines.append("")
        
        if parsed_patch.modeling_type == 'edit':
            for i, sr in enumerate(parsed_patch.search_replaces, 1):
                report_lines.append(f"Block {i}:")
                report_lines.append(f"  Method: {sr.method_signature}")
                report_lines.append(f"  Search Block:")
                for line in sr.search_block.split('\n'):
                    report_lines.append(f"    {line}")
                report_lines.append("")
        
        report_content = '\n'.join(report_lines)
        
        # Save report using reporter
        try:
            report_path = self.reporter.save_failure_report(
                bug_slug=parsed_patch.bug_slug,
                attempt_num=parsed_patch.attempt_num,
                content=report_content
            )
            logger.info(f"Failure report saved to: {report_path}")
            return report_path
        except Exception as e:
            logger.error(f"Failed to save failure report: {e}")
            return None

    
    # ========================================================================
    # Validation Methods
    # ========================================================================
    
    def validate_normalized_patch(
        self,
        patch: NormalizedPatch
    ) -> Tuple[bool, Optional[str]]:
        """Validate a normalized patch.
        
        Checks that the patch is well-formed and can potentially be applied.
        
        Args:
            patch: NormalizedPatch to validate.
            
        Returns:
            Tuple of (is_valid, error_message).
        """
        # Check that patch has content
        if not patch.is_valid:
            return False, "Patch has no diff content"
        
        # Check diff format
        is_valid_format, format_error = self._is_valid_diff_format(
            patch.diff_content
        )
        if not is_valid_format:
            return False, f"Invalid diff format: {format_error}"
        
        # Check line numbers
        is_valid_lines, lines_error = self._validate_line_numbers(
            patch.diff_content
        )
        if not is_valid_lines:
            return False, f"Invalid line numbers: {lines_error}"
        
        # Check context
        is_valid_context, context_error = self._validate_context(
            patch.diff_content
        )
        if not is_valid_context:
            return False, f"Invalid context: {context_error}"
        
        return True, None
    
    def _is_valid_diff_format(self, diff_content: str) -> Tuple[bool, Optional[str]]:
        """Check if diff content is in valid unified diff format.
        
        Args:
            diff_content: Diff content to validate.
            
        Returns:
            Tuple of (is_valid, error_message).
        """
        if not diff_content or not diff_content.strip():
            return False, "Empty diff content"
        
        lines = diff_content.split('\n')
        
        # Check for required headers
        has_from_file = any(line.startswith('---') for line in lines)
        has_to_file = any(line.startswith('+++') for line in lines)
        has_hunk_header = any(line.startswith('@@') for line in lines)
        
        if not has_from_file:
            return False, "Missing '---' header"
        
        if not has_to_file:
            return False, "Missing '+++' header"
        
        if not has_hunk_header:
            return False, "Missing '@@ hunk header"
        
        # Check that headers are in correct order
        from_idx = next(i for i, line in enumerate(lines) if line.startswith('---'))
        to_idx = next(i for i, line in enumerate(lines) if line.startswith('+++'))
        hunk_idx = next(i for i, line in enumerate(lines) if line.startswith('@@'))
        
        if not (from_idx < to_idx < hunk_idx):
            return False, "Headers in wrong order"
        
        return True, None
    
    def _validate_line_numbers(
        self,
        diff_content: str
    ) -> Tuple[bool, Optional[str]]:
        """Validate line numbers in hunk headers.
        
        Args:
            diff_content: Diff content to validate.
            
        Returns:
            Tuple of (is_valid, error_message).
        """
        lines = diff_content.split('\n')
        
        for line in lines:
            if line.startswith('@@'):
                # Parse hunk header
                match = re.match(r'@@ -(\d+),(\d+) \+(\d+),(\d+) @@', line)
                if not match:
                    # Try single-line format
                    match = re.match(r'@@ -(\d+) \+(\d+) @@', line)
                    if not match:
                        return False, f"Invalid hunk header format: {line}"
                
                # Extract line numbers
                if len(match.groups()) == 4:
                    old_start = int(match.group(1))
                    old_count = int(match.group(2))
                    new_start = int(match.group(3))
                    new_count = int(match.group(4))
                else:
                    old_start = int(match.group(1))
                    new_start = int(match.group(2))
                    old_count = 1
                    new_count = 1
                
                # Validate line numbers are positive
                if old_start < 1 or new_start < 1:
                    return False, f"Line numbers must be >= 1: {line}"
                
                if old_count < 0 or new_count < 0:
                    return False, f"Line counts must be >= 0: {line}"
        
        return True, None
    
    def _validate_context(
        self,
        diff_content: str
    ) -> Tuple[bool, Optional[str]]:
        """Validate context lines in diff.
        
        Args:
            diff_content: Diff content to validate.
            
        Returns:
            Tuple of (is_valid, error_message).
        """
        lines = diff_content.split('\n')
        
        in_hunk = False
        for line in lines:
            if line.startswith('@@'):
                in_hunk = True
                continue
            
            if in_hunk:
                # Check that hunk lines start with valid prefix
                if line and not line[0] in [' ', '-', '+', '\\']:
                    return False, f"Invalid hunk line prefix: {line[:50]}"
        
        return True, None

    
    def dry_run_apply(
        self,
        patch: NormalizedPatch,
        source_file: Path
    ) -> Tuple[bool, Optional[str]]:
        """Test if patch can be applied without actually applying it.
        
        Uses git apply --check to validate the patch.
        
        Args:
            patch: NormalizedPatch to test.
            source_file: Source file to apply patch to.
            
        Returns:
            Tuple of (can_apply, error_message).
        """
        import subprocess
        import tempfile
        import shutil
        
        if not source_file.exists():
            return False, f"Source file not found: {source_file}"
        
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Copy source file to temp directory
            temp_file = temp_path / source_file.name
            shutil.copy2(source_file, temp_file)
            
            # Write patch to temp file
            patch_file = temp_path / 'patch.diff'
            with open(patch_file, 'w', encoding='utf-8') as f:
                f.write(patch.diff_content)
            
            # Try to apply patch with --check flag
            try:
                result = subprocess.run(
                    ['git', 'apply', '--check', str(patch_file)],
                    cwd=temp_path,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    logger.debug("Dry-run apply succeeded")
                    return True, None
                else:
                    error_msg = result.stderr or result.stdout
                    logger.debug(f"Dry-run apply failed: {error_msg}")
                    return False, error_msg
                    
            except subprocess.TimeoutExpired:
                return False, "git apply timed out"
            except FileNotFoundError:
                return False, "git command not found"
            except Exception as e:
                return False, f"Unexpected error: {str(e)}"
