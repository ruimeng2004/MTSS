"""Unit tests for InputHandler class."""

import json
import tempfile
import unittest
from pathlib import Path

from evaluation.core.input_handler import InputHandler
from evaluation.core.data_structures import FixAttempt


class TestInputHandler(unittest.TestCase):
    """Test cases for InputHandler class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary directory for test data
        self.test_dir = tempfile.mkdtemp()
        self.test_path = Path(self.test_dir)
        
        # Create test result folder structure
        self._create_test_structure()
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.test_dir)
    
    def _create_test_structure(self):
        """Create test folder structure with sample data."""
        # Create Chart_1 with 2 attempts
        chart1_dir = self.test_path / "Chart_1"
        chart1_dir.mkdir()
        
        # Attempt 1
        attempt1_dir = chart1_dir / "1"
        attempt1_dir.mkdir()
        
        (attempt1_dir / "model_output.txt").write_text(
            "```java\n###public void foo()\n"
            "<<<<<<< SEARCH\nold code\n=======\nnew code\n"
            ">>>>>>> REPLACE\n```"
        )
        (attempt1_dir / "query.txt").write_text("Test query")
        (attempt1_dir / "result.json").write_text(json.dumps({
            "task": "d4j_edit",
            "slug": "Chart_1",
            "sample_idx": 1
        }))
        
        # Attempt 2
        attempt2_dir = chart1_dir / "2"
        attempt2_dir.mkdir()
        
        (attempt2_dir / "model_output.txt").write_text("Test output 2")
        (attempt2_dir / "query.txt").write_text("Test query 2")
        (attempt2_dir / "result.json").write_text(json.dumps({
            "task": "d4j_rewrite",
            "slug": "Chart_1",
            "sample_idx": 2
        }))
        
        # Create Closure_10 with 1 attempt
        closure10_dir = self.test_path / "Closure_10"
        closure10_dir.mkdir()
        
        attempt1_dir = closure10_dir / "1"
        attempt1_dir.mkdir()
        
        (attempt1_dir / "model_output.txt").write_text("Test output")
        (attempt1_dir / "query.txt").write_text("Test query")
        (attempt1_dir / "result.json").write_text(json.dumps({
            "task": "d4j_edit",
            "slug": "Closure_10",
            "sample_idx": 1
        }))
        
        # Create invalid folder (missing files)
        chart2_dir = self.test_path / "Chart_2"
        chart2_dir.mkdir()
        
        invalid_attempt = chart2_dir / "1"
        invalid_attempt.mkdir()
        # Only create model_output.txt, missing other files
        (invalid_attempt / "model_output.txt").write_text("Test")
        
        # Create non-bug folder (should be ignored)
        other_dir = self.test_path / "other_folder"
        other_dir.mkdir()
    
    def test_init_valid_folder(self):
        """Test initialization with valid result folder."""
        handler = InputHandler(self.test_path)
        self.assertEqual(handler.result_folder, self.test_path)
    
    def test_init_nonexistent_folder(self):
        """Test initialization with nonexistent folder."""
        with self.assertRaises(ValueError) as context:
            InputHandler(self.test_path / "nonexistent")
        
        self.assertIn("does not exist", str(context.exception))
    
    def test_init_file_instead_of_folder(self):
        """Test initialization with file instead of folder."""
        test_file = self.test_path / "test.txt"
        test_file.write_text("test")
        
        with self.assertRaises(ValueError) as context:
            InputHandler(test_file)
        
        self.assertIn("not a directory", str(context.exception))
    
    def test_list_bugs(self):
        """Test listing all bugs in result folder."""
        handler = InputHandler(self.test_path)
        bugs = handler.list_bugs()
        
        # Should find Chart_1, Chart_2, and Closure_10
        # (Chart_2 has invalid attempts but is still a bug folder)
        self.assertEqual(len(bugs), 3)
        self.assertIn("Chart_1", bugs)
        self.assertIn("Chart_2", bugs)
        self.assertIn("Closure_10", bugs)
        self.assertNotIn("other_folder", bugs)
    
    def test_list_attempts(self):
        """Test listing attempts for a specific bug."""
        handler = InputHandler(self.test_path)
        
        # Chart_1 should have 2 valid attempts
        attempts = handler.list_attempts("Chart_1")
        self.assertEqual(len(attempts), 2)
        self.assertEqual(attempts, [1, 2])
        
        # Closure_10 should have 1 valid attempt
        attempts = handler.list_attempts("Closure_10")
        self.assertEqual(len(attempts), 1)
        self.assertEqual(attempts, [1])
        
        # Chart_2 should have 0 valid attempts (missing files)
        attempts = handler.list_attempts("Chart_2")
        self.assertEqual(len(attempts), 0)
    
    def test_list_attempts_nonexistent_bug(self):
        """Test listing attempts for nonexistent bug."""
        handler = InputHandler(self.test_path)
        attempts = handler.list_attempts("Nonexistent_1")
        self.assertEqual(len(attempts), 0)
    
    def test_load_attempt(self):
        """Test loading a specific fix attempt."""
        handler = InputHandler(self.test_path)
        
        # Load Chart_1 attempt 1
        fix_attempt = handler.load_attempt("Chart_1", 1)
        
        self.assertIsNotNone(fix_attempt)
        self.assertIsInstance(fix_attempt, FixAttempt)
        self.assertEqual(fix_attempt.bug_slug, "Chart_1")
        self.assertEqual(fix_attempt.attempt_num, 1)
        self.assertIn("<<<<<<< SEARCH", fix_attempt.model_output)
        self.assertEqual(fix_attempt.query, "Test query")
        self.assertEqual(fix_attempt.result_json["task"], "d4j_edit")
        self.assertEqual(fix_attempt.modeling_type, "edit")
    
    def test_load_attempt_rewrite_format(self):
        """Test loading attempt with rewrite format."""
        handler = InputHandler(self.test_path)
        
        # Load Chart_1 attempt 2 (rewrite format)
        fix_attempt = handler.load_attempt("Chart_1", 2)
        
        self.assertIsNotNone(fix_attempt)
        self.assertEqual(fix_attempt.modeling_type, "rewrite")
    
    def test_load_attempt_nonexistent(self):
        """Test loading nonexistent attempt."""
        handler = InputHandler(self.test_path)
        
        # Nonexistent bug
        fix_attempt = handler.load_attempt("Nonexistent_1", 1)
        self.assertIsNone(fix_attempt)
        
        # Nonexistent attempt number
        fix_attempt = handler.load_attempt("Chart_1", 999)
        self.assertIsNone(fix_attempt)
    
    def test_load_attempt_missing_files(self):
        """Test loading attempt with missing files."""
        handler = InputHandler(self.test_path)
        
        # Chart_2 attempt 1 is missing query.txt and result.json
        fix_attempt = handler.load_attempt("Chart_2", 1)
        self.assertIsNone(fix_attempt)
    
    def test_load_attempt_invalid_json(self):
        """Test loading attempt with invalid JSON."""
        # Create attempt with invalid JSON
        chart3_dir = self.test_path / "Chart_3"
        chart3_dir.mkdir()
        
        attempt_dir = chart3_dir / "1"
        attempt_dir.mkdir()
        
        (attempt_dir / "model_output.txt").write_text("Test")
        (attempt_dir / "query.txt").write_text("Test")
        (attempt_dir / "result.json").write_text("invalid json{")
        
        handler = InputHandler(self.test_path)
        fix_attempt = handler.load_attempt("Chart_3", 1)
        
        self.assertIsNone(fix_attempt)
    
    def test_load_all_attempts(self):
        """Test loading all attempts for a bug."""
        handler = InputHandler(self.test_path)
        
        # Load all attempts for Chart_1
        attempts = handler.load_all_attempts("Chart_1")
        
        self.assertEqual(len(attempts), 2)
        self.assertEqual(attempts[0].attempt_num, 1)
        self.assertEqual(attempts[1].attempt_num, 2)
    
    def test_load_all_bugs(self):
        """Test loading all attempts for all bugs."""
        handler = InputHandler(self.test_path)
        
        all_attempts = handler.load_all_bugs()
        
        # Should have 2 bugs with valid attempts (Chart_1 and Closure_10)
        # Chart_2 has no valid attempts
        self.assertEqual(len(all_attempts), 2)
        
        # Find Chart_1 attempts
        chart1_attempts = [
            attempts for attempts in all_attempts 
            if attempts[0].bug_slug == "Chart_1"
        ][0]
        self.assertEqual(len(chart1_attempts), 2)
        
        # Find Closure_10 attempts
        closure10_attempts = [
            attempts for attempts in all_attempts 
            if attempts[0].bug_slug == "Closure_10"
        ][0]
        self.assertEqual(len(closure10_attempts), 1)
    
    def test_validate_structure_valid(self):
        """Test structure validation with valid folder."""
        handler = InputHandler(self.test_path)
        self.assertTrue(handler.validate_structure())
    
    def test_validate_structure_empty_folder(self):
        """Test structure validation with empty folder."""
        empty_dir = tempfile.mkdtemp()
        try:
            handler = InputHandler(empty_dir)
            self.assertFalse(handler.validate_structure())
        finally:
            import shutil
            shutil.rmtree(empty_dir)
    
    def test_validate_structure_no_valid_attempts(self):
        """Test structure validation with no valid attempts."""
        # Create folder with only invalid attempts
        invalid_dir = tempfile.mkdtemp()
        try:
            bug_dir = Path(invalid_dir) / "Chart_1"
            bug_dir.mkdir()
            
            attempt_dir = bug_dir / "1"
            attempt_dir.mkdir()
            # Only create one file (incomplete)
            (attempt_dir / "model_output.txt").write_text("Test")
            
            handler = InputHandler(invalid_dir)
            self.assertFalse(handler.validate_structure())
        finally:
            import shutil
            shutil.rmtree(invalid_dir)
    
    def test_fix_attempt_properties(self):
        """Test FixAttempt property methods."""
        handler = InputHandler(self.test_path)
        fix_attempt = handler.load_attempt("Chart_1", 1)
        
        self.assertIsNotNone(fix_attempt)
        
        # Test path properties
        self.assertTrue(fix_attempt.model_output_path.exists())
        self.assertTrue(fix_attempt.query_path.exists())
        self.assertTrue(fix_attempt.result_json_path.exists())
        
        # Test validate method
        self.assertTrue(fix_attempt.validate())


if __name__ == '__main__':
    unittest.main()
