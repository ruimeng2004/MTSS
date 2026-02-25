"""性能测试。

测试系统在不同负载下的性能表现。
注意：这些测试主要测试解析和基本操作的性能，不涉及复杂的数据结构。
"""

import json
import os
import tempfile
import shutil
import time

import pytest

from evaluation.core import (
    OutputParser,
    StorageManager,
)


class TestParserPerformance:
    """解析器性能测试。"""
    
    def test_single_parse_performance(self):
        """测试单个补丁解析性能。"""
        parser = OutputParser()
        
        llm_output = """
<<<<<<< SEARCH
public int calculate(int x) {
    return x * 2;
}
=======
public int calculate(int x) {
    return x * 3;
}
>>>>>>> REPLACE
"""
        
        start_time = time.time()
        parsed = parser.parse(llm_output, "Test_1", 0)
        elapsed = time.time() - start_time
        
        # 单个解析应该在 0.1 秒内完成
        assert elapsed < 0.1
        assert parsed is not None
        print(f"\n单次解析耗时: {elapsed*1000:.2f}ms")
    
    def test_batch_parse_performance(self):
        """测试批量补丁解析性能。"""
        parser = OutputParser()
        
        llm_output = """
<<<<<<< SEARCH
public int add(int a, int b) {
    return a + b;
}
=======
public int add(int a, int b) {
    return a + b + 1;
}
>>>>>>> REPLACE
"""
        
        num_iterations = 100
        start_time = time.time()
        
        for i in range(num_iterations):
            parsed = parser.parse(llm_output, f"Test_{i}", 0)
            assert parsed is not None
        
        elapsed = time.time() - start_time
        avg_time = elapsed / num_iterations
        
        # 平均每个解析应该在 0.01 秒内完成
        assert avg_time < 0.01
        print(f"\n批量解析性能: {num_iterations} 次解析耗时 {elapsed:.3f}秒, "
              f"平均 {avg_time*1000:.2f}ms/次")
    
    def test_large_patch_parsing(self):
        """测试大型补丁解析性能。"""
        parser = OutputParser()
        
        # 创建一个大型补丁
        search_lines = []
        replace_lines = []
        for i in range(100):
            search_lines.append(f"    int var{i} = {i};")
            replace_lines.append(f"    int var{i} = {i+1};")
        
        llm_output = f"""
<<<<<<< SEARCH
{chr(10).join(search_lines)}
=======
{chr(10).join(replace_lines)}
>>>>>>> REPLACE
"""
        
        start_time = time.time()
        parsed = parser.parse(llm_output, "Test_Large", 0)
        elapsed = time.time() - start_time
        
        # 大型补丁解析应该在 0.5 秒内完成
        assert elapsed < 0.5
        assert parsed is not None
        print(f"\n大型补丁解析耗时: {elapsed*1000:.2f}ms")
    
    def test_memory_usage(self):
        """测试解析器内存使用。"""
        import sys
        
        parser = OutputParser()
        
        # 获取初始内存使用
        initial_size = sys.getsizeof(parser)
        
        # 解析多个补丁
        for i in range(100):
            llm_output = f"""
<<<<<<< SEARCH
public int method{i}() {{
    return {i};
}}
=======
public int method{i}() {{
    return {i+1};
}}
>>>>>>> REPLACE
"""
            parsed = parser.parse(llm_output, f"Test_{i}", 0)
        
        # 检查解析器对象大小没有显著增长
        final_size = sys.getsizeof(parser)
        size_increase = final_size - initial_size
        
        # 对象大小增长应该小于 1KB
        assert size_increase < 1024
        
        print(f"\n解析器内存使用: 初始 {initial_size} 字节, "
              f"最终 {final_size} 字节, 增长 {size_increase} 字节")


