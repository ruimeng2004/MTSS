# 设计文档：D4J 修复评估系统

## 概述

本文档描述了 D4J 修复评估系统的技术设计。该系统读取包含模型生成修复的结果文件夹，将修复应用到 Defects4J 代码仓库，运行测试套件进行验证，并生成批次评估结果。

### 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    D4J Fix Evaluation System                 │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐      ┌──────────────┐      ┌───────────┐ │
│  │ Input Handler│─────▶│ Output Parser│─────▶│Normalizer │ │
│  └──────────────┘      └──────────────┘      └───────────┘ │
│         │                                            │       │
│         ▼                                            ▼       │
│  ┌──────────────┐      ┌──────────────┐      ┌───────────┐ │
│  │ Environment  │◀─────│Patch         │◀─────│Test       │ │
│  │ Manager      │      │Applicator    │      │Executor   │ │
│  └──────────────┘      └──────────────┘      └───────────┘ │
│         │                     │                      │       │
│         └─────────────────────┴──────────────────────┘       │
│                               ▼                               │
│                    ┌──────────────────┐                      │
│                    │ Result Generator │                      │
│                    └──────────────────┘                      │
│                               │                               │
│                               ▼                               │
│                    ┌──────────────────┐                      │
│                    │ Storage Manager  │                      │
│                    └──────────────────┘                      │
└─────────────────────────────────────────────────────────────┘
```

## 补丁归一化详细设计

### 问题分析

#### 问题 1: SEARCH 块精确定位

**挑战**：
- SEARCH 块可能在文件中出现多次
- 空白字符（缩进、空格）可能不完全匹配
- 需要避免在错误位置应用补丁
- **关键问题**：模糊匹配不可靠，需要严格的精确匹配和完整的追踪机制

**解决方案**：严格匹配 + 完整标注

```
策略：只使用精确匹配，不使用模糊匹配
├─ 第1步：方法级定位（使用 AST）
├─ 第2步：字符串精确匹配（仅规范化换行符）
├─ 第3步：唯一性强制验证
│   ├─ 唯一匹配 → 标记为 EXACT_MATCH
│   ├─ 多个匹配 → 标记为 AMBIGUOUS，记录所有位置
│   └─ 无匹配 → 标记为 NOT_FOUND，保存原始内容
└─ 第4步：生成详细的匹配报告
```

**匹配质量分级**：

```python
class MatchQuality(Enum):
    """匹配质量等级"""
    EXACT_UNIQUE = "exact_unique"           # 精确唯一匹配 ✓
    EXACT_AMBIGUOUS = "exact_ambiguous"     # 精确但多处匹配 ⚠
    NOT_FOUND = "not_found"                 # 未找到匹配 ✗
    METHOD_NOT_FOUND = "method_not_found"   # 方法未找到 ✗
    PARSE_ERROR = "parse_error"             # 解析错误 ✗
```

**实现示例**：

```python
def locate_search_block_with_method_context(
    self, 
    search_text: str,
    source_content: str, 
    method_signature: str
) -> MatchResult:
    """使用方法上下文精确定位 SEARCH 块"""
    
    # Step 1: 使用 tree-sitter 定位方法
    method_node = self._locate_method_with_treesitter(
        source_content, 
        method_signature
    )
    
    if not method_node:
        return MatchResult(
            quality=MatchQuality.METHOD_NOT_FOUND,
            found=False,
            matches=[],
            metadata={
                'error': f"Method not found: {method_signature}",
                'search_text': search_text
            }
        )
    
    method_start_line = method_node['start_line']
    method_end_line = method_node['end_line']
    method_text = method_node['text']
    
    # Step 2: 在方法体内精确匹配 SEARCH 块
    # 只规范化换行符，不改变空白字符
    normalized_search = self._normalize_newlines(search_text)
    normalized_method = self._normalize_newlines(method_text)
    
    # Step 3: 查找所有精确匹配
    matches = self._find_exact_matches(
        normalized_search,
        normalized_method,
        method_start_line
    )
    
    # Step 4: 根据匹配数量返回结果
    if len(matches) == 0:
        return MatchResult(
            quality=MatchQuality.NOT_FOUND,
            found=False,
            matches=[],
            metadata={
                'method_signature': method_signature,
                'method_range': (method_start_line, method_end_line),
                'search_text': search_text,
                'method_text': method_text[:500]  # 保存前500字符用于调试
            }
        )
    elif len(matches) == 1:
        return MatchResult(
            quality=MatchQuality.EXACT_UNIQUE,
            found=True,
            matches=matches,
            metadata={
                'method_signature': method_signature,
                'method_range': (method_start_line, method_end_line)
            }
        )
    else:
        # 多个匹配 - 这是一个问题
        return MatchResult(
            quality=MatchQuality.EXACT_AMBIGUOUS,
            found=True,
            matches=matches,
            metadata={
                'method_signature': method_signature,
                'method_range': (method_start_line, method_end_line),
                'match_count': len(matches),
                'all_match_locations': [
                    (m['start_line'], m['end_line']) for m in matches
                ]
            }
        )

def _locate_method_with_treesitter(
    self,
    source_content: str,
    method_signature: str
) -> Optional[Dict[str, Any]]:
    """使用 tree-sitter 定位方法
    
    Args:
        source_content: Java 源代码
        method_signature: 方法签名（如 "public LegendItemCollection getLegendItems()"）
        
    Returns:
        Dict 包含方法的起始行、结束行和文本，如果未找到返回 None
    """
    from tree_sitter import Language, Parser
    import tree_sitter_java
    
    # 初始化 parser
    JAVA_LANGUAGE = Language(tree_sitter_java.language())
    parser = Parser(JAVA_LANGUAGE)
    
    # 解析源代码
    tree = parser.parse(bytes(source_content, 'utf8'))
    root_node = tree.root_node
    
    # 提取方法名
    method_name = self._extract_method_name(method_signature)
    
    # 遍历 AST 查找方法声明
    def find_method(node):
        if node.type == 'method_declaration':
            # 获取方法名节点
            for child in node.children:
                if child.type == 'identifier':
                    if child.text.decode('utf8') == method_name:
                        # 找到匹配的方法
                        start_byte = node.start_byte
                        end_byte = node.end_byte
                        start_point = node.start_point
                        end_point = node.end_point
                        
                        return {
                            'start_line': start_point[0] + 1,  # tree-sitter 是 0-based
                            'end_line': end_point[0] + 1,
                            'start_byte': start_byte,
                            'end_byte': end_byte,
                            'text': source_content[start_byte:end_byte],
                            'node': node
                        }
        
        # 递归搜索子节点
        for child in node.children:
            result = find_method(child)
            if result:
                return result
        
        return None
    
    return find_method(root_node)

def _normalize_newlines(self, text: str) -> str:
    """仅规范化换行符，保留所有空白字符
    
    这是唯一的规范化操作，确保匹配的严格性
    """
    # 统一换行符为 \n
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    return text

def _find_exact_matches(
    self,
    search_text: str,
    target_text: str,
    base_line: int
) -> List[Dict[str, Any]]:
    """在目标文本中查找搜索文本的所有精确匹配
    
    Args:
        search_text: 要搜索的文本
        target_text: 目标文本
        base_line: 目标文本的起始行号
        
    Returns:
        List[Dict]: 所有匹配的列表，每个包含 start_line, end_line, matched_text
    """
    matches = []
    search_lines = search_text.split('\n')
    target_lines = target_text.split('\n')
    
    # 滑动窗口查找精确匹配
    for i in range(len(target_lines) - len(search_lines) + 1):
        window = target_lines[i:i + len(search_lines)]
        
        # 精确比较（逐行比较）
        if self._exact_match(search_lines, window):
            matches.append({
                'start_line': base_line + i,
                'end_line': base_line + i + len(search_lines) - 1,
                'matched_text': '\n'.join(window),
                'window_index': i
            })
    
    return matches

