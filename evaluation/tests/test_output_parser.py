"""Unit tests for OutputParser module.

Tests the parsing of model-generated fix outputs in both Edit and Rewrite
formats, including format detection, validation, and error handling.
"""

import pytest

from evaluation.core.output_parser import OutputParser
from evaluation.core.data_structures import (
    ParsedPatch,
    SearchReplace,
    RewritePatch
)


class TestOutputParser:
    """Test suite for OutputParser class."""
    
    @pytest.fixture
    def parser(self):
        """Create OutputParser instance."""
        return OutputParser()
    
    # ========================================================================
    # Test Edit Format Parsing
    # ========================================================================
    
    def test_parse_edit_format_single_block(self, parser):
        """Test parsing Edit format with single SEARCH/REPLACE block."""
        model_output = """```java
###public LegendItemCollection getLegendItems()
<<<<<<< SEARCH
        CategoryDataset dataset = this.plot.getDataset(index);
        if (dataset != null) {
            return result;
        }
        int seriesCount = dataset.getRowCount();
=======
        CategoryDataset dataset = this.plot.getDataset(index);
        if (dataset == null) {
            return result;
        }
        int seriesCount = dataset.getRowCount();
>>>>>>> REPLACE
```"""
        
        result = parser.parse(model_output, "Chart_1", 1, "edit")
        
        assert result.parse_success is True
        assert result.modeling_type == "edit"
        assert result.bug_slug == "Chart_1"
        assert result.attempt_num == 1
        assert len(result.search_replaces) == 1
        
        sr = result.search_replaces[0]
        assert sr.method_signature == "public LegendItemCollection getLegendItems()"
        assert "if (dataset != null)" in sr.search_block
        assert "if (dataset == null)" in sr.replace_block
    
    def test_parse_edit_format_multiple_blocks(self, parser):
        """Test parsing Edit format with multiple SEARCH/REPLACE blocks."""
        model_output = """```java
###public void method1()
<<<<<<< SEARCH
int x = 1;
=======
int x = 2;
>>>>>>> REPLACE

###public void method2()
<<<<<<< SEARCH
int y = 3;
=======
int y = 4;
>>>>>>> REPLACE
```"""
        
        result = parser.parse(model_output, "Test_1", 1, "edit")
        
        assert result.parse_success is True
        assert len(result.search_replaces) == 2
        
        assert result.search_replaces[0].method_signature == "public void method1()"
        assert "int x = 1;" in result.search_replaces[0].search_block
        assert "int x = 2;" in result.search_replaces[0].replace_block
        
        assert result.search_replaces[1].method_signature == "public void method2()"
        assert "int y = 3;" in result.search_replaces[1].search_block
        assert "int y = 4;" in result.search_replaces[1].replace_block
    
    def test_parse_edit_format_without_code_blocks(self, parser):
        """Test parsing Edit format without markdown code blocks."""
        model_output = """###public void test()
<<<<<<< SEARCH
old code
=======
new code
>>>>>>> REPLACE"""
        
        result = parser.parse(model_output, "Test_1", 1, "edit")
        
        assert result.parse_success is True
        assert len(result.search_replaces) == 1
        assert result.search_replaces[0].method_signature == "public void test()"
    
    # ========================================================================
    # Test Rewrite Format Parsing
    # ========================================================================
    
    def test_parse_rewrite_format_single_method(self, parser):
        """Test parsing Rewrite format with single method."""
        model_output = """```java
###public void calculate()
public void calculate() {
    int result = 0;
    for (int i = 0; i < 10; i++) {
        result += i;
    }
    return result;
}
```"""
        
        result = parser.parse(model_output, "Test_1", 1, "rewrite")
        
        assert result.parse_success is True
        assert result.modeling_type == "rewrite"
        assert len(result.rewrites) == 1
        
        rewrite = result.rewrites[0]
        assert rewrite.method_signature == "public void calculate()"
        assert "int result = 0;" in rewrite.full_code
        assert "{" in rewrite.full_code
        assert "}" in rewrite.full_code
    
    def test_parse_rewrite_format_multiple_methods(self, parser):
        """Test parsing Rewrite format with multiple methods."""
        model_output = """```java
###public void method1()
public void method1() {
    System.out.println("Method 1");
}

###public void method2()
public void method2() {
    System.out.println("Method 2");
}
```"""
        
        result = parser.parse(model_output, "Test_1", 1, "rewrite")
        
        assert result.parse_success is True
        assert len(result.rewrites) == 2
        
        assert result.rewrites[0].method_signature == "public void method1()"
        assert "Method 1" in result.rewrites[0].full_code
        
        assert result.rewrites[1].method_signature == "public void method2()"
        assert "Method 2" in result.rewrites[1].full_code
    
    # ========================================================================
    # Test Format Detection
    # ========================================================================
    
    def test_detect_format_edit(self, parser):
        """Test format detection for Edit format."""
        model_output = """
###public void test()
<<<<<<< SEARCH
old
=======
new
>>>>>>> REPLACE
"""
        
        detected = parser.detect_format(model_output)
        assert detected == "edit"
    
    def test_detect_format_rewrite(self, parser):
        """Test format detection for Rewrite format."""
        model_output = """
###public void test()
public void test() {
    // code
}
"""
        
        detected = parser.detect_format(model_output)
        assert detected == "rewrite"
    
    def test_detect_format_ambiguous(self, parser):
        """Test format detection with ambiguous input."""
        model_output = "some random text"
        
        detected = parser.detect_format(model_output)
        # Should default to 'edit'
        assert detected == "edit"
    
    def test_auto_detect_format(self, parser):
        """Test automatic format detection when modeling_type is None."""
        edit_output = """
<<<<<<< SEARCH
old
=======
new
>>>>>>> REPLACE
"""
        
        result = parser.parse(edit_output, "Test_1", 1, modeling_type=None)
        assert result.modeling_type == "edit"
    
    # ========================================================================
    # Test Validation Methods
    # ========================================================================
    
    def test_validate_search_replace_valid(self, parser):
        """Test validation of valid SearchReplace."""
        sr = SearchReplace(
            method_signature="public void test()",
            search_block="old code",
            replace_block="new code",
            raw_text="..."
        )
        
        is_valid, error = parser.validate_search_replace(sr)
        assert is_valid is True
        assert error is None
    
    def test_validate_search_replace_missing_signature(self, parser):
        """Test validation with missing method signature."""
        sr = SearchReplace(
            method_signature="",
            search_block="old code",
            replace_block="new code",
            raw_text="..."
        )
        
        is_valid, error = parser.validate_search_replace(sr)
        assert is_valid is False
        assert "method signature" in error.lower()
    
    def test_validate_search_replace_empty_search(self, parser):
        """Test validation with empty SEARCH block."""
        sr = SearchReplace(
            method_signature="public void test()",
            search_block="",
            replace_block="new code",
            raw_text="..."
        )
        
        is_valid, error = parser.validate_search_replace(sr)
        assert is_valid is False
        assert "search" in error.lower()
    
    def test_validate_search_replace_empty_replace(self, parser):
        """Test validation with empty REPLACE block."""
        sr = SearchReplace(
            method_signature="public void test()",
            search_block="old code",
            replace_block="",
            raw_text="..."
        )
        
        is_valid, error = parser.validate_search_replace(sr)
        assert is_valid is False
        assert "replace" in error.lower()
    
    def test_validate_search_replace_identical_blocks(self, parser):
        """Test validation with identical SEARCH and REPLACE blocks."""
        sr = SearchReplace(
            method_signature="public void test()",
            search_block="same code",
            replace_block="same code",
            raw_text="..."
        )
        
        is_valid, error = parser.validate_search_replace(sr)
        assert is_valid is False
        assert "identical" in error.lower()
    
    def test_validate_rewrite_valid(self, parser):
        """Test validation of valid RewritePatch."""
        rewrite = RewritePatch(
            method_signature="public void test()",
            full_code="public void test() { return; }",
            raw_text="..."
        )
        
        is_valid, error = parser.validate_rewrite(rewrite)
        assert is_valid is True
        assert error is None
    
    def test_validate_rewrite_missing_signature(self, parser):
        """Test validation with missing method signature."""
        rewrite = RewritePatch(
            method_signature="",
            full_code="public void test() { return; }",
            raw_text="..."
        )
        
        is_valid, error = parser.validate_rewrite(rewrite)
        assert is_valid is False
        assert "method signature" in error.lower()
    
    def test_validate_rewrite_empty_code(self, parser):
        """Test validation with empty code."""
        rewrite = RewritePatch(
            method_signature="public void test()",
            full_code="",
            raw_text="..."
        )
        
        is_valid, error = parser.validate_rewrite(rewrite)
        assert is_valid is False
        assert "empty" in error.lower()
    
    def test_validate_rewrite_incomplete_method(self, parser):
        """Test validation with incomplete method (missing braces)."""
        rewrite = RewritePatch(
            method_signature="public void test()",
            full_code="public void test() return;",
            raw_text="..."
        )
        
        is_valid, error = parser.validate_rewrite(rewrite)
        assert is_valid is False
        assert "complete method" in error.lower()
    
    # ========================================================================
    # Test Error Handling
    # ========================================================================
    
    def test_parse_empty_output(self, parser):
        """Test parsing empty model output."""
        result = parser.parse("", "Test_1", 1, "edit")
        
        # Should not crash, but may have no patches
        assert result.parse_success is True
        assert len(result.search_replaces) == 0
    
    def test_parse_malformed_search_replace(self, parser):
        """Test parsing malformed SEARCH/REPLACE block."""
        model_output = """
<<<<<<< SEARCH
old code
=======
# Missing REPLACE marker
"""
        
        result = parser.parse(model_output, "Test_1", 1, "edit")
        
        # Should handle gracefully
        assert result.parse_success is True
        assert len(result.search_replaces) == 0
    
    def test_parse_with_exception(self, parser, monkeypatch):
        """Test error handling when parsing raises exception."""
        def mock_parse_edit(*args, **kwargs):
            raise ValueError("Mock error")
        
        monkeypatch.setattr(parser, "parse_edit_format", mock_parse_edit)
        
        result = parser.parse("test", "Test_1", 1, "edit")
        
        assert result.parse_success is False
        assert result.parse_error is not None
        assert "Mock error" in result.parse_error
    
    def test_parse_unknown_modeling_type(self, parser):
        """Test parsing with unknown modeling type."""
        result = parser.parse("test", "Test_1", 1, "unknown_type")
        
        assert result.parse_success is False
        assert result.parse_error is not None
    
    # ========================================================================
    # Test Edge Cases
    # ========================================================================
    
    def test_parse_with_extra_whitespace(self, parser):
        """Test parsing with extra whitespace in blocks."""
        model_output = """
###public void test()

<<<<<<< SEARCH

old code

=======

new code

>>>>>>> REPLACE
"""
        
        result = parser.parse(model_output, "Test_1", 1, "edit")
        
        assert result.parse_success is True
        assert len(result.search_replaces) == 1
    
    def test_parse_method_signature_with_generics(self, parser):
        """Test parsing method signature with generics."""
        model_output = """
###public <T extends Comparable<T>> List<T> sort(List<T> items)
<<<<<<< SEARCH
return items;
=======
Collections.sort(items);
return items;
>>>>>>> REPLACE
"""
        
        result = parser.parse(model_output, "Test_1", 1, "edit")
        
        assert result.parse_success is True
        assert len(result.search_replaces) == 1
        assert "<T extends Comparable<T>>" in result.search_replaces[0].method_signature
    
    def test_parse_nested_code_blocks(self, parser):
        """Test parsing with nested code structures."""
        model_output = """```java
###public void test()
<<<<<<< SEARCH
if (condition) {
    if (nested) {
        doSomething();
    }
}
=======
if (condition && nested) {
    doSomething();
}
>>>>>>> REPLACE
```"""
        
        result = parser.parse(model_output, "Test_1", 1, "edit")
        
        assert result.parse_success is True
        assert len(result.search_replaces) == 1
        assert "nested" in result.search_replaces[0].search_block
    
    def test_parse_multiple_code_blocks_in_markdown(self, parser):
        """Test parsing multiple markdown code blocks."""
        model_output = """
Some text before

```java
###public void method1()
<<<<<<< SEARCH
code1
=======
new1
>>>>>>> REPLACE
```

Some text in between

```java
###public void method2()
<<<<<<< SEARCH
code2
=======
new2
>>>>>>> REPLACE
```
"""
        
        result = parser.parse(model_output, "Test_1", 1, "edit")
        
        assert result.parse_success is True
        # Should extract both blocks
        assert len(result.search_replaces) >= 1
    
    def test_parsed_patch_properties(self, parser):
        """Test ParsedPatch property methods."""
        # Test edit format properties
        edit_result = parser.parse(
            "<<<<<<< SEARCH\nold\n=======\nnew\n>>>>>>> REPLACE",
            "Test_1",
            1,
            "edit"
        )
        
        assert edit_result.is_edit_format is True
        assert edit_result.is_rewrite_format is False
        assert edit_result.patch_count >= 0
        
        # Test rewrite format properties
        rewrite_result = parser.parse(
            "###public void test()\npublic void test() { }",
            "Test_2",
            1,
            "rewrite"
        )
        
        assert rewrite_result.is_rewrite_format is True
        assert rewrite_result.is_edit_format is False
    
    def test_extract_code_blocks_helper(self, parser):
        """Test _extract_code_blocks helper method."""
        content_with_blocks = """
Some text
```java
code here
```
More text
```
more code
```
"""
        
        extracted = parser._extract_code_blocks(content_with_blocks)
        assert "code here" in extracted
        assert "more code" in extracted
    
    def test_extract_method_signatures_helper(self, parser):
        """Test _extract_method_signatures helper method."""
        content = """
###public void method1()
some code
###private int method2(String arg)
more code
###protected void method3()
"""
        
        signatures = parser._extract_method_signatures(content)
        assert len(signatures) == 3
        assert "public void method1()" in signatures
        assert "private int method2(String arg)" in signatures
        assert "protected void method3()" in signatures
