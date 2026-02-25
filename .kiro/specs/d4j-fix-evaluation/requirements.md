# 需求文档：D4J 修复评估系统

## 简介

本文档规定了 D4J (Defects4J) 修复评估系统的需求。该系统的核心功能是：

**输入**：修复结果文件夹（例如 `ppl/result/20260105_132306/`），包含多个 bug 的模型生成修复输出
**输出**：该批次的真实修复结果，包括每个 bug 的验证状态、成功的修复、失败原因等

该系统将 MTSS（多任务模型选择）生成的修复结果应用到实际的 Defects4J 代码仓库中，运行测试套件进行验证，并生成详细的评估报告。系统支持两种任务建模方法（重写 vs 编辑），能够处理不同的输出格式，并将其规范化为统一的 diff patch 格式后应用到代码仓库。

## 术语表

- **Fix_Result_Folder（修复结果文件夹）**: 包含批次修复结果的时间戳目录（例如 `ppl/result/20260105_132306/`）
- **Batch_Evaluation_Result（批次评估结果）**: 对一个修复结果文件夹中所有 bug 的验证结果汇总
- **Task_Modeling（任务建模）**: 用于生成 bug 修复的方法（重写或编辑）
- **Rewrite_Modeling（重写建模）**: 完整代码重写方法，生成完整的替换代码
- **Edit_Modeling（编辑建模）**: 目标编辑方法，生成 SEARCH/REPLACE 补丁
- **Model_Output（模型输出）**: 存储在 `model_output.txt` 中的生成修复，可能是 SEARCH/REPLACE 格式或完整重写格式
- **Fix_Attempt（修复尝试）**: 对一个 bug 的单次补丁生成和验证（每个 bug 可能有多次尝试，编号为 1, 2, 3...）
- **D4J_Repository（D4J 仓库）**: 包含有 bug 版本的 Defects4J 项目仓库
- **Patch（补丁）**: 尝试修复 bug 的代码修改
- **Normalized_Patch（规范化补丁）**: 转换为统一 diff 格式的补丁，可以使用 git apply 或 patch 命令应用
- **Validation_Result（验证结果）**: 在应用的补丁上运行 D4J 测试套件的结果（通过/失败）
- **Slug**: bug 标识符，格式为 "Project_Number"（例如 "Chart_1"、"Closure_10"）
- **Result_Directory_Structure（结果目录结构）**: 
  ```
  ppl/result/20260105_132306/
  ├── Chart_1/
  │   ├── 1/
  │   │   ├── model_output.txt
  │   │   ├── query.txt
  │   │   └── result.json
  │   ├── 2/
  │   └── ...
  ├── Chart_2/
  └── ...
  ```

## 需求

### 需求 1：修复结果文件夹输入处理

**用户故事：** 作为研究人员，我想要系统能够读取修复结果文件夹，以便我可以评估一个批次的所有修复结果。

#### 验收标准

1. WHEN 指定修复结果文件夹路径时，THE Input_Handler SHALL 验证路径存在且包含有效的结果结构
2. WHEN 扫描结果文件夹时，THE Input_Handler SHALL 识别所有 bug slug（例如 Chart_1, Closure_10）
3. WHEN 处理每个 bug 时，THE Input_Handler SHALL 枚举所有修复尝试（子目录 1, 2, 3...）
4. WHEN 读取修复尝试时，THE Input_Handler SHALL 加载 model_output.txt、query.txt 和 result.json 文件
5. WHEN 遇到缺失或损坏的文件时，THE Input_Handler SHALL 记录错误并继续处理其他尝试

### 需求 2：D4J 环境管理

**用户故事：** 作为研究人员，我想要设置和管理 Defects4J 环境，以便我可以执行 bug 修复并运行测试套件。

#### 验收标准