def _exact_match(self, lines1: List[str], lines2: List[str]) -> bool:
    """精确匹配两个行列表
    
    只有完全相同才返回 True
    """
    if len(lines1) != len(lines2):
        return False
    
    for l1, l2 in zip(lines1, lines2):
        if l1 != l2:
            return False
    
    return True

def _extract_method_name(self, method_signature: str) -> str:
    """从方法签名中提取方法名
    
    例如: "public LegendItemCollection getLegendItems()" -> "getLegendItems"
    """
    import re
    
    # 匹配方法名（在括号前的最后一个标识符）
    match = re.search(r'\b(\w+)\s*\(', method_signature)
    if match:
        return match.group(1)
    
    # 如果没有括号，尝试提取最后一个单词
    words = method_signature.split()
    if words:
        return words[-1]
    
    return ""
```

#### 问题 2: 行号精确定位

**挑战**：
- Unified diff 需要精确的行号
- 需要包含足够的上下文行用于验证
- 行号必须与源文件完全对应

**解决方案**：基于匹配位置生成 diff

```
行号定位流程：
1. 通过 SEARCH 块匹配获得起始行号 (start_line)
2. 计算 SEARCH 块的行数 (num_lines)
3. 获取前后上下文行（默认3行）
4. 生成标准 unified diff 格式

Unified diff 格式：
@@ -start,count +start,count @@
  - start: 起始行号（1-based）
  - count: 行数
```

**实现示例**：

```python
def generate_unified_diff(
    self,
    original_lines: List[str],
    modified_lines: List[str],
    filepath: str,
    start_line: int,  # 1-based line number
    context_lines: int = 3
) -> str:
    """生成精确的 unified diff
    
    Args:
        original_lines: 原始代码行（SEARCH 块）
        modified_lines: 修改后的代码行（REPLACE 块）
        filepath: 文件路径
        start_line: SEARCH 块在源文件中的起始行号（1-based）
        context_lines: 上下文行数
        
    Returns:
        str: unified diff 格式的补丁
    """
    
    # 1. 读取源文件
    with open(filepath, 'r') as f:
        all_lines = f.readlines()
    
    # 2. 获取上下文
    # 注意：start_line 是 1-based，需要转换为 0-based
    start_idx = start_line - 1
    end_idx = start_idx + len(original_lines)
    
    # 前置上下文
    context_before_start = max(0, start_idx - context_lines)
    context_before = all_lines[context_before_start:start_idx]
    
    # 后置上下文
    context_after_end = min(len(all_lines), end_idx + context_lines)
    context_after = all_lines[end_idx:context_after_end]
    
    # 3. 构建完整的 before/after
    before_lines = context_before + original_lines + context_after
    after_lines = context_before + modified_lines + context_after
    
    # 4. 生成 diff
    import difflib
    
    diff_lines = list(difflib.unified_diff(
        before_lines,
        after_lines,
        fromfile=f'a/{filepath}',
        tofile=f'b/{filepath}',
        fromfiledate='',
        tofiledate='',
        n=context_lines,
        lineterm=''
    ))
    
    # 5. 修正行号信息
    # difflib 默认从第1行开始，需要调整为实际行号
    if len(diff_lines) >= 3:
        # 第3行是 @@ 行，包含行号信息
        hunk_header = diff_lines[2]
        # 替换为正确的起始行号
        actual_start = context_before_start + 1  # 1-based
        diff_lines[2] = self._adjust_hunk_header(
            hunk_header, 
            actual_start
        )
    
    return '\n'.join(diff_lines)

def _adjust_hunk_header(self, header: str, actual_start: int) -> str:
    """调整 hunk header 中的行号
    
    原始格式: @@ -1,10 +1,10 @@
    调整后:   @@ -actual_start,10 +actual_start,10 @@
    """
    import re
    
    # 解析原始 header
    match = re.match(r'@@ -(\d+),(\d+) \+(\d+),(\d+) @@', header)
    if not match:
        return header
    
    old_count = match.group(2)
    new_count = match.group(4)
    
    # 生成新的 header
    return f'@@ -{actual_start},{old_count} +{actual_start},{new_count} @@'
```

#### 问题 3: 处理 Rewrite 格式

**挑战**：
- Rewrite 格式替换整个方法
- 需要精确定位方法的起始和结束位置
- 可能涉及多行方法定义

**解决方案**：基于 AST 的方法边界检测

```python
def normalize_rewrite_patch(
    self,
    rewrite: RewritePatch,
    source_file: Path
) -> NormalizedPatch:
    """将 Rewrite 格式转换为 unified diff
    
    策略：
    1. 使用 AST 定位整个方法
    2. 替换方法体（保留方法签名）
    3. 生成 unified diff
    """
    
    # 1. 读取源文件
    with open(source_file, 'r') as f:
        source_content = f.read()
    
    # 2. 定位方法
    method_ast = self._parse_java_method(
        source_content, 
        rewrite.method_signature
    )
    
    if not method_ast:
        raise MethodNotFoundError(
            f"Method not found: {rewrite.method_signature}"
        )
    
    # 3. 提取原始方法
    lines = source_content.split('\n')
    original_method = lines[
        method_ast.start_line - 1:method_ast.end_line
    ]
    
    # 4. 构建新方法
    # 保留方法签名和注释，替换方法体
    new_method_lines = self._build_new_method(
        original_method,
        rewrite.full_code
    )
    
    # 5. 生成 unified diff
    diff = self.generate_unified_diff(
        original_lines=original_method,
        modified_lines=new_method_lines,
        filepath=str(source_file),
        start_line=method_ast.start_line,
        context_lines=3
    )
    
    return NormalizedPatch(
        bug_slug=rewrite.bug_slug,
        attempt_num=rewrite.attempt_num,
        modeling_type='rewrite',
        diff_content=diff,
        target_files=[str(source_file)],
        metadata={
            'method_signature': rewrite.method_signature,
            'method_start_line': method_ast.start_line,
            'method_end_line': method_ast.end_line
        }
    )
```

### 降级策略

当精确匹配失败时，使用降级策略（**注意：不使用模糊匹配**）：

```python
class NormalizationStrategy(Enum):
    """归一化策略"""
    METHOD_SCOPED_EXACT = "method_scoped_exact"  # 方法范围内精确匹配
    FILE_SCOPED_EXACT = "file_scoped_exact"      # 文件范围内精确匹配
    MANUAL_REVIEW = "manual"                      # 需要人工审查

