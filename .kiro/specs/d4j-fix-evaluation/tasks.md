# 任务列表：D4J 修复评估系统

## 1. 项目设置和基础架构

- [x] 1.1 创建项目目录结构
  - 创建 `evaluation/` 主目录
  - 创建子目录：`core/`, `utils/`, `tests/`
  - 设置 `__init__.py` 文件

- [x] 1.2 配置依赖和环境
  - 创建 `requirements.txt` 包含所有依赖
  - 安装 tree-sitter 和 tree-sitter-java
  - 验证 D4J 环境配置
  - 创建配置文件模板

- [x] 1.3 设置日志系统
  - 实现统一的日志配置
  - 支持不同级别的日志输出
  - 日志文件轮转机制

## 2. 输入处理模块（Input Handler）

- [x] 2.1 实现 InputHandler 类
  - 实现 `validate_structure()` 方法
  - 实现 `list_bugs()` 方法
  - 实现 `list_attempts()` 方法
  - 实现 `load_attempt()` 方法

- [x] 2.2 定义数据结构
  - 实现 `FixAttempt` dataclass
  - 添加数据验证逻辑

- [x] 2.3 编写单元测试
  - 测试文件夹结构验证
  - 测试 bug 列表提取
  - 测试修复尝试加载

## 3. 输出解析模块（Output Parser）

- [x] 3.1 实现 OutputParser 类
  - 实现 `detect_format()` 方法
  - 实现 `parse()` 方法

- [x] 3.2 实现 Edit 格式解析
  - 实现 `parse_edit_format()` 方法
  - 提取方法签名
  - 提取 SEARCH/REPLACE 块
  - 处理多个 SEARCH/REPLACE 对

- [x] 3.3 实现 Rewrite 格式解析
  - 实现 `parse_rewrite_format()` 方法
  - 提取方法签名
  - 提取完整代码

- [x] 3.4 定义解析数据结构
  - 实现 `SearchReplace` dataclass
  - 实现 `RewritePatch` dataclass
  - 实现 `ParsedPatch` dataclass

- [x] 3.5 编写单元测试
  - 测试 Edit 格式解析
  - 测试 Rewrite 格式解析
  - 测试边界情况和错误处理

## 4. 补丁归一化模块（Normalizer）

### 4.1 核心归一化功能

- [x] 4.1.1 实现 PatchNormalizer 类基础结构
  - 初始化方法
  - 配置上下文行数
  - 集成 NormalizationReporter

- [x] 4.1.2 实现 tree-sitter 方法定位
  - 实现 `_locate_method_with_treesitter()` 方法
  - 实现 `_extract_method_name()` 方法
  - 处理方法重载情况
  - 错误处理和日志记录

- [x] 4.1.3 实现精确匹配逻辑
  - 实现 `_normalize_newlines()` 方法
  - 实现 `_find_exact_matches()` 方法
  - 实现 `_exact_match()` 方法
  - 滑动窗口匹配算法

- [x] 4.1.4 实现主要定位方法
  - 实现 `locate_search_block_with_method_context()` 方法
  - 实现 `locate_search_block_in_file()` 方法（降级策略）
  - 返回 MatchResult 对象

### 4.2 降级策略

- [x] 4.2.1 实现降级策略框架
  - 实现 `normalize_with_fallback()` 方法
  - 定义 NormalizationStrategy 枚举
  - 策略顺序：方法范围 → 文件范围 → 人工审查

- [x] 4.2.2 实现失败报告生成
  - 实现 `_generate_failure_report()` 方法
  - 生成详细的文本报告
  - 包含所有匹配位置和元数据

### 4.3 Diff 生成

- [x] 4.3.1 实现 unified diff 生成
  - 实现 `generate_unified_diff()` 方法
  - 实现 `_adjust_hunk_header()` 方法
  - 正确处理行号偏移

- [x] 4.3.2 实现 Edit 格式归一化
  - 实现 `normalize_edit_patch()` 方法
  - 集成精确匹配和 diff 生成

- [x] 4.3.3 实现 Rewrite 格式归一化
  - 实现 `normalize_rewrite_patch()` 方法
  - 方法边界检测
  - 完整方法替换

### 4.4 数据结构

