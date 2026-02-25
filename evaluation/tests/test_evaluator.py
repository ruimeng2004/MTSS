"""Tests for the D4JFixEvaluator class."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from evaluation.core.data_structures import (
    BugEvaluationResult,
    FixAttempt,
    ParsedPatch,
    TestResult,
)
from evaluation.core.evaluator import D4JFixEvaluator, FixResult


@pytest.fixture
def temp_dirs():
    """Create temporary directories for testing."""
    with tempfile.TemporaryDirectory() as result_dir, \
         tempfile.TemporaryDirectory() as output_dir:
        yield Path(result_dir), Path(output_dir)


@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    return {
        'd4j_path': 'defects4j',
        'workspace_dir': './workspace',
        'timeout': 600
    }


@pytest.fixture
def sample_result_folder(temp_dirs):
    """Create a sample result folder structure."""
    result_dir, _ = temp_dirs
    
    # Create bug folder
    bug_dir = result_dir / "Chart_1"
    bug_dir.mkdir()
    
    # Create attempt folder
    attempt_dir = bug_dir / "1"
    attempt_dir.mkdir()
    
    # Create required files
    (attempt_dir / "model_output.txt").write_text("sample output")
    (attempt_dir / "query.txt").write_text("sample query")
    (attempt_dir / "result.json").write_text(
        json.dumps({"task": "edit", "status": "success"})
    )
    
    return result_dir


class TestD4JFixEvaluator:
    """Tests for D4JFixEvaluator class."""
    
    def test_init(self, temp_dirs, mock_config):
        """Test evaluator initialization."""
        result_dir, output_dir = temp_dirs
        
        evaluator = D4JFixEvaluator(
            result_folder=result_dir,
            output_dir=output_dir,
            config=mock_config
        )
        
        assert evaluator.result_folder == result_dir
        assert evaluator.output_dir == output_dir
        assert evaluator.config == mock_config
        assert evaluator.input_handler is not None
        assert evaluator.output_parser is not None
        assert evaluator.normalizer is not None
        assert evaluator.env_manager is not None
        assert evaluator.result_generator is not None
        assert evaluator.storage_manager is not None
    
    @patch('evaluation.core.evaluator.InputHandler')
    @patch('evaluation.core.evaluator.EnvironmentManager')
    def test_evaluate_invalid_structure(
        self,
        mock_env_manager,
        mock_input_handler,
        temp_dirs,
        mock_config
    ):
        """Test evaluation with invalid folder structure."""
        result_dir, output_dir = temp_dirs
        
        # Mock invalid structure
        mock_handler = Mock()
        mock_handler.validate_structure.return_value = False
        mock_input_handler.return_value = mock_handler
        
        evaluator = D4JFixEvaluator(
            result_folder=result_dir,
            output_dir=output_dir,
            config=mock_config
        )
        
        with pytest.raises(ValueError, match="Invalid result folder"):
            evaluator.evaluate()
    
    @patch('evaluation.core.evaluator.InputHandler')
    @patch('evaluation.core.evaluator.EnvironmentManager')
    @patch('evaluation.core.evaluator.ResultGenerator')
    @patch('evaluation.core.evaluator.StorageManager')
    def test_evaluate_empty_bugs(
        self,
        mock_storage,
        mock_result_gen,
        mock_env_manager,
        mock_input_handler,
        temp_dirs,
        mock_config
    ):
        """Test evaluation with no bugs."""
        result_dir, output_dir = temp_dirs
        
        # Mock empty bug list
        mock_handler = Mock()
        mock_handler.validate_structure.return_value = True
        mock_handler.list_bugs.return_value = []
        mock_input_handler.return_value = mock_handler
        
        # Mock result generator
        mock_gen = Mock()
        mock_gen.generate_batch_result.return_value = Mock(
            total_bugs=0,
            fixed_bugs=0,
            fix_rate=0.0
        )
        mock_result_gen.return_value = mock_gen
        
        evaluator = D4JFixEvaluator(
            result_folder=result_dir,
            output_dir=output_dir,
            config=mock_config
        )
        
        result = evaluator.evaluate()
        
        assert result.total_bugs == 0
        assert result.fixed_bugs == 0
    
    @patch('evaluation.core.evaluator.EnvironmentManager')
    def test_evaluate_bug_deprecated(
        self,
        mock_env_manager_class,
        temp_dirs,
        mock_config
    ):
        """Test evaluation of deprecated bug."""
        result_dir, output_dir = temp_dirs
        
        # Mock deprecated bug
        mock_env = Mock()
        mock_env.is_deprecated.return_value = True
        mock_env_manager_class.return_value = mock_env
        
        evaluator = D4JFixEvaluator(
            result_folder=result_dir,
            output_dir=output_dir,
            config=mock_config
        )
        
        result = evaluator.evaluate_bug("Chart_1")
        
        assert result.bug_slug == "Chart_1"
        assert result.total_attempts == 0
        assert result.successful_attempt is None
        assert "deprecated" in result.failure_reasons[0].lower()
    
    @patch('evaluation.core.evaluator.EnvironmentManager')
    def test_evaluate_bug_checkout_failure(
        self,
        mock_env_manager_class,
        temp_dirs,
        mock_config
    ):
        """Test evaluation when bug checkout fails."""
        result_dir, output_dir = temp_dirs
        
        # Mock checkout failure
        mock_env = Mock()
        mock_env.is_deprecated.return_value = False
        mock_env.checkout_bug.side_effect = Exception("Checkout failed")
        mock_env_manager_class.return_value = mock_env
        
        evaluator = D4JFixEvaluator(
            result_folder=result_dir,
            output_dir=output_dir,
            config=mock_config
        )
        
        result = evaluator.evaluate_bug("Chart_1")
        
        assert result.bug_slug == "Chart_1"
        assert result.successful_attempt is None
        assert "Checkout failed" in result.failure_reasons[0]
    
    @patch('evaluation.core.evaluator.EnvironmentManager')
    @patch('evaluation.core.evaluator.InputHandler')
    def test_evaluate_bug_no_attempts(
        self,
        mock_input_handler_class,
        mock_env_manager_class,
        temp_dirs,
        mock_config
    ):
        """Test evaluation when bug has no attempts."""
        result_dir, output_dir = temp_dirs
        
        # Mock environment manager
        mock_env = Mock()
        mock_env.is_deprecated.return_value = False
        mock_env.checkout_bug.return_value = Path("/tmp/repo")
        mock_env_manager_class.return_value = mock_env
        
        # Mock input handler with no attempts
        mock_handler = Mock()
        mock_handler.list_attempts.return_value = []
        mock_input_handler_class.return_value = mock_handler
        
        evaluator = D4JFixEvaluator(
            result_folder=result_dir,
            output_dir=output_dir,
            config=mock_config
        )
        
        result = evaluator.evaluate_bug("Chart_1")
        
        assert result.bug_slug == "Chart_1"
        assert result.total_attempts == 0
        assert result.successful_attempt is None
    
    def test_try_fix_parse_failure(self, temp_dirs, mock_config):
        """Test fix attempt with parse failure."""
        result_dir, output_dir = temp_dirs
        
        evaluator = D4JFixEvaluator(
            result_folder=result_dir,
            output_dir=output_dir,
            config=mock_config
        )
        
        # Mock input handler
        mock_attempt = Mock(spec=FixAttempt)
        mock_attempt.model_output = "invalid output"
        evaluator.input_handler.load_attempt = Mock(return_value=mock_attempt)
        
        # Mock parser to return parse failure
        mock_parsed = Mock(spec=ParsedPatch)
        mock_parsed.parse_success = False
        mock_parsed.parse_error = "Parse error"
        evaluator.output_parser.parse = Mock(return_value=mock_parsed)
        
        result = evaluator._try_fix("Chart_1", 1, Path("/tmp/repo"))
        
        assert not result.success
        assert "Parse failed" in result.error
    
    def test_try_fix_source_file_not_found(self, temp_dirs, mock_config):
        """Test fix attempt when source file not found."""
        result_dir, output_dir = temp_dirs
        
        evaluator = D4JFixEvaluator(
            result_folder=result_dir,
            output_dir=output_dir,
            config=mock_config
        )
        
        # Mock successful parse
        mock_attempt = Mock(spec=FixAttempt)
        mock_attempt.model_output = "valid output"
        evaluator.input_handler.load_attempt = Mock(return_value=mock_attempt)
        
        mock_parsed = Mock(spec=ParsedPatch)
        mock_parsed.parse_success = True
        evaluator.output_parser.parse = Mock(return_value=mock_parsed)
        
        # Mock source file not found
        evaluator._locate_source_file = Mock(return_value=None)
        
        result = evaluator._try_fix("Chart_1", 1, Path("/tmp/repo"))
        
        assert not result.success
        assert "Source file not found" in result.error
    
    def test_create_skipped_result(self, temp_dirs, mock_config):
        """Test creation of skipped result."""
        result_dir, output_dir = temp_dirs
        
        evaluator = D4JFixEvaluator(
            result_folder=result_dir,
            output_dir=output_dir,
            config=mock_config
        )
        
        result = evaluator._create_skipped_result("Chart_1")
        
        assert result.bug_slug == "Chart_1"
        assert result.total_attempts == 0
        assert result.successful_attempt is None
        assert "deprecated" in result.failure_reasons[0].lower()
    
    def test_create_error_result(self, temp_dirs, mock_config):
        """Test creation of error result."""
        result_dir, output_dir = temp_dirs
        
        evaluator = D4JFixEvaluator(
            result_folder=result_dir,
            output_dir=output_dir,
            config=mock_config
        )
        
        result = evaluator._create_error_result("Chart_1", "Test error")
        
        assert result.bug_slug == "Chart_1"
        assert result.total_attempts == 0
        assert result.successful_attempt is None
        assert "Test error" in result.failure_reasons[0]
    
    def test_evaluate_sequential_empty(self, temp_dirs, mock_config):
        """Test sequential evaluation with empty bug list."""
        result_dir, output_dir = temp_dirs
        
        evaluator = D4JFixEvaluator(
            result_folder=result_dir,
            output_dir=output_dir,
            config=mock_config
        )
        
        results = evaluator._evaluate_sequential([], verbose=False)
        
        assert len(results) == 0
    
    @patch('evaluation.core.evaluator.EnvironmentManager')
    def test_evaluate_sequential_with_bugs(
        self,
        mock_env_manager_class,
        temp_dirs,
        mock_config
    ):
        """Test sequential evaluation with bugs."""
        result_dir, output_dir = temp_dirs
        
        # Mock environment manager
        mock_env = Mock()
        mock_env.is_deprecated.return_value = True
        mock_env_manager_class.return_value = mock_env
        
        evaluator = D4JFixEvaluator(
            result_folder=result_dir,
            output_dir=output_dir,
            config=mock_config
        )
        
        results = evaluator._evaluate_sequential(
            ["Chart_1", "Chart_2"],
            verbose=False
        )
        
        assert len(results) == 2
        assert all(isinstance(r, BugEvaluationResult) for r in results)
    
    def test_evaluate_parallel_not_implemented(self, temp_dirs, mock_config):
        """Test that parallel evaluation raises NotImplementedError."""
        result_dir, output_dir = temp_dirs
        
        evaluator = D4JFixEvaluator(
            result_folder=result_dir,
            output_dir=output_dir,
            config=mock_config
        )
        
        with pytest.raises(NotImplementedError):
            evaluator._evaluate_parallel(["Chart_1"], workers=2)
    
    @patch('evaluation.core.evaluator.InputHandler')
    @patch('evaluation.core.evaluator.EnvironmentManager')
    @patch('evaluation.core.evaluator.ResultGenerator')
    @patch('evaluation.core.evaluator.StorageManager')
    def test_evaluate_with_bug_filter(
        self,
        mock_storage,
        mock_result_gen,
        mock_env_manager,
        mock_input_handler,
        temp_dirs,
        mock_config
    ):
        """Test evaluation with bug filter."""
        result_dir, output_dir = temp_dirs
        
        # Mock bug list
        mock_handler = Mock()
        mock_handler.validate_structure.return_value = True
        mock_handler.list_bugs.return_value = [
            "Chart_1", "Chart_2", "Chart_3"
        ]
        mock_input_handler.return_value = mock_handler
        
        # Mock result generator
        mock_gen = Mock()
        mock_gen.generate_batch_result.return_value = Mock(
            total_bugs=2,
            fixed_bugs=0,
            fix_rate=0.0
        )
        mock_result_gen.return_value = mock_gen
        
        # Mock environment manager
        mock_env = Mock()
        mock_env.is_deprecated.return_value = True
        mock_env_manager.return_value = mock_env
        
        evaluator = D4JFixEvaluator(
            result_folder=result_dir,
            output_dir=output_dir,
            config=mock_config
        )
        
        # Evaluate with filter
        result = evaluator.evaluate(bug_filter=["Chart_1", "Chart_2"])
        
        # Should only evaluate filtered bugs
        assert result.total_bugs == 2


class TestFixResult:
    """Tests for FixResult dataclass."""
    
    def test_fix_result_success(self):
        """Test successful fix result."""
        test_result = TestResult(
            success=True,
            total_tests=10,
            passed_tests=10,
            failed_tests=0
        )
        
        result = FixResult(
            success=True,
            modeling_type="edit",
            test_result=test_result
        )
        
        assert result.success
        assert result.modeling_type == "edit"
        assert result.test_result == test_result
        assert result.error is None
    
    def test_fix_result_failure(self):
        """Test failed fix result."""
        result = FixResult(
            success=False,
            error="Patch application failed"
        )
        
        assert not result.success
        assert result.modeling_type is None
        assert result.test_result is None
        assert result.error == "Patch application failed"
