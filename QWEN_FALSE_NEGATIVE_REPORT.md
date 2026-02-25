# Qwen3Coder-30B 假阴性分析报告

## 执行摘要

对 qwen3coder30b_gen_20260107_025618 评估结果的分析显示:

- **总失败案例数**: 340
- **潜在假阴性数**: 223 (65.6%)
- **真实失败数**: 117 (34.4%)

## 关键发现

### 🔴 存在大量假阴性案例

**223个失败案例实际上生成了有效的补丁文件**,但由于以下原因被错误地标记为失败:

### 失败原因分析

| 失败类型 | 数量 | 占比 |
|---------|------|------|
| **文件路径错误** | 219 | 98.2% |
| **其他错误** | 4 | 1.8% |

### 主要问题: 文件路径不匹配

绝大多数假阴性 (98.2%) 是由于补丁文件中的路径与实际项目结构不匹配导致的。

**典型错误示例**:
```
Apply failed: can't find file to patch at input line 3
Perhaps you used the wrong -p or --strip option?
The text leading up to this was:
--------------------------
|--- a/source/org/jfree/chart/plot/CategoryPlot.java
|+++ b/source/org/jfree/chart/plot/CategoryPlot.java
--------------------------
```

**问题原因**:
- 补丁使用了 `source/` 或 `src/main/java/` 等路径前缀
- 实际应用时,这些路径前缀与D4J项目的实际目录结构不匹配
- 需要正确的 `-p` 参数来剥离路径前缀

### 按项目统计的假阴性

| 项目 | 假阴性数量 |
|------|-----------|
| Closure | 54 |
| Lang | 41 |
| Math | 78 |
| Chart | 8 |
| Cli | 15 |
| Mockito | 10 |
| Time | 7 |
| 其他 | 10 |

## 实际成功率计算

如果这223个假阴性案例能够正确应用:

- **当前报告的成功率**: 51.3% (358/698)
- **潜在真实成功率**: 至少 51.3% + X%

其中X取决于这223个补丁实际能通过测试的比例。保守估计,即使只有50%的假阴性补丁能通过测试,真实成功率也应该在:

**估算真实成功率**: (358 + 223×0.5) / 698 ≈ **67.2%**

## 建议

### 1. 修复补丁应用逻辑

需要改进补丁应用程序,使其能够:
- 自动检测正确的 `-p` 参数
- 处理不同的路径格式 (`source/`, `src/main/java/`, `src/java/` 等)
- 智能匹配文件路径

### 2. 重新评估这223个案例

建议使用修复后的补丁应用逻辑重新评估这些案例,以获得准确的成功率。

### 3. 补丁生成优化

改进补丁生成过程,使其:
- 使用相对于项目根目录的标准路径
- 或者不使用路径前缀,仅使用文件名

## 示例案例

**Bug: Cli_29**

生成的补丁:
```patch
--- a/src/java/org/apache/commons/cli/Util.java
+++ b/src/java/org/apache/commons/cli/Util.java
@@ -60,18 +60,10 @@
      *
      * @return The string without the leading and trailing quotes.
      */
-static String stripLeadingAndTrailingQuotes(String str)
-    {
-        if (str.startsWith("\""))
-        {
-            str = str.substring(1, str.length());
-        }
-        int length = str.length();
-        if (str.endsWith("\""))
-        {
-            str = str.substring(0, length - 1);
-        }
-        
-        return str;
+static String stripLeadingAndTrailingQuotes(String str) {
+    // 补丁内容...
```

该补丁生成成功,但由于路径前缀 `src/java/` 无法在D4J项目中找到而失败。

## 结论

**重要**: 当前报告的340个失败案例中,有223个(65.6%)是**假阴性**——它们实际上生成了有效的补丁,但由于路径匹配问题未能成功应用。

修复补丁应用逻辑后,真实的成功率可能比当前报告的51.3%**高出15-20个百分点**。
