"""Tests for PatchNormalizer tree-sitter method location.

Tests the tree-sitter based method location functionality including
simple methods, overloaded methods, and methods in nested classes.
"""

import pytest

from evaluation.core.patch_normalizer import PatchNormalizer


class TestPatchNormalizerTreeSitter:
    """Test suite for tree-sitter method location."""
    
    @pytest.fixture
    def normalizer(self):
        """Create PatchNormalizer instance."""
        return PatchNormalizer(context_lines=3)
    
    # ========================================================================
    # Test Simple Method Location
    # ========================================================================
    
    def test_locate_simple_method(self, normalizer):
        """Test locating a simple method."""
        source_code = """public class TestClass {
    public void simpleMethod() {
        int x = 1;
        int y = 2;
    }
}"""
        
        method_node = normalizer._locate_method_with_treesitter(
            source_code,
            "public void simpleMethod()"
        )
        
        assert method_node is not None
        assert method_node['start_line'] == 2
        assert 'simpleMethod' in method_node['text']
    
    def test_locate_method_with_return_type(self, normalizer):
        """Test locating method with return type."""
        source_code = """public class TestClass {
    public String getString() {
        return "hello";
    }
}"""
        
        method_node = normalizer._locate_method_with_treesitter(
            source_code,
            "public String getString()"
        )
        
        assert method_node is not None
        assert 'getString' in method_node['text']
    
    def test_locate_method_with_parameters(self, normalizer):
        """Test locating method with parameters."""
        source_code = """public class TestClass {
    public int add(int a, int b) {
        return a + b;
    }
}"""
        
        method_node = normalizer._locate_method_with_treesitter(
            source_code,
            "public int add(int a, int b)"
        )
        
        assert method_node is not None
        assert 'add' in method_node['text']
    
    def test_locate_static_method(self, normalizer):
        """Test locating static method."""
        source_code = """public class TestClass {
    public static void main(String[] args) {
        System.out.println("Hello");
    }
}"""
        
        method_node = normalizer._locate_method_with_treesitter(
            source_code,
            "public static void main(String[] args)"
        )
        
        assert method_node is not None
        assert 'main' in method_node['text']
    
    def test_locate_private_method(self, normalizer):
        """Test locating private method."""
        source_code = """public class TestClass {
    private void helper() {
        // helper code
    }
}"""
        
        method_node = normalizer._locate_method_with_treesitter(
            source_code,
            "private void helper()"
        )
        
        assert method_node is not None
        assert 'helper' in method_node['text']
    
    def test_locate_method_not_found(self, normalizer):
        """Test when method is not found."""
        source_code = """public class TestClass {
    public void existingMethod() {
        // code
    }
}"""
        
        method_node = normalizer._locate_method_with_treesitter(
            source_code,
            "public void nonExistentMethod()"
        )
        
        assert method_node is None
    
    # ========================================================================
    # Test Overloaded Methods
    # ========================================================================
    
    def test_locate_overloaded_method_first(self, normalizer):
        """Test locating first overloaded method."""
        source_code = """public class TestClass {
    public void calculate() {
        // no params
    }
    
    public void calculate(int x) {
        // one param
    }
    
    public void calculate(int x, int y) {
        // two params
    }
}"""
        
        # Should find the first one (method name matches)
        method_node = normalizer._locate_method_with_treesitter(
            source_code,
            "public void calculate()"
        )
        
        assert method_node is not None
        assert 'calculate' in method_node['text']
        # Should be the first occurrence
        assert method_node['start_line'] == 2
    
    def test_locate_overloaded_method_by_name(self, normalizer):
        """Test that overloaded methods are found by name."""
        source_code = """public class TestClass {
    public int add(int a) {
        return a;
    }
    
    public int add(int a, int b) {
        return a + b;
    }
}"""
        
        # Both should be found by name (returns first match)
        method_node = normalizer._locate_method_with_treesitter(
            source_code,
            "public int add(int a, int b)"
        )
        
        assert method_node is not None
        assert 'add' in method_node['text']
    
    # ========================================================================
    # Test Nested Classes
    # ========================================================================
    
    def test_locate_method_in_nested_class(self, normalizer):
        """Test locating method in nested class."""
        source_code = """public class OuterClass {
    public void outerMethod() {
        // outer
    }
    
    public static class InnerClass {
        public void innerMethod() {
            // inner
        }
    }
}"""
        
        # Should find method in nested class
        method_node = normalizer._locate_method_with_treesitter(
            source_code,
            "public void innerMethod()"
        )
        
        assert method_node is not None
        assert 'innerMethod' in method_node['text']
    
    def test_locate_method_in_outer_class(self, normalizer):
        """Test locating method in outer class when nested class exists."""
        source_code = """public class OuterClass {
    public void outerMethod() {
        // outer
    }
    
    public static class InnerClass {
        public void innerMethod() {
            // inner
        }
    }
}"""
        
        method_node = normalizer._locate_method_with_treesitter(
            source_code,
            "public void outerMethod()"
        )
        
        assert method_node is not None
        assert 'outerMethod' in method_node['text']
        assert method_node['start_line'] == 2
    
    def test_locate_method_in_anonymous_class(self, normalizer):
        """Test locating method with anonymous inner class."""
        source_code = """public class TestClass {
    public void methodWithAnonymous() {
        Runnable r = new Runnable() {
            public void run() {
                // anonymous
            }
        };
    }
}"""
        
        # Should find the outer method
        method_node = normalizer._locate_method_with_treesitter(
            source_code,
            "public void methodWithAnonymous()"
        )
        
        assert method_node is not None
        assert 'methodWithAnonymous' in method_node['text']
    
    # ========================================================================
    # Test Method Name Extraction
    # ========================================================================
    
    def test_extract_method_name_simple(self, normalizer):
        """Test extracting simple method name."""
        name = normalizer._extract_method_name("public void test()")
        assert name == "test"
    
    def test_extract_method_name_with_generics(self, normalizer):
        """Test extracting method name with generics."""
        name = normalizer._extract_method_name(
            "public <T> List<T> getList()"
        )
        assert name == "getList"
    
    def test_extract_method_name_with_array(self, normalizer):
        """Test extracting method name with array return type."""
        name = normalizer._extract_method_name(
            "public String[] getArray()"
        )
        assert name == "getArray"
    
    def test_extract_method_name_constructor(self, normalizer):
        """Test extracting constructor name."""
        name = normalizer._extract_method_name("public TestClass()")
        assert name == "TestClass"
    
    def test_extract_method_name_with_throws(self, normalizer):
        """Test extracting method name with throws clause."""
        name = normalizer._extract_method_name(
            "public void test() throws Exception"
        )
        assert name == "test"
    
    # ========================================================================
    # Test Edge Cases
    # ========================================================================
    
    def test_locate_method_with_annotations(self, normalizer):
        """Test locating method with annotations."""
        source_code = """public class TestClass {
    @Override
    @Deprecated
    public void annotatedMethod() {
        // code
    }
}"""
        
        method_node = normalizer._locate_method_with_treesitter(
            source_code,
            "public void annotatedMethod()"
        )
        
        assert method_node is not None
        assert 'annotatedMethod' in method_node['text']
    
    def test_locate_method_with_javadoc(self, normalizer):
        """Test locating method with Javadoc."""
        source_code = """public class TestClass {
    /**
     * This is a documented method.
     * @return nothing
     */
    public void documentedMethod() {
        // code
    }
}"""
        
        method_node = normalizer._locate_method_with_treesitter(
            source_code,
            "public void documentedMethod()"
        )
        
        assert method_node is not None
        assert 'documentedMethod' in method_node['text']
    
    def test_locate_method_multiline_signature(self, normalizer):
        """Test locating method with multiline signature."""
        source_code = """public class TestClass {
    public void methodWithLongSignature(
        String param1,
        int param2,
        boolean param3
    ) {
        // code
    }
}"""
        
        method_node = normalizer._locate_method_with_treesitter(
            source_code,
            "public void methodWithLongSignature(String param1, int param2, boolean param3)"
        )
        
        assert method_node is not None
        assert 'methodWithLongSignature' in method_node['text']
    
    def test_locate_method_empty_body(self, normalizer):
        """Test locating method with empty body."""
        source_code = """public class TestClass {
    public void emptyMethod() {
    }
}"""
        
        method_node = normalizer._locate_method_with_treesitter(
            source_code,
            "public void emptyMethod()"
        )
        
        assert method_node is not None
        assert 'emptyMethod' in method_node['text']
    
    def test_locate_method_with_lambda(self, normalizer):
        """Test locating method containing lambda."""
        source_code = """public class TestClass {
    public void methodWithLambda() {
        List<String> list = new ArrayList<>();
        list.forEach(s -> System.out.println(s));
    }
}"""
        
        method_node = normalizer._locate_method_with_treesitter(
            source_code,
            "public void methodWithLambda()"
        )
        
        assert method_node is not None
        assert 'methodWithLambda' in method_node['text']
        assert 'forEach' in method_node['text']
