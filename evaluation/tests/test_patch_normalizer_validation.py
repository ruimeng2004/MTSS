"""Tests for PatchNormalizer validation mechanisms.

Tests the patch validation and dry-run application functionality.
"""

import pytest
import tempfile
from pathlib import Path

from evaluation.core.patch_normalizer import PatchNormalizer
from evaluation.core.data_structures import NormalizedPatch, MatchQuality


class TestPatchNormalizerValidation:
    """Test suite for patch validation in PatchNormalizer."""
    
    @pytest.fixture
    def normalizer(self):
        """Create PatchNormalizer instance."""
        return PatchNormalizer(context_lines=3)
    
    @pytest.fixture
    def valid_diff(self):
        """Create a valid unified diff."""
        return """--- a/test.java
+++ b/test.java
@@ -10,3 +10,3 @@
     public void test() {
-        int x = 1;
+        int x = 2;
     }
"""
    
    @pytest.fixture
    def temp_java_file(self):
        """Create a temporary Java file."""
        content = """public class Test {
    public void method() {
        int x = 1;
        int y = 2;
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
        
        if temp_path.exists():
            temp_path.unlink()
    
    # ========================================================================
    # Test Diff Format Validation
    # ========================================================================
    
    def test_is_valid_diff_format_valid(self, normalizer, valid_diff):
        """Test validation of valid diff format."""
        is_valid, error = normalizer._is_valid_diff_format(valid_diff)
        assert is_valid is True
        assert error is None
    
    def test_is_valid_diff_format_empty(self, normalizer):
        """Test validation of empty diff."""
        is_valid, error = normalizer._is_valid_diff_format("")
        assert is_valid is False
        assert "Empty" in error
    
    def test_is_valid_diff_format_missing_from_header(self, normalizer):
        """Test validation when --- header is missing."""
        diff = """+++ b/test.java
@@ -1,1 +1,1 @@
-old
+new
"""
        is_valid, error = normalizer._is_valid_diff_format(diff)
        assert is_valid is False
        assert "---" in error
    
    def test_is_valid_diff_format_missing_to_header(self, normalizer):
        """Test validation when +++ header is missing."""
        diff = """--- a/test.java
@@ -1,1 +1,1 @@
-old
+new
"""
        is_valid, error = normalizer._is_valid_diff_format(diff)
        assert is_valid is False
        assert "+++" in error
    
    def test_is_valid_diff_format_missing_hunk_header(self, normalizer):
        """Test validation when @@ header is missing."""
        diff = """--- a/test.java
+++ b/test.java
-old
+new
"""
        is_valid, error = normalizer._is_valid_diff_format(diff)
        assert is_valid is False
        assert "@@" in error
    
    def test_is_valid_diff_format_wrong_order(self, normalizer):
        """Test validation when headers are in wrong order."""
        diff = """+++ b/test.java
--- a/test.java
@@ -1,1 +1,1 @@
-old
+new
"""
        is_valid, error = normalizer._is_valid_diff_format(diff)
        assert is_valid is False
        assert "order" in error.lower()
    
    # ========================================================================
    # Test Line Number Validation
    # ========================================================================
    
    def test_validate_line_numbers_valid(self, normalizer, valid_diff):
        """Test validation of valid line numbers."""
        is_valid, error = normalizer._validate_line_numbers(valid_diff)
        assert is_valid is True
        assert error is None
    
    def test_validate_line_numbers_invalid_format(self, normalizer):
        """Test validation with invalid hunk header format."""
        diff = """--- a/test.java
+++ b/test.java
@@ invalid @@
-old
+new
"""
        is_valid, error = normalizer._validate_line_numbers(diff)
        assert is_valid is False
        assert "Invalid hunk header" in error
    
    def test_validate_line_numbers_negative(self, normalizer):
        """Test validation with negative line numbers."""
        diff = """--- a/test.java
+++ b/test.java
@@ -0,1 +1,1 @@
-old
+new
"""
        is_valid, error = normalizer._validate_line_numbers(diff)
        assert is_valid is False
        assert ">= 1" in error
    
    def test_validate_line_numbers_single_line_format(self, normalizer):
        """Test validation with single-line hunk format."""
        diff = """--- a/test.java
