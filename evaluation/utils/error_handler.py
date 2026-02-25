"""错误处理和恢复机制。

提供统一的错误处理、重试机制和断点续传功能。
"""

import json
import logging
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type
from functools import wraps

logger = logging.getLogger(__name__)


class RetryableError(Exception):
    """可重试的错误。"""
    pass


class FatalError(Exception):
    """致命错误，不应重试。"""
    pass


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
    fatal_exceptions: tuple = (FatalError,)
):
    """重试装饰器。
    
    Args:
        max_attempts: 最大尝试次数。
        delay: 初始延迟时间（秒）。
        backoff: 延迟时间的倍增因子。
        exceptions: 需要重试的异常类型。
        fatal_exceptions: 致命异常，不应重试。
    
    Returns:
        装饰器函数。
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except fatal_exceptions as e:
                    logger.error(
                        f"Fatal error in {func.__name__}: {e}"
                    )
                    raise
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts:
                        logger.warning(
                            f"Attempt {attempt}/{max_attempts} failed for "
                            f"{func.__name__}: {e}. Retrying in "
                            f"{current_delay}s..."
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for "
                            f"{func.__name__}"
                        )
            
            # 所有尝试都失败
            raise last_exception
        
        return wrapper
    return decorator


class CheckpointManager:
    """断点续传管理器。
    
    保存和恢复执行进度，支持从中断点继续执行。
    """
    
    def __init__(self, checkpoint_dir: Path):
        """初始化断点管理器。
        
        Args:
            checkpoint_dir: 断点文件保存目录。
        """
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Checkpoint directory: {self.checkpoint_dir}")
    
    def save_checkpoint(
        self,
        task_id: str,
        state: Dict[str, Any]
    ):
        """保存断点。
        
        Args:
            task_id: 任务标识符。
            state: 任务状态字典。
        """
        checkpoint_file = self.checkpoint_dir / f"{task_id}.json"
        
        try:
            with open(checkpoint_file, 'w') as f:
                json.dump(state, f, indent=2)
            logger.debug(f"Checkpoint saved: {task_id}")
        except Exception as e:
            logger.error(f"Failed to save checkpoint {task_id}: {e}")
    
    def load_checkpoint(
        self,
        task_id: str
    ) -> Optional[Dict[str, Any]]:
        """加载断点。
        
        Args:
            task_id: 任务标识符。
        
        Returns:
            任务状态字典，如果不存在则返回 None。
        """
        checkpoint_file = self.checkpoint_dir / f"{task_id}.json"
        
        if not checkpoint_file.exists():
            return None
        
        try:
            with open(checkpoint_file, 'r') as f:
                state = json.load(f)
            logger.info(f"Checkpoint loaded: {task_id}")
            return state
        except Exception as e:
            logger.error(f"Failed to load checkpoint {task_id}: {e}")
            return None
    
    def delete_checkpoint(self, task_id: str):
        """删除断点。
        
        Args:
            task_id: 任务标识符。
        """
        checkpoint_file = self.checkpoint_dir / f"{task_id}.json"
        
        if checkpoint_file.exists():
            try:
                checkpoint_file.unlink()
                logger.debug(f"Checkpoint deleted: {task_id}")
            except Exception as e:
                logger.error(f"Failed to delete checkpoint {task_id}: {e}")
    
    def list_checkpoints(self) -> List[str]:
        """列出所有断点。
        
        Returns:
            任务标识符列表。
        """
        checkpoints = []
        for checkpoint_file in self.checkpoint_dir.glob("*.json"):
            checkpoints.append(checkpoint_file.stem)
        return sorted(checkpoints)
    
    def clear_all(self):
        """清除所有断点。"""
        for checkpoint_file in self.checkpoint_dir.glob("*.json"):
            checkpoint_file.unlink()
        logger.info("All checkpoints cleared")


class ErrorContext:
    """错误上下文管理器。
    
    捕获和记录错误信息，提供详细的错误报告。
    """
    
    def __init__(
        self,
        operation: str,
        log_errors: bool = True,
        raise_errors: bool = True
    ):
        """初始化错误上下文。
        
        Args:
            operation: 操作描述。
            log_errors: 是否记录错误。
            raise_errors: 是否重新抛出错误。
        """
        self.operation = operation
        self.log_errors = log_errors
        self.raise_errors = raise_errors
        self.error: Optional[Exception] = None
        self.error_details: Dict[str, Any] = {}
    
    def __enter__(self):
        """进入上下文。"""
        logger.debug(f"Starting operation: {self.operation}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文。"""
        if exc_type is not None:
            self.error = exc_val
            self.error_details = {
                'operation': self.operation,
                'error_type': exc_type.__name__,
                'error_message': str(exc_val),
                'traceback': exc_tb
            }
            
            if self.log_errors:
                logger.error(
                    f"Error in {self.operation}: "
                    f"{exc_type.__name__}: {exc_val}"
                )
            
            # 如果不重新抛出错误，返回 True 抑制异常
            return not self.raise_errors
        
        logger.debug(f"Completed operation: {self.operation}")
        return False
    
    def get_error_report(self) -> Optional[Dict[str, Any]]:
        """获取错误报告。
        
        Returns:
            错误详情字典，如果没有错误则返回 None。
        """
        if self.error is None:
            return None
        return self.error_details


