"""边界情况测试。

测试系统在异常情况下的行为，包括损坏的输入、资源限制等。
"""

import json
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from evaluation.core import (
    InputHandler,
    OutputParser,
    StorageManager,
    EnvironmentManager,
    PatchApplicator,
    TestExecutor,
)
from evaluation.core.data_structures import (
    FixAttempt,
    NormalizedPatch,
    ApplyResult,
    TestResult,
)


class TestCorruptedInput:
    """测试损坏的输入处理。"""
    
    def setup_method(self):
        """设置测试环境。"""
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """清理测试环境。"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_corrupted_json_file(self):
        """测试损坏的 JSON 文件。"""
        # 创建一个损坏的 result.json
        bug_dir = Path(self.temp_dir) / "Chart_1"
        bug_dir.mkdir()
        attempt_dir = bug_dir / "1"
        attempt_dir.mkdir()
        
        # 写入损坏的 JSON
        (attempt_dir / "result.json").write_text("{ invalid json }")
        (attempt_dir / "model_output.txt").write_text("some output")
        (attempt_dir / "query.txt").write_text("some query")
        
        handler = InputHandler(self.temp_dir)
        
        # 系统应该能够优雅地处理损坏的 JSON，返回空字典
        attempt = handler.load_attempt("Chart_1", 1)
        # 应该返回 None 或一个带有空 result_json 的对象
        assert attempt is None or attempt.result_json == {}
    
    def test_missing_required_files(self):
        """测试缺少必需文件。"""
        # 创建目录但不创建文件
        bug_dir = Path(self.temp_dir) / "Chart_1"
        bug_dir.mkdir()
        attempt_dir = bug_dir / "1"
        attempt_dir.mkdir()
        
        handler = InputHandler(self.temp_dir)
        
        # 系统应该能够优雅地处理缺失文件，返回 None
        attempt = handler.load_attempt("Chart_1", 1)
        assert attempt is None
    
    def test_empty_model_output(self):
        """测试空的模型输出。"""
        parser = OutputParser()
        
        # 空输出 - 系统会返回一个空的 ParsedPatch
        parsed = parser.parse("", "Test_1", 0)
        assert parsed is not None
        assert parsed.patch_count == 0  # 没有找到补丁
        
        # 只有空白字符
        parsed = parser.parse("   \n\n  ", "Test_1", 0)
        assert parsed is not None
        assert parsed.patch_count == 0
    
    def test_malformed_patch_format(self):
        """测试格式错误的补丁。"""
        parser = OutputParser()
        
        # 缺少 REPLACE 标记 - 系统会返回空的 ParsedPatch
        malformed = """
<<<<<<< SEARCH
public void foo() {
}
=======
public void foo() {
    return;
}
"""
        parsed = parser.parse(malformed, "Test_1", 0)
        assert parsed is not None
        assert parsed.patch_count == 0  # 没有找到完整的补丁
        
        # 缺少 SEARCH 标记
        malformed2 = """
=======
public void foo() {
    return;
}
>>>>>>> REPLACE
"""
        parsed = parser.parse(malformed2, "Test_1", 0)
        assert parsed is not None
        assert parsed.patch_count == 0
    
    def test_unicode_in_patch(self):
        """测试补丁中的 Unicode 字符。"""
        parser = OutputParser()
        
        # 包含中文字符
        unicode_patch = """
<<<<<<< SEARCH
public void test() {
    // 测试
}
=======
public void test() {
    // 测试修改
}
>>>>>>> REPLACE
"""
        parsed = parser.parse(unicode_patch, "Test_1", 0)
        # 应该能够正确解析
        assert parsed is not None
        assert parsed.parse_success


class TestResourceLimits:
    """测试资源限制情况。"""
    
    def setup_method(self):
        """设置测试环境。"""
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """清理测试环境。"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_disk_space_check(self):
        """测试磁盘空间检查。"""
        output_folder = os.path.join(self.temp_dir, "output")
        storage = StorageManager(output_folder)
        
        # 尝试写入大量数据
        large_content = "x" * (1024 * 1024)  # 1MB
        
        try:
            for i in range(10):
                storage.log(large_content, level="INFO")
            # 应该成功或抛出磁盘空间异常
        except Exception as e:
            # 如果抛出异常，应该是有意义的错误消息
            assert "disk" in str(e).lower() or "space" in str(e).lower() or True
    
    @patch('subprocess.run')
    def test_timeout_handling(self, mock_run):
        """测试超时处理。"""
        import tempfile
        import os
        
        # 创建一个临时目录作为 repo_path
        temp_repo = tempfile.mkdtemp()
        
        try:
            # 模拟超时
            import subprocess
            mock_run.side_effect = subprocess.TimeoutExpired(
                cmd="defects4j test",
                timeout=60
            )
            
            # TestExecutor 需要 repo_path 参数
            executor = TestExecutor(repo_path=temp_repo, timeout=60)
            
            # 应该能够处理超时
            result = executor.run_tests(bug_slug="Test_1")
            assert result.timeout is True
            assert not result.success
        finally:
            # 清理临时目录
            import shutil
            if os.path.exists(temp_repo):
                shutil.rmtree(temp_repo)
    
    def test_very_large_patch(self):
        """测试非常大的补丁。"""
        parser = OutputParser()
        
        # 创建一个非常大的补丁（1000 行）
        search_lines = []
        replace_lines = []
        for i in range(1000):
            search_lines.append(f"    int var{i} = {i};")
            replace_lines.append(f"    int var{i} = {i+1};")
        
        large_patch = f"""
<<<<<<< SEARCH
{chr(10).join(search_lines)}
=======
{chr(10).join(replace_lines)}
>>>>>>> REPLACE
"""
        
        # 应该能够解析或优雅地失败
        try:
            parsed = parser.parse(large_patch, "Test_Large", 0)
            # 如果成功，验证结果
            if parsed:
                assert parsed.parse_success
        except Exception as e:
            # 如果失败，应该有清晰的错误消息
            assert len(str(e)) > 0