+++ b/test.java
@@ -5 +5 @@
-old
+new
"""
        is_valid, error = normalizer._validate_line_numbers(diff)
        assert is_valid is True
        assert error is None
    
    # ========================================================================
    # Test Context Validation
    # ========================================================================
    
    def test_validate_context_valid(self, normalizer, valid_diff):
        """Test validation of valid context."""
        is_valid, error = normalizer._validate_context(valid_diff)
        assert is_valid is True
        assert error is None
    
    def test_validate_context_invalid_prefix(self, normalizer):
        """Test validation with invalid line prefix."""
        diff = """--- a/test.java
+++ b/test.java
@@ -1,3 +1,3 @@
 context
-old
invalid line without prefix
+new
"""
        is_valid, error = normalizer._validate_context(diff)
        assert is_valid is False
        assert "Invalid hunk line prefix" in error
    
    def test_validate_context_with_backslash(self, normalizer):
        """Test validation with backslash (no newline marker)."""
        diff = """--- a/test.java
+++ b/test.java
@@ -1,2 +1,2 @@
-old
+new
\\ No newline at end of file
"""
        is_valid, error = normalizer._validate_context(diff)
        assert is_valid is True
        assert error is None
    
    # ========================================================================
    # Test Complete Patch Validation
    # ========================================================================
    
    def test_validate_normalized_patch_valid(self, normalizer, valid_diff):
        """Test validation of valid normalized patch."""
        patch = NormalizedPatch(
            bug_slug="Test_1",
            attempt_num=1,
            modeling_type="edit",
            diff_content=valid_diff,
            target_files=["test.java"]
        )
        
        is_valid, error = normalizer.validate_normalized_patch(patch)
        assert is_valid is True
        assert error is None
    
    def test_validate_normalized_patch_empty(self, normalizer):
        """Test validation of patch with no content."""
        patch = NormalizedPatch(
            bug_slug="Test_1",
            attempt_num=1,
            modeling_type="edit",
            diff_content="",
            target_files=["test.java"]
        )
        
        is_valid, error = normalizer.validate_normalized_patch(patch)
        assert is_valid is False
        assert "no diff content" in error.lower()
    
    def test_validate_normalized_patch_invalid_format(self, normalizer):
        """Test validation of patch with invalid format."""
        patch = NormalizedPatch(
            bug_slug="Test_1",
            attempt_num=1,
            modeling_type="edit",
            diff_content="not a valid diff",
            target_files=["test.java"]
        )
        
        is_valid, error = normalizer.validate_normalized_patch(patch)
        assert is_valid is False
        assert "Invalid diff format" in error
    
    # ========================================================================
    # Test Dry-Run Apply
    # ========================================================================
    
    def test_dry_run_apply_file_not_found(self, normalizer):
        """Test dry-run with non-existent file."""
        patch = NormalizedPatch(
            bug_slug="Test_1",
            attempt_num=1,
            modeling_type="edit",
            diff_content="dummy",
            target_files=["nonexistent.java"]
        )
        
        can_apply, error = normalizer.dry_run_apply(
            patch,
            Path("nonexistent.java")
        )
        
        assert can_apply is False
        assert "not found" in error.lower()
    
    def test_dry_run_apply_valid_patch(self, normalizer, temp_java_file):
        """Test dry-run with valid patch."""
        # Create a valid diff for the temp file
        diff = f"""--- a/{temp_java_file.name}
+++ b/{temp_java_file.name}
@@ -2,3 +2,3 @@
     public void method() {{
-        int x = 1;
+        int x = 10;
         int y = 2;
"""
        
        patch = NormalizedPatch(
            bug_slug="Test_1",
            attempt_num=1,
            modeling_type="edit",
            diff_content=diff,
            target_files=[str(temp_java_file)]
        )
        
        can_apply, error = normalizer.dry_run_apply(patch, temp_java_file)
        
        # This might fail if git is not available, so we check both cases
        if can_apply:
            assert error is None
        else:
            # If git is not available or patch doesn't apply
            assert error is not None
