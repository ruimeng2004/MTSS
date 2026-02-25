"""缓存管理器测试。"""

import os
import tempfile
import shutil
from pathlib import Path

import pytest

from evaluation.utils.cache_manager import (
    CacheManager,
    FileCache,
    get_cache,
    get_file_cache,
    init_cache,
)


class TestCacheManager:
    """缓存管理器测试。"""
    
    def setup_method(self):
        """设置测试环境。"""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_dir = Path(self.temp_dir) / "cache"
    
    def teardown_method(self):
        """清理测试环境。"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_memory_cache(self):
        """测试内存缓存。"""
        cache = CacheManager()
        
        # 设置缓存
        cache.set("key1", "value1")
        cache.set("key2", {"data": "value2"})
        
        # 获取缓存
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == {"data": "value2"}
        assert cache.get("nonexistent") is None
    
    def test_disk_cache(self):
        """测试磁盘缓存。"""
        cache = CacheManager(cache_dir=self.cache_dir)
        
        # 设置磁盘缓存
        cache.set("key1", "value1", disk=True)
        
        # 清除内存缓存
        cache.memory_cache.clear()
        
        # 应该能从磁盘加载
        assert cache.get("key1") == "value1"
    
    def test_cache_eviction(self):
        """测试缓存淘汰。"""
        cache = CacheManager(max_memory_items=3)
        
        # 添加 4 个项
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        cache.set("key4", "value4")
        
        # 第一个项应该被淘汰
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"
    
    def test_cache_decorator(self):
        """测试缓存装饰器。"""
        cache = CacheManager()
        call_count = [0]
        
        @cache.cached()
        def expensive_function(x):
            call_count[0] += 1
            return x * 2
        
        # 第一次调用
        result1 = expensive_function(5)
        assert result1 == 10
        assert call_count[0] == 1
        
        # 第二次调用（应该使用缓存）
        result2 = expensive_function(5)
        assert result2 == 10
        assert call_count[0] == 1  # 没有增加
        
        # 不同参数
        result3 = expensive_function(10)
        assert result3 == 20
        assert call_count[0] == 2
    
    def test_cache_disabled(self):
        """测试禁用缓存。"""
        cache = CacheManager(enabled=False)
        
        cache.set("key1", "value1")
        assert cache.get("key1") is None
    
    def test_clear_cache(self):
        """测试清除缓存。"""
        cache = CacheManager(cache_dir=self.cache_dir)
        
        # 添加缓存
        cache.set("key1", "value1")
        cache.set("key2", "value2", disk=True)
        
        # 清除内存缓存
        cache.clear(memory=True, disk=False)
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"  # 从磁盘加载
        
        # 清除磁盘缓存
        cache.clear(memory=False, disk=True)
        cache.memory_cache.clear()
        assert cache.get("key2") is None
    
    def test_cache_stats(self):
        """测试缓存统计。"""
        cache = CacheManager(
            cache_dir=self.cache_dir,
            max_memory_items=10
        )
        
        # 添加一些缓存
        cache.set("key1", "value1")
        cache.set("key2", "value2", disk=True)
        
        stats = cache.get_stats()
        assert stats['enabled'] is True
        assert stats['memory_items'] == 2
        assert stats['max_memory_items'] == 10
        assert stats['disk_items'] == 1


class TestFileCache:
    """文件缓存测试。"""
    
    def setup_method(self):
        """设置测试环境。"""
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """清理测试环境。"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_file_cache(self):
        """测试文件缓存。"""
        cache = FileCache()
        
        # 创建测试文件
        test_file = Path(self.temp_dir) / "test.txt"
        test_file.write_text("test content")
        
        # 第一次读取
        content1 = cache.read_file(test_file)
        assert content1 == "test content"
        
        # 修改文件
        test_file.write_text("modified content")
        
        # 第二次读取（应该返回缓存的内容）
        content2 = cache.read_file(test_file)
        assert content2 == "test content"  # 仍然是旧内容
        
        # 清除缓存后再读取
        cache.clear()
        content3 = cache.read_file(test_file)
        assert content3 == "modified content"
    
    def test_file_cache_eviction(self):
        """测试文件缓存淘汰。"""
        cache = FileCache(max_size=2)
        
        # 创建 3 个文件
        file1 = Path(self.temp_dir) / "file1.txt"
        file2 = Path(self.temp_dir) / "file2.txt"
        file3 = Path(self.temp_dir) / "file3.txt"
        
        file1.write_text("content1")
        file2.write_text("content2")
        file3.write_text("content3")
        
        # 读取 3 个文件
        cache.read_file(file1)
        cache.read_file(file2)
        cache.read_file(file3)
        
        # 缓存应该只有 2 个文件
        stats = cache.get_stats()
        assert stats['cached_files'] == 2
    
    def test_file_cache_stats(self):
        """测试文件缓存统计。"""
        cache = FileCache(max_size=10)
        
        # 创建并读取文件
        test_file = Path(self.temp_dir) / "test.txt"
        test_file.write_text("test content")
        cache.read_file(test_file)
        
        stats = cache.get_stats()
        assert stats['cached_files'] == 1
        assert stats['max_size'] == 10
        assert stats['usage_percent'] == 10.0


class TestGlobalCache:
    """全局缓存测试。"""
    
    def test_get_cache(self):
        """测试获取全局缓存。"""
        cache1 = get_cache()
        cache2 = get_cache()
        
        # 应该返回同一个实例
        assert cache1 is cache2
    
    def test_get_file_cache(self):
        """测试获取全局文件缓存。"""
        cache1 = get_file_cache()
        cache2 = get_file_cache()
        
        # 应该返回同一个实例
        assert cache1 is cache2
    
    def test_init_cache(self):
        """测试初始化全局缓存。"""
        temp_dir = tempfile.mkdtemp()
        
        try:
            cache_dir = Path(temp_dir) / "cache"
            init_cache(cache_dir=cache_dir, max_memory_items=500)
            
            cache = get_cache()
            assert cache.cache_dir == cache_dir
            assert cache.max_memory_items == 500
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
