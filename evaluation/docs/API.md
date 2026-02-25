# API 文档

本文档详细说明了 D4J 修复评估系统的核心 API。

## 目录

- [核心模块](#核心模块)
- [工具模块](#工具模块)
- [数据结构](#数据结构)

## 核心模块

### D4JFixEvaluator

主评估器类，协调整个评估流程。

```python
from evaluation.core import D4JFixEvaluator

evaluator = D4JFixEvaluator(
    result_folder="path/to/results",
    output_folder="path/to/output",
    config_path="config.yaml",
    workers=4,
    verbose=True
)

# 评估所有 bug
results = evaluator.evaluate()

# 评估特定 bug
result = evaluator.evaluate_bug("Chart_1")
```

#### 方法

**`__init__(result_folder, output_folder, config_path, workers, verbose)`**

初始化评估器。

参数：
- `result_folder` (str): 包含修复尝试的结果文件夹路径
- `output_folder` (str): 输出文件夹路径
- `config_path` (str, optional): 配置文件路径
- `workers` (int, optional): 并行工作进程数，默认为 1
- `verbose` (bool, optional): 是否启用详细输出，默认为 False

**`evaluate(bug_filter=None)`**

评估所有或指定的 bug。

参数：
- `bug_filter` (List[str], optional): 要评估的 bug 列表，None 表示评估所有

返回：
- `BatchEvaluationResult`: 批次评估结果

**`evaluate_bug(bug_id)`**

评估单个 bug。

参数：
- `bug_id` (str): Bug ID（如 "Chart_1"）

返回：
- `BugEvaluationResult`: Bug 评估结果

---

### InputHandler

处理输入文件夹结构和修复尝试加载。

```python
from evaluation.core import InputHandler

handler = InputHandler("path/to/results")

# 验证文件夹结构
handler.validate_structure()

# 列出所有 bug
bugs = handler.list_bugs()

# 列出某个 bug 的所有尝试
attempts = handler.list_attempts("Chart_1")

# 加载特定尝试
attempt = handler.load_attempt("Chart_1", 0)
```

#### 方法

**`validate_structure()`**

验证结果文件夹结构是否正确。

抛出：
- `ValueError`: 如果结构无效

**`list_bugs()`**

列出所有可用的 bug。

返回：
- `List[str]`: Bug ID 列表

**`list_attempts(bug_id)`**

列出指定 bug 的所有修复尝试。

参数：
- `bug_id` (str): Bug ID

返回：
- `List[int]`: 尝试编号列表

**`load_attempt(bug_id, attempt_num)`**

加载特定的修复尝试。

参数：
- `bug_id` (str): Bug ID
- `attempt_num` (int): 尝试编号

返回：
- `FixAttempt`: 修复尝试对象

---

### OutputParser

解析 LLM 输出的补丁。

```python
from evaluation.core import OutputParser

parser = OutputParser()

# 自动检测格式并解析
parsed = parser.parse(llm_output)

# 检测格式
format_type = parser.detect_format(llm_output)
```

#### 方法

**`detect_format(content)`**

检测补丁格式（Edit 或 Rewrite）。

参数：
- `content` (str): LLM 输出内容

返回：
- `str`: "edit" 或 "rewrite"

抛出：
- `ValueError`: 如果格式无法识别

**`parse(content)`**

解析补丁内容。

参数：
- `content` (str): LLM 输出内容

返回：
- `ParsedPatch`: 解析后的补丁对象

---

### PatchNormalizer

将解析后的补丁归一化为标准 unified diff 格式。

```python
from evaluation.core import PatchNormalizer

normalizer = PatchNormalizer(
    buggy_version_dir="path/to/buggy",
    context_lines=3
)

# 归一化补丁
normalized = normalizer.normalize_with_fallback(parsed_patch)
```

#### 方法

**`normalize_with_fallback(parsed_patch)`**

使用降级策略归一化补丁。

参数：
- `parsed_patch` (ParsedPatch): 解析后的补丁

返回：
- `NormalizedPatch`: 归一化后的补丁

**`normalize_edit_patch(edit_patch)`**

归一化 Edit 格式补丁。

参数：
- `edit_patch` (ParsedPatch): Edit 格式补丁

返回：
- `NormalizedPatch`: 归一化后的补丁

**`normalize_rewrite_patch(rewrite_patch)`**

归一化 Rewrite 格式补丁。

参数：
- `rewrite_patch` (ParsedPatch): Rewrite 格式补丁

返回：
- `NormalizedPatch`: 归一化后的补丁

---

### PatchApplicator

应用补丁到代码库。

```python
from evaluation.core import PatchApplicator

applicator = PatchApplicator(work_dir="path/to/checkout")

# 应用补丁
result = applicator.apply(normalized_patch)

# 回滚补丁
applicator.rollback()
```

#### 方法

**`apply(normalized_patch)`**

应用归一化的补丁。

参数：
- `normalized_patch` (NormalizedPatch): 归一化的补丁

返回：
- `ApplyResult`: 应用结果

**`rollback()`**

回滚最后应用的补丁。

返回：
- `bool`: 是否成功回滚

---

### TestExecutor

执行 Defects4J 测试。

```python
from evaluation.core import TestExecutor

executor = TestExecutor(
    work_dir="path/to/checkout",
    timeout=300
)

# 运行测试
result = executor.run_tests()
```

#### 方法

**`run_tests()`**

运行 Defects4J 测试套件。

返回：
- `TestResult`: 测试结果

---

### EnvironmentManager

管理 Defects4J 环境和 bug 检出。

```python
from evaluation.core import EnvironmentManager

env_manager = EnvironmentManager(
    work_dir="path/to/workspace",
    config=config
)

# 验证 D4J 安装
env_manager.verify_installation()

# 检出 bug
env_manager.checkout_bug("Chart", 1, "buggy")

# 清理
env_manager.cleanup()
```

#### 方法

**`verify_installation()`**

验证 Defects4J 是否正确安装。

抛出：
- `RuntimeError`: 如果 D4J 未安装或配置错误

**`checkout_bug(project, bug_id, version)`**

检出指定的 bug 版本。

参数：
- `project` (str): 项目名称（如 "Chart"）
- `bug_id` (int): Bug 编号
- `version` (str): 版本类型（"buggy" 或 "fixed"）

**`is_deprecated(project, bug_id)`**

检查 bug 是否已弃用。

参数：
- `project` (str): 项目名称
- `bug_id` (int): Bug 编号

返回：
- `bool`: 是否已弃用

**`cleanup()`**

清理工作目录。

---

### ResultGenerator

生成和聚合评估结果。

```python
from evaluation.core import ResultGenerator

generator = ResultGenerator()

# 添加 bug 结果
generator.add_bug_result(bug_result)

# 生成批次结果
batch_result = generator.generate_batch_result()

# 计算统计信息
stats = generator.calculate_statistics()
```

#### 方法

**`add_bug_result(bug_result)`**

添加单个 bug 的评估结果。

参数：
- `bug_result` (BugEvaluationResult): Bug 评估结果

**`generate_batch_result()`**

生成批次评估结果。

返回：
- `BatchEvaluationResult`: 批次评估结果

**`calculate_statistics()`**

计算统计信息。

返回：
- `Dict[str, Any]`: 统计信息字典

---

### StorageManager

管理结果存储和日志记录。

```python
from evaluation.core import StorageManager

storage = StorageManager(output_folder="path/to/output")

# 保存归一化补丁
storage.save_normalized_patch(bug_id, attempt_num, normalized_patch)

# 保存 bug 结果
storage.save_bug_result(bug_result)

# 保存批次结果
storage.save_batch_result(batch_result)

# 记录日志
storage.log(bug_id, attempt_num, "message", level="INFO")
```

#### 方法

**`save_normalized_patch(bug_id, attempt_num, normalized_patch)`**

保存归一化的补丁。

参数：
- `bug_id` (str): Bug ID
- `attempt_num` (int): 尝试编号
- `normalized_patch` (NormalizedPatch): 归一化的补丁

**`save_bug_result(bug_result)`**

保存 bug 评估结果。

参数：
- `bug_result` (BugEvaluationResult): Bug 评估结果

**`save_batch_result(batch_result)`**

保存批次评估结果。

参数：
- `batch_result` (BatchEvaluationResult): 批次评估结果

**`save_statistics(stats)`**

保存统计信息。

参数：
- `stats` (Dict[str, Any]): 统计信息

**`log(bug_id, attempt_num, message, level)`**

记录日志消息。

参数：
- `bug_id` (str): Bug ID
- `attempt_num` (int): 尝试编号
- `message` (str): 日志消息
- `level` (str): 日志级别

---

## 工具模块

### ConfigLoader

加载和验证配置文件。

```python
from evaluation.core import ConfigLoader

config = ConfigLoader.load_config("config.yaml")
```

#### 方法

**`load_config(config_path)`** (静态方法)

加载配置文件。

参数：
- `config_path` (str): 配置文件路径

返回：
- `Dict[str, Any]`: 配置字典

---

### LoggingConfig

配置日志系统。

```python
from evaluation.utils import setup_logging

setup_logging(
    log_file="evaluation.log",
    level="INFO",
    verbose=True
)
```

#### 函数

**`setup_logging(log_file, level, verbose)`**

设置日志系统。

参数：
- `log_file` (str, optional): 日志文件路径
- `level` (str, optional): 日志级别，默认为 "INFO"
- `verbose` (bool, optional): 是否启用详细输出，默认为 False

---

## 数据结构

### FixAttempt

表示一次修复尝试。

```python
@dataclass
class FixAttempt:
    bug_id: str
    attempt_num: int
    model_type: str
    llm_output: str
    metadata: Dict[str, Any]
```

### ParsedPatch

表示解析后的补丁。

```python
@dataclass
class ParsedPatch:
    format_type: str  # "edit" or "rewrite"
    file_path: str
    method_signature: str
    search_replace_pairs: Optional[List[SearchReplace]] = None
    full_code: Optional[str] = None
```

### SearchReplace

表示 SEARCH/REPLACE 对。

```python
@dataclass
class SearchReplace:
    search: str
    replace: str
```

### NormalizedPatch

表示归一化后的补丁。

```python
@dataclass
class NormalizedPatch:
    unified_diff: str
    file_path: str
    strategy: str
    quality: str
    metadata: Dict[str, Any]
```

### ApplyResult

表示补丁应用结果。

```python
@dataclass
class ApplyResult:
    success: bool
    method: str
    error_message: Optional[str] = None
```

### TestResult

表示测试执行结果。

```python
@dataclass
class TestResult:
    passed: bool
    total_tests: int
    failed_tests: int
    error_tests: int
    failed_test_cases: List[str]
    execution_time: float
    output: str
```

### BugEvaluationResult

表示单个 bug 的评估结果。

```python
@dataclass
class BugEvaluationResult:
    bug_id: str
    model_type: str
    attempt_num: int
    success: bool
    stage: str
    error_message: Optional[str] = None
    test_result: Optional[TestResult] = None
    execution_time: float
```

### BatchEvaluationResult

表示批次评估结果。

```python
@dataclass
class BatchEvaluationResult:
    total_bugs: int
    successful_fixes: int
    failed_fixes: int
    bug_results: List[BugEvaluationResult]
    statistics: Dict[str, Any]
    execution_time: float
```

---

## 异常类

### NormalizationError

补丁归一化过程中的基础异常。

```python
class NormalizationError(Exception):
    pass
```

### SearchBlockNotFoundError

当 SEARCH 块无法在源文件中找到时抛出。

```python
class SearchBlockNotFoundError(NormalizationError):
    pass
```

### AmbiguousMatchError

当 SEARCH 块有多个匹配时抛出。

```python
class AmbiguousMatchError(NormalizationError):
    pass
```

### MethodNotFoundError

当方法无法在源文件中找到时抛出。

```python
class MethodNotFoundError(NormalizationError):
    pass
```

---

## 使用示例

### 完整评估流程

```python
from evaluation.core import D4JFixEvaluator

# 创建评估器
evaluator = D4JFixEvaluator(
    result_folder="results/",
    output_folder="output/",
    config_path="config.yaml",
    workers=4,
    verbose=True
)

# 评估所有 bug
results = evaluator.evaluate()

# 打印统计信息
print(f"总计: {results.total_bugs}")
print(f"成功: {results.successful_fixes}")
print(f"失败: {results.failed_fixes}")
print(f"修复率: {results.statistics['fix_rate']:.2%}")
```

### 评估特定 bug

```python
from evaluation.core import D4JFixEvaluator

evaluator = D4JFixEvaluator(
    result_folder="results/",
    output_folder="output/"
)

# 评估单个 bug
result = evaluator.evaluate_bug("Chart_1")

if result.success:
    print(f"Bug {result.bug_id} 修复成功！")
    print(f"测试通过: {result.test_result.total_tests - result.test_result.failed_tests}")
else:
    print(f"Bug {result.bug_id} 修复失败")
    print(f"失败阶段: {result.stage}")
    print(f"错误信息: {result.error_message}")
```

### 自定义归一化流程

```python
from evaluation.core import (
    InputHandler,
    OutputParser,
    PatchNormalizer,
    EnvironmentManager
)

# 加载修复尝试
handler = InputHandler("results/")
attempt = handler.load_attempt("Chart_1", 0)

# 解析补丁
parser = OutputParser()
parsed = parser.parse(attempt.llm_output)

# 检出 buggy 版本
env_manager = EnvironmentManager("workspace/")
env_manager.checkout_bug("Chart", 1, "buggy")

# 归一化补丁
normalizer = PatchNormalizer("workspace/Chart_1_buggy")
normalized = normalizer.normalize_with_fallback(parsed)

print(f"归一化策略: {normalized.strategy}")
print(f"质量: {normalized.quality}")
print(f"Unified diff:\n{normalized.unified_diff}")
```

---

## 配置选项

详细的配置选项请参考 [config.example.yaml](../config.example.yaml)。

主要配置项：

- `d4j_home`: Defects4J 安装路径
- `workspace_dir`: 工作空间目录
- `timeout`: 测试超时时间（秒）
- `max_workers`: 最大并行工作进程数
- `context_lines`: 补丁上下文行数
- `deprecated_bugs`: 弃用的 bug 列表

---

## 扩展和自定义

### 自定义补丁格式

如果需要支持新的补丁格式，可以扩展 `OutputParser` 类：

```python
from evaluation.core import OutputParser

class CustomOutputParser(OutputParser):
    def detect_format(self, content: str) -> str:
        if "<<<CUSTOM_FORMAT>>>" in content:
            return "custom"
        return super().detect_format(content)
    
    def parse_custom_format(self, content: str) -> ParsedPatch:
        # 实现自定义格式解析
        pass
```

### 自定义测试执行

如果需要自定义测试执行逻辑，可以扩展 `TestExecutor` 类：

```python
from evaluation.core import TestExecutor

class CustomTestExecutor(TestExecutor):
    def run_tests(self) -> TestResult:
        # 实现自定义测试逻辑
        pass
```

---

## 性能考虑

- 使用 `workers` 参数启用并行处理以提高性能
- 对于大批次评估，建议使用 SSD 存储以提高 I/O 性能
- 调整 `timeout` 参数以适应不同项目的测试时间
- 使用 `bug_filter` 参数只评估特定的 bug 子集

---

## 故障排除

常见问题和解决方案请参考 [TROUBLESHOOTING.md](TROUBLESHOOTING.md)。