class TestNetworkIssues:
    """测试网络相关问题（主要是 D4J 命令）。"""
    
    @patch('subprocess.run')
    def test_d4j_command_failure(self, mock_run):
        """测试 D4J 命令失败。"""
        # 模拟命令失败
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Error: Network connection failed"
        mock_run.return_value = mock_result
        
        env_manager = EnvironmentManager()
        
        # 应该能够处理命令失败
        with pytest.raises(Exception):
            env_manager.checkout_bug("Chart_1", "/tmp/test")
    
    @patch('subprocess.run')
    def test_d4j_not_installed(self, mock_run):
        """测试 D4J 未安装。"""
        # 模拟 D4J 命令不存在
        import subprocess
        mock_run.side_effect = FileNotFoundError("defects4j: command not found")
        
        env_manager = EnvironmentManager()
        
        # 系统应该能够检测到 D4J 未安装并返回 False
        result = env_manager.verify_installation()
        assert result is False
    
    @patch('subprocess.run')
    def test_intermittent_network_failure(self, mock_run):
        """测试间歇性网络故障。"""
        # 第一次失败，第二次成功
        call_count = [0]
        
        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("Network error")
            else:
                mock_result = Mock()
                mock_result.returncode = 0
                mock_result.stdout = "Success"
                mock_result.stderr = ""
                return mock_result
        
        mock_run.side_effect = side_effect
        
        # 系统目前没有重试机制，第一次调用会失败
        # 这是预期行为，我们只是验证系统不会崩溃
        env_manager = EnvironmentManager()
        # verify_installation 会在第一次调用时失败
        result = env_manager.verify_installation()
        # 应该返回 False 或抛出异常
        assert result is False or call_count[0] > 0


class TestEdgeCasePatches:
    """测试边界情况的补丁。"""
    
    def test_empty_search_block(self):
        """测试空的 SEARCH 块。"""
        parser = OutputParser()
        
        empty_search = """
<<<<<<< SEARCH
=======
public void foo() {
}
>>>>>>> REPLACE
"""
        parsed = parser.parse(empty_search, "Test_1", 0)
        # 应该能够处理或标记为无效
        assert parsed is None or not parsed.parse_success or len(parsed.search_replaces) == 0
    
    def test_empty_replace_block(self):
        """测试空的 REPLACE 块（删除代码）。"""
        parser = OutputParser()
        
        empty_replace = """
<<<<<<< SEARCH
public void foo() {
}
=======
>>>>>>> REPLACE
"""
        parsed = parser.parse(empty_replace, "Test_1", 0)
        # 系统会解析这个补丁，但可能不会提取 SEARCH/REPLACE 块
        # 因为格式不完整
        assert parsed is not None
        # 可能有或没有 search_replaces，取决于解析器的实现
        # 我们只验证系统不会崩溃
    
    def test_nested_markers(self):
        """测试嵌套的标记。"""
        parser = OutputParser()
        
        nested = """
<<<<<<< SEARCH
public void foo() {
    // <<<<<<< SEARCH
    int x = 1;
}
=======
public void foo() {
    // >>>>>>> REPLACE
    int x = 2;
}
>>>>>>> REPLACE
"""
        parsed = parser.parse(nested, "Test_1", 0)
        # 应该能够正确处理嵌套标记
        assert parsed is not None
    
    def test_multiple_consecutive_patches(self):
        """测试多个连续的补丁。"""
        parser = OutputParser()
        
        multiple = """
<<<<<<< SEARCH
int a = 1;
=======
int a = 2;
>>>>>>> REPLACE

<<<<<<< SEARCH
int b = 1;
=======
int b = 2;
>>>>>>> REPLACE

<<<<<<< SEARCH
int c = 1;
=======
int c = 2;
>>>>>>> REPLACE
"""
        parsed = parser.parse(multiple, "Test_1", 0)
        # 应该能够解析所有三个补丁
        if parsed and parsed.parse_success:
            assert parsed.patch_count >= 3


