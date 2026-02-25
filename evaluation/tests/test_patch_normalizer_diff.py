"""Tests for PatchNormalizer diff generation.

Tests the unified diff generation functionality including context lines,
line number adjustment, and integration with SEARCH/REPLACE blocks.
"""

import pytest
import tempfile
from pathlib import Path

from evaluation.core.patch_normalizer import PatchNormalizer
from evaluation.core.data_structures import SearchReplace, RewritePatch


class TestPatchNormalizerDiff:
    """Test suite for diff generation in PatchNormalizer."""
    
    @pytest.fixture
    def normalizer(self):
        """Create PatchNormalizer instance."""
        return PatchNormalizer(context_lines=3)
    
    @pytest.fixture
    def temp_java_file(self):
        """Create a temporary Java file for testing."""
        content = """public class TestClass {
    public void method1() {
        int x = 1;
        int y = 2;
        int z = 3;
        return x + y + z;
    }
    
    public void method2() {
        System.out.println("Hello");
        System.out.println("World");
    }
}"""
        
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.java',
            delete=False,
            encoding='utf-8'
        ) as f:
            f.write(content)
            temp_path = Path(f.name)
        
        yield temp_path
        
        # Cleanup
        if temp_path.exists():
            temp_path.unlink()
    
    # ========================================================================
    # Test Hunk Header Adjustment
    # ========================================================================
    
    def test_adjust_hunk_header_standard(self, normalizer):
        """Test adjusting standard hunk header."""
        header = "@@ -1,10 +1,10 @@"
        adjusted = normalizer._adjust_hunk_header(header, 50)
        assert adjusted == "@@ -50,10 +50,10 @@"
    
    def test_adjust_hunk_header_different_counts(self, normalizer):
        """Test adjusting hunk header with different line counts."""
        header = "@@ -1,5 +1,8 @@"
        adjusted = normalizer._adjust_hunk_header(header, 100)
        assert adjusted == "@@ -100,5 +100,8 @@"
    
    def test_adjust_hunk_header_single_line(self, normalizer):
        """Test adjusting single-line hunk header."""
        header = "@@ -1 +1 @@"
        adjusted = normalizer._adjust_hunk_header(header, 25)
        assert adjusted == "@@ -25 +25 @@"
    
    def test_adjust_hunk_header_invalid(self, normalizer):
        """Test that invalid header is returned unchanged."""
        header = "invalid header"
        adjusted = normalizer._adjust_hunk_header(header, 50)
        assert adjusted == "invalid header"
    
    # ========================================================================
    # Test Unified Diff Generation
    # ========================================================================
    
    def test_generate_unified_diff_simple(self, normalizer, temp_java_file):
        """Test generating unified diff for simple change."""
        original_lines = ["        int x = 1;"]
        modified_lines = ["        int x = 10;"]
        
        diff = normalizer.generate_unified_diff(
            original_lines=original_lines,
            modified_lines=modified_lines,
            filepath=str(temp_java_file),
            start_line=3,
            context_lines=2
        )
        
        # Check that diff is generated
        assert diff
        assert "---" in diff
        assert "+++" in diff
        assert "@@" in diff
        assert "-        int x = 1;" in diff
        assert "+        int x = 10;" in diff
    
    def test_generate_unified_diff_with_context(self, normalizer, temp_java_file):
        """Test that context lines are included."""
        original_lines = ["        int y = 2;"]
        modified_lines = ["        int y = 20;"]
        
        diff = normalizer.generate_unified_diff(
            original_lines=original_lines,
            modified_lines=modified_lines,
            filepath=str(temp_java_file),
            start_line=4,
            context_lines=1
        )
        
        # Should include context lines
        assert "int x = 1;" in diff  # Context before
        assert "int z = 3;" in diff  # Context after
    
    def test_generate_unified_diff_multiline(self, normalizer, temp_java_file):
        """Test generating diff for multiple lines."""
        original_lines = [
            "        int x = 1;",
            "        int y = 2;",
            "        int z = 3;"
        ]
        modified_lines = [
            "        int x = 10;",
            "        int y = 20;",
            "        int z = 30;"
        ]
        
        diff = normalizer.generate_unified_diff(
            original_lines=original_lines,
            modified_lines=modified_lines,
            filepath=str(temp_java_file),
            start_line=3,
            context_lines=1
        )
        
        assert diff
        assert "-        int x = 1;" in diff
        assert "+        int x = 10;" in diff
        assert "-        int y = 2;" in diff
        assert "+        int y = 20;" in diff
    
    def test_generate_unified_diff_line_numbers(self, normalizer, temp_java_file):
        """Test that line numbers are correctly adjusted."""
        original_lines = ["        int y = 2;"]
        modified_lines = ["        int y = 20;"]
        
        diff = normalizer.generate_unified_diff(
            original_lines=original_lines,
            modified_lines=modified_lines,
            filepath=str(temp_java_file),
            start_line=4,
            context_lines=1
        )
        
        # Check that hunk header has correct line numbers
        # Should start at line 3 (line 4 - 1 context line)
        assert "@@ -3," in diff or "@@ -3 " in diff
    
    # ========================================================================
    # Test SEARCH/REPLACE Diff Generation
    # ========================================================================
    
    def test_generate_diff_for_search_replace(self, normalizer, temp_java_file):
        """Test generating diff for SearchReplace block."""
        sr = SearchReplace(
            method_signature="public void method1()",
            search_block="        int x = 1;",
            replace_block="        int x = 100;",
            raw_text=""
        )
        
        diff = normalizer._generate_diff_for_search_replace(
            sr=sr,
            source_file=temp_java_file,
            source_content=temp_java_file.read_text(),
            match_start_line=3,
            match_end_line=3
        )
        
        assert diff
        assert "-        int x = 1;" in diff
        assert "+        int x = 100;" in diff
    
    def test_generate_diff_for_search_replace_multiline(
        self,
        normalizer,
        temp_java_file
    ):
        """Test generating diff for multiline SearchReplace."""
        sr = SearchReplace(
            method_signature="public void method2()",
            search_block='        System.out.println("Hello");\n        System.out.println("World");',
            replace_block='        System.out.println("Goodbye");\n        System.out.println("Universe");',
            raw_text=""
        )
        
        diff = normalizer._generate_diff_for_search_replace(
            sr=sr,
            source_file=temp_java_file,
            source_content=temp_java_file.read_text(),
            match_start_line=10,
            match_end_line=11
        )
        
        assert diff
        assert '-        System.out.println("Hello");' in diff
        assert '+        System.out.println("Goodbye");' in diff
        assert '-        System.out.println("World");' in diff
        assert '+        System.out.println("Universe");' in diff
    
    # ========================================================================
    # Test Edge Cases
    # ========================================================================
    
    def test_generate_diff_at_file_start(self, normalizer, temp_java_file):
        """Test generating diff at the start of file."""
        original_lines = ["public class TestClass {"]
        modified_lines = ["public class ModifiedClass {"]
        
        diff = normalizer.generate_unified_diff(
            original_lines=original_lines,
            modified_lines=modified_lines,
            filepath=str(temp_java_file),
            start_line=1,
            context_lines=2
        )
        
        assert diff
        assert "-public class TestClass {" in diff
        assert "+public class ModifiedClass {" in diff
    
    def test_generate_diff_at_file_end(self, normalizer, temp_java_file):
        """Test generating diff at the end of file."""
        # Get last line number
        lines = temp_java_file.read_text().split('\n')
        last_line_num = len(lines)
        
        original_lines = ["}"]
        modified_lines = ["} // End of class"]
        
        diff = normalizer.generate_unified_diff(
            original_lines=original_lines,
            modified_lines=modified_lines,
            filepath=str(temp_java_file),
            start_line=last_line_num,
            context_lines=2
        )
        
        assert diff
        assert "-}" in diff
        assert "+} // End of class" in diff
    
    def test_generate_diff_zero_context(self, normalizer, temp_java_file):
        """Test generating diff with zero context lines."""
        normalizer_no_context = PatchNormalizer(context_lines=0)
        
        original_lines = ["        int x = 1;"]
        modified_lines = ["        int x = 10;"]
        
        diff = normalizer_no_context.generate_unified_diff(
            original_lines=original_lines,
            modified_lines=modified_lines,
            filepath=str(temp_java_file),
            start_line=3,
            context_lines=0
        )
        
        assert diff
        # Should not include context lines
        lines = diff.split('\n')
        # Count lines starting with space (context lines)
        context_count = sum(1 for line in lines if line.startswith(' ') and len(line) > 1)
        assert context_count == 0