def normalize_with_fallback(
    self,
    parsed_patch: ParsedPatch,
    source_file: Path
) -> Tuple[NormalizedPatch, NormalizationStrategy]:
    """带降级策略的归一化
    
    策略顺序：
    1. 方法范围内精确匹配（使用方法签名定位）
    2. 文件范围内精确匹配（不使用方法签名）
    3. 标记为需要人工审查
    
    Returns:
        Tuple[NormalizedPatch, NormalizationStrategy]: 
            归一化结果和使用的策略
    """
    
    strategies = [
        NormalizationStrategy.METHOD_SCOPED_EXACT,
        NormalizationStrategy.FILE_SCOPED_EXACT,
    ]
    
    last_match_result = None
    
    for strategy in strategies:
        try:
            if strategy == NormalizationStrategy.METHOD_SCOPED_EXACT:
                # 策略1：在方法范围内精确匹配
                match_result = self.locate_search_block_with_method_context(
                    parsed_patch.search_text,
                    source_file.read_text(),
                    parsed_patch.method_signature
                )
            else:  # FILE_SCOPED_EXACT
                # 策略2：在整个文件范围内精确匹配
                match_result = self.locate_search_block_in_file(
                    parsed_patch.search_text,
                    source_file.read_text()
                )
            
            last_match_result = match_result
            
            # 检查匹配质量
            if match_result.quality == MatchQuality.EXACT_UNIQUE:
                # 唯一精确匹配 - 成功
                patch = self._build_normalized_patch(
                    parsed_patch,
                    match_result,
                    source_file,
                    strategy
                )
                logger.info(f"Normalization succeeded with strategy: {strategy}")
                return patch, strategy
            elif match_result.quality == MatchQuality.EXACT_AMBIGUOUS:
                # 多个精确匹配 - 记录但不自动选择
                logger.warning(
                    f"Strategy {strategy} found {len(match_result.matches)} "
                    f"exact matches. Cannot auto-select."
                )
                continue
            else:
                # 未找到匹配
                logger.warning(
                    f"Strategy {strategy} failed: {match_result.quality.value}"
                )
                continue
            
        except Exception as e:
            logger.warning(f"Strategy {strategy} raised exception: {e}")
            continue
    
    # 所有策略都失败 - 需要人工审查
    logger.error(
        f"All normalization strategies failed. "
        f"Last match quality: {last_match_result.quality if last_match_result else 'N/A'}"
    )
    
    # 生成详细的失败报告
    failure_report = self._generate_failure_report(
        parsed_patch,
        source_file,
        last_match_result
    )
    
    raise NormalizationError(
        f"Failed to normalize patch - requires manual review. "
        f"See failure report: {failure_report}"
    )

def locate_search_block_in_file(
    self,
    search_text: str,
    source_content: str
) -> MatchResult:
    """在整个文件范围内精确定位 SEARCH 块（降级策略）
    
    不使用方法签名，直接在整个文件中搜索
    """
    # 规范化换行符
    normalized_search = self._normalize_newlines(search_text)
    normalized_source = self._normalize_newlines(source_content)
    
    # 查找所有精确匹配
    matches = self._find_exact_matches(
        normalized_search,
        normalized_source,
        base_line=1
    )
    
    # 返回匹配结果
    if len(matches) == 0:
        return MatchResult(
            quality=MatchQuality.NOT_FOUND,
            found=False,
            matches=[],
            metadata={
                'search_text': search_text,
                'search_scope': 'file'
            }
        )
    elif len(matches) == 1:
        return MatchResult(
            quality=MatchQuality.EXACT_UNIQUE,
            found=True,
            matches=matches,
            metadata={
                'search_scope': 'file'
            }
        )
    else:
        return MatchResult(
            quality=MatchQuality.EXACT_AMBIGUOUS,
            found=True,
            matches=matches,
            metadata={
                'search_scope': 'file',
                'match_count': len(matches),
                'all_match_locations': [
                    (m['start_line'], m['end_line']) for m in matches
                ]
            }
        )

def _generate_failure_report(
    self,
    parsed_patch: ParsedPatch,
    source_file: Path,
    match_result: Optional[MatchResult]
) -> str:
    """生成详细的失败报告用于人工审查
    
    报告包含：
    - 补丁信息（bug_slug, attempt_num, method_signature）
    - 匹配质量和原因
    - SEARCH 块内容
    - 如果是 EXACT_AMBIGUOUS，列出所有匹配位置
    - 源文件路径和相关代码片段
    """
    report_lines = [
        "=" * 80,
        "NORMALIZATION FAILURE REPORT",
        "=" * 80,
        f"Bug: {parsed_patch.bug_slug}",
        f"Attempt: {parsed_patch.attempt_num}",
        f"Method Signature: {parsed_patch.method_signature}",
        f"Source File: {source_file}",
        ""
    ]
    
    if match_result:
        report_lines.extend([
            f"Match Quality: {match_result.quality.value}",
            f"Found: {match_result.found}",
            ""
        ])
        
        if match_result.quality == MatchQuality.EXACT_AMBIGUOUS:
            report_lines.append(f"Number of Matches: {len(match_result.matches)}")
            report_lines.append("Match Locations:")
            for i, match in enumerate(match_result.matches, 1):
                report_lines.append(
                    f"  {i}. Lines {match['start_line']}-{match['end_line']}"
                )
            report_lines.append("")
        
        if match_result.metadata:
            report_lines.append("Metadata:")
            for key, value in match_result.metadata.items():
                report_lines.append(f"  {key}: {value}")
            report_lines.append("")
    
    report_lines.extend([
        "SEARCH Block:",
        "-" * 80,
        parsed_patch.search_text,
        "-" * 80,
        ""
    ])
    
    # 保存报告到文件
    report_path = self.failure_reports_dir / f"{parsed_patch.bug_slug}_{parsed_patch.attempt_num}_failure.txt"
    report_content = "\n".join(report_lines)
    report_path.write_text(report_content)
    
    return str(report_path)
```

### 验证机制

归一化后验证补丁的正确性：

```python
def validate_normalized_patch(
    self,
    patch: NormalizedPatch,
    source_file: Path
) -> ValidationResult:
    """验证归一化的补丁
    
    验证项：
    1. Diff 格式正确性
    2. 行号有效性
    3. 上下文匹配
    4. 可应用性测试
    """
    
    # 1. 验证 diff 格式
    if not self._is_valid_diff_format(patch.diff_content):
        return ValidationResult(
            valid=False,
            error="Invalid diff format"
        )
    
    # 2. 验证行号
    if not self._validate_line_numbers(patch, source_file):
        return ValidationResult(
            valid=False,
            error="Invalid line numbers"
        )
    
    # 3. 验证上下文
    if not self._validate_context(patch, source_file):
        return ValidationResult(
            valid=False,
            error="Context mismatch"
        )
    
    # 4. 尝试应用（dry-run）
    try:
        self._dry_run_apply(patch, source_file)
    except Exception as e:
        return ValidationResult(
            valid=False,
            error=f"Patch cannot be applied: {e}"
        )
    
    return ValidationResult(valid=True)

def _dry_run_apply(self, patch: NormalizedPatch, 
                   source_file: Path):
    """干运行：尝试应用补丁但不实际修改文件"""
    import subprocess
    import tempfile
    import shutil
    
    # 创建临时副本
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_file = Path(tmpdir) / source_file.name
        shutil.copy(source_file, tmp_file)
        
        # 尝试应用补丁
        result = subprocess.run(
            ['git', 'apply', '--check', '-'],
            input=patch.diff_content.encode(),
            cwd=tmpdir,
            capture_output=True
        )
        
        if result.returncode != 0:
            raise Exception(
                f"git apply --check failed: {result.stderr.decode()}"
            )
```

### 匹配报告和追踪机制

为了追踪所有不确定和失败的匹配情况，系统生成详细的报告：

#### 报告数据结构

```python
@dataclass
class NormalizationReport:
    """归一化过程的完整报告"""
    bug_slug: str
    attempt_num: int
    timestamp: str
    success: bool
    strategy_used: Optional[NormalizationStrategy]
    match_quality: MatchQuality
    match_details: MatchResult
    failure_reason: Optional[str]
    requires_manual_review: bool

@dataclass
class BatchNormalizationSummary:
    """批次归一化汇总"""
    total_patches: int
    successful: int
    exact_unique: int
    exact_ambiguous: int
    not_found: int
    method_not_found: int
    parse_errors: int
    requires_manual_review: List[str]  # bug_slug 列表
