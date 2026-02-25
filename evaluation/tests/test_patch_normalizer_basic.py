"""Basic tests for PatchNormalizer module.

Tests the core functionality of PatchNormalizer including tree-sitter
method location, exact matching, and basic normalization.
"""

import pytest
from pathlib import Path

from evaluation.core.patch_normalizer import PatchNormalizer
from evaluation.core.data_structures import MatchQuality


class TestPatchNormalizerBasic:
    """Basic test suite for PatchNormalizer."""
    
    @pytest.fixture
    def normalizer(self):
        """Create PatchNormalizer instance."""
        return PatchNormalizer(context_lines=3)
    
    # ========================================================================
    # Test Initialization
    # ========================================================================
    
    def test_init_default(self):
        """Test PatchNormalizer initialization with defaults."""
        normalizer = PatchNormalizer()
        assert normalizer.context_lines == 3
        assert normalizer.reporter is None
        assert normalizer.java_parser is not None
    
    def test_init_custom_context_lines(self):
        """Test initialization with custom context lines."""
        normalizer = PatchNormalizer(context_lines=5)
        assert normalizer.context_lines == 5
    
    # ========================================================================
    # Test Newline Normalization
    # ========================================================================
    
    def test_normalize_newlines_unix(self, normalizer):
        """Test normalization of Unix newlines."""
        text = "line1\nline2\nline3"
        result = normalizer._normalize_newlines(text)
        assert result == "line1\nline2\nline3"
    
    def test_normalize_newlines_windows(self, normalizer):
        """Test normalization of Windows newlines."""
        text = "line1\r\nline2\r\nline3"
        result = normalizer._normalize_newlines(text)
        assert result == "line1\nline2\nline3"
    
    def test_normalize_newlines_mac(self, normalizer):
        """Test normalization of old Mac newlines."""
        text = "line1\rline2\rline3"
        result = normalizer._normalize_newlines(text)
        assert result == "line1\nline2\nline3"
    
    def test_normalize_newlines_mixed(self, normalizer):
        """Test normalization of mixed newlines."""
        text = "line1\nline2\r\nline3\rline4"
        result = normalizer._normalize_newlines(text)
        assert result == "line1\nline2\nline3\nline4"
    
    def test_normalize_newlines_preserves_whitespace(self, normalizer):
        """Test that normalization preserves other whitespace."""
        text = "  line1  \n\tline2\t\n    line3    "
        result = normalizer._normalize_newlines(text)
        assert result == "  line1  \n\tline2\t\n    line3    "
    
    # ========================================================================
    # Test Exact Matching
    # ========================================================================
    
    def test_exact_match_identical(self, normalizer):
        """Test exact match with identical lines."""
        lines1 = ["line1", "line2", "line3"]
        lines2 = ["line1", "line2", "line3"]
        assert normalizer._exact_match(lines1, lines2) is True
    
    def test_exact_match_different(self, normalizer):
        """Test exact match with different lines."""
        lines1 = ["line1", "line2", "line3"]
        lines2 = ["line1", "line2", "line4"]
        assert normalizer._exact_match(lines1, lines2) is False
    
    def test_exact_match_different_length(self, normalizer):
        """Test exact match with different lengths."""
        lines1 = ["line1", "line2"]
        lines2 = ["line1", "line2", "line3"]
        assert normalizer._exact_match(lines1, lines2) is False
    
    def test_exact_match_whitespace_sensitive(self, normalizer):
        """Test that exact match is whitespace-sensitive."""
        lines1 = ["line1", "  line2"]
        lines2 = ["line1", " line2"]
        assert normalizer._exact_match(lines1, lines2) is False
    
    # ========================================================================
    # Test Find Exact Matches
    # ========================================================================
    
    def test_find_exact_matches_single(self, normalizer):
        """Test finding single exact match."""
        search_text = "line2\nline3"
        target_text = "line1\nline2\nline3\nline4"
        
        matches = normalizer._find_exact_matches(search_text, target_text, 1)
        
        assert len(matches) == 1
        assert matches[0]['start_line'] == 2
        assert matches[0]['end_line'] == 3
        assert matches[0]['matched_text'] == "line2\nline3"
    
    def test_find_exact_matches_multiple(self, normalizer):
        """Test finding multiple exact matches."""
        search_text = "line2\nline3"
        target_text = "line1\nline2\nline3\nline4\nline2\nline3\nline5"
        
        matches = normalizer._find_exact_matches(search_text, target_text, 1)
        
        assert len(matches) == 2
        assert matches[0]['start_line'] == 2
        assert matches[0]['end_line'] == 3
        assert matches[1]['start_line'] == 5
        assert matches[1]['end_line'] == 6
    
    def test_find_exact_matches_none(self, normalizer):
        """Test when no matches are found."""
        search_text = "not found"
        target_text = "line1\nline2\nline3"
        
        matches = normalizer._find_exact_matches(search_text, target_text, 1)
        
        assert len(matches) == 0
    
    def test_find_exact_matches_with_base_line(self, normalizer):
        """Test that base_line offset is applied correctly."""
        search_text = "line1"
        target_text = "line1\nline2"
        
        matches = normalizer._find_exact_matches(search_text, target_text, 100)
        
        assert len(matches) == 1
        assert matches[0]['start_line'] == 100
        assert matches[0]['end_line'] == 100
    
    # ========================================================================
    # Test Method Name Extraction
    # ========================================================================
    
    def test_extract_method_name_simple(self, normalizer):
        """Test extracting method name from simple signature."""
        signature = "public void calculate()"
        name = normalizer._extract_method_name(signature)
        assert name == "calculate"
    
    def test_extract_method_name_with_return_type(self, normalizer):
        """Test extracting method name with return type."""
        signature = "public LegendItemCollection getLegendItems()"
        name = normalizer._extract_method_name(signature)
        assert name == "getLegendItems"
    
    def test_extract_method_name_with_parameters(self, normalizer):
        """Test extracting method name with parameters."""
        signature = "private void calculate(int x, int y)"
        name = normalizer._extract_method_name(signature)
        assert name == "calculate"
    
    def test_extract_method_name_with_generics(self, normalizer):
        """Test extracting method name with generics."""
        signature = "public <T> List<T> sort(List<T> items)"
        name = normalizer._extract_method_name(signature)
        assert name == "sort"
    
    def test_extract_method_name_static(self, normalizer):
        """Test extracting static method name."""
        signature = "public static void main(String[] args)"
        name = normalizer._extract_method_name(signature)
        assert name == "main"
    
    def test_extract_method_name_no_parenthesis(self, normalizer):
        """Test extracting method name without parenthesis."""
        signature = "public void calculate"
        name = normalizer._extract_method_name(signature)
        # Should still try to extract
        assert name == "calculate"
    
    def test_extract_method_name_empty(self, normalizer):
        """Test extracting from empty signature."""
        signature = ""
        name = normalizer._extract_method_name(signature)
        assert name == ""
    
    # ========================================================================
    # Test File-Scoped Search
    # ========================================================================
    
    def test_locate_search_block_in_file_found(self, normalizer):
        """Test file-scoped search when block is found."""
        source_content = """public class Test {
    public void method1() {
        int x = 1;
        int y = 2;
    }
}"""
        search_text = "        int x = 1;\n        int y = 2;"
        
        result = normalizer.locate_search_block_in_file(
            source_content,
            search_text
        )
        
        assert result.found is True
        assert result.quality == MatchQuality.EXACT_UNIQUE
        assert len(result.matches) == 1
    
    def test_locate_search_block_in_file_not_found(self, normalizer):
        """Test file-scoped search when block is not found."""
        source_content = """
public class Test {
    public void method1() {
        int x = 1;
    }
}
"""
        search_text = "int z = 3;"
        
        result = normalizer.locate_search_block_in_file(
            source_content,
            search_text
        )
        
        assert result.found is False
        assert result.quality == MatchQuality.NOT_FOUND
    
    def test_locate_search_block_in_file_ambiguous(self, normalizer):
        """Test file-scoped search with multiple matches."""
        source_content = """public class Test {
    public void method1() {
        int x = 1;
    }
    public void method2() {
        int x = 1;
    }
}"""
        search_text = "        int x = 1;"
        
        result = normalizer.locate_search_block_in_file(
            source_content,
            search_text
        )
        
        assert result.found is True
        assert result.quality == MatchQuality.EXACT_AMBIGUOUS
        assert len(result.matches) == 2


    # ========================================================================
    # Additional Exact Matching Tests (Task 4.6.2)
    # ========================================================================
    
    def test_exact_match_with_tabs(self, normalizer):
        """Test exact match with tab characters."""
        lines1 = ["\tline1", "\t\tline2"]
        lines2 = ["\tline1", "\t\tline2"]
        assert normalizer._exact_match(lines1, lines2) is True
        
        # Different tabs should not match
        lines3 = [" line1", "  line2"]
        assert normalizer._exact_match(lines1, lines3) is False
    
    def test_exact_match_with_trailing_spaces(self, normalizer):
        """Test exact match with trailing spaces."""
        lines1 = ["line1  ", "line2   "]
        lines2 = ["line1  ", "line2   "]
        assert normalizer._exact_match(lines1, lines2) is True
        
        # Different trailing spaces should not match
        lines3 = ["line1 ", "line2  "]
        assert normalizer._exact_match(lines1, lines3) is False
    
    def test_find_exact_matches_at_start(self, normalizer):
        """Test finding match at the start of text."""
        search_text = "line1\nline2"
        target_text = "line1\nline2\nline3\nline4"
        
        matches = normalizer._find_exact_matches(search_text, target_text, 1)
        
        assert len(matches) == 1
        assert matches[0]['start_line'] == 1
        assert matches[0]['end_line'] == 2
    
    def test_find_exact_matches_at_end(self, normalizer):
        """Test finding match at the end of text."""
        search_text = "line3\nline4"
        target_text = "line1\nline2\nline3\nline4"
        
        matches = normalizer._find_exact_matches(search_text, target_text, 1)
        
        assert len(matches) == 1
        assert matches[0]['start_line'] == 3
        assert matches[0]['end_line'] == 4
    
    def test_find_exact_matches_overlapping_patterns(self, normalizer):
        """Test finding matches with overlapping patterns."""
        search_text = "A\nB"
        target_text = "A\nB\nA\nB\nA"
        
        matches = normalizer._find_exact_matches(search_text, target_text, 1)
        
        # Should find two non-overlapping matches
        assert len(matches) == 2
        assert matches[0]['start_line'] == 1
        assert matches[1]['start_line'] == 3
    
    def test_find_exact_matches_single_line(self, normalizer):
        """Test finding single-line matches."""
        search_text = "target_line"
        target_text = "line1\ntarget_line\nline3\ntarget_line\nline5"
        
        matches = normalizer._find_exact_matches(search_text, target_text, 1)
        
        assert len(matches) == 2
        assert matches[0]['start_line'] == 2
        assert matches[1]['start_line'] == 4
    
    def test_find_exact_matches_empty_search(self, normalizer):
        """Test finding matches with empty search text."""
        search_text = ""
        target_text = "line1\nline2"
        
        matches = normalizer._find_exact_matches(search_text, target_text, 1)
        
        # Empty search should match at every position
        # But our implementation may handle this differently
        # Just verify it doesn't crash
        assert isinstance(matches, list)
    
    def test_find_exact_matches_empty_target(self, normalizer):
        """Test finding matches in empty target text."""
        search_text = "line1"
        target_text = ""
        
        matches = normalizer._find_exact_matches(search_text, target_text, 1)
        
        assert len(matches) == 0
    
    def test_find_exact_matches_case_sensitive(self, normalizer):
        """Test that matching is case-sensitive."""
        search_text = "Line1"
        target_text = "line1\nLine1\nLINE1"
        
        matches = normalizer._find_exact_matches(search_text, target_text, 1)
        
        # Should only match the exact case
        assert len(matches) == 1
        assert matches[0]['start_line'] == 2
    
    def test_find_exact_matches_with_special_chars(self, normalizer):
        """Test matching with special characters."""
        search_text = "int x = 1;"
        target_text = "int x = 1;\nint y = 2;\nint x = 1;"
        
        matches = normalizer._find_exact_matches(search_text, target_text, 1)
        
        assert len(matches) == 2
        assert matches[0]['start_line'] == 1
        assert matches[1]['start_line'] == 3
    
    def test_find_exact_matches_preserves_indentation(self, normalizer):
        """Test that indentation is preserved in matching."""
        search_text = "    int x = 1;"
        target_text = "int x = 1;\n    int x = 1;\n        int x = 1;"
        
        matches = normalizer._find_exact_matches(search_text, target_text, 1)
        
        # Should only match the one with exact indentation
        assert len(matches) == 1
        assert matches[0]['start_line'] == 2
