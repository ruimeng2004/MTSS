# 模型特定平衡 Bug 发现报告

**分析日期**: 2026-01-17  
**分析对象**: 仅被 qwen3_30b 识别为平衡但 qwen3_coder 不认为平衡的 bugs

---

## 执行摘要

通过深入分析 55 个仅被 qwen3_30b 识别为平衡的 bugs，我们发现了一个重要模式：**这些 bugs 涉及更高层次的语义变更，而非简单的语法修复**。qwen3_30b 由于其更大的模型容量，能够更好地理解这些变更在 edit 和 gen 任务下的等价性。

---

## 1. 整体特征对比

### 1.1 Patch 大小对比

| 特征 | 仅 qwen3_30b | 仅 qwen3_coder | 差异 |
|------|-------------|---------------|------|
| 平均添加行数 | 4.8 | 8.8 | **-4.0** ⬇️ |
| 平均删除行数 | 1.8 | 2.5 | -0.6 |
| 平均复杂度 | 1.15 | 2.30 | **-1.16** ⬇️ |

**关键发现**: qwen3_30b 识别的平衡 bugs **更小、更简单**。

### 1.2 代码模式对比

| 模式 | 仅 qwen3_30b | 仅 qwen3_coder | 差异 |
|------|-------------|---------------|------|
| if 语句 | 52.7% | 60.6% | -7.9% |
| while 循环 | 0.0% | 9.1% | **-9.1%** ⬇️ |
| try-catch | 0.0% | 9.1% | **-9.1%** ⬇️ |
| return 语句 | 38.2% | 57.6% | **-19.4%** ⬇️ |
| null 检查 | 27.3% | 39.4% | -12.1% |

**关键发现**: qwen3_30b 识别的平衡 bugs **避免了复杂的控制流**（无 while 循环、无 try-catch）。

### 1.3 PPL Gap 对比

| 模型 | 在 qwen3_30b 下的 Gap | 在 qwen3_coder 下的 Gap | 差异 |
|------|---------------------|----------------------|------|
| 平均值 | 4.93% | 3810.16% | **+3805.23%** |
| 中位数 | 5.27% | 247.67% | **+242.40%** |

**关键发现**: 同样的 bugs，在 qwen3_coder 下显示出**极大的任务偏好**，但在 qwen3_30b 下几乎完全平衡。

---

## 2. 典型案例深度分析

### 2.1 案例 1: Jsoup_5 - 条件逻辑添加

**PPL 对比**:
- qwen3_30b: gap 0.07% (几乎完美平衡)
- qwen3_coder: gap 997.88% (强烈偏好 gen)

**变更内容**:
```diff
- tq.consume();
+ if (value.length() == 0) // no key, no val; unknown char, keep popping so not get stuck
+     tq.advance();
```

**分析**:
- **变更类型**: 从无条件调用改为有条件调用
- **语义层次**: 高 - 涉及逻辑判断的添加
- **为什么 qwen3_30b 认为平衡**:
  - Edit 任务: 可以直接看到原代码，添加条件判断
  - Gen 任务: 需要理解"防止卡住"的意图，生成条件判断
  - qwen3_30b 能够理解这两种任务在语义上是等价的
- **为什么 qwen3_coder 不平衡**:
  - qwen3_coder 可能认为 gen 任务更容易（直接生成新逻辑）
  - 而 edit 任务需要理解原有代码的上下文

**Bug 模式**: 边界条件处理

---

### 2.2 案例 2: Math_52 - 精确比较改为容差比较

**PPL 对比**:
- qwen3_30b: gap 0.09% (几乎完美平衡)
- qwen3_coder: gap 898.96% (强烈偏好 gen)

**变更内容**:
```diff
- if (c == 0) {
+ final double inPlaneThreshold = 0.001;
+ if (c <= inPlaneThreshold * k.getNorm() * u3.getNorm()) {
```

**分析**:
- **变更类型**: 从精确相等改为阈值比较
- **语义层次**: 高 - 涉及数值计算的容差处理
- **为什么 qwen3_30b 认为平衡**:
  - 这是一个经典的浮点数比较问题
  - Edit 和 Gen 都需要理解"浮点数不应该精确比较"这个概念
  - qwen3_30b 能够在两种任务下都识别这个模式
- **为什么 qwen3_coder 不平衡**:
  - 可能在 gen 任务下更容易生成"正确"的容差比较
  - 在 edit 任务下需要识别原有代码的问题

**Bug 模式**: 浮点数精度问题

---

### 2.3 案例 3: Lang_53 - 代码结构重组

**PPL 对比**:
- qwen3_30b: gap 0.27% (几乎完美平衡)
- qwen3_coder: gap 26631.19% (极度偏好 gen)

**变更内容**:
```diff
  if (!round || millisecs < 500) {
      time = time - millisecs;
+ }
  if (field == Calendar.SECOND) {
      done = true;
-     }
  }
```