```

#### 报告生成器

```python
class NormalizationReporter:
    """归一化报告生成器"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.reports_dir = output_dir / "normalization_reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.reports: List[NormalizationReport] = []
        
    def add_report(self, report: NormalizationReport):
        """添加单个归一化报告"""
        self.reports.append(report)
        
        # 如果需要人工审查，生成详细报告文件
        if report.requires_manual_review:
            self._generate_detailed_report(report)
    
    def _generate_detailed_report(self, report: NormalizationReport):
        """生成详细的失败报告文件
        
        报告包含：
        - 基本信息（bug_slug, attempt, timestamp）
        - 匹配质量和策略
        - 所有匹配位置（如果是 EXACT_AMBIGUOUS）
        - SEARCH 块内容
        - 相关源代码片段
        - 建议的人工审查步骤
        """
        report_path = self.reports_dir / f"{report.bug_slug}_{report.attempt_num}.txt"
        
        lines = [
            "=" * 80,
            "NORMALIZATION REPORT - REQUIRES MANUAL REVIEW",
            "=" * 80,
            f"Bug: {report.bug_slug}",
            f"Attempt: {report.attempt_num}",
            f"Timestamp: {report.timestamp}",
            f"Match Quality: {report.match_quality.value}",
            f"Strategy Used: {report.strategy_used.value if report.strategy_used else 'N/A'}",
            ""
        ]
        
        if report.failure_reason:
            lines.extend([
                "Failure Reason:",
                f"  {report.failure_reason}",
                ""
            ])
        
        # 添加匹配详情
        match_details = report.match_details
        if match_details.quality == MatchQuality.EXACT_AMBIGUOUS:
            lines.extend([
                f"Found {len(match_details.matches)} exact matches:",
                ""
            ])
            for i, match in enumerate(match_details.matches, 1):
                lines.extend([
                    f"Match {i}:",
                    f"  Location: Lines {match['start_line']}-{match['end_line']}",
                    f"  Context:",
                    "  " + "-" * 76,
                ])
                # 添加匹配的代码片段
                matched_lines = match['matched_text'].split('\n')
                for line in matched_lines[:10]:  # 最多显示10行
                    lines.append(f"  {line}")
                if len(matched_lines) > 10:
                    lines.append(f"  ... ({len(matched_lines) - 10} more lines)")
                lines.append("  " + "-" * 76)
                lines.append("")
        
        elif match_details.quality == MatchQuality.NOT_FOUND:
            lines.extend([
                "SEARCH block not found in source file.",
                "",
                "SEARCH Block Content:",
                "-" * 80,
            ])
            if 'search_text' in match_details.metadata:
                search_lines = match_details.metadata['search_text'].split('\n')
                for line in search_lines:
                    lines.append(line)
            lines.extend([
                "-" * 80,
                ""
            ])
        
        # 添加元数据
        if match_details.metadata:
            lines.extend([
                "Additional Metadata:",
                ""
            ])
            for key, value in match_details.metadata.items():
                if key not in ['search_text', 'matched_text']:  # 已经显示过的
                    lines.append(f"  {key}: {value}")
            lines.append("")
        
        # 添加建议
        lines.extend([
            "Suggested Actions:",
            ""
        ])
        
        if match_details.quality == MatchQuality.EXACT_AMBIGUOUS:
            lines.extend([
                "1. Review all match locations above",
                "2. Determine which match is the intended target",
                "3. Consider adding more context to the SEARCH block",
                "4. Or manually specify the target line number",
                ""
            ])
        elif match_details.quality == MatchQuality.NOT_FOUND:
            lines.extend([
                "1. Verify the SEARCH block content matches the source file",
                "2. Check for whitespace differences (tabs vs spaces)",
                "3. Verify the method signature is correct",
                "4. Check if the source file has been modified",
                ""
            ])
        elif match_details.quality == MatchQuality.METHOD_NOT_FOUND:
            lines.extend([
                "1. Verify the method signature is correct",
                "2. Check if the method exists in the source file",
                "3. Check for typos in the method name or parameters",
                ""
            ])
        
        lines.append("=" * 80)
        
        # 写入文件
        report_path.write_text('\n'.join(lines))
        logger.info(f"Detailed report saved to: {report_path}")
    
    def generate_summary(self) -> BatchNormalizationSummary:
        """生成批次归一化汇总"""
        summary = BatchNormalizationSummary(
            total_patches=len(self.reports),
            successful=sum(1 for r in self.reports if r.success),
            exact_unique=sum(
                1 for r in self.reports 
                if r.match_quality == MatchQuality.EXACT_UNIQUE
            ),
            exact_ambiguous=sum(
                1 for r in self.reports 
                if r.match_quality == MatchQuality.EXACT_AMBIGUOUS
            ),
            not_found=sum(
                1 for r in self.reports 
                if r.match_quality == MatchQuality.NOT_FOUND
            ),
            method_not_found=sum(
                1 for r in self.reports 
                if r.match_quality == MatchQuality.METHOD_NOT_FOUND
            ),
            parse_errors=sum(
                1 for r in self.reports 
                if r.match_quality == MatchQuality.PARSE_ERROR
            ),
            requires_manual_review=[
                r.bug_slug for r in self.reports 
                if r.requires_manual_review
            ]
        )
        
        # 保存汇总到 JSON
        summary_path = self.output_dir / "normalization_summary.json"
        summary_dict = {
            'total_patches': summary.total_patches,
            'successful': summary.successful,
            'success_rate': summary.successful / summary.total_patches if summary.total_patches > 0 else 0,
            'match_quality_breakdown': {
                'exact_unique': summary.exact_unique,
                'exact_ambiguous': summary.exact_ambiguous,
                'not_found': summary.not_found,
                'method_not_found': summary.method_not_found,
                'parse_errors': summary.parse_errors
            },
            'requires_manual_review_count': len(summary.requires_manual_review),
            'requires_manual_review': summary.requires_manual_review
        }
        
        import json
        with open(summary_path, 'w') as f:
            json.dump(summary_dict, f, indent=2)
        
        logger.info(f"Normalization summary saved to: {summary_path}")
        
        return summary
    
    def print_summary(self):
        """打印汇总到控制台"""
        summary = self.generate_summary()
        
        print("\n" + "=" * 80)
        print("NORMALIZATION SUMMARY")
        print("=" * 80)
        print(f"Total Patches: {summary.total_patches}")
        print(f"Successful: {summary.successful} ({summary.successful/summary.total_patches*100:.1f}%)")
        print()
        print("Match Quality Breakdown:")
        print(f"  Exact Unique:     {summary.exact_unique}")
        print(f"  Exact Ambiguous:  {summary.exact_ambiguous}")
        print(f"  Not Found:        {summary.not_found}")
        print(f"  Method Not Found: {summary.method_not_found}")
        print(f"  Parse Errors:     {summary.parse_errors}")
        print()
        print(f"Requires Manual Review: {len(summary.requires_manual_review)}")
        if summary.requires_manual_review:
            print("  Bugs:")
            for bug in summary.requires_manual_review[:10]:  # 最多显示10个
                print(f"    - {bug}")
            if len(summary.requires_manual_review) > 10:
                print(f"    ... and {len(summary.requires_manual_review) - 10} more")
        print("=" * 80 + "\n")
```

#### 集成到归一化流程

```python
class PatchNormalizer:
    def __init__(self, context_lines: int = 3, reporter: Optional[NormalizationReporter] = None):
        self.context_lines = context_lines
        self.reporter = reporter or NormalizationReporter(Path("./output"))
        self.failure_reports_dir = self.reporter.reports_dir
        
    def normalize(self, parsed_patch: ParsedPatch, 
                  source_file: Path) -> NormalizedPatch:
        """将解析的补丁规范化为 unified diff 格式
        
        自动生成报告并追踪匹配质量
        """
        start_time = datetime.now()
        
        try:
            # 尝试归一化
            normalized_patch, strategy = self.normalize_with_fallback(
                parsed_patch, 
                source_file
            )
            
            # 生成成功报告
            report = NormalizationReport(
                bug_slug=parsed_patch.bug_slug,
                attempt_num=parsed_patch.attempt_num,
                timestamp=start_time.isoformat(),
                success=True,
                strategy_used=strategy,
                match_quality=MatchQuality.EXACT_UNIQUE,
                match_details=normalized_patch.metadata.get('match_result'),
                failure_reason=None,
                requires_manual_review=False
            )
            self.reporter.add_report(report)
            
            return normalized_patch
            
        except NormalizationError as e:
            # 生成失败报告
            match_result = getattr(e, 'match_result', None)
            
            report = NormalizationReport(
                bug_slug=parsed_patch.bug_slug,
                attempt_num=parsed_patch.attempt_num,
                timestamp=start_time.isoformat(),
                success=False,
                strategy_used=None,
                match_quality=match_result.quality if match_result else MatchQuality.PARSE_ERROR,
                match_details=match_result,
                failure_reason=str(e),
                requires_manual_review=True
            )
            self.reporter.add_report(report)
            
            raise
```

## 核心组件设计

### 1. Input Handler（输入处理器）

**职责**：读取和验证修复结果文件夹结构

**接口**：
```python
class InputHandler:
    def __init__(self, result_folder: Path):
        """初始化输入处理器
        
        Args:
            result_folder: 修复结果文件夹路径
        """
        
    def validate_structure(self) -> bool:
        """验证文件夹结构是否有效"""
        
    def list_bugs(self) -> List[str]:
        """列出所有 bug slugs"""
        
    def list_attempts(self, bug_slug: str) -> List[int]:
        """列出指定 bug 的所有修复尝试编号"""
        
    def load_attempt(self, bug_slug: str, attempt_num: int) -> FixAttempt:
        """加载单个修复尝试的数据
        
        Returns:
            FixAttempt: 包含 model_output, query, result_json 的数据对象
        """
```

**数据结构**：
```python
@dataclass
class FixAttempt:
    bug_slug: str
    attempt_num: int
    model_output: str
    query: str
    result_json: Dict[str, Any]
    modeling_type: str  # "rewrite" or "edit"
```

### 2. Output Parser（输出解析器）

**职责**：从 model_output.txt 中提取补丁内容

**接口**：
```python
class OutputParser:
    def parse(self, model_output: str) -> ParsedPatch:
        """解析模型输出
        
        Args:
            model_output: model_output.txt 的内容
            
        Returns:
            ParsedPatch: 解析后的补丁对象
            
        Raises:
            ParseError: 解析失败时抛出
        """
        
    def detect_format(self, model_output: str) -> str:
        """检测输出格式（rewrite 或 edit）"""
        
    def parse_edit_format(self, model_output: str) -> List[SearchReplace]:
        """解析 SEARCH/REPLACE 格式"""
        
    def parse_rewrite_format(self, model_output: str) -> RewritePatch:
        """解析完整重写格式"""
```

**数据结构**：
```python
@dataclass
class SearchReplace:
    method_signature: str
    search_block: str
    replace_block: str

@dataclass
class RewritePatch:
    method_signature: str
    full_code: str

@dataclass
class ParsedPatch:
    format_type: str  # "edit" or "rewrite"
    patches: Union[List[SearchReplace], RewritePatch]
    target_file: Optional[str]
```

### 3. Normalizer（规范化器）

**职责**：将不同格式的补丁转换为统一的 diff patch

**核心挑战**：
1. **SEARCH 块精确定位**：避免在多处匹配导致错误应用
2. **行号定位**：生成的 diff 需要准确的行号信息
3. **上下文保留**：确保 diff 包含足够的上下文用于验证

**接口**：
```python
class PatchNormalizer:
    def __init__(self, context_lines: int = 3):
        """初始化规范化器
        
        Args:
            context_lines: diff 中包含的上下文行数（默认3行）
        """
        self.context_lines = context_lines
        
    def normalize(self, parsed_patch: ParsedPatch, 
                  source_file: Path) -> NormalizedPatch:
        """将解析的补丁规范化为 unified diff 格式
        
        Args:
            parsed_patch: 解析后的补丁
            source_file: 源代码文件路径
            
        Returns:
            NormalizedPatch: 规范化的补丁对象
            
        Raises:
            NormalizationError: 归一化失败时抛出
        """
        
    def normalize_edit_patch(self, search_replace: SearchReplace,
                            source_content: str,
                            filepath: str) -> str:
        """将 SEARCH/REPLACE 格式转换为 unified diff
        
        策略：
        1. 使用方法签名缩小搜索范围
        2. 在方法体内精确匹配 SEARCH 块
        3. 计算精确的行号
        4. 生成带上下文的 unified diff
        """
        
    def normalize_rewrite_patch(self, rewrite: RewritePatch,
                               source_content: str,
                               filepath: str) -> str:
        """将完整重写格式转换为 unified diff
        
        策略：
        1. 定位目标方法的起始和结束行
        2. 替换整个方法体
        3. 生成 unified diff
        """
        
    def locate_search_block(self, search_text: str, 
                           source_content: str,
                           method_signature: str) -> Optional[Tuple[int, int]]:
        """精确定位 SEARCH 块在源代码中的位置
        
        Args:
            search_text: 要搜索的代码块
            source_content: 源文件内容
            method_signature: 方法签名（用于缩小搜索范围）
            
        Returns:
            Optional[Tuple[int, int]]: (起始行号, 结束行号)，如果未找到返回 None
            
        策略：
        1. 首先定位方法签名所在的方法
        2. 在方法体内搜索 SEARCH 块
        3. 使用模糊匹配处理空白字符差异
        4. 验证匹配的唯一性
        """
        
    def fuzzy_match(self, search_text: str, target_text: str,
                   threshold: float = 0.95) -> bool:
        """模糊匹配，忽略空白字符差异
        
        Args:
            search_text: 搜索文本
            target_text: 目标文本
            threshold: 相似度阈值（0-1）
            
        Returns:
            bool: 是否匹配
        """
        
    def to_unified_diff(self, original_lines: List[str], 
                       modified_lines: List[str],
                       filepath: str,
                       start_line: int) -> str:
        """生成 unified diff 格式的补丁
        
        Args:
            original_lines: 原始代码行
            modified_lines: 修改后的代码行
            filepath: 文件路径
            start_line: 起始行号
            
        Returns:
            str: unified diff 格式的补丁
        """
```

**数据结构**：
```python
@dataclass
class NormalizedPatch:
    bug_slug: str
    attempt_num: int
    modeling_type: str
    diff_content: str  # unified diff format
    target_files: List[str]
    metadata: Dict[str, Any]
    
@dataclass
class MatchResult:
    """SEARCH 块匹配结果
    
    包含匹配质量、位置信息和元数据，用于追踪和报告
    """
    quality: MatchQuality  # 匹配质量等级
    found: bool  # 是否找到匹配
    matches: List[Dict[str, Any]]  # 所有匹配的列表，每个包含 start_line, end_line, matched_text
    metadata: Dict[str, Any]  # 额外的元数据（如方法范围、错误信息等）
```

**归一化详细策略**：

#### 策略 1: SEARCH 块精确定位

```python
def locate_search_block(self, search_text: str, 
                       source_content: str,
                       method_signature: str) -> MatchResult:
    """
    多层定位策略：
    
    第1层：方法级定位
    - 解析方法签名（如 "public LegendItemCollection getLegendItems()"）
    - 使用 AST 或正则表达式定位方法边界
    - 缩小搜索范围到方法体内
    
    第2层：代码块匹配
    - 规范化空白字符（统一缩进、去除多余空格）
    - 在方法体内逐行匹配 SEARCH 块
    - 计算相似度分数
    
    第3层：唯一性验证
    - 检查是否有多个匹配
    - 如果有多个匹配，使用额外的上下文信息
    - 如果仍然模糊，标记为 ambiguous
    """
    
    # 1. 定位方法
    method_range = self._locate_method(source_content, method_signature)
    if not method_range:
        return MatchResult(found=False, ambiguous=False, match_count=0)
    
    method_start, method_end = method_range
    method_body = source_content[method_start:method_end]
    
    # 2. 规范化搜索文本和方法体
    normalized_search = self._normalize_code(search_text)
    normalized_body = self._normalize_code(method_body)
    
    # 3. 查找所有匹配
    matches = []
    lines = normalized_body.split('\n')
    search_lines = normalized_search.split('\n')
    
    for i in range(len(lines) - len(search_lines) + 1):
        window = lines[i:i+len(search_lines)]
        similarity = self._calculate_similarity(search_lines, window)
        
        if similarity >= 0.95:  # 高置信度匹配
            matches.append({
                'start': method_start + i,
                'end': method_start + i + len(search_lines),
                'confidence': similarity
            })
    
    # 4. 处理匹配结果
    if len(matches) == 0:
        return MatchResult(found=False, ambiguous=False, match_count=0)
    elif len(matches) == 1:
        return MatchResult(
            found=True,
            start_line=matches[0]['start'],
            end_line=matches[0]['end'],
            confidence=matches[0]['confidence'],
            ambiguous=False,
            match_count=1
        )
    else:
        # 多个匹配，尝试使用额外信息消歧
        best_match = self._disambiguate_matches(matches, source_content)
        return MatchResult(
            found=True,
            start_line=best_match['start'],
            end_line=best_match['end'],
            confidence=best_match['confidence'],
            ambiguous=True,
            match_count=len(matches)
        )

def _normalize_code(self, code: str) -> str:
    """规范化代码，用于匹配
    
    规范化规则：
    1. 统一缩进（转换为4个空格）
    2. 去除行尾空白
    3. 统一换行符为 \n
    4. 保留代码结构和语义
    """
    lines = code.split('\n')
    normalized = []
    
    for line in lines:
        # 去除行尾空白
        line = line.rstrip()
        # 计算缩进级别
        indent_level = len(line) - len(line.lstrip())
        # 统一缩进
        content = line.lstrip()
        normalized_line = ' ' * (indent_level // 4 * 4) + content
        normalized.append(normalized_line)
    
    return '\n'.join(normalized)

def _calculate_similarity(self, lines1: List[str], 
                         lines2: List[str]) -> float:
    """计算两段代码的相似度
    
    使用编辑距离算法（Levenshtein distance）
    """
    from difflib import SequenceMatcher
    
    text1 = '\n'.join(lines1)
    text2 = '\n'.join(lines2)
    
    matcher = SequenceMatcher(None, text1, text2)
    return matcher.ratio()

def _disambiguate_matches(self, matches: List[Dict], 
                         source_content: str) -> Dict:
    """消歧多个匹配
    
    策略：
    1. 选择置信度最高的匹配
    2. 如果置信度相同，选择第一个匹配
    3. 记录警告日志
    """
    # 按置信度排序
    sorted_matches = sorted(matches, 
                          key=lambda x: x['confidence'], 
                          reverse=True)
    
    best_match = sorted_matches[0]
    
    # 记录警告
    if len(matches) > 1:
        logger.warning(
            f"Found {len(matches)} matches for SEARCH block. "
            f"Using match at line {best_match['start']} "
            f"with confidence {best_match['confidence']:.2f}"
        )
    
    return best_match
```

#### 策略 2: 行号精确定位

```python
def to_unified_diff(self, original_lines: List[str], 
                   modified_lines: List[str],
                   filepath: str,
                   start_line: int) -> str:
    """生成带精确行号的 unified diff
    
    Unified diff 格式：
    --- a/path/to/file.java
    +++ b/path/to/file.java
    @@ -start_line,num_lines +start_line,num_lines @@
     context line
    -removed line
    +added line
     context line
    """
    import difflib
    
    # 1. 添加上下文行
    # 从源文件中获取前后的上下文
    context_before = self._get_context_lines(
        source_content, 
        start_line, 
        self.context_lines, 
        before=True
    )
    context_after = self._get_context_lines(
        source_content, 
        start_line + len(original_lines), 
        self.context_lines, 
        before=False
    )
    
    # 2. 构建完整的原始和修改后的内容
    full_original = context_before + original_lines + context_after
    full_modified = context_before + modified_lines + context_after
    
    # 3. 生成 unified diff
    diff = difflib.unified_diff(
        full_original,
        full_modified,
        fromfile=f'a/{filepath}',
        tofile=f'b/{filepath}',
        fromfiledate='',
        tofiledate='',
        n=self.context_lines,
        lineterm='',
        # 关键：指定起始行号
        fromline=start_line - self.context_lines,
        toline=start_line - self.context_lines
    )
    
    return '\n'.join(diff)

def _get_context_lines(self, source_content: str, 
                      line_num: int, 
                      num_lines: int,
                      before: bool = True) -> List[str]:
    """获取指定行号前后的上下文行"""
    lines = source_content.split('\n')
    
    if before:
        start = max(0, line_num - num_lines)
        end = line_num
    else:
        start = line_num
        end = min(len(lines), line_num + num_lines)
    
    return lines[start:end]
```

#### 策略 3: 处理边界情况

```python
class NormalizationError(Exception):
    """归一化错误基类"""
    pass

class SearchBlockNotFoundError(NormalizationError):
    """SEARCH 块未找到"""
    pass

class AmbiguousMatchError(NormalizationError):
    """存在多个匹配"""
    pass

class MethodNotFoundError(NormalizationError):
    """方法未找到"""
    pass

def normalize_with_fallback(self, parsed_patch: ParsedPatch,
                            source_file: Path) -> NormalizedPatch:
    """带降级策略的归一化
    
    降级策略：
    1. 尝试精确匹配（方法级 + 代码块级）
    2. 如果失败，尝试仅代码块级匹配
    3. 如果仍失败，尝试模糊匹配（降低阈值）
    4. 如果全部失败，抛出异常
    """
    try:
        # 策略1：精确匹配
        return self.normalize(parsed_patch, source_file)
    except SearchBlockNotFoundError:
        logger.warning("Exact match failed, trying block-level match")
        try:
            # 策略2：仅代码块级匹配
            return self.normalize_block_level(parsed_patch, source_file)
        except SearchBlockNotFoundError:
            logger.warning("Block-level match failed, trying fuzzy match")
            try:
                # 策略3：模糊匹配
                return self.normalize_fuzzy(parsed_patch, source_file, 
                                           threshold=0.85)
            except SearchBlockNotFoundError:
                # 策略4：全部失败
                raise NormalizationError(
                    f"Failed to normalize patch for {parsed_patch.bug_slug}"
                )
```

### 4. Environment Manager（环境管理器）

**职责**：管理 Defects4J 环境和代码仓库

**接口**：
```python
class EnvironmentManager:
    def __init__(self, d4j_path: Path, workspace_dir: Path):
        """初始化环境管理器
        
        Args:
            d4j_path: Defects4J 安装路径
            workspace_dir: 工作目录
        """
        
    def verify_installation(self) -> bool:
        """验证 D4J 和依赖项是否正确安装"""
        
    def checkout_bug(self, bug_slug: str) -> Path:
        """检出指定 bug 的有 bug 版本
        
        Returns:
            Path: 检出的仓库路径
        """
        
    def is_deprecated(self, bug_slug: str) -> bool:
        """检查 bug 是否在 D4J v3.0 中已弃用"""
        
    def cleanup(self, repo_path: Path):
        """清理检出的仓库"""
```

### 5. Patch Applicator（补丁应用器）

**职责**：将规范化的补丁应用到代码仓库

**接口**：
```python
class PatchApplicator:
    def __init__(self, repo_path: Path):
        """初始化补丁应用器
        
        Args:
            repo_path: 代码仓库路径
        """
        
    def apply(self, patch: NormalizedPatch) -> ApplyResult:
        """应用补丁到仓库
        
        Returns:
            ApplyResult: 应用结果
        """
        
    def rollback(self):
        """回滚到原始状态"""
        
    def apply_with_git(self, diff_content: str) -> bool:
        """使用 git apply 应用补丁"""
        
    def apply_with_patch(self, diff_content: str) -> bool:
        """使用 patch 命令应用补丁"""
```

**数据结构**：
```python
@dataclass
class ApplyResult:
    success: bool
    method: str  # "git_apply" or "patch" or "manual"
    error_message: Optional[str]
    applied_files: List[str]
```

### 6. Test Executor（测试执行器）

**职责**：运行 D4J 测试套件并收集结果

**接口**：
```python
class TestExecutor:
    def __init__(self, repo_path: Path, timeout: int = 600):
        """初始化测试执行器
        
        Args:
            repo_path: 代码仓库路径
            timeout: 测试超时时间（秒）
        """
        
    def run_tests(self, bug_slug: str) -> TestResult:
        """运行测试套件
        
        Returns:
            TestResult: 测试结果
        """
        
    def parse_test_output(self, output: str) -> Dict[str, Any]:
        """解析 D4J 测试输出"""
```

**数据结构**：
```python
@dataclass
class TestResult:
    success: bool
    total_tests: int
    passed_tests: int
    failed_tests: int
    timeout: bool
    error_message: Optional[str]
    failed_test_cases: List[str]
    execution_time: float
```

### 7. Result Generator（结果生成器）

**职责**：生成批次评估结果

**接口**：
```python
class ResultGenerator:
    def __init__(self):
        """初始化结果生成器"""
        
    def add_bug_result(self, bug_result: BugEvaluationResult):
        """添加单个 bug 的评估结果"""
        
    def generate_batch_result(self) -> BatchEvaluationResult:
        """生成批次评估结果"""
        
    def calculate_statistics(self) -> Dict[str, Any]:
        """计算统计信息"""
```

**数据结构**：
```python
@dataclass
class BugEvaluationResult:
    bug_slug: str
    total_attempts: int
    successful_attempt: Optional[int]  # None if no success
    modeling_type: Optional[str]  # "rewrite" or "edit"
    test_result: Optional[TestResult]
    failure_reasons: List[str]
    
@dataclass
class BatchEvaluationResult:
    result_folder: str
    timestamp: str
    total_bugs: int
    fixed_bugs: int
    failed_bugs: int
    rewrite_success: int
    edit_success: int
    bug_results: List[BugEvaluationResult]
    statistics: Dict[str, Any]
```

### 8. Storage Manager（存储管理器）

**职责**：存储评估结果和中间数据

**接口**：
```python
class StorageManager:
    def __init__(self, output_dir: Path):
        """初始化存储管理器
        
        Args:
            output_dir: 输出目录
        """
        
    def save_normalized_patch(self, patch: NormalizedPatch):
        """保存规范化的补丁"""
        
    def save_bug_result(self, result: BugEvaluationResult):
        """保存单个 bug 的评估结果"""
        
    def save_batch_result(self, result: BatchEvaluationResult):
        """保存批次评估结果"""
        
    def save_statistics(self, stats: Dict[str, Any]):
        """保存统计信息"""
        
    def log(self, message: str, level: str = "INFO"):
        """记录日志"""
```

**输出目录结构**：
```
output/
├── batch_evaluation.json          # 批次评估结果
├── statistics.json                # 统计信息
├── evaluation.log                 # 详细日志
├── patches/                       # 规范化的补丁
│   ├── Chart_1_attempt_1.patch
│   ├── Chart_1_attempt_2.patch
│   └── ...
└── bug_results/                   # 每个 bug 的详细结果
    ├── Chart_1.json
    ├── Closure_10.json
    └── ...
```

## 主流程设计

### 评估流程

```python
class D4JFixEvaluator:
    def __init__(self, result_folder: Path, output_dir: Path, 
                 config: Dict[str, Any]):
        """初始化评估器"""
        self.input_handler = InputHandler(result_folder)
        self.output_parser = OutputParser()
        self.normalizer = PatchNormalizer()
        self.env_manager = EnvironmentManager(
            config['d4j_path'], 
            config['workspace_dir']
        )
        self.result_generator = ResultGenerator()
        self.storage_manager = StorageManager(output_dir)
        
    def evaluate(self, parallel: int = 1, verbose: bool = False):
        """执行批次评估
        
        Args:
            parallel: 并行进程数
            verbose: 是否显示详细日志
        """
        # 1. 验证输入
        if not self.input_handler.validate_structure():
            raise ValueError("Invalid result folder structure")
            
        # 2. 获取所有 bugs
        bugs = self.input_handler.list_bugs()
        
        # 3. 并行或串行处理每个 bug
        if parallel > 1:
            results = self._evaluate_parallel(bugs, parallel)
        else:
            results = self._evaluate_sequential(bugs, verbose)
            
        # 4. 生成批次结果
        batch_result = self.result_generator.generate_batch_result()
        
        # 5. 保存结果
        self.storage_manager.save_batch_result(batch_result)
        self.storage_manager.save_statistics(
            self.result_generator.calculate_statistics()
        )
        
        return batch_result
        
    def evaluate_bug(self, bug_slug: str) -> BugEvaluationResult:
        """评估单个 bug
        
        Args:
            bug_slug: Bug 标识符
            
        Returns:
            BugEvaluationResult: 评估结果
        """
        # 1. 检查是否已弃用
        if self.env_manager.is_deprecated(bug_slug):
            self.storage_manager.log(
                f"Skipping deprecated bug: {bug_slug}", 
                "WARNING"
            )
            return self._create_skipped_result(bug_slug)
            
        # 2. 检出 bug
        repo_path = self.env_manager.checkout_bug(bug_slug)
        
        try:
            # 3. 获取所有修复尝试
            attempts = self.input_handler.list_attempts(bug_slug)
            
            # 4. 逐个尝试修复
            for attempt_num in attempts:
                result = self._try_fix(bug_slug, attempt_num, repo_path)
                
                if result.success:
                    # 修复成功，记录并返回
                    bug_result = BugEvaluationResult(
                        bug_slug=bug_slug,
                        total_attempts=len(attempts),
                        successful_attempt=attempt_num,
                        modeling_type=result.modeling_type,
                        test_result=result.test_result,
                        failure_reasons=[]
                    )
                    self.result_generator.add_bug_result(bug_result)
                    return bug_result
                    
            # 5. 所有尝试都失败
            bug_result = BugEvaluationResult(
                bug_slug=bug_slug,
                total_attempts=len(attempts),
                successful_attempt=None,
                modeling_type=None,
                test_result=None,
                failure_reasons=self._collect_failure_reasons(attempts)
            )
            self.result_generator.add_bug_result(bug_result)
            return bug_result
            
        finally:
            # 6. 清理
            self.env_manager.cleanup(repo_path)
            
    def _try_fix(self, bug_slug: str, attempt_num: int, 
                 repo_path: Path) -> FixResult:
        """尝试应用单个修复
        
        Returns:
            FixResult: 修复尝试结果
        """
        try:
            # 1. 加载修复尝试
            attempt = self.input_handler.load_attempt(bug_slug, attempt_num)
            
            # 2. 解析模型输出
            parsed_patch = self.output_parser.parse(attempt.model_output)
            
            # 3. 规范化补丁
            source_file = self._locate_source_file(repo_path, parsed_patch)
            normalized_patch = self.normalizer.normalize(
                parsed_patch, 
                source_file
            )
            
            # 4. 保存规范化补丁
            self.storage_manager.save_normalized_patch(normalized_patch)
            
            # 5. 应用补丁
            applicator = PatchApplicator(repo_path)
            apply_result = applicator.apply(normalized_patch)
            
            if not apply_result.success:
                return FixResult(
                    success=False,
                    error="Patch application failed: " + 
                          apply_result.error_message
                )
                
            # 6. 运行测试
            executor = TestExecutor(repo_path)
            test_result = executor.run_tests(bug_slug)
            
            # 7. 回滚补丁
            applicator.rollback()
            
            return FixResult(
                success=test_result.success,
                modeling_type=attempt.modeling_type,
                test_result=test_result
            )
            
        except Exception as e:
            self.storage_manager.log(
                f"Error in attempt {attempt_num} for {bug_slug}: {str(e)}", 
                "ERROR"
            )
            return FixResult(success=False, error=str(e))
```

## 配置设计

### 配置文件扩展

在现有的 `config.yaml` 中添加评估配置：

```yaml
evaluation_config:
  d4j_path: "/path/to/defects4j"
  workspace_dir: "./workspace"
  output_dir: "./evaluation_output"
  timeout: 600  # 测试超时时间（秒）
  parallel_workers: 4  # 并行进程数
  cache_enabled: true  # 是否启用缓存
  deprecated_bugs:  # D4J v3.0 中已弃用的 bugs
    - "Lang_18"
    - "Lang_25"
    - "Lang_48"
    - "JacksonDatabind_65"
    - "JacksonDatabind_89"
```

## 命令行接口设计

```bash
# 基本用法
python -m evaluation.evaluate \
    --result-folder ppl/result/20260105_132306 \
    --output evaluation_output \
    --workers 4 \
    --verbose

# 参数说明
# --result-folder: 修复结果文件夹路径（必需）
# --output: 输出目录（默认：./evaluation_output）
# --workers: 并行进程数（默认：1）
# --verbose: 显示详细日志
# --config: 配置文件路径（默认：config.yaml）
# --bugs: 仅评估指定的 bugs（逗号分隔）
```

## 错误处理策略

### 错误分类

1. **可恢复错误**：记录日志，继续处理
   - 解析失败
   - 补丁应用失败
   - 单个测试超时

2. **不可恢复错误**：保存部分结果，终止执行
   - D4J 环境未安装
   - 输入文件夹结构无效
   - 磁盘空间不足

### 错误处理机制

```python
class ErrorHandler:
    def __init__(self, storage_manager: StorageManager):
        self.storage = storage_manager
        self.errors = []
        
    def handle_recoverable(self, error: Exception, context: str):
        """处理可恢复错误"""
        self.errors.append({
            'type': 'recoverable',
            'error': str(error),
            'context': context,
            'timestamp': datetime.now().isoformat()
        })
        self.storage.log(f"Recoverable error in {context}: {error}", "WARNING")
        
    def handle_fatal(self, error: Exception, context: str):
        """处理致命错误"""
        self.errors.append({
            'type': 'fatal',
            'error': str(error),
            'context': context,
            'timestamp': datetime.now().isoformat()
        })
        self.storage.log(f"Fatal error in {context}: {error}", "ERROR")
        self.storage.save_statistics({'errors': self.errors})
        raise
```

## 性能优化

### 1. 并行处理

使用 `multiprocessing.Pool` 并行处理多个 bugs：

```python
def _evaluate_parallel(self, bugs: List[str], workers: int):
    with multiprocessing.Pool(workers) as pool:
        results = pool.map(self.evaluate_bug, bugs)
    return results
```

### 2. 缓存机制

缓存已验证的修复尝试：

```python
class CacheManager:
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache = {}
        
    def get_cached_result(self, bug_slug: str, 
                         attempt_num: int) -> Optional[TestResult]:
        """获取缓存的测试结果"""
        cache_key = f"{bug_slug}_{attempt_num}"
        return self.cache.get(cache_key)
        
    def cache_result(self, bug_slug: str, attempt_num: int, 
                    result: TestResult):
        """缓存测试结果"""
        cache_key = f"{bug_slug}_{attempt_num}"
        self.cache[cache_key] = result
        self._save_to_disk(cache_key, result)
```

### 3. 进度跟踪

```python
class ProgressTracker:
    def __init__(self, total: int):
        self.total = total
        self.completed = 0
        self.start_time = time.time()
        
    def update(self, increment: int = 1):
        """更新进度"""
        self.completed += increment
        elapsed = time.time() - self.start_time
        rate = self.completed / elapsed
        remaining = (self.total - self.completed) / rate
        
        print(f"Progress: {self.completed}/{self.total} "
              f"({self.completed/self.total*100:.1f}%) "
              f"ETA: {remaining/60:.1f} min")
```

## 测试策略

### 单元测试

每个组件都需要单元测试：

```python
# tests/test_output_parser.py
def test_parse_edit_format():
    parser = OutputParser()
    model_output = """
    ###public void method()
    <<<<<<< SEARCH
    old code
    =======
    new code
    >>>>>>> REPLACE
    """
    result = parser.parse(model_output)
    assert result.format_type == "edit"
    assert len(result.patches) == 1
```

### 集成测试

测试完整的评估流程：

```python
# tests/test_integration.py
def test_evaluate_single_bug():
    evaluator = D4JFixEvaluator(
        result_folder=Path("test_data/sample_results"),
        output_dir=Path("test_output"),
        config=test_config
    )
    result = evaluator.evaluate_bug("Chart_1")
    assert result.bug_slug == "Chart_1"
    assert result.total_attempts > 0
```

## 依赖项

### Python 包

```txt
# requirements.txt
pyyaml>=6.0
gitpython>=3.1.0
tqdm>=4.65.0
pytest>=7.0.0
tree-sitter>=0.20.0
tree-sitter-java>=0.20.0
```

### 系统依赖

- Defects4J v2.0 或 v3.0
- Java 11
- Git >= 1.9
- SVN >= 1.8
- Perl >= 5.0.12

## 部署和使用

### 安装

```bash
# 1. 安装 Python 依赖
pip install -r requirements.txt

# 2. 配置 Defects4J 路径
export D4J_HOME=/path/to/defects4j
export PATH=$PATH:$D4J_HOME/framework/bin

# 3. 验证安装
python -m evaluation.verify_setup
```

### 使用示例

```bash
# 评估单个结果文件夹
python -m evaluation.evaluate \
    --result-folder ppl/result/20260105_132306 \
    --output evaluation_output \
    --workers 4

# 评估特定 bugs
python -m evaluation.evaluate \
    --result-folder ppl/result/20260105_132306 \
    --bugs Chart_1,Chart_2,Closure_10 \
    --verbose

# 使用自定义配置
python -m evaluation.evaluate \
    --result-folder ppl/result/20260105_132306 \
    --config custom_config.yaml
```
