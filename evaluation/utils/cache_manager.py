"""缓存管理器，用于优化性能。

该模块提供缓存功能，减少重复计算和文件 I/O 操作。
"""

import hashlib
import json
import logging
import pickle
from pathlib import Path
from typing import Any, Callable, Dict, Optional
from functools import wraps

logger = logging.getLogger(__name__)


class CacheManager:
    """管理缓存数据以提高性能。
    
    提供内存缓存和磁盘缓存功能，用于存储计算结果和文件内容。
    
    Attributes:
        cache_dir: 缓存目录路径。
        memory_cache: 内存缓存字典。
        max_memory_items: 内存缓存最大项数。
        enabled: 是否启用缓存。
    """
    
    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        max_memory_items: int = 1000,
        enabled: bool = True
    ):
        """初始化缓存管理器。
        
        Args:
            cache_dir: 缓存目录路径。如果为 None，则只使用内存缓存。
            max_memory_items: 内存缓存最大项数。
            enabled: 是否启用缓存。
        """
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.memory_cache: Dict[str, Any] = {}
        self.max_memory_items = max_memory_items
        self.enabled = enabled
        
        if self.cache_dir and self.enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Cache directory: {self.cache_dir}")
    
    def _generate_key(self, *args, **kwargs) -> str:
        """生成缓存键。
        
        Args:
            *args: 位置参数。
            **kwargs: 关键字参数。
        
        Returns:
            缓存键的哈希值。
        """
        # 将参数转换为字符串并生成哈希
        key_data = f"{args}_{sorted(kwargs.items())}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """从缓存获取数据。
        
        首先尝试从内存缓存获取，如果不存在则尝试从磁盘缓存获取。
        
        Args:
            key: 缓存键。
        
        Returns:
            缓存的数据，如果不存在则返回 None。
        """
        if not self.enabled:
            return None
        
        # 尝试从内存缓存获取
        if key in self.memory_cache:
            logger.debug(f"Memory cache hit: {key}")
            return self.memory_cache[key]
        
        # 尝试从磁盘缓存获取
        if self.cache_dir:
            cache_file = self.cache_dir / f"{key}.pkl"
            if cache_file.exists():
                try:
                    with open(cache_file, 'rb') as f:
                        data = pickle.load(f)
                    logger.debug(f"Disk cache hit: {key}")
                    
                    # 加载到内存缓存
                    self._add_to_memory_cache(key, data)
                    return data
                except Exception as e:
                    logger.warning(f"Failed to load cache {key}: {e}")
        
        return None
    
    def set(self, key: str, value: Any, disk: bool = False):
        """设置缓存数据。
        
        Args:
            key: 缓存键。
            value: 要缓存的数据。
            disk: 是否同时保存到磁盘缓存。
        """
        if not self.enabled:
            return
        
        # 添加到内存缓存
        self._add_to_memory_cache(key, value)
        
        # 如果需要，保存到磁盘缓存
        if disk and self.cache_dir:
            cache_file = self.cache_dir / f"{key}.pkl"
            try:
                with open(cache_file, 'wb') as f:
                    pickle.dump(value, f)
                logger.debug(f"Saved to disk cache: {key}")
            except Exception as e:
                logger.warning(f"Failed to save cache {key}: {e}")
    
    def _add_to_memory_cache(self, key: str, value: Any):
        """添加数据到内存缓存。
        
        如果缓存已满，删除最旧的项。
        
        Args:
            key: 缓存键。
            value: 要缓存的数据。
        """
        # 如果缓存已满，删除第一个项（FIFO）
        if len(self.memory_cache) >= self.max_memory_items:
            first_key = next(iter(self.memory_cache))
            del self.memory_cache[first_key]
            logger.debug(f"Evicted from memory cache: {first_key}")
        
        self.memory_cache[key] = value
    
    def clear(self, memory: bool = True, disk: bool = False):
        """清除缓存。
        
        Args:
            memory: 是否清除内存缓存。
            disk: 是否清除磁盘缓存。
        """
        if memory:
            self.memory_cache.clear()
            logger.info("Memory cache cleared")
        
        if disk and self.cache_dir:
            for cache_file in self.cache_dir.glob("*.pkl"):
                cache_file.unlink()
            logger.info("Disk cache cleared")
    
    def cached(
        self,
        disk: bool = False,
        key_func: Optional[Callable] = None
    ):
        """装饰器：缓存函数结果。
        
        Args:
            disk: 是否使用磁盘缓存。
            key_func: 自定义键生成函数。
        
        Returns:
            装饰器函数。
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                if not self.enabled:
                    return func(*args, **kwargs)
                
                # 生成缓存键
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    cache_key = self._generate_key(
                        func.__name__,
                        *args,
                        **kwargs
                    )
                
                # 尝试从缓存获取
                cached_result = self.get(cache_key)
                if cached_result is not None:
                    return cached_result
                
                # 执行函数
                result = func(*args, **kwargs)
                
                # 保存到缓存
                self.set(cache_key, result, disk=disk)
                
                return result
            
            return wrapper
        return decorator
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息。
        
        Returns:
            包含缓存统计信息的字典。
        """
        stats = {
            'enabled': self.enabled,
            'memory_items': len(self.memory_cache),
            'max_memory_items': self.max_memory_items,
            'memory_usage_percent': (
                len(self.memory_cache) / self.max_memory_items * 100
                if self.max_memory_items > 0 else 0
            )
        }
        
        if self.cache_dir:
            disk_files = list(self.cache_dir.glob("*.pkl"))
            stats['disk_items'] = len(disk_files)
            stats['disk_size_bytes'] = sum(
                f.stat().st_size for f in disk_files
            )
        
        return stats


class FileCache:
    """文件内容缓存，优化文件 I/O。
    
    缓存文件内容，避免重复读取相同文件。
    """
    
    def __init__(self, max_size: int = 100):
        """初始化文件缓存。
        
        Args:
            max_size: 最大缓存文件数。
        """
        self.cache: Dict[str, str] = {}
        self.max_size = max_size
    
    def read_file(self, filepath: Path) -> str:
        """读取文件内容（带缓存）。
        
        Args:
            filepath: 文件路径。
        
        Returns:
            文件内容。
        """
        filepath_str = str(filepath)
        
        # 检查缓存
        if filepath_str in self.cache:
            logger.debug(f"File cache hit: {filepath}")
            return self.cache[filepath_str]
        
        # 读取文件
        try:
            content = filepath.read_text()
            
            # 添加到缓存
            if len(self.cache) >= self.max_size:
                # 删除第一个项
                first_key = next(iter(self.cache))
                del self.cache[first_key]
            
            self.cache[filepath_str] = content
            logger.debug(f"File cached: {filepath}")
            
            return content
        except Exception as e:
            logger.error(f"Failed to read file {filepath}: {e}")
            raise
    
    def clear(self):
        """清除文件缓存。"""
        self.cache.clear()
        logger.info("File cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息。
        
        Returns:
            包含缓存统计信息的字典。
        """
        return {
            'cached_files': len(self.cache),
            'max_size': self.max_size,
            'usage_percent': (
                len(self.cache) / self.max_size * 100
                if self.max_size > 0 else 0
            )
        }


# 全局缓存实例
_global_cache: Optional[CacheManager] = None
_global_file_cache: Optional[FileCache] = None


def get_cache() -> CacheManager:
    """获取全局缓存管理器实例。
    
    Returns:
        全局缓存管理器。
    """
    global _global_cache
    if _global_cache is None:
        _global_cache = CacheManager()
    return _global_cache


def get_file_cache() -> FileCache:
    """获取全局文件缓存实例。
    
    Returns:
        全局文件缓存。
    """
    global _global_file_cache
    if _global_file_cache is None:
        _global_file_cache = FileCache()
    return _global_file_cache


def init_cache(
    cache_dir: Optional[Path] = None,
    max_memory_items: int = 1000,
    enabled: bool = True
):
    """初始化全局缓存。
    
    Args:
        cache_dir: 缓存目录路径。
        max_memory_items: 内存缓存最大项数。
        enabled: 是否启用缓存。
    """
    global _global_cache
    _global_cache = CacheManager(
        cache_dir=cache_dir,
        max_memory_items=max_memory_items,
        enabled=enabled
    )
    logger.info("Global cache initialized")