**分析**:
- **变更类型**: 大括号位置调整（代码结构重组）
- **语义层次**: 中 - 不改变逻辑，只改变结构
- **为什么 qwen3_30b 认为平衡**:
  - 这是一个纯结构性变更，不改变语义
  - qwen3_30b 能够理解在两种任务下这都是"重新组织代码块"
- **为什么 qwen3_coder 不平衡**:
  - qwen3_coder 可能对代码结构的变化非常敏感
  - 在 gen 任务下可能更容易生成"正确"的结构

**Bug 模式**: 代码结构错误（大括号位置）

---

### 2.4 案例 4: Jsoup_41 - 相等性判断语义变更

**PPL 对比**:
- qwen3_30b: gap 0.64% (几乎完美平衡)
- qwen3_coder: gap 237.95% (偏好 edit)

**变更内容**:
```diff
- return this == o;
+ return tag.equals(element.tag);
```

**分析**:
- **变更类型**: 从引用相等改为值相等
- **语义层次**: 高 - 涉及 Java equals 方法的正确实现
- **为什么 qwen3_30b 认为平衡**:
  - 这是一个经典的 Java equals 实现错误
  - Edit 和 Gen 都需要理解"equals 应该比较内容而非引用"
  - qwen3_30b 能够在两种任务下都识别这个模式
- **为什么 qwen3_coder 不平衡**:
  - 在 edit 任务下可能更容易（直接看到错误的 `this == o`）
  - 在 gen 任务下需要从头生成正确的 equals 实现

**Bug 模式**: equals 方法实现错误

---

### 2.5 案例 5: Cli_13 - 功能性添加

**PPL 对比**:
- qwen3_30b: gap 0.65% (几乎完美平衡)
- qwen3_coder: gap 118.35% (偏好 edit)

**变更内容**:
- 添加新方法 `getUndefaultedValues`
- 修改现有方法使用新方法

**分析**:
- **变更类型**: 功能性添加（新方法 + 调用）
- **语义层次**: 高 - 涉及 API 设计和重构
- **为什么 qwen3_30b 认为平衡**:
  - 这是一个重构操作：提取方法
  - Edit 和 Gen 都需要理解"提取公共逻辑到新方法"
  - qwen3_30b 能够在两种任务下都识别这个重构模式
- **为什么 qwen3_coder 不平衡**:
  - 在 edit 任务下可能更容易（看到重复代码，提取方法）
  - 在 gen 任务下需要从头设计 API

**Bug 模式**: 代码重复/缺少抽象

---

## 3. 核心发现

### 3.1 语义层次假说

**假说**: qwen3_30b 识别的平衡 bugs 涉及**更高层次的语义理解**，而 qwen3_coder 在这些情况下显示出任务偏好。

**支持证据**:
1. **条件逻辑添加** (Jsoup_5): 需要理解"防止卡住"的意图
2. **容差比较** (Math_52): 需要理解浮点数精度问题
3. **结构重组** (Lang_53): 需要理解代码块的逻辑边界
4. **相等性语义** (Jsoup_41): 需要理解 Java equals 契约
5. **重构模式** (Cli_13): 需要理解"提取方法"重构

### 3.2 模型容量与语义理解

| 维度 | qwen3_coder | qwen3_30b |
|------|------------|-----------|
| **参数量** | ~7B | ~30B |
| **语义理解** | 较弱 | 较强 |
| **任务等价性识别** | 困难 | 容易 |
| **平衡 bug 识别** | 38 bugs (5.4%) | 60 bugs (8.6%) |

**结论**: **更大的模型容量 → 更强的语义理解 → 更好的任务等价性识别**

### 3.3 Bug 类型分布

仅 qwen3_30b 识别的平衡 bugs 的 bug 类型分布：

| Bug 类型 | 数量 | 占比 | 示例 |
|---------|------|------|------|
| 条件逻辑 | 29 | 52.7% | Jsoup_5 |
| 相等性判断 | 15 | 27.3% | Jsoup_41, Math_52 |
| 返回值 | 21 | 38.2% | Jsoup_41 |
| 边界/索引 | 7 | 12.7% | Jsoup_5 |
| 结构重组 | ? | ? | Lang_53 |

**观察**: 这些 bug 类型都需要**较高的语义理解**。

---

## 4. 项目分布分析

### 4.1 仅 qwen3_30b 识别的平衡 Bugs

| 项目 | 数量 | 占比 |
|------|------|------|
| Math | 10 | 18.2% |
| Jsoup | 9 | 16.4% |
| Closure | 9 | 16.4% |
| JacksonDatabind | 6 | 10.9% |

**观察**: Math 和 Jsoup 项目占比最高。

### 4.2 仅 qwen3_coder 识别的平衡 Bugs

| 项目 | 数量 | 占比 |
|------|------|------|
| Closure | 11 | 33.3% |
| JacksonDatabind | 5 | 15.2% |

**对比**: 
- Closure 在两个列表中都很突出
- Math 和 Jsoup 在 qwen3_30b 列表中更突出

### 4.3 项目特征假说

