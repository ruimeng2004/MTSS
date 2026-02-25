from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class BugView(str, Enum):
    report = "report"
    test = "test"
    error = "error"
    error_plus_test = "error_plus_test"
    buggy_code = "buggy_code"
    buggy_code_obfuscated = "buggy_code_obfuscated"
    buggy_code_mixed = "buggy_code_mixed"


@dataclass(frozen=True)
class ViewSpec:
    view: BugView
    source_file: str | None
    derived_from: BugView | None = None


DEFAULT_VIEW_SPECS: tuple[ViewSpec, ...] = (
    ViewSpec(view=BugView.report, source_file="query.txt"),
    ViewSpec(view=BugView.test, source_file="FAILED_TEST.txt"),
    ViewSpec(view=BugView.error, source_file="ERROR_MESSAGE.txt"),
    ViewSpec(view=BugView.error_plus_test, source_file=None, derived_from=BugView.error),
    ViewSpec(view=BugView.buggy_code, source_file="BUGGY_CODE.txt"),
    ViewSpec(view=BugView.buggy_code_obfuscated, source_file=None, derived_from=BugView.buggy_code),
    ViewSpec(view=BugView.buggy_code_mixed, source_file=None, derived_from=BugView.buggy_code),
)
