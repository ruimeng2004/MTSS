#!/usr/bin/env python3
"""代码质量检查脚本。

检查代码是否符合 Google Python Style Guide 和项目标准。
"""

import ast
import os
import sys
from pathlib import Path
from typing import List, Tuple


class CodeQualityChecker:
    """代码质量检查器。"""
    
    def __init__(self, root_dir: Path):
        """初始化检查器。
        
        Args:
            root_dir: 项目根目录。
        """
        self.root_dir = root_dir
        self.issues: List[Tuple[str, str, str]] = []
    
    def check_file(self, filepath: Path):
        """检查单个文件。
        
        Args:
            filepath: 文件路径。
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析 AST
            tree = ast.parse(content, filename=str(filepath))
            
            # 检查各项
            self._check_docstrings(tree, filepath)
            self._check_type_hints(tree, filepath)
            self._check_line_length(content, filepath)
            
        except SyntaxError as e:
            self.issues.append((
                str(filepath),
                "SYNTAX_ERROR",
                f"Syntax error: {e}"
            ))
        except Exception as e:
            self.issues.append((
                str(filepath),
                "ERROR",
                f"Error checking file: {e}"
            ))
    
    def _check_docstrings(self, tree: ast.AST, filepath: Path):
        """检查 docstrings。
        
        Args:
            tree: AST 树。
            filepath: 文件路径。
        """
        for node in ast.walk(tree):
            # 检查模块 docstring
            if isinstance(node, ast.Module):
                if not ast.get_docstring(node):
                    self.issues.append((
                        str(filepath),
                        "MISSING_DOCSTRING",
                        "Module missing docstring"
                    ))
            
            # 检查类 docstring
            elif isinstance(node, ast.ClassDef):
                if not ast.get_docstring(node):
                    self.issues.append((
                        str(filepath),
                        "MISSING_DOCSTRING",
                        f"Class '{node.name}' missing docstring"
                    ))
            
            # 检查函数 docstring（公共函数）
            elif isinstance(node, ast.FunctionDef):
                if not node.name.startswith('_'):
                    if not ast.get_docstring(node):
                        self.issues.append((
                            str(filepath),
                            "MISSING_DOCSTRING",
                            f"Function '{node.name}' missing docstring"
                        ))
    
    def _check_type_hints(self, tree: ast.AST, filepath: Path):
        """检查类型注解。
        
        Args:
            tree: AST 树。
            filepath: 文件路径。
        """
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # 跳过私有函数和特殊方法
                if node.name.startswith('_') and not node.name.startswith('__'):
                    continue
                
                # 检查参数类型注解（跳过 self 和 cls）
                for arg in node.args.args:
                    if arg.arg not in ['self', 'cls']:
                        if arg.annotation is None:
                            self.issues.append((
                                str(filepath),
                                "MISSING_TYPE_HINT",
                                f"Function '{node.name}' parameter '{arg.arg}' "
                                f"missing type hint"
                            ))
                
                # 检查返回值类型注解
                if node.returns is None and node.name not in ['__init__']:
                    self.issues.append((
                        str(filepath),
                        "MISSING_TYPE_HINT",
                        f"Function '{node.name}' missing return type hint"
                    ))
    
    def _check_line_length(self, content: str, filepath: Path):
        """检查行长度。
        
        Args:
            content: 文件内容。
            filepath: 文件路径。
        """
        max_length = 80
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # 跳过注释和 docstring
            stripped = line.strip()
            if stripped.startswith('#') or stripped.startswith('"""'):
                continue
            
            if len(line) > max_length:
                self.issues.append((
                    str(filepath),
                    "LINE_TOO_LONG",
                    f"Line {i} exceeds {max_length} characters ({len(line)} chars)"
                ))
    
    def check_directory(self, directory: Path):
        """检查目录中的所有 Python 文件。
        
        Args:
            directory: 目录路径。
        """
        for filepath in directory.rglob("*.py"):
            # 跳过虚拟环境和缓存
            if any(part in filepath.parts for part in ['.venv', '__pycache__', '.pytest_cache']):
                continue
            
            self.check_file(filepath)
    
    def print_report(self):
        """打印检查报告。"""
        if not self.issues:
            print("✓ No code quality issues found!")
            return
        
        print(f"\n⚠ Found {len(self.issues)} code quality issues:\n")
        
        # 按文件分组
        issues_by_file = {}
        for filepath, issue_type, message in self.issues:
            if filepath not in issues_by_file:
                issues_by_file[filepath] = []
            issues_by_file[filepath].append((issue_type, message))
        
        # 打印每个文件的问题
        for filepath, issues in sorted(issues_by_file.items()):
            print(f"\n{filepath}:")
            for issue_type, message in issues:
                print(f"  [{issue_type}] {message}")
        
        print(f"\nTotal issues: {len(self.issues)}")
    
    def get_summary(self) -> dict:
        """获取检查摘要。
        
        Returns:
            包含统计信息的字典。
        """
        issue_types = {}
        for _, issue_type, _ in self.issues:
            issue_types[issue_type] = issue_types.get(issue_type, 0) + 1
        
        return {
            'total_issues': len(self.issues),
            'issue_types': issue_types
        }


def main():
    """主函数。"""
    # 获取项目根目录
    script_dir = Path(__file__).parent
    root_dir = script_dir.parent
    
    # 创建检查器
    checker = CodeQualityChecker(root_dir)
    
    # 检查 evaluation 目录
    evaluation_dir = root_dir / "evaluation"
    if evaluation_dir.exists():
        print(f"Checking code quality in: {evaluation_dir}")
        checker.check_directory(evaluation_dir)
    
    # 打印报告
    checker.print_report()
    
    # 打印摘要
    summary = checker.get_summary()
    if summary['total_issues'] > 0:
        print("\nSummary:")
        for issue_type, count in sorted(summary['issue_types'].items()):
            print(f"  {issue_type}: {count}")
    
    # 返回退出码
    return 1 if summary['total_issues'] > 0 else 0


if __name__ == '__main__':
    sys.exit(main())