- [x] 4.4.1 定义匹配相关数据结构
  - 实现 MatchQuality 枚举
  - 实现 MatchResult dataclass
  - 实现 NormalizedPatch dataclass

- [x] 4.4.2 定义异常类
  - 实现 NormalizationError
  - 实现 SearchBlockNotFoundError
  - 实现 AmbiguousMatchError
  - 实现 MethodNotFoundError

### 4.5 验证机制

- [x] 4.5.1 实现补丁验证
  - 实现 `validate_normalized_patch()` 方法
  - 实现 `_is_valid_diff_format()` 方法
  - 实现 `_validate_line_numbers()` 方法
  - 实现 `_validate_context()` 方法

- [x] 4.5.2 实现 dry-run 应用
  - 实现 `_dry_run_apply()` 方法
  - 使用临时目录测试
  - 集成 git apply --check

### 4.6 单元测试

- [x] 4.6.1 测试 tree-sitter 方法定位
  - 测试简单方法定位
  - 测试重载方法
  - 测试嵌套类中的方法

- [x] 4.6.2 测试精确匹配
  - 测试唯一匹配情况
  - 测试多个匹配情况
  - 测试未找到情况
  - 测试空白字符处理

- [x] 4.6.3 测试降级策略
  - 测试方法范围匹配
  - 测试文件范围匹配
  - 测试失败报告生成

- [x] 4.6.4 测试 diff 生成
  - 测试行号正确性
  - 测试上下文行
  - 测试边界情况

## 5. 报告和追踪模块（Reporter）

- [x] 5.1 实现 NormalizationReporter 类
  - 初始化和目录创建
  - 实现 `add_report()` 方法

- [x] 5.2 实现详细报告生成
  - 实现 `_generate_detailed_report()` 方法
  - 格式化 EXACT_AMBIGUOUS 报告
  - 格式化 NOT_FOUND 报告
  - 格式化 METHOD_NOT_FOUND 报告
  - 添加建议的人工审查步骤

- [x] 5.3 实现批次汇总
  - 实现 `generate_summary()` 方法
  - 实现 `print_summary()` 方法
  - 生成 JSON 格式汇总
  - 计算统计信息

- [x] 5.4 定义报告数据结构
  - 实现 NormalizationReport dataclass
  - 实现 BatchNormalizationSummary dataclass

- [x] 5.5 编写单元测试
  - 测试报告生成
  - 测试汇总统计
  - 测试 JSON 输出

## 6. 环境管理模块（Environment Manager）

- [x] 6.1 实现 EnvironmentManager 类
  - 实现 `verify_installation()` 方法
  - 实现 `checkout_bug()` 方法
  - 实现 `is_deprecated()` 方法
  - 实现 `cleanup()` 方法

- [x] 6.2 D4J 命令封装
  - 封装 `defects4j checkout` 命令
  - 封装 `defects4j compile` 命令
  - 封装 `defects4j test` 命令
  - 错误处理和重试机制

- [x] 6.3 工作空间管理
  - 创建和清理临时目录
  - 管理多个并发检出
  - 磁盘空间检查

- [x] 6.4 编写单元测试
  - 测试 D4J 安装验证
  - 测试 bug 检出
  - 测试清理功能
  - 使用 mock 避免实际 D4J 调用

## 7. 补丁应用模块（Patch Applicator）

- [x] 7.1 实现 PatchApplicator 类
  - 实现 `apply()` 方法
  - 实现 `rollback()` 方法

- [x] 7.2 实现应用策略
  - 实现 `apply_with_git()` 方法
  - 实现 `apply_with_patch()` 方法
  - 自动选择最佳方法

- [x] 7.3 定义数据结构
  - 实现 ApplyResult dataclass

- [x] 7.4 编写单元测试
  - 测试 git apply
  - 测试 patch 命令
  - 测试回滚功能

## 8. 测试执行模块（Test Executor）

- [x] 8.1 实现 TestExecutor 类
  - 实现 `run_tests()` 方法
  - 实现超时控制
  - 实现 `parse_test_output()` 方法

- [x] 8.2 D4J 测试集成
  - 执行 D4J 测试命令
  - 解析测试结果
  - 提取失败的测试用例