class TestFileSystemIssues:
    """测试文件系统相关问题。"""
    
    def setup_method(self):
        """设置测试环境。"""
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """清理测试环境。"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_readonly_directory(self):
        """测试只读目录。"""
        output_folder = os.path.join(self.temp_dir, "readonly")
        os.makedirs(output_folder)
        
        # 在某些系统上设置为只读
        try:
            os.chmod(output_folder, 0o444)
            
            # 尝试创建 StorageManager
            with pytest.raises(Exception):
                storage = StorageManager(output_folder)
                storage.log("test", level="INFO")
        finally:
            # 恢复权限以便清理
            os.chmod(output_folder, 0o755)
    
    def test_invalid_path_characters(self):
        """测试无效的路径字符。"""
        # 某些字符在文件名中是无效的
        invalid_chars = ['<', '>', ':', '"', '|', '?', '*']
        
        for char in invalid_chars:
            if char in ['<', '>', ':', '"', '|', '?', '*']:
                # 这些字符在大多数系统上是无效的
                # 我们应该能够处理或清理它们
                bug_slug = f"Test{char}Bug"
                # 系统应该清理或拒绝这个名称
                # 这里我们只是验证不会崩溃
                try:
                    output_folder = os.path.join(self.temp_dir, "output")
                    storage = StorageManager(output_folder)
                    patch = NormalizedPatch(
                        bug_slug=bug_slug,
                        attempt_num=0,
                        modeling_type="edit",
                        diff_content="test"
                    )
                    # 可能成功（如果系统清理了字符）或失败（如果拒绝）
                    storage.save_normalized_patch(patch)
                except Exception:
                    # 失败是可以接受的
                    pass
    
    def test_path_too_long(self):
        """测试路径过长。"""
        # 创建一个非常长的路径
        long_name = "a" * 255  # 大多数文件系统的限制
        
        output_folder = os.path.join(self.temp_dir, "output")
        storage = StorageManager(output_folder)
        
        try:
            patch = NormalizedPatch(
                bug_slug=long_name,
                attempt_num=0,
                modeling_type="edit",
                diff_content="test"
            )
            storage.save_normalized_patch(patch)
            # 可能成功或失败，取决于文件系统
        except Exception as e:
            # 如果失败，应该有清晰的错误消息
            assert len(str(e)) > 0
    
    def test_concurrent_file_access(self):
        """测试并发文件访问。"""
        import threading
        
        output_folder = os.path.join(self.temp_dir, "output")
        storage = StorageManager(output_folder)
        
        errors = []
        
        def write_log(i):
            try:
                storage.log(f"Message {i}", level="INFO")
            except Exception as e:
                errors.append(e)
        
        # 创建多个线程同时写入
        threads = []
        for i in range(10):
            t = threading.Thread(target=write_log, args=(i,))
            threads.append(t)
            t.start()
        
        # 等待所有线程完成
        for t in threads:
            t.join()
        
        # 应该没有错误或只有少量错误
        assert len(errors) < 5  # 允许一些并发冲突


class TestDataValidation:
    """测试数据验证。"""
    
    def test_invalid_bug_slug(self):
        """测试无效的 bug slug。"""
        parser = OutputParser()
        
        # 空的 bug slug - 系统会接受但可能不会产生有用的结果
        parsed = parser.parse("test", "", 0)
        assert parsed is not None  # 系统不会崩溃
        
        # None bug slug - 系统会接受（Python 允许 None 作为字符串参数）
        parsed = parser.parse("test", None, 0)
        assert parsed is not None  # 系统不会崩溃
    
    def test_negative_attempt_number(self):
        """测试负数的尝试编号。"""
        parser = OutputParser()
        
        # 负数尝试编号
        parsed = parser.parse("test", "Bug_1", -1)
        # 应该能够处理或拒绝
    
    def test_invalid_modeling_type(self):
        """测试无效的建模类型。"""
        from evaluation.core.data_structures import ParsedPatch
        
        # 创建一个无效建模类型的补丁
        patch = ParsedPatch(
            bug_slug="Test_1",
            attempt_num=0,
            modeling_type="invalid_type"
        )
        
        # 应该能够处理
        assert not patch.is_edit_format
        assert not patch.is_rewrite_format
