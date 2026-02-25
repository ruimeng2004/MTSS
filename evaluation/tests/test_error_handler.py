"""错误处理模块测试。"""

import json
import os
import tempfile
import shutil
from pathlib import Path

import pytest

from evaluation.utils.error_handler import (
    RetryableError,
    FatalError,
    retry,
    CheckpointManager,
    ErrorContext,
    safe_execute,
    ErrorCollector,
)


class TestRetry:
    """重试装饰器测试。"""
    
    def test_retry_success(self):
        """测试成功执行（无需重试）。"""
        call_count = [0]
        
        @retry(max_attempts=3)
        def func():
            call_count[0] += 1
            return "success"
        
        result = func()
        assert result == "success"
        assert call_count[0] == 1
    
    def test_retry_eventual_success(self):
        """测试最终成功（需要重试）。"""
        call_count = [0]
        
        @retry(max_attempts=3, delay=0.01)
        def func():
            call_count[0] += 1
            if call_count[0] < 3:
                raise RetryableError("Temporary error")
            return "success"
        
        result = func()
        assert result == "success"
        assert call_count[0] == 3
    
    def test_retry_all_fail(self):
        """测试所有尝试都失败。"""
        call_count = [0]
        
        @retry(max_attempts=3, delay=0.01)
        def func():
            call_count[0] += 1
            raise RetryableError("Persistent error")
        
        with pytest.raises(RetryableError):
            func()
        
        assert call_count[0] == 3
    
    def test_retry_fatal_error(self):
        """测试致命错误（不重试）。"""
        call_count = [0]
        
        @retry(max_attempts=3, delay=0.01)
        def func():
            call_count[0] += 1
            raise FatalError("Fatal error")
        
        with pytest.raises(FatalError):
            func()
        
        assert call_count[0] == 1  # 只调用一次


class TestCheckpointManager:
    """断点管理器测试。"""
    
    def setup_method(self):
        """设置测试环境。"""
        self.temp_dir = tempfile.mkdtemp()
        self.checkpoint_dir = Path(self.temp_dir) / "checkpoints"
    
    def teardown_method(self):
        """清理测试环境。"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_save_and_load_checkpoint(self):
        """测试保存和加载断点。"""
        manager = CheckpointManager(self.checkpoint_dir)
        
        # 保存断点
        state = {
            'progress': 50,
            'completed_items': ['item1', 'item2']
        }
        manager.save_checkpoint('task1', state)
        
        # 加载断点
        loaded_state = manager.load_checkpoint('task1')
        assert loaded_state == state
    
    def test_load_nonexistent_checkpoint(self):
        """测试加载不存在的断点。"""
        manager = CheckpointManager(self.checkpoint_dir)
        
        loaded_state = manager.load_checkpoint('nonexistent')
        assert loaded_state is None
    
    def test_delete_checkpoint(self):
        """测试删除断点。"""
        manager = CheckpointManager(self.checkpoint_dir)
        
        # 保存断点
        manager.save_checkpoint('task1', {'progress': 50})
        
        # 删除断点
        manager.delete_checkpoint('task1')
        
        # 应该无法加载
        loaded_state = manager.load_checkpoint('task1')
        assert loaded_state is None
    
    def test_list_checkpoints(self):
        """测试列出所有断点。"""
        manager = CheckpointManager(self.checkpoint_dir)
        
        # 保存多个断点
        manager.save_checkpoint('task1', {'progress': 50})
        manager.save_checkpoint('task2', {'progress': 75})
        manager.save_checkpoint('task3', {'progress': 100})
        
        # 列出断点
        checkpoints = manager.list_checkpoints()
        assert set(checkpoints) == {'task1', 'task2', 'task3'}
    
    def test_clear_all_checkpoints(self):
        """测试清除所有断点。"""
        manager = CheckpointManager(self.checkpoint_dir)
        
        # 保存多个断点
        manager.save_checkpoint('task1', {'progress': 50})
        manager.save_checkpoint('task2', {'progress': 75})
        
        # 清除所有
        manager.clear_all()
        
        # 应该没有断点
        checkpoints = manager.list_checkpoints()
        assert len(checkpoints) == 0


class TestErrorContext:
    """错误上下文测试。"""
    
    def test_no_error(self):
        """测试无错误情况。"""
        with ErrorContext("test operation") as ctx:
            pass
        
        assert ctx.error is None
        assert ctx.get_error_report() is None
    
    def test_with_error(self):
        """测试有错误情况。"""
        with ErrorContext("test operation", raise_errors=False) as ctx:
            raise ValueError("Test error")
        
        assert ctx.error is not None
        assert isinstance(ctx.error, ValueError)
        
        report = ctx.get_error_report()
        assert report is not None
        assert report['operation'] == "test operation"
        assert report['error_type'] == "ValueError"
    
    def test_raise_errors(self):
        """测试重新抛出错误。"""
        with pytest.raises(ValueError):
            with ErrorContext("test operation", raise_errors=True):
                raise ValueError("Test error")


class TestSafeExecute:
    """安全执行测试。"""
    
    def test_safe_execute_success(self):
        """测试成功执行。"""
        def func(x):
            return x * 2
        
        result = safe_execute(func, 5)
        assert result == 10
    
    def test_safe_execute_with_error(self):
        """测试执行出错。"""
        def func():
            raise ValueError("Error")
        
        result = safe_execute(func, default="default_value")
        assert result == "default_value"
    
    def test_safe_execute_with_kwargs(self):
        """测试带关键字参数的执行。"""
        def func(x, y=10):
            return x + y
        
        result = safe_execute(func, 5, y=20)
        assert result == 25


class TestErrorCollector:
    """错误收集器测试。"""
    
    def setup_method(self):
        """设置测试环境。"""
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """清理测试环境。"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_add_and_get_errors(self):
        """测试添加和获取错误。"""
        collector = ErrorCollector()
        
        # 添加错误
        collector.add_error("operation1", ValueError("Error 1"))
        collector.add_error("operation2", TypeError("Error 2"))
        
        # 检查错误
        assert collector.has_errors()
        assert collector.get_error_count() == 2
        
        errors = collector.get_errors()
        assert len(errors) == 2
        assert errors[0]['operation'] == "operation1"
        assert errors[1]['operation'] == "operation2"
    
    def test_clear_errors(self):
        """测试清除错误。"""
        collector = ErrorCollector()
        
        collector.add_error("operation1", ValueError("Error 1"))
        assert collector.has_errors()
        
        collector.clear()
        assert not collector.has_errors()
        assert collector.get_error_count() == 0
    
    def test_generate_report(self):
        """测试生成报告。"""
        collector = ErrorCollector()
        
        # 无错误时
        report = collector.generate_report()
        assert "No errors" in report
        
        # 有错误时
        collector.add_error("operation1", ValueError("Error 1"))
        report = collector.generate_report()
        assert "operation1" in report
        assert "ValueError" in report
    
    def test_save_report(self):
        """测试保存报告。"""
        collector = ErrorCollector()
        
        collector.add_error("operation1", ValueError("Error 1"))
        collector.add_error("operation2", TypeError("Error 2"))
        
        report_file = Path(self.temp_dir) / "errors.json"
        collector.save_report(report_file)
        
        # 验证文件存在
        assert report_file.exists()
        
        # 验证内容
        with open(report_file, 'r') as f:
            data = json.load(f)
        
        assert len(data) == 2
        assert data[0]['operation'] == "operation1"
