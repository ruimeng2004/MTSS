"""Tests for the CLI module."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from evaluation.cli import main, parse_args, parse_bug_list, validate_args


class TestParseArgs:
    """Tests for argument parsing."""
    
    def test_parse_args_minimal(self):
        """Test parsing with minimal required arguments."""
        args = parse_args(['--result-folder', 'results/'])
        
        assert args.result_folder == 'results/'
        assert args.output == './evaluation_output'
        assert args.workers == 1
        assert args.verbose is False
        assert args.config == 'config.yaml'
        assert args.bugs is None
    
    def test_parse_args_all_options(self):
        """Test parsing with all options."""
        args = parse_args([
            '--result-folder', 'results/',
            '--output', 'output/',
            '--workers', '4',
            '--verbose',
            '--config', 'custom.yaml',
            '--bugs', 'Chart_1,Chart_2',
            '--log-file', 'eval.log'
        ])
        
        assert args.result_folder == 'results/'
        assert args.output == 'output/'
        assert args.workers == 4
        assert args.verbose is True
        assert args.config == 'custom.yaml'
        assert args.bugs == 'Chart_1,Chart_2'
        assert args.log_file == 'eval.log'
    
    def test_parse_args_missing_required(self):
        """Test parsing fails without required arguments."""
        with pytest.raises(SystemExit):
            parse_args([])
    
    def test_parse_args_help(self):
        """Test help flag."""
        with pytest.raises(SystemExit) as exc_info:
            parse_args(['--help'])
        
        # Help should exit with code 0
        assert exc_info.value.code == 0


class TestValidateArgs:
    """Tests for argument validation."""
    
    def test_validate_args_valid(self):
        """Test validation with valid arguments."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create config file
            config_path = Path(tmpdir) / 'config.yaml'
            config_path.write_text('d4j_path: defects4j')
            
            args = Mock()
            args.result_folder = tmpdir
            args.workers = 2
            args.config = str(config_path)
            
            # Should not raise
            validate_args(args)
    
    def test_validate_args_nonexistent_folder(self):
        """Test validation fails with nonexistent folder."""
        args = Mock()
        args.result_folder = '/nonexistent/folder'
        args.workers = 1
        args.config = 'config.yaml'
        
        with pytest.raises(ValueError, match="does not exist"):
            validate_args(args)
    
    def test_validate_args_folder_is_file(self):
        """Test validation fails when folder is a file."""
        with tempfile.NamedTemporaryFile() as tmpfile:
            args = Mock()
            args.result_folder = tmpfile.name
            args.workers = 1
            args.config = 'config.yaml'
            
            with pytest.raises(ValueError, match="not a directory"):
                validate_args(args)
    
    def test_validate_args_invalid_workers(self):
        """Test validation fails with invalid workers count."""
        with tempfile.TemporaryDirectory() as tmpdir:
            args = Mock()
            args.result_folder = tmpdir
            args.workers = 0
            args.config = 'config.yaml'
            
            with pytest.raises(ValueError, match="must be >= 1"):
                validate_args(args)
    
    def test_validate_args_nonexistent_config(self):
        """Test validation fails with nonexistent config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            args = Mock()
            args.result_folder = tmpdir
            args.workers = 1
            args.config = '/nonexistent/config.yaml'
            
            with pytest.raises(ValueError, match="Config file does not exist"):
                validate_args(args)


class TestParseBugList:
    """Tests for bug list parsing."""
    
    def test_parse_bug_list_none(self):
        """Test parsing None returns None."""
        result = parse_bug_list(None)
        assert result is None
    
    def test_parse_bug_list_single(self):
        """Test parsing single bug."""
        result = parse_bug_list('Chart_1')
        assert result == ['Chart_1']
    
    def test_parse_bug_list_multiple(self):
        """Test parsing multiple bugs."""
        result = parse_bug_list('Chart_1,Chart_2,Closure_10')
        assert result == ['Chart_1', 'Chart_2', 'Closure_10']
    
    def test_parse_bug_list_with_spaces(self):
        """Test parsing with spaces."""
        result = parse_bug_list('Chart_1, Chart_2 , Closure_10')
        assert result == ['Chart_1', 'Chart_2', 'Closure_10']
    
    def test_parse_bug_list_empty_string(self):
        """Test parsing empty string returns None."""
        result = parse_bug_list('')
        assert result is None
    
    def test_parse_bug_list_only_commas(self):
        """Test parsing only commas returns None."""
        result = parse_bug_list(',,,')
        assert result is None


class TestMain:
    """Tests for main function."""
    
    @patch('evaluation.cli.D4JFixEvaluator')
    @patch('evaluation.cli.load_config')
    @patch('evaluation.cli.setup_evaluation_logging')
    def test_main_success(
        self,
        mock_setup_logging,
        mock_load_config,
        mock_evaluator_class
    ):
        """Test successful evaluation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create config file
            config_path = Path(tmpdir) / 'config.yaml'
            config_path.write_text('d4j_path: defects4j')
            
            # Mock config
            mock_load_config.return_value = {'d4j_path': 'defects4j'}
            
            # Mock evaluator
            mock_evaluator = Mock()
            mock_batch_result = Mock()
            mock_batch_result.total_bugs = 10
            mock_batch_result.fixed_bugs = 5
            mock_batch_result.failed_bugs = 5
            mock_batch_result.fix_rate = 50.0
            mock_batch_result.statistics = {}
            mock_evaluator.evaluate.return_value = mock_batch_result
            mock_evaluator_class.return_value = mock_evaluator
            
            # Run main
            exit_code = main([
                '--result-folder', tmpdir,
                '--config', str(config_path)
            ])
            
            # Should succeed
            assert exit_code == 0
            mock_evaluator.evaluate.assert_called_once()
    
    @patch('evaluation.cli.D4JFixEvaluator')
    @patch('evaluation.cli.load_config')
    @patch('evaluation.cli.setup_evaluation_logging')
    def test_main_no_fixes(
        self,
        mock_setup_logging,
        mock_load_config,
        mock_evaluator_class
    ):
        """Test evaluation with no fixes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create config file
            config_path = Path(tmpdir) / 'config.yaml'
            config_path.write_text('d4j_path: defects4j')
            
            # Mock config
            mock_load_config.return_value = {'d4j_path': 'defects4j'}
            
            # Mock evaluator with no fixes
            mock_evaluator = Mock()
            mock_batch_result = Mock()
            mock_batch_result.total_bugs = 10
            mock_batch_result.fixed_bugs = 0
            mock_batch_result.failed_bugs = 10
            mock_batch_result.fix_rate = 0.0
            mock_batch_result.statistics = {}
            mock_evaluator.evaluate.return_value = mock_batch_result
            mock_evaluator_class.return_value = mock_evaluator
            
            # Run main
            exit_code = main([
                '--result-folder', tmpdir,
                '--config', str(config_path)
            ])
            
            # Should return 1 (no fixes)
            assert exit_code == 1
    
    @patch('evaluation.cli.setup_evaluation_logging')
    def test_main_invalid_folder(self, mock_setup_logging):
        """Test main with invalid result folder."""
        exit_code = main([
            '--result-folder', '/nonexistent/folder'
        ])
        
        # Should fail
        assert exit_code == 1
    
    @patch('evaluation.cli.load_config')
    @patch('evaluation.cli.setup_evaluation_logging')
    def test_main_config_load_error(
        self,
        mock_setup_logging,
        mock_load_config
    ):
        """Test main with config load error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Mock config load failure
            mock_load_config.side_effect = Exception("Config error")
            
            # Run main
            exit_code = main([
                '--result-folder', tmpdir,
                '--config', 'config.yaml'
            ])
            
            # Should fail
            assert exit_code == 1
    
    @patch('evaluation.cli.D4JFixEvaluator')
    @patch('evaluation.cli.load_config')
    @patch('evaluation.cli.setup_evaluation_logging')
    def test_main_evaluation_error(
        self,
        mock_setup_logging,
        mock_load_config,
        mock_evaluator_class
    ):
        """Test main with evaluation error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create config file
            config_path = Path(tmpdir) / 'config.yaml'
            config_path.write_text('d4j_path: defects4j')
            
            # Mock config
            mock_load_config.return_value = {'d4j_path': 'defects4j'}
            
            # Mock evaluator with error
            mock_evaluator = Mock()
            mock_evaluator.evaluate.side_effect = Exception("Evaluation error")
            mock_evaluator_class.return_value = mock_evaluator
            
            # Run main
            exit_code = main([
                '--result-folder', tmpdir,
                '--config', str(config_path)
            ])
            
            # Should fail
            assert exit_code == 1
    
    @patch('evaluation.cli.D4JFixEvaluator')
    @patch('evaluation.cli.load_config')
    @patch('evaluation.cli.setup_evaluation_logging')
    def test_main_with_bug_filter(
        self,
        mock_setup_logging,
        mock_load_config,
        mock_evaluator_class
    ):
        """Test main with bug filter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create config file
            config_path = Path(tmpdir) / 'config.yaml'
            config_path.write_text('d4j_path: defects4j')
            
            # Mock config
            mock_load_config.return_value = {'d4j_path': 'defects4j'}
            
            # Mock evaluator
            mock_evaluator = Mock()
            mock_batch_result = Mock()
            mock_batch_result.total_bugs = 2
            mock_batch_result.fixed_bugs = 1
            mock_batch_result.failed_bugs = 1
            mock_batch_result.fix_rate = 50.0
            mock_batch_result.statistics = {}
            mock_evaluator.evaluate.return_value = mock_batch_result
            mock_evaluator_class.return_value = mock_evaluator
            
            # Run main with bug filter
            exit_code = main([
                '--result-folder', tmpdir,
                '--config', str(config_path),
                '--bugs', 'Chart_1,Chart_2'
            ])
            
            # Should succeed
            assert exit_code == 0
            
            # Check bug filter was passed
            call_args = mock_evaluator.evaluate.call_args
            assert call_args[1]['bug_filter'] == ['Chart_1', 'Chart_2']
    
    @patch('evaluation.cli.D4JFixEvaluator')
    @patch('evaluation.cli.load_config')
    @patch('evaluation.cli.setup_evaluation_logging')
    def test_main_verbose_mode(
        self,
        mock_setup_logging,
        mock_load_config,
        mock_evaluator_class
    ):
        """Test main with verbose mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create config file
            config_path = Path(tmpdir) / 'config.yaml'
            config_path.write_text('d4j_path: defects4j')
            
            # Mock config
            mock_load_config.return_value = {'d4j_path': 'defects4j'}
            
            # Mock evaluator
            mock_evaluator = Mock()
            mock_batch_result = Mock()
            mock_batch_result.total_bugs = 1
            mock_batch_result.fixed_bugs = 1
            mock_batch_result.failed_bugs = 0
            mock_batch_result.fix_rate = 100.0
            mock_batch_result.statistics = {}
            mock_evaluator.evaluate.return_value = mock_batch_result
            mock_evaluator_class.return_value = mock_evaluator
            
            # Run main with verbose
            exit_code = main([
                '--result-folder', tmpdir,
                '--config', str(config_path),
                '--verbose'
            ])
            
            # Should succeed
            assert exit_code == 0
            
            # Check verbose was passed
            call_args = mock_evaluator.evaluate.call_args
            assert call_args[1]['verbose'] is True