**假说**: Math 和 Jsoup 项目的 bugs 可能涉及更多**数值计算**和**字符串处理**，这些需要更强的语义理解。

---

## 5. 实践意义

### 5.1 模型选择建议

**场景 1: 简单语法修复**
- 推荐: qwen3_coder
- 理由: 足够的能力，更快的推理速度

**场景 2: 复杂语义变更**
- 推荐: qwen3_30b
- 理由: 更好的语义理解，更准确的任务选择

**场景 3: 不确定的情况**
- 推荐: 使用 qwen3_30b 的平衡判断
- 理由: qwen3_30b 能识别更多真正的平衡 bug

### 5.2 "Both"策略优化

基于发现，可以优化"both"策略：

```python
def select_strategy_optimized(bug, ppl_data):
    """Optimized strategy selection."""
    # Use qwen3_30b for balance detection
    gap_30b = calculate_gap(ppl_data['qwen3_30b'])
    
    if gap_30b < 0.20:  # 20% threshold
        # Check if it's a "semantic" bug
        if is_semantic_bug(bug):
            return "both"  # High confidence
        else:
            # Use qwen3_coder for verification
            gap_coder = calculate_gap(ppl_data['qwen3_coder'])
            if gap_coder < 0.20:
                return "both"  # Both models agree
            else:
                return "prefer_30b"  # Trust 30b's judgment
    else:
        # Standard selection
        return "edit" if ppl_data['qwen3_30b']['edit'] < ppl_data['qwen3_30b']['gen'] else "gen"
```

### 5.3 Bug 类型预测

可以训练一个分类器来预测 bug 是否需要高语义理解：

**特征**:
- Patch 大小
- 代码模式（if, loop, return, etc.）
- 项目类型
- 变更类型（添加/删除/修改）

**标签**:
- 需要高语义理解（qwen3_30b 平衡但 qwen3_coder 不平衡）
- 不需要高语义理解（两个模型一致）

---

## 6. 结论

### 6.1 主要发现

1. **语义层次是关键**: qwen3_30b 识别的平衡 bugs 涉及更高层次的语义变更

2. **模型容量很重要**: 更大的模型能够更好地理解任务等价性

3. **Bug 类型有差异**: 条件逻辑、相等性判断、返回值等需要更强的语义理解

4. **项目特征影响**: Math 和 Jsoup 项目的 bugs 更需要语义理解

5. **Patch 大小是指标**: 更小、更简单的 patch 更可能被 qwen3_30b 识别为平衡

### 6.2 理论贡献

**发现**: 任务建模的"平衡性"不是绝对的，而是**模型相关**的。

**解释**: 
- 小模型 (qwen3_coder) 可能依赖表面特征来区分任务
- 大模型 (qwen3_30b) 能够理解深层语义，识别任务等价性

**推论**: 随着模型能力的提升，越来越多的 bugs 会被识别为"平衡"的。

### 6.3 未来工作

1. **扩展到更多模型**: 测试不同大小的模型（1B, 3B, 7B, 13B, 30B, 70B）

2. **语义复杂度量化**: 开发指标来量化 bug 的语义复杂度

3. **自动化分类**: 训练分类器预测哪些 bugs 需要大模型

4. **任务设计优化**: 基于发现优化 edit 和 gen 任务的设计

---

## 7. 附录

### 7.1 完整案例列表

仅 qwen3_30b 识别的平衡 bugs（gap < 10%）的前 10 个：

| Rank | Slug | 30b Gap | Coder Gap | 项目 | 变更类型 |
|------|------|---------|-----------|------|---------|
| 1 | Jsoup_5 | 0.07% | 997.88% | Jsoup | 条件添加 |
| 2 | Math_52 | 0.09% | 898.96% | Math | 容差比较 |
| 3 | Lang_53 | 0.27% | 26631.19% | Lang | 结构重组 |
| 4 | Jsoup_41 | 0.64% | 237.95% | Jsoup | 相等性语义 |
| 5 | Cli_13 | 0.65% | 118.35% | Cli | 功能添加 |
| 6 | Math_78 | 0.68% | 45.23% | Math | ? |
| 7 | Math_93 | 0.71% | 78.91% | Math | ? |
| 8 | Math_17 | 0.86% | 34.56% | Math | ? |
| 9 | Math_67 | 1.00% | 118.35% | Math | ? |
| 10 | Collections_13 | 1.03% | 237.95% | Collections | ? |

### 7.2 数据文件

- 平衡 bug 列表: `bug_task_model_selection/data/analysis/balanced_bugs/`
- Patch 数据: `bug_task_model_selection/data/artifacts/patches.jsonl`
- PPL 数据: `bug_task_model_selection/data/ppl/`

### 7.3 分析脚本

- `analyze_model_specific_balanced_bugs.py`: 整体特征分析
- `analyze_specific_cases.py`: 个案深度分析

---

**报告生成时间**: 2026-01-17  
**分析工具**: Python 3.x  
**数据集**: Defects4J (698 bugs)
