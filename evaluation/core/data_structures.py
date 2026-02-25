"""Data structures for the D4J Fix Evaluation System.

This module defines the core data structures used throughout the evaluation
system, including fix attempts, parsed patches, and evaluation results.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class FixAttempt:
    """Represents a single fix attempt for a bug.
    
    A fix attempt contains the model output, query, and metadata for one
    attempt to fix a specific bug. Each bug may have multiple attempts
    (numbered 1, 2, 3, etc.).
    
    Attributes:
        bug_slug: Bug identifier (e.g., "Chart_1", "Closure_10").
        attempt_num: Attempt number (1, 2, 3, ...).
        attempt_dir: Path to the attempt directory.
        model_output: Content of model_output.txt file.
        query: Content of query.txt file.
        result_json: Parsed content of result.json file.
        modeling_type: Type of task modeling ("edit" or "rewrite").
    """
    
    bug_slug: str
    attempt_num: int
    attempt_dir: Path
    model_output: str
    query: str
    result_json: Dict[str, Any]
    modeling_type: Optional[str] = None
    
    def __post_init__(self):
        """Validate and infer modeling type from result_json."""
        if self.modeling_type is None and self.result_json:
            # Infer modeling type from task field in result.json
            task = self.result_json.get('task', '')
            if 'edit' in task.lower():
                self.modeling_type = 'edit'
            elif 'rewrite' in task.lower() or 'rew' in task.lower() or 'gen' in task.lower():
                self.modeling_type = 'rewrite'
            else:
                self.modeling_type = 'unknown'
    
    @property
    def model_output_path(self) -> Path:
        """Path to model_output.txt file."""
        return self.attempt_dir / 'model_output.txt'
    
    @property
    def query_path(self) -> Path:
        """Path to query.txt file."""
        return self.attempt_dir / 'query.txt'
    
    @property
    def result_json_path(self) -> Path:
        """Path to result.json file."""
        return self.attempt_dir / 'result.json'
    
    def validate(self) -> bool:
        """Validate that all required files exist.
        
        Returns:
            True if all required files exist, False otherwise.
        """
        return (
            self.model_output_path.exists() and
            self.query_path.exists() and
            self.result_json_path.exists()
        )


@dataclass
class SearchReplace:
    """Represents a SEARCH/REPLACE block in Edit format.
    
    Edit format uses SEARCH/REPLACE blocks to specify targeted code changes.
    
    Attributes:
        method_signature: Method signature (e.g., "public void foo()").
        search_block: Code to search for (between <<<<<<< SEARCH and =======).
        replace_block: Code to replace with (between ======= and >>>>>>> REPLACE).
        raw_text: Original raw text of the SEARCH/REPLACE block.
    """
    
    method_signature: str
    search_block: str
    replace_block: str
    raw_text: str = ""


@dataclass
class RewritePatch:
    """Represents a complete method rewrite in Rewrite format.
    
    Rewrite format replaces an entire method with new code.
    
    Attributes:
        method_signature: Method signature (e.g., "public void foo()").
        full_code: Complete replacement code for the method.
        raw_text: Original raw text of the rewrite.
    """
    
    method_signature: str
    full_code: str
    raw_text: str = ""


@dataclass
class ParsedPatch:
    """Represents a parsed patch from model output.
    
    This is the intermediate representation after parsing model_output.txt
    but before normalization to unified diff format.
    
    Attributes:
        bug_slug: Bug identifier.
        attempt_num: Attempt number.
        modeling_type: Type of modeling ("edit" or "rewrite").
        search_replaces: List of SEARCH/REPLACE blocks (for edit format).
        rewrites: List of method rewrites (for rewrite format).
        parse_success: Whether parsing was successful.
        parse_error: Error message if parsing failed.
    """
    
    bug_slug: str
    attempt_num: int
    modeling_type: str
    search_replaces: List[SearchReplace] = field(default_factory=list)
    rewrites: List[RewritePatch] = field(default_factory=list)
    parse_success: bool = True
    parse_error: Optional[str] = None
    
    @property
    def is_edit_format(self) -> bool:
        """Check if this is edit format."""
        return self.modeling_type == 'edit' and len(self.search_replaces) > 0
    
    @property
    def is_rewrite_format(self) -> bool:
        """Check if this is rewrite format."""
        return self.modeling_type == 'rewrite' and len(self.rewrites) > 0
    
    @property
    def patch_count(self) -> int:
        """Total number of patches (SEARCH/REPLACE blocks or rewrites)."""
        return len(self.search_replaces) + len(self.rewrites)


class MatchQuality(Enum):
    """Quality level of a search block match.
    
    This enum defines the different quality levels for matching SEARCH blocks
    in the source code during patch normalization.
    """
    
    EXACT_UNIQUE = "exact_unique"           # Exact match, unique location ✓
    EXACT_AMBIGUOUS = "exact_ambiguous"     # Exact match, multiple locations ⚠
    NOT_FOUND = "not_found"                 # No match found ✗
    METHOD_NOT_FOUND = "method_not_found"   # Method not found ✗
    PARSE_ERROR = "parse_error"             # Parse error ✗


class NormalizationStrategy(Enum):
    """Normalization strategy used for patch conversion.
    
    Defines the different strategies for normalizing patches, from most
    specific (method-scoped) to least specific (manual review).
    """
    
    METHOD_SCOPED_EXACT = "method_scoped_exact"  # Method scope exact match
    FILE_SCOPED_EXACT = "file_scoped_exact"      # File scope exact match
    MANUAL_REVIEW = "manual"                      # Requires manual review


@dataclass
class MatchResult:
    """Result of searching for a code block in source file.
    
    Attributes:
        quality: Quality level of the match.
        found: Whether any match was found.
        matches: List of match locations (each with start_line, end_line, etc.).
        metadata: Additional metadata about the match (method range, etc.).
    """
    
    quality: MatchQuality
    found: bool
    matches: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_unique(self) -> bool:
        """Check if match is unique."""
        return self.quality == MatchQuality.EXACT_UNIQUE
    
    @property
    def is_ambiguous(self) -> bool:
        """Check if match is ambiguous (multiple locations)."""
        return self.quality == MatchQuality.EXACT_AMBIGUOUS
    
    @property
    def match_count(self) -> int:
        """Number of matches found."""
        return len(self.matches)


@dataclass
class NormalizedPatch:
    """Represents a normalized patch in unified diff format.
    
    After normalization, all patches (both edit and rewrite formats) are
    converted to standard unified diff format that can be applied with
    git apply or patch command.
    
    Attributes:
        bug_slug: Bug identifier.
        attempt_num: Attempt number.
        modeling_type: Type of modeling ("edit" or "rewrite").
        diff_content: Unified diff content.
        target_files: List of files modified by this patch.
        metadata: Additional metadata (method signatures, line numbers, etc.).
        normalization_strategy: Strategy used for normalization.
        match_quality: Quality of the match (for edit format).
    """
    
    bug_slug: str
    attempt_num: int
    modeling_type: str
    diff_content: str
    target_files: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    normalization_strategy: Optional[str] = None
    match_quality: Optional[MatchQuality] = None
    
    @property
    def is_valid(self) -> bool:
        """Check if patch is valid (has diff content)."""
        return bool(self.diff_content and self.diff_content.strip())
    
    @property
    def file_count(self) -> int:
        """Number of files modified by this patch."""
        return len(self.target_files)


@dataclass
class ApplyResult:
    """Result of applying a patch to a repository.
    
    Attributes:
        success: Whether patch was applied successfully.
        method: Method used to apply patch ("git_apply", "patch", or "manual").
        error_message: Error message if application failed.
        applied_files: List of files that were modified.
        stdout: Standard output from the apply command.
        stderr: Standard error from the apply command.
    """
    
    success: bool
    method: str
    error_message: Optional[str] = None
    applied_files: List[str] = field(default_factory=list)
    stdout: Optional[str] = None
    stderr: Optional[str] = None


@dataclass
class TestResult:
    """Result of running D4J test suite.
    
    Attributes:
        success: Whether all tests passed.
        total_tests: Total number of tests run.
        passed_tests: Number of tests that passed.
        failed_tests: Number of tests that failed.
        failed_test_cases: Names of failed test cases.
        timeout: Whether execution timed out.
        error_message: Error message if execution failed.
        execution_time: Time taken to run tests (seconds).
        stdout: Standard output from test execution.
        stderr: Standard error from test execution.
    """
    
    success: bool
    total_tests: int
    passed_tests: int
    failed_tests: int
    failed_test_cases: List[str] = field(default_factory=list)
    timeout: bool = False
    error_message: Optional[str] = None
    execution_time: float = 0.0
    stdout: Optional[str] = None
    stderr: Optional[str] = None


@dataclass
class BugEvaluationResult:
    """Evaluation result for a single bug.
    
    Attributes:
        bug_slug: Bug identifier.
        total_attempts: Total number of fix attempts.
        successful_attempt: Attempt number that succeeded (None if all failed).
        modeling_type: Modeling type of successful attempt.
        test_result: Test execution result if patch was applied.
        failure_reasons: List of reasons why fix attempts failed.
        execution_time: Total time spent evaluating this bug.
        all_attempts: List of all attempt results (deprecated).
        failure_reason: Single failure reason (deprecated, use failure_reasons).
    """
    
    bug_slug: str
    total_attempts: int
    successful_attempt: Optional[int] = None
    modeling_type: Optional[str] = None
    test_result: Optional['TestResult'] = None
    failure_reasons: List[str] = field(default_factory=list)
    execution_time: float = 0.0
    all_attempts: List[Dict[str, Any]] = field(default_factory=list)
    failure_reason: Optional[str] = None
    
    @property
    def is_fixed(self) -> bool:
        """Check if bug was successfully fixed."""
        return self.successful_attempt is not None
    
    @property
    def evaluation_time(self) -> float:
        """Alias for execution_time for backward compatibility."""
        return self.execution_time


@dataclass
class BatchEvaluationResult:
    """Evaluation result for a batch of bugs.
    
    Attributes:
        batch_name: Name of the batch (e.g., timestamp folder name).
        total_bugs: Total number of bugs evaluated.
        fixed_bugs: Number of bugs successfully fixed.
        bug_results: List of individual bug evaluation results.
        statistics: Aggregated statistics.
        evaluation_time: Total time taken for batch evaluation (seconds).
    """
    
    batch_name: str
    total_bugs: int
    fixed_bugs: int
    bug_results: List[BugEvaluationResult] = field(default_factory=list)
    statistics: Dict[str, Any] = field(default_factory=dict)
    evaluation_time: float = 0.0
    
    @property
    def fix_rate(self) -> float:
        """Calculate fix rate (percentage of bugs fixed)."""
        if self.total_bugs == 0:
            return 0.0
        return (self.fixed_bugs / self.total_bugs) * 100.0
    
    @property
    def failed_bugs(self) -> int:
        """Number of bugs that failed to be fixed."""
        return self.total_bugs - self.fixed_bugs


@dataclass
class ValidationResult:
    """Result of validating a normalized patch.
    
    Attributes:
        valid: Whether patch is valid.
        error: Error message if validation failed.
    """
    
    valid: bool
    error: Optional[str] = None





# ============================================================================
# Exception Classes
# ============================================================================

class NormalizationError(Exception):
    """Base exception for normalization errors."""
    pass


class SearchBlockNotFoundError(NormalizationError):
    """Raised when SEARCH block cannot be found in source file."""
    pass


class AmbiguousMatchError(NormalizationError):
    """Raised when SEARCH block matches multiple locations."""
    pass


class MethodNotFoundError(NormalizationError):
    """Raised when method cannot be found in source file."""
    pass