1. WHEN 系统初始化时，THE Environment_Manager SHALL 验证已安装 Defects4J v2.0 或 v3.0
2. WHEN 检查依赖项时，THE Environment_Manager SHALL 验证 Java、Git、SVN 和 Perl 可用
3. WHEN 需要检出 bug 时，THE Environment_Manager SHALL 使用现有的 checkout.py 基础设施获取有 bug 的版本
4. WHEN D4J 项目被检出时，THE Environment_Manager SHALL 验证测试套件可以成功执行
5. WHEN 处理已弃用的 bug 时，THE Environment_Manager SHALL 跳过在 D4J v3.0 中已弃用的 bug 并记录被跳过的 bug

### 需求 3：模型输出解析

**用户故事：** 作为开发人员，我想要解析不同的模型输出格式，以便我可以从重写和编辑建模结果中提取补丁。

#### 验收标准

1. WHEN 解析编辑建模输出时，THE Output_Parser SHALL 从 model_output.txt 文件中提取 SEARCH/REPLACE 块
2. WHEN 解析重写建模输出时，THE Output_Parser SHALL 从 model_output.txt 文件中提取完整的代码替换
3. WHEN 模型输出包含多个 SEARCH/REPLACE 块时，THE Output_Parser SHALL 按顺序提取所有块
4. WHEN 解析失败时，THE Output_Parser SHALL 返回描述性错误，指示解析失败的原因
5. WHEN 模型输出文件缺失时，THE Output_Parser SHALL 优雅地处理缺失文件并记录错误

### 需求 4：补丁规范化

**用户故事：** 作为研究人员，我想要将不同的修复格式规范化为统一的 diff patch 格式，以便我可以一致地应用和分析修复。

#### 验收标准

1. WHEN 规范化编辑风格修复时，THE Normalizer SHALL 将 SEARCH/REPLACE 块转换为统一 diff 格式
2. WHEN 规范化重写风格修复时，THE Normalizer SHALL 将完整重写转换为统一 diff 格式
3. WHEN 生成 diff patch 时，THE Normalizer SHALL 包含适当的文件头、行号和上下文行
4. WHEN 存储规范化补丁时，THE Normalizer SHALL 保留元数据，包括 bug ID、尝试编号和建模类型
5. WHEN 生成的 patch 时，THE Normalizer SHALL 确保补丁可以使用标准工具（git apply、patch）应用

### 需求 5：补丁应用

**用户故事：** 作为开发人员，我想要将规范化的补丁应用到 D4J 仓库，以便我可以测试修复是否有效。

#### 验收标准

1. WHEN 应用规范化补丁时，THE Patch_Applicator SHALL 使用 git apply 或 patch 命令应用 diff
2. WHEN 应用编辑风格补丁时，THE Patch_Applicator SHALL 在目标文件中定位 SEARCH 块并用 REPLACE 块替换它
3. WHEN 应用重写风格补丁时，THE Patch_Applicator SHALL 用新代码替换整个目标方法或类
4. WHEN 补丁应用失败时，THE Patch_Applicator SHALL 将仓库恢复到原始状态
5. WHEN 顺序应用多个补丁时，THE Patch_Applicator SHALL 跟踪哪些补丁已成功应用

### 需求 6：测试执行和验证

**用户故事：** 作为研究人员，我想要在应用的补丁上运行 D4J 测试套件，以便我可以确定哪些修复是成功的。

#### 验收标准

1. WHEN 应用补丁时，THE Test_Executor SHALL 为该 bug 运行 D4J 测试套件
2. WHEN 测试完成时，THE Test_Executor SHALL 收集所有测试的通过/失败结果
3. WHEN 测试执行超时时，THE Test_Executor SHALL 在 600 秒后终止执行并记录超时失败
4. WHEN 测试失败时，THE Test_Executor SHALL 捕获哪些特定测试失败及其错误消息
5. WHEN 修复通过所有测试时，THE Test_Executor SHALL 将修复尝试标记为成功并记录尝试索引

### 需求 7：批次评估结果生成

**用户故事：** 作为研究人员，我想要生成批次评估结果，以便我可以了解这个修复结果文件夹的整体修复效果。

#### 验收标准