class TestStoragePerformance:
    """存储性能测试。"""
    
    def setup_method(self):
        """设置测试环境。"""
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """清理测试环境。"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_log_write_performance(self):
        """测试日志写入性能。"""
        output_folder = os.path.join(self.temp_dir, "output")
        storage = StorageManager(output_folder)
        
        num_logs = 100
        start_time = time.time()
        
        for i in range(num_logs):
            storage.log(f"Test message {i}", level="INFO")
        
        elapsed = time.time() - start_time
        avg_time = elapsed / num_logs
        
        # 平均每次日志写入应该在 0.01 秒内完成
        assert avg_time < 0.01
        
        print(f"\n日志写入性能: {num_logs} 次写入耗时 {elapsed:.3f}秒, "
              f"平均 {avg_time*1000:.2f}ms/次")
    
    def test_file_creation_performance(self):
        """测试文件创建性能。"""
        from evaluation.core.data_structures import NormalizedPatch
        
        output_folder = os.path.join(self.temp_dir, "output")
        storage = StorageManager(output_folder)
        
        num_files = 50
        start_time = time.time()
        
        for i in range(num_files):
            patch_content = f"--- a/file{i}.java\n+++ b/file{i}.java\n@@ -1,1 +1,1 @@\n"
            patch = NormalizedPatch(
                bug_slug=f"Bug_{i}",
                attempt_num=0,
                modeling_type="edit",
                diff_content=patch_content
            )
            storage.save_normalized_patch(patch, filename=f"bug_{i}.patch")
        
        elapsed = time.time() - start_time
        avg_time = elapsed / num_files
        
        # 平均每次文件创建应该在 0.02 秒内完成
        assert avg_time < 0.02
        
        print(f"\n文件创建性能: {num_files} 个文件耗时 {elapsed:.3f}秒, "
              f"平均 {avg_time*1000:.2f}ms/次")
    
    def test_disk_space_usage(self):
        """测试磁盘空间使用。"""
        output_folder = os.path.join(self.temp_dir, "output")
        storage = StorageManager(output_folder)
        
        # 写入一些数据
        for i in range(10):
            storage.log("Test message" * 100, level="INFO")
        
        # 计算使用的磁盘空间
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(output_folder):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                total_size += os.path.getsize(filepath)
        
        # 10 个日志文件应该小于 100KB
        assert total_size < 100 * 1024
        
        print(f"\n磁盘空间使用: {total_size} 字节 ({total_size/1024:.2f} KB)")


class TestScalability:
    """可扩展性测试。"""
    
    def setup_method(self):
        """设置测试环境。"""
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """清理测试环境。"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_concurrent_parsing(self):
        """测试并发解析能力。"""
        parser = OutputParser()
        
        num_parses = 200
        start_time = time.time()
        
        for i in range(num_parses):
            llm_output = f"""
<<<<<<< SEARCH
int x = {i};
=======
int x = {i+1};
>>>>>>> REPLACE
"""
            parsed = parser.parse(llm_output, f"Test_{i}", 0)
            assert parsed is not None
        
        elapsed = time.time() - start_time
        
        # 200 次解析应该在 2 秒内完成
        assert elapsed < 2.0
        
        print(f"\n并发解析: {num_parses} 次解析耗时 {elapsed:.3f}秒")
    
    def test_large_scale_storage(self):
        """测试大规模存储操作。"""
        from evaluation.core.data_structures import NormalizedPatch
        
        output_folder = os.path.join(self.temp_dir, "output")
        storage = StorageManager(output_folder)
        
        num_operations = 100
        start_time = time.time()
        
        for i in range(num_operations):
            # 写入日志
            storage.log(f"Message {i}", level="INFO")
            
            # 保存补丁
            if i % 2 == 0:
                patch_content = f"--- a/file{i}.java\n+++ b/file{i}.java\n"
                patch = NormalizedPatch(
                    bug_slug=f"Bug_{i}",
                    attempt_num=0,
                    modeling_type="edit",
                    diff_content=patch_content
                )
                storage.save_normalized_patch(patch, filename=f"bug_{i}.patch")
        
        elapsed = time.time() - start_time
        
        # 100 次操作应该在 2 秒内完成
        assert elapsed < 2.0
        
        print(f"\n大规模存储: {num_operations} 次操作耗时 {elapsed:.3f}秒")


@pytest.mark.slow
class TestStressTest:
    """压力测试（标记为 slow，使用 -m slow 运行）。"""
    
    def test_extreme_parsing_load(self):
        """测试极限解析负载。"""
        parser = OutputParser()
        
        num_parses = 1000
        start_time = time.time()
        
        for i in range(num_parses):
            llm_output = f"""
<<<<<<< SEARCH
public void method{i}() {{
    System.out.println("{i}");
}}
=======
public void method{i}() {{
    System.out.println("{i+1}");
}}
>>>>>>> REPLACE
"""
            parsed = parser.parse(llm_output, f"Test_{i}", 0)
            assert parsed is not None
        
        elapsed = time.time() - start_time
        
        # 1000 次解析应该在 10 秒内完成
        assert elapsed < 10.0
        
        print(f"\n极限解析: {num_parses} 次解析耗时 {elapsed:.3f}秒")