def safe_execute(
    func: Callable,
    *args,
    default: Any = None,
    log_errors: bool = True,
    **kwargs
) -> Any:
    """安全执行函数。
    
    捕获异常并返回默认值，而不是让程序崩溃。
    
    Args:
        func: 要执行的函数。
        *args: 函数参数。
        default: 发生错误时的默认返回值。
        log_errors: 是否记录错误。
        **kwargs: 函数关键字参数。
    
    Returns:
        函数返回值或默认值。
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if log_errors:
            logger.error(f"Error executing {func.__name__}: {e}")
        return default


class ErrorCollector:
    """错误收集器。
    
    收集执行过程中的所有错误，用于批量处理和报告。
    """
    
    def __init__(self):
        """初始化错误收集器。"""
        self.errors: List[Dict[str, Any]] = []
    
    def add_error(
        self,
        operation: str,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ):
        """添加错误。
        
        Args:
            operation: 操作描述。
            error: 异常对象。
            context: 额外的上下文信息。
        """
        error_info = {
            'operation': operation,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context or {}
        }
        self.errors.append(error_info)
        logger.warning(f"Error collected: {operation} - {error}")
    
    def has_errors(self) -> bool:
        """检查是否有错误。
        
        Returns:
            如果有错误返回 True。
        """
        return len(self.errors) > 0
    
    def get_error_count(self) -> int:
        """获取错误数量。
        
        Returns:
            错误数量。
        """
        return len(self.errors)
    
    def get_errors(self) -> List[Dict[str, Any]]:
        """获取所有错误。
        
        Returns:
            错误列表。
        """
        return self.errors.copy()
    
    def clear(self):
        """清除所有错误。"""
        self.errors.clear()
    
    def generate_report(self) -> str:
        """生成错误报告。
        
        Returns:
            格式化的错误报告字符串。
        """
        if not self.errors:
            return "No errors collected."
        
        report = [f"Collected {len(self.errors)} errors:\n"]
        
        for i, error in enumerate(self.errors, 1):
            report.append(f"{i}. {error['operation']}")
            report.append(f"   Type: {error['error_type']}")
            report.append(f"   Message: {error['error_message']}")
            if error['context']:
                report.append(f"   Context: {error['context']}")
            report.append("")
        
        return "\n".join(report)
    
    def save_report(self, filepath: Path):
        """保存错误报告到文件。
        
        Args:
            filepath: 报告文件路径。
        """
        try:
            with open(filepath, 'w') as f:
                json.dump(self.errors, f, indent=2)
            logger.info(f"Error report saved: {filepath}")
        except Exception as e:
            logger.error(f"Failed to save error report: {e}")