1. WHEN 完成所有 bug 的验证时，THE Result_Generator SHALL 生成批次评估结果汇总
2. WHEN 统计修复结果时，THE Result_Generator SHALL 计算总 bug 数、成功修复数、失败数
3. WHEN 记录每个 bug 时，THE Result_Generator SHALL 包含 bug ID、成功的尝试编号（如果有）、失败原因
4. WHEN 生成报告时，THE Result_Generator SHALL 区分重写建模和编辑建模的成功率
5. WHEN 输出结果时，THE Result_Generator SHALL 生成 JSON 格式（用于程序访问）和 Markdown 格式（用于人类可读性）

### 需求 8：结果存储和组织

**用户故事：** 作为研究人员，我想要以结构化格式存储评估结果，以便我可以分析和重现实验。

#### 验收标准

1. WHEN 存储评估结果时，THE Storage_Manager SHALL 在输出目录下创建结构化的结果文件
2. WHEN 保存修复尝试时，THE Storage_Manager SHALL 存储每次尝试的规范化补丁、验证结果和时间戳
3. WHEN 记录批次结果时，THE Storage_Manager SHALL 在 batch_evaluation.json 中保存所有 bug 的评估结果
4. WHEN 存储统计信息时，THE Storage_Manager SHALL 在 statistics.json 中保存聚合统计信息
5. WHEN 保存详细日志时，THE Storage_Manager SHALL 在 evaluation.log 中记录所有操作和错误

### 需求 9：与现有基础设施集成

**用户故事：** 作为开发人员，我想要重用现有的 D4J 基础设施，以便我可以保持一致性并避免代码重复。

#### 验收标准

1. WHEN 验证修复时，THE System SHALL 使用现有的 validator/ 模块执行 D4J 测试
2. WHEN 检出 bug 时，THE System SHALL 使用现有的 checkout.py 脚本
3. WHEN 读取配置时，THE System SHALL 使用修复评估设置扩展现有的 config.yaml
4. WHEN 处理超时时，THE System SHALL 使用现有的超时配置（默认：600 秒）
5. WHEN 解析 D4J 输出时，THE System SHALL 重用现有的解析逻辑

### 需求 10：错误处理和鲁棒性

**用户故事：** 作为开发人员，我想要系统优雅地处理错误，以便部分失败不会破坏整个批次评估。

#### 验收标准

1. WHEN 补丁应用失败时，THE System SHALL 记录错误并继续下一次尝试
2. WHEN 测试执行超时时，THE System SHALL 记录超时并将尝试标记为失败
3. WHEN 由于环境问题验证失败时，THE System SHALL 区分验证失败和修复失败
4. WHEN 解析失败时，THE System SHALL 记录带有文件路径的解析错误并继续处理其他 bug
5. WHEN 系统遇到不可恢复的错误时，THE System SHALL 在终止前保存所有部分结果

### 需求 11：性能和可扩展性

**用户故事：** 作为研究人员，我想要高效地运行评估，以便我可以在合理的时间内处理大型批次。

#### 验收标准

1. WHEN 处理多个 bug 时，THE System SHALL 支持跨多个进程的并行执行
2. WHEN 运行评估时，THE System SHALL 提供显示已完成和剩余 bug 的进度指示器
3. WHEN 估算时间时，THE System SHALL 在开始评估前计算并显示估计的运行时间
4. WHEN 启用缓存时，THE System SHALL 重用缓存的验证结果以避免冗余测试
5. WHEN 在子集上运行时，THE System SHALL 支持可配置的 bug 采样以进行快速验证

### 需求 12：命令行接口

**用户故事：** 作为研究人员，我想要通过命令行运行评估，以便我可以轻松地集成到脚本和工作流中。

#### 验收标准

1. WHEN 运行评估时，THE CLI SHALL 接受修复结果文件夹路径作为必需参数
2. WHEN 指定输出目录时，THE CLI SHALL 支持 --output 参数来设置结果存储位置
3. WHEN 配置并行度时，THE CLI SHALL 支持 --workers 参数来设置并行进程数
4. WHEN 启用详细日志时，THE CLI SHALL 支持 --verbose 标志来显示详细的执行信息
5. WHEN 评估完成时，THE CLI SHALL 打印批次评估结果摘要并返回适当的退出代码
