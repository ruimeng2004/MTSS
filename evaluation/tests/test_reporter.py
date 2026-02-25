"""Tests for NormalizationReporter class."""

import json
import pytest
from pathlib import Path
from evaluation.core.reporter import NormalizationReporter
from evaluation.core.data_structures import (
    MatchQuality,
    NormalizationStrategy,
    MatchResult
)


class TestNormalizationReporter:
    """Test suite for NormalizationReporter."""
    
    def test_init_creates_directories(self, tmp_path):
        """Test that initialization creates required directories."""
        output_dir = tmp_path / "output"
        reporter = NormalizationReporter(output_dir)
        
        assert reporter.output_dir.exists()
        assert reporter.reports_dir.exists()
        assert reporter.reports_dir == output_dir / "normalization_reports"
        assert len(reporter.reports) == 0
    
    def test_add_report_success(self, tmp_path):
        """Test adding a successful normalization report."""
        reporter = NormalizationReporter(tmp_path)
        
        reporter.add_report(
            bug_slug="Chart_1",
            attempt_num=1,
            success=True,
            strategy_used=NormalizationStrategy.METHOD_SCOPED_EXACT,
            match_quality=MatchQuality.EXACT_UNIQUE,
            requires_manual_review=False
        )
        
        assert len(reporter.reports) == 1
        report = reporter.reports[0]
        
        assert report['bug_slug'] == "Chart_1"
        assert report['attempt_num'] == 1
        assert report['success'] is True
        assert report['strategy_used'] == "method_scoped_exact"
        assert report['match_quality'] == "exact_unique"
        assert report['requires_manual_review'] is False
        assert 'timestamp' in report
    
    def test_add_report_failure(self, tmp_path):
        """Test adding a failed normalization report."""
        reporter = NormalizationReporter(tmp_path)
        
        match_result = MatchResult(
            quality=MatchQuality.NOT_FOUND,
            found=False,
            metadata={'search_text_preview': 'some code'}
        )
        
        reporter.add_report(
            bug_slug="Chart_2",
            attempt_num=1,
            success=False,
            strategy_used=None,
            match_quality=MatchQuality.NOT_FOUND,
            match_details=match_result,
            failure_reason="Search block not found",
            requires_manual_review=True
        )
        
        assert len(reporter.reports) == 1
        report = reporter.reports[0]
        
        assert report['success'] is False
        assert report['strategy_used'] is None
        assert report['match_quality'] == "not_found"
        assert report['failure_reason'] == "Search block not found"
        assert report['requires_manual_review'] is True
        assert report['match_count'] == 0
    
    def test_add_report_ambiguous(self, tmp_path):
        """Test adding an ambiguous match report."""
        reporter = NormalizationReporter(tmp_path)
        
        match_result = MatchResult(
            quality=MatchQuality.EXACT_AMBIGUOUS,
            found=True,
            matches=[
                {'start_line': 10, 'end_line': 15, 'matched_text': 'code1'},
                {'start_line': 30, 'end_line': 35, 'matched_text': 'code2'}
            ],
            metadata={'match_count': 2}
        )
        
        reporter.add_report(
            bug_slug="Chart_3",
            attempt_num=1,
            success=False,
            strategy_used=None,
            match_quality=MatchQuality.EXACT_AMBIGUOUS,
            match_details=match_result,
            failure_reason="Multiple matches found",
            requires_manual_review=True
        )
        
        assert len(reporter.reports) == 1
        report = reporter.reports[0]
        
        assert report['match_quality'] == "exact_ambiguous"
        assert report['match_count'] == 2
        assert report['requires_manual_review'] is True
    
    def test_save_failure_report(self, tmp_path):
        """Test saving a failure report to file."""
        reporter = NormalizationReporter(tmp_path)
        
        content = "Test failure report content"
        report_path = reporter.save_failure_report(
            bug_slug="Chart_1",
            attempt_num=1,
            content=content
        )
        
        assert report_path.exists()
        assert report_path.name == "Chart_1_1_failure.txt"
        
        with open(report_path, 'r') as f:
            saved_content = f.read()
        
        assert saved_content == content
    
    def test_generate_detailed_report_not_found(self, tmp_path):
        """Test generating detailed report for NOT_FOUND case."""
        reporter = NormalizationReporter(tmp_path)
        
        match_result = MatchResult(
            quality=MatchQuality.NOT_FOUND,
            found=False,
            metadata={'search_text_preview': 'int x = 5;'}
        )
        
        reporter.add_report(
            bug_slug="Chart_1",
            attempt_num=1,
            success=False,
            strategy_used=None,
            match_quality=MatchQuality.NOT_FOUND,
            match_details=match_result,
            failure_reason="Search block not found",
            requires_manual_review=True
        )
        
        # Check that report file was created
        report_path = reporter.reports_dir / "Chart_1_1_failure.txt"
        assert report_path.exists()
        
        # Check report content
        with open(report_path, 'r') as f:
            content = f.read()
        
        assert "NORMALIZATION REPORT - REQUIRES MANUAL REVIEW" in content
        assert "Bug: Chart_1" in content
        assert "Attempt: 1" in content
        assert "Match Quality: not_found" in content
        assert "ISSUE: Search block not found in source file." in content
        assert "Suggested Actions:" in content
    
    def test_generate_detailed_report_ambiguous(self, tmp_path):
        """Test generating detailed report for EXACT_AMBIGUOUS case."""
        reporter = NormalizationReporter(tmp_path)
        
        match_result = MatchResult(
            quality=MatchQuality.EXACT_AMBIGUOUS,
            found=True,
            matches=[
                {
                    'start_line': 10,
                    'end_line': 15,
                    'matched_text': 'int x = 5;\nint y = 10;'
                },
                {
                    'start_line': 30,
                    'end_line': 35,
                    'matched_text': 'int x = 5;\nint y = 10;'
                }
            ]
        )
        
        reporter.add_report(
            bug_slug="Chart_2",
            attempt_num=2,
            success=False,
            strategy_used=None,
            match_quality=MatchQuality.EXACT_AMBIGUOUS,
            match_details=match_result,
            failure_reason="Multiple exact matches",
            requires_manual_review=True
        )
        
        # Check report file
        report_path = reporter.reports_dir / "Chart_2_2_failure.txt"
        assert report_path.exists()
        
        with open(report_path, 'r') as f:
            content = f.read()
        
        assert "Found 2 exact matches:" in content
        assert "Match 1:" in content
        assert "Match 2:" in content
        assert "Lines 10-15" in content
        assert "Lines 30-35" in content
    
    def test_generate_detailed_report_method_not_found(self, tmp_path):
        """Test generating detailed report for METHOD_NOT_FOUND case."""
        reporter = NormalizationReporter(tmp_path)
        
        match_result = MatchResult(
            quality=MatchQuality.METHOD_NOT_FOUND,
            found=False,
            metadata={'method_signature': 'public void calculate()'}
        )
        
        reporter.add_report(
            bug_slug="Chart_3",
            attempt_num=1,
            success=False,
            strategy_used=None,
            match_quality=MatchQuality.METHOD_NOT_FOUND,
            match_details=match_result,
            failure_reason="Method not found",
            requires_manual_review=True
        )
        
        report_path = reporter.reports_dir / "Chart_3_1_failure.txt"
        assert report_path.exists()
        
        with open(report_path, 'r') as f:
            content = f.read()
        
        assert "ISSUE: Method not found in source file." in content
        assert "Method Signature: public void calculate()" in content
    
    def test_generate_summary_empty(self, tmp_path):
        """Test generating summary with no reports."""
        reporter = NormalizationReporter(tmp_path)
        
        summary = reporter.generate_summary()
        
        assert summary['total_patches'] == 0
        assert summary['successful'] == 0
        assert summary['success_rate'] == 0.0
        assert summary['requires_manual_review_count'] == 0
        assert len(summary['requires_manual_review']) == 0
    
    def test_generate_summary_with_reports(self, tmp_path):
        """Test generating summary with multiple reports."""
        reporter = NormalizationReporter(tmp_path)
        
        # Add successful reports
        for i in range(3):
            reporter.add_report(
                bug_slug=f"Chart_{i}",
                attempt_num=1,
                success=True,
                strategy_used=NormalizationStrategy.METHOD_SCOPED_EXACT,
                match_quality=MatchQuality.EXACT_UNIQUE,
                requires_manual_review=False
            )
        
        # Add failed reports
        for i in range(2):
            reporter.add_report(
                bug_slug=f"Closure_{i}",
                attempt_num=1,
                success=False,
                strategy_used=None,
                match_quality=MatchQuality.NOT_FOUND,
                failure_reason="Not found",
                requires_manual_review=True
            )
        
        summary = reporter.generate_summary()
        
        assert summary['total_patches'] == 5
        assert summary['successful'] == 3
        assert summary['success_rate'] == 60.0
        assert summary['requires_manual_review_count'] == 2
        assert len(summary['requires_manual_review']) == 2
        assert 'Closure_0/1' in summary['requires_manual_review']
        assert 'Closure_1/1' in summary['requires_manual_review']
    
    def test_generate_summary_match_quality_breakdown(self, tmp_path):
        """Test match quality breakdown in summary."""
        reporter = NormalizationReporter(tmp_path)
        
        # Add reports with different match qualities
        reporter.add_report(
            bug_slug="Chart_1",
            attempt_num=1,
            success=True,
            strategy_used=NormalizationStrategy.METHOD_SCOPED_EXACT,
            match_quality=MatchQuality.EXACT_UNIQUE,
            requires_manual_review=False
        )
        
        reporter.add_report(
            bug_slug="Chart_2",
            attempt_num=1,
            success=False,
            strategy_used=None,
            match_quality=MatchQuality.EXACT_AMBIGUOUS,
            requires_manual_review=True
        )
        
        reporter.add_report(
            bug_slug="Chart_3",
            attempt_num=1,
            success=False,
            strategy_used=None,
            match_quality=MatchQuality.NOT_FOUND,
            requires_manual_review=True
        )
        
        summary = reporter.generate_summary()
        
        breakdown = summary['match_quality_breakdown']
        assert breakdown['exact_unique'] == 1
        assert breakdown['exact_ambiguous'] == 1
        assert breakdown['not_found'] == 1
        assert breakdown['method_not_found'] == 0
        assert breakdown['parse_error'] == 0
    
    def test_generate_summary_saves_json(self, tmp_path):
        """Test that summary is saved to JSON file."""
        reporter = NormalizationReporter(tmp_path)
        
        reporter.add_report(
            bug_slug="Chart_1",
            attempt_num=1,
            success=True,
            strategy_used=NormalizationStrategy.METHOD_SCOPED_EXACT,
            match_quality=MatchQuality.EXACT_UNIQUE,
            requires_manual_review=False
        )
        
        summary = reporter.generate_summary()
        
        # Check JSON file exists
        json_path = tmp_path / "normalization_summary.json"
        assert json_path.exists()
        
        # Load and verify JSON content
        with open(json_path, 'r') as f:
            loaded_summary = json.load(f)
        
        assert loaded_summary['total_patches'] == 1
        assert loaded_summary['successful'] == 1
        assert 'timestamp' in loaded_summary
    
    def test_print_summary(self, tmp_path, capsys):
        """Test printing summary to console."""
        reporter = NormalizationReporter(tmp_path)
        
        reporter.add_report(
            bug_slug="Chart_1",
            attempt_num=1,
            success=True,
            strategy_used=NormalizationStrategy.METHOD_SCOPED_EXACT,
            match_quality=MatchQuality.EXACT_UNIQUE,
            requires_manual_review=False
        )
        
        reporter.add_report(
            bug_slug="Chart_2",
            attempt_num=1,
            success=False,
            strategy_used=None,
            match_quality=MatchQuality.NOT_FOUND,
            requires_manual_review=True
        )
        
        reporter.print_summary()
        
        captured = capsys.readouterr()
        output = captured.out
        
        assert "NORMALIZATION SUMMARY" in output
        assert "Total Patches: 2" in output
        assert "Successful: 1 (50.0%)" in output
        assert "Match Quality Breakdown:" in output
        assert "Requires Manual Review: 1" in output
        assert "Chart_2/1" in output
    
    def test_print_summary_many_manual_reviews(self, tmp_path, capsys):
        """Test printing summary with many manual reviews (truncation)."""
        reporter = NormalizationReporter(tmp_path)
        
        # Add 15 reports requiring manual review
        for i in range(15):
            reporter.add_report(
                bug_slug=f"Chart_{i}",
                attempt_num=1,
                success=False,
                strategy_used=None,
                match_quality=MatchQuality.NOT_FOUND,
                requires_manual_review=True
            )
        
        reporter.print_summary()
        
        captured = capsys.readouterr()
        output = captured.out
        
        assert "Requires Manual Review: 15" in output
        assert "... and 5 more" in output
    
    def test_save_all_reports(self, tmp_path):
        """Test saving all reports to JSON file."""
        reporter = NormalizationReporter(tmp_path)
        
        reporter.add_report(
            bug_slug="Chart_1",
            attempt_num=1,
            success=True,
            strategy_used=NormalizationStrategy.METHOD_SCOPED_EXACT,
            match_quality=MatchQuality.EXACT_UNIQUE,
            requires_manual_review=False
        )
        
        reporter.add_report(
            bug_slug="Chart_2",
            attempt_num=1,
            success=False,
            strategy_used=None,
            match_quality=MatchQuality.NOT_FOUND,
            requires_manual_review=True
        )
        
        reporter.save_all_reports()
        
        # Check JSON file exists
        json_path = tmp_path / "all_normalization_reports.json"
        assert json_path.exists()
        
        # Load and verify JSON content
        with open(json_path, 'r') as f:
            reports = json.load(f)
        
        assert len(reports) == 2
        assert reports[0]['bug_slug'] == "Chart_1"
        assert reports[1]['bug_slug'] == "Chart_2"
    
    def test_multiple_reports_same_bug(self, tmp_path):
        """Test adding multiple reports for the same bug."""
        reporter = NormalizationReporter(tmp_path)
        
        # Add multiple attempts for same bug
        for attempt in range(1, 4):
            reporter.add_report(
                bug_slug="Chart_1",
                attempt_num=attempt,
                success=False,
                strategy_used=None,
                match_quality=MatchQuality.NOT_FOUND,
                requires_manual_review=True
            )
        
        assert len(reporter.reports) == 3
        
        # Check that all reports are tracked
        bug_slugs = [r['bug_slug'] for r in reporter.reports]
        assert bug_slugs.count("Chart_1") == 3
        
        # Check that separate failure reports were created
        for attempt in range(1, 4):
            report_path = reporter.reports_dir / f"Chart_1_{attempt}_failure.txt"
            assert report_path.exists()
