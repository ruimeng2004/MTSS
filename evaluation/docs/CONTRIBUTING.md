# 贡献指南

感谢您对 D4J 修复评估系统的关注！本文档将指导您如何为项目做出贡献。

## 目录

- [开发环境设置](#开发环境设置)
- [代码规范](#代码规范)
- [提交流程](#提交流程)
- [测试要求](#测试要求)
- [文档要求](#文档要求)

## 开发环境设置

### 1. 克隆仓库

```bash
git clone <repository-url>
cd <repository-name>
```

### 2. 安装依赖

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
pip install -r evaluation/requirements.txt
```

### 3. 安装 tree-sitter

```bash
pip install tree-sitter tree-sitter-java
```

### 4. 配置 Defects4J

确保 Defects4J 已正确安装并配置：

```bash
defects4j info -p Lang
```

### 5. 运行测试

```bash
# 运行所有测试
python -m pytest evaluation/tests/

# 运行特定测试文件
python -m pytest evaluation/tests/test_input_handler.py

# 运行特定测试
python -m pytest evaluation/tests/test_input_handler.py::test_validate_structure
```

## 代码规范

### Python 代码风格

我们遵循 [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)。

#### 关键要点

1. **缩进**：使用 4 个空格
2. **行长度**：最多 80 字符（文档字符串和注释最多 100 字符）
3. **命名**：
   - 函数和变量：`snake_case`
   - 类：`PascalCase`
   - 常量：`UPPER_CASE`
4. **类型提示**：所有函数参数和返回值都应有类型提示

#### 示例代码

```python
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class ExampleData:
    """示例数据类。
    
    Attributes:
        name: 数据名称。
        value: 数据值。
    """
    name: str
    value: int


def process_data(
    data: List[ExampleData],
    threshold: int = 10
) -> Dict[str, int]:
    """处理数据并返回结果。
    
    Args:
        data: 要处理的数据列表。
        threshold: 过滤阈值，默认为 10。
    
    Returns:
        包含处理结果的字典。
    
    Raises:
        ValueError: 如果数据为空。
    """
    if not data:
        raise ValueError("数据不能为空")
    
    result = {}
    for item in data:
        if item.value > threshold:
            result[item.name] = item.value
    
    return result
```

### 文档字符串

所有公共函数、类和模块都必须有文档字符串：

```python
def example_function(param1: str, param2: int) -> bool:
    """简短的一行描述。
    
    更详细的描述（如果需要）。可以包含多个段落。
    
    Args:
        param1: 第一个参数的描述。
        param2: 第二个参数的描述。
    
    Returns:
        返回值的描述。
    
    Raises:
        ValueError: 在什么情况下抛出此异常。
        RuntimeError: 在什么情况下抛出此异常。
    """
    pass
```

### 导入顺序

```python
# 1. 标准库导入
import os
import sys
from typing import List, Dict

# 2. 第三方库导入
import tree_sitter
from dataclasses import dataclass

# 3. 本地导入
from evaluation.core import InputHandler
from evaluation.utils import setup_logging
```

## 提交流程

### 1. 创建分支

```bash
git checkout -b feature/your-feature-name
# 或
git checkout -b fix/your-bug-fix
```

分支命名规范：
- 新功能：`feature/feature-name`
- Bug 修复：`fix/bug-description`
- 文档：`docs/doc-description`
- 重构：`refactor/refactor-description`

### 2. 进行更改

- 遵循代码规范
- 编写清晰的提交消息
- 保持提交原子化（每个提交只做一件事）

### 3. 编写测试

为所有新功能和 bug 修复编写测试：

```python
import pytest
from evaluation.core import YourNewClass


def test_your_new_feature():
    """测试新功能的基本行为。"""
    obj = YourNewClass()
    result = obj.your_method()
    assert result == expected_value


def test_your_new_feature_edge_case():
    """测试新功能的边界情况。"""
    obj = YourNewClass()
    with pytest.raises(ValueError):
        obj.your_method(invalid_input)
```

### 4. 运行测试

```bash
# 运行所有测试
python -m pytest evaluation/tests/

# 运行特定模块的测试
python -m pytest evaluation/tests/test_your_module.py

# 查看覆盖率
python -m pytest --cov=evaluation evaluation/tests/
```

### 5. 提交更改

```bash
git add .
git commit -m "feat: 添加新功能描述"
```

提交消息格式：
- `feat:` 新功能
- `fix:` Bug 修复
- `docs:` 文档更新
- `test:` 测试相关
- `refactor:` 代码重构
- `style:` 代码格式调整
- `chore:` 构建或辅助工具的变动

### 6. 推送分支

```bash
git push origin feature/your-feature-name
```

### 7. 创建 Pull Request

在 GitHub/GitLab 上创建 Pull Request，并：
- 提供清晰的标题和描述
- 引用相关的 issue
- 确保所有测试通过
- 请求代码审查

## 测试要求

### 单元测试

每个新功能都必须有对应的单元测试：

```python
import pytest
from unittest.mock import Mock, patch
from evaluation.core import YourClass


class TestYourClass:
    """YourClass 的测试套件。"""
    
    def setup_method(self):
        """每个测试方法前的设置。"""
        self.obj = YourClass()
    
    def test_basic_functionality(self):
        """测试基本功能。"""
        result = self.obj.method()
        assert result is not None
    
    def test_with_mock(self):
        """使用 mock 测试外部依赖。"""
        with patch('evaluation.core.external_function') as mock_func:
            mock_func.return_value = "mocked"
            result = self.obj.method_with_dependency()
            assert result == "expected"
            mock_func.assert_called_once()
    
    def test_error_handling(self):
        """测试错误处理。"""
        with pytest.raises(ValueError, match="expected error"):
            self.obj.method_with_error()
```

### 测试覆盖率

- 新代码的测试覆盖率应达到 80% 以上
- 关键路径必须有测试覆盖
- 边界情况和错误处理必须测试

### 集成测试

对于涉及多个模块的功能，编写集成测试：

```python
def test_end_to_end_evaluation():
    """测试完整的评估流程。"""
    # 准备测试数据
    # 执行评估
    # 验证结果
    pass
```

## 文档要求

### 代码文档

- 所有公共 API 必须有文档字符串
- 复杂的算法需要注释说明
- 使用类型提示提高代码可读性

### 用户文档

如果添加了新功能，更新相关文档：

- `README.md`：用户指南
- `docs/API.md`：API 文档
- `docs/EXAMPLES.md`：使用示例

### 开发者文档

如果更改了架构或设计：

- `docs/ARCHITECTURE.md`：架构说明
- `docs/CONTRIBUTING.md`：贡献指南

## 添加新功能

### 1. 添加新的补丁格式

如果要支持新的补丁格式：

1. 扩展 `OutputParser` 类：

```python
class OutputParser:
    def detect_format(self, content: str) -> str:
        """检测补丁格式。"""
        if self._is_new_format(content):
            return "new_format"
        # 现有逻辑
    
    def parse_new_format(self, content: str) -> ParsedPatch:
        """解析新格式。"""
        # 实现解析逻辑
        pass
```

2. 添加测试：

```python
def test_parse_new_format():
    """测试新格式解析。"""
    parser = OutputParser()
    content = "新格式的示例内容"
    result = parser.parse(content)
    assert result.format_type == "new_format"
```

3. 更新文档：
   - 在 `docs/API.md` 中添加新格式说明
   - 在 `README.md` 中添加使用示例

### 2. 添加新的归一化策略

如果要添加新的归一化策略：

1. 扩展 `PatchNormalizer` 类：

```python
class PatchNormalizer:
    def normalize_with_new_strategy(
        self,
        parsed_patch: ParsedPatch
    ) -> NormalizedPatch:
        """使用新策略归一化。"""
        # 实现新策略
        pass
```

2. 更新降级策略链：

```python
def normalize_with_fallback(
    self,
    parsed_patch: ParsedPatch
) -> NormalizedPatch:
    """使用降级策略归一化。"""
    strategies = [
        self.normalize_with_method_context,
        self.normalize_with_file_context,
        self.normalize_with_new_strategy,  # 添加新策略
    ]
    # 实现降级逻辑
```

3. 添加测试和文档

### 3. 添加新的存储后端

如果要支持新的存储后端（如数据库）：

1. 扩展 `StorageManager` 类：

```python
class DatabaseStorageManager(StorageManager):
    """数据库存储管理器。"""
    
    def __init__(self, db_url: str):
        """初始化数据库连接。"""
        self.db = connect_to_database(db_url)
    
    def save_bug_result(self, result: BugEvaluationResult):
        """保存到数据库。"""
        self.db.insert(result)
```

2. 更新配置系统支持新后端
3. 添加测试和文档

## 代码审查清单

在提交 PR 前，请检查：

- [ ] 代码遵循 Google Python Style Guide
- [ ] 所有函数都有文档字符串和类型提示
- [ ] 添加了单元测试，覆盖率 > 80%
- [ ] 所有测试通过
- [ ] 更新了相关文档
- [ ] 提交消息清晰且遵循规范
- [ ] 没有遗留的调试代码或注释
- [ ] 没有硬编码的路径或配置
- [ ] 错误处理完善
- [ ] 日志记录适当

## 常见问题

### Q: 如何运行单个测试？

```bash
python -m pytest evaluation/tests/test_module.py::test_function
```

### Q: 如何调试测试？

```bash
# 使用 pytest 的详细输出
python -m pytest -v -s evaluation/tests/test_module.py

# 使用 pdb 调试
python -m pytest --pdb evaluation/tests/test_module.py
```

### Q: 如何更新依赖？

```bash
# 更新 requirements.txt
pip freeze > requirements.txt

# 或手动编辑 requirements.txt
```

### Q: 如何处理测试中的外部依赖？

使用 mock：

```python
from unittest.mock import patch, Mock

@patch('evaluation.core.external_function')
def test_with_mock(mock_func):
    mock_func.return_value = "mocked"
    # 测试代码
```

### Q: 如何添加新的配置选项？

1. 在 `config.yaml` 中添加新选项
2. 在 `ConfigLoader` 中添加验证
3. 更新 `config.example.yaml`
4. 更新文档

## 获取帮助

如果您有任何问题：

1. 查看现有文档
2. 搜索已有的 issue
3. 创建新的 issue 描述问题
4. 在 PR 中请求帮助

## 行为准则

- 尊重所有贡献者
- 提供建设性的反馈
- 保持专业和友好
- 欢迎新手贡献者

感谢您的贡献！
