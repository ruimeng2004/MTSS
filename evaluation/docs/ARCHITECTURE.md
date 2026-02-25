# 架构说明

本文档详细说明了 D4J 修复评估系统的架构设计。

## 目录

- [系统概述](#系统概述)
- [架构设计](#架构设计)
- [模块详解](#模块详解)
- [数据流](#数据流)
- [设计决策](#设计决策)

## 系统概述

D4J 修复评估系统是一个用于评估 LLM 生成的 Defects4J bug 修复的自动化工具。系统采用模块化设计，将评估流程分解为多个独立的组件，每个组件负责特定的功能。

### 核心功能

1. **输入处理**：加载和验证修复尝试
2. **补丁解析**：解析 LLM 输出的不同格式
3. **补丁归一化**：将补丁转换为标准 unified diff 格式
4. **环境管理**：管理 Defects4J 环境和 bug 检出
5. **补丁应用**：应用补丁到代码库
6. **测试执行**：运行 Defects4J 测试套件
7. **结果生成**：聚合和分析评估结果
8. **存储管理**：保存结果和日志

### 设计原则

- **模块化**：每个组件职责单一，易于测试和维护
- **可扩展性**：支持新的补丁格式和评估策略
- **容错性**：优雅处理错误，提供详细的错误信息
- **性能**：支持并行处理，提高评估效率
- **可观测性**：详细的日志和进度跟踪

## 架构设计

### 高层架构

```
┌─────────────────────────────────────────────────────────────┐
│                     CLI / API 入口                           │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   D4JFixEvaluator                            │
│                   (主评估器)                                 │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        ▼             ▼             ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ InputHandler │  │ Environment  │  │   Result     │
│              │  │   Manager    │  │  Generator   │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │
       ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Output     │  │    Patch     │  │   Storage    │
│   Parser     │  │  Applicator  │  │   Manager    │
└──────┬───────┘  └──────┬───────┘  └──────────────┘
       │                 │
       ▼                 ▼
┌──────────────┐  ┌──────────────┐
│    Patch     │  │     Test     │
│  Normalizer  │  │   Executor   │
└──────────────┘  └──────────────┘
```

### 模块依赖关系

```
D4JFixEvaluator
├── InputHandler
├── OutputParser
├── PatchNormalizer
│   └── NormalizationReporter
├── EnvironmentManager
├── PatchApplicator
├── TestExecutor
├── ResultGenerator
└── StorageManager
```

## 模块详解

### 1. InputHandler（输入处理器）

**职责**：
- 验证结果文件夹结构
- 列出可用的 bug 和修复尝试
- 加载修复尝试数据

**关键方法**：
- `validate_structure()`: 验证文件夹结构
- `list_bugs()`: 列出所有 bug
- `load_attempt()`: 加载特定修复尝试

**设计考虑**：
- 使用 dataclass 表示修复尝试，确保类型安全
- 支持灵活的文件夹结构
- 提供详细的验证错误信息

### 2. OutputParser（输出解析器）

**职责**：
- 检测 LLM 输出的补丁格式
- 解析 Edit 格式（SEARCH/REPLACE）
- 解析 Rewrite 格式（完整方法重写）

**关键方法**：
- `detect_format()`: 自动检测格式
- `parse_edit_format()`: 解析 Edit 格式
- `parse_rewrite_format()`: 解析 Rewrite 格式

**设计考虑**：
- 使用正则表达式提取结构化信息
- 支持多个 SEARCH/REPLACE 对
- 容错处理格式变体

### 3. PatchNormalizer（补丁归一化器）

**职责**：
- 将解析后的补丁转换为 unified diff 格式
- 使用 tree-sitter 定位方法
- 实现降级策略（方法范围 → 文件范围 → 人工审查）
- 验证归一化后的补丁

**关键方法**：
- `normalize_with_fallback()`: 主归一化方法
- `locate_search_block_with_method_context()`: 方法范围定位
- `locate_search_block_in_file()`: 文件范围定位
- `generate_unified_diff()`: 生成 unified diff

**设计考虑**：
- 使用 tree-sitter 进行精确的语法分析
- 实现多级降级策略，提高成功率
- 详细的匹配质量评估
- 生成人工审查报告

### 4. EnvironmentManager（环境管理器）

**职责**：
- 验证 Defects4J 安装
- 检出指定的 bug 版本
- 管理工作空间
- 清理临时文件

**关键方法**：
- `verify_installation()`: 验证 D4J 安装
- `checkout_bug()`: 检出 bug
- `is_deprecated()`: 检查 bug 是否弃用
- `cleanup()`: 清理工作空间

**设计考虑**：
- 封装 D4J 命令行接口
- 支持并发检出（使用独立工作目录）
- 自动处理弃用的 bug
- 提供清理机制防止磁盘空间耗尽

### 5. PatchApplicator（补丁应用器）

**职责**：
- 应用归一化的补丁到代码库
- 支持多种应用方法（git apply, patch 命令）
- 提供回滚功能

**关键方法**：
- `apply()`: 应用补丁
- `apply_with_git()`: 使用 git apply
- `apply_with_patch()`: 使用 patch 命令
- `rollback()`: 回滚补丁

**设计考虑**：
- 优先使用 git apply（更严格）
- 自动降级到 patch 命令
- 保存原始状态以支持回滚
- 详细的错误报告

### 6. TestExecutor（测试执行器）

**职责**：
- 执行 Defects4J 测试套件
- 解析测试输出
- 提取失败的测试用例
- 支持超时控制

**关键方法**：
- `run_tests()`: 运行测试
- `parse_test_output()`: 解析测试输出

**设计考虑**：
- 使用 subprocess 执行 D4J 命令
- 实现超时机制防止挂起
- 解析 D4J 输出格式
- 捕获详细的测试结果

### 7. ResultGenerator（结果生成器）

**职责**：
- 聚合单个 bug 的评估结果
- 生成批次评估结果
- 计算统计信息
- 按建模类型分组分析

**关键方法**：
- `add_bug_result()`: 添加 bug 结果
- `generate_batch_result()`: 生成批次结果
- `calculate_statistics()`: 计算统计信息

**设计考虑**：
- 使用 dataclass 表示结果，确保类型安全
- 支持增量添加结果
- 提供丰富的统计分析
- 支持按不同维度分组

### 8. StorageManager（存储管理器）

**职责**：
- 保存归一化的补丁
- 保存评估结果
- 管理日志文件
- 组织输出目录结构

**关键方法**：
- `save_normalized_patch()`: 保存补丁
- `save_bug_result()`: 保存 bug 结果
- `save_batch_result()`: 保存批次结果
- `log()`: 记录日志

**设计考虑**：
- 使用 JSON 格式存储结构化数据
- 组织清晰的目录结构
- 支持增量保存
- 提供日志记录功能

### 9. D4JFixEvaluator（主评估器）

**职责**：
- 协调所有组件
- 实现评估流程
- 支持并行处理
- 错误处理和恢复

**关键方法**：
- `evaluate()`: 批次评估
- `evaluate_bug()`: 单个 bug 评估
- `_try_fix()`: 尝试应用修复
- `_evaluate_parallel()`: 并行评估

**设计考虑**：
- 使用组合模式集成所有组件
- 支持串行和并行两种模式
- 详细的进度跟踪
- 优雅的错误处理

## 数据流

### 完整评估流程

```
1. 输入处理
   ├── 验证文件夹结构
   ├── 列出所有 bug
   └── 加载修复尝试
        │
        ▼
2. 补丁解析
   ├── 检测格式（Edit/Rewrite）
   └── 解析为结构化数据
        │
        ▼
3. 环境准备
   ├── 验证 D4J 安装
   └── 检出 buggy 版本
        │
        ▼
4. 补丁归一化
   ├── 使用 tree-sitter 定位方法
   ├── 精确匹配 SEARCH 块
   ├── 生成 unified diff
   └── 验证补丁
        │
        ▼
5. 补丁应用
   ├── 尝试 git apply
   ├── 降级到 patch 命令
   └── 验证应用结果
        │
        ▼
6. 测试执行
   ├── 运行 D4J 测试
   ├── 解析测试输出
   └── 提取失败用例
        │
        ▼
7. 结果生成
   ├── 创建 bug 结果
   ├── 聚合批次结果
   └── 计算统计信息
        │
        ▼
8. 结果存储
   ├── 保存归一化补丁
   ├── 保存评估结果
   └── 记录日志
```

### 数据结构转换

```
LLM 输出 (str)
    │
    ▼ OutputParser
ParsedPatch
    │
    ▼ PatchNormalizer
NormalizedPatch
    │
    ▼ PatchApplicator
ApplyResult
    │
    ▼ TestExecutor
TestResult
    │
    ▼ ResultGenerator
BugEvaluationResult → BatchEvaluationResult
    │
    ▼ StorageManager
JSON 文件
```

## 设计决策

### 1. 为什么使用 tree-sitter？

**决策**：使用 tree-sitter 进行 Java 代码解析

**原因**：
- 提供精确的语法分析
- 支持方法定位和边界检测
- 比正则表达式更可靠
- 性能优秀

**权衡**：
- 增加了依赖复杂度
- 需要安装 tree-sitter-java
- 但提供了更高的准确性

### 2. 为什么实现降级策略？

**决策**：实现多级降级策略（方法范围 → 文件范围 → 人工审查）

**原因**：
- LLM 输出可能不完全准确
- 提高归一化成功率
- 在自动化和准确性之间平衡

**权衡**：
- 增加了代码复杂度
- 但显著提高了成功率

### 3. 为什么支持并行处理？

**决策**：支持多进程并行评估

**原因**：
- 评估大量 bug 时性能关键
- D4J 操作（检出、编译、测试）耗时
- 充分利用多核 CPU

**权衡**：
- 增加了资源消耗
- 需要管理进程间通信
- 但大幅提高了吞吐量

### 4. 为什么使用 dataclass？

**决策**：使用 Python dataclass 表示数据结构

**原因**：
- 提供类型安全
- 自动生成 `__init__`, `__repr__` 等方法
- 支持默认值和验证
- 代码更简洁

### 5. 为什么分离存储管理？

**决策**：将存储逻辑独立为 StorageManager

**原因**：
- 单一职责原则
- 便于更改存储格式
- 支持不同的存储后端
- 易于测试

## 扩展点

系统设计了多个扩展点，便于添加新功能：

### 1. 新的补丁格式

扩展 `OutputParser` 类：

```python
class CustomOutputParser(OutputParser):
    def detect_format(self, content: str) -> str:
        if self._is_custom_format(content):
            return "custom"
        return super().detect_format(content)
    
    def parse_custom_format(self, content: str) -> ParsedPatch:
        # 实现自定义解析逻辑
        pass
```

### 2. 新的归一化策略

扩展 `PatchNormalizer` 类：

```python
class CustomPatchNormalizer(PatchNormalizer):
    def normalize_with_custom_strategy(
        self, 
        parsed_patch: ParsedPatch
    ) -> NormalizedPatch:
        # 实现自定义归一化策略
        pass
```

### 3. 新的测试执行器

扩展 `TestExecutor` 类：

```python
class CustomTestExecutor(TestExecutor):
    def run_custom_tests(self) -> TestResult:
        # 实现自定义测试逻辑
        pass
```

### 4. 新的存储后端

扩展 `StorageManager` 类：

```python
class DatabaseStorageManager(StorageManager):
    def save_to_database(self, data):
        # 实现数据库存储
        pass
```

## 性能优化

### 1. 并行处理

- 使用 `multiprocessing.Pool` 实现并行评估
- 每个 worker 处理独立的 bug
- 避免共享状态，减少锁竞争

### 2. 缓存机制

- 缓存 tree-sitter 解析结果
- 缓存文件内容读取
- 避免重复的 D4J 命令

### 3. 资源管理

- 及时清理临时文件
- 限制并发数量防止资源耗尽
- 使用上下文管理器确保资源释放

### 4. I/O 优化

- 批量写入日志
- 使用 JSON 流式写入大文件
- 异步 I/O（未来改进）

## 测试策略

### 1. 单元测试

- 每个模块都有对应的测试文件
- 使用 mock 避免外部依赖
- 覆盖正常流程和边界情况

### 2. 集成测试

- 测试模块间的交互
- 使用真实的测试数据
- 验证端到端流程

### 3. 性能测试

- 测试大批次处理性能
- 测试并行处理效率
- 监控内存使用

## 安全考虑

### 1. 输入验证

- 验证文件路径，防止路径遍历
- 验证 bug ID 格式
- 验证配置参数

### 2. 命令注入防护

- 使用 subprocess 的列表参数形式
- 避免 shell=True
- 验证所有外部输入

### 3. 资源限制

- 设置测试超时
- 限制并发数量
- 监控磁盘空间

## 未来改进

### 1. 短期改进

- 添加断点续传功能
- 实现更智能的缓存机制
- 优化内存使用

### 2. 中期改进

- 支持更多补丁格式
- 实现机器学习辅助的匹配
- 添加 Web UI

### 3. 长期改进

- 支持其他 bug 数据集
- 分布式评估
- 实时监控和告警

## 参考资料

- [Defects4J 文档](https://github.com/rjust/defects4j)
- [tree-sitter 文档](https://tree-sitter.github.io/tree-sitter/)
- [Python multiprocessing](https://docs.python.org/3/library/multiprocessing.html)