- [x] 8.3 定义数据结构
  - 实现 TestResult dataclass

- [x] 8.4 编写单元测试
  - 测试测试执行
  - 测试输出解析
  - 测试超时处理

## 9. 结果生成模块（Result Generator）

- [x] 9.1 实现 ResultGenerator 类
  - 实现 `add_bug_result()` 方法
  - 实现 `generate_batch_result()` 方法
  - 实现 `calculate_statistics()` 方法

- [x] 9.2 定义数据结构
  - 实现 BugEvaluationResult dataclass
  - 实现 BatchEvaluationResult dataclass

- [x] 9.3 统计计算
  - 计算修复率
  - 按建模类型分组统计
  - 失败原因分析

- [x] 9.4 编写单元测试
  - 测试结果聚合
  - 测试统计计算
  - 测试边界情况

## 10. 存储管理模块（Storage Manager）

- [x] 10.1 实现 StorageManager 类
  - 实现 `save_normalized_patch()` 方法
  - 实现 `save_bug_result()` 方法
  - 实现 `save_batch_result()` 方法
  - 实现 `save_statistics()` 方法
  - 实现 `log()` 方法

- [x] 10.2 文件组织
  - 创建输出目录结构
  - JSON 格式化输出
  - 日志文件管理

- [x] 10.3 编写单元测试
  - 测试文件保存
  - 测试目录创建
  - 测试 JSON 序列化

## 11. 主评估器（Main Evaluator）

- [x] 11.1 实现 D4JFixEvaluator 类
  - 初始化所有组件
  - 实现 `evaluate()` 方法
  - 实现 `evaluate_bug()` 方法
  - 实现 `_try_fix()` 方法

- [x] 11.2 并行处理
  - 实现 `_evaluate_parallel()` 方法
  - 实现 `_evaluate_sequential()` 方法
  - 进程池管理

- [x] 11.3 进度跟踪
  - 实现 ProgressTracker 类
  - 实时进度显示
  - ETA 计算

- [x] 11.4 错误处理
  - 实现 ErrorHandler 类
  - 可恢复错误处理
  - 致命错误处理

- [x] 11.5 编写集成测试
  - 测试单个 bug 评估
  - 测试批次评估
  - 测试并行处理

## 12. 命令行接口（CLI）

- [x] 12.1 实现 CLI 入口
  - 使用 argparse 解析参数
  - 实现主函数
  - 帮助信息

- [x] 12.2 参数处理
  - 必需参数：result-folder
  - 可选参数：output, workers, verbose, config, bugs
  - 参数验证

- [x] 12.3 输出格式化
  - 进度条显示
  - 彩色输出（可选）
  - 详细模式

- [x] 12.4 编写 CLI 测试
  - 测试参数解析
  - 测试不同参数组合

## 13. 配置管理

- [x] 13.1 扩展 config.yaml
  - 添加 evaluation_config 部分
  - D4J 路径配置
  - 超时和并行配置
  - 弃用 bug 列表

- [x] 13.2 配置加载和验证
  - 实现配置加载器
  - 配置验证
  - 默认值处理

## 14. 文档和部署

- [x] 14.1 编写用户文档
  - README.md
  - 安装指南
  - 使用示例
  - 故障排除

- [x] 14.2 编写开发者文档
  - API 文档
  - 架构说明
  - 贡献指南

- [x] 14.3 部署脚本
  - 安装脚本
  - 环境验证脚本
  - 示例配置文件

## 15. 集成测试和验证

- [x] 15.1 端到端测试
  - 使用真实 D4J bug 测试
  - 测试完整评估流程
  - 验证输出正确性

- [x] 15.2 性能测试
  - 测试大批次处理
  - 测试并行性能
  - 内存使用分析

- [x] 15.3 边界情况测试
  - 测试损坏的输入
  - 测试网络问题
  - 测试磁盘空间不足

## 16. 优化和改进

- [x] 16.1 性能优化
  - 缓存机制实现
  - 减少重复计算
  - 优化文件 I/O

- [x] 16.2 代码质量
  - 代码审查
  - 重构重复代码
  - 添加类型注解

- [x] 16.3 错误处理改进
  - 更详细的错误消息
  - 恢复机制
  - 断点续传功能
