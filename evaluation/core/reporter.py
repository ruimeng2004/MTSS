"""Reporter for tracking and reporting patch normalization issues.

This module provides the NormalizationReporter class for tracking normalization
results, generating detailed failure reports, and producing batch summaries.
"""

import json
import logging
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from evaluation.core.data_structures import (
    MatchQuality,
    NormalizationStrategy,
    MatchResult
)

logger = logging.getLogger(__name__)


class NormalizationReporter:
    """Reporter for tracking patch normalization results.
    
    This class tracks all normalization attempts, generates detailed failure
    reports for manual review, and produces batch summaries with statistics.
    
    Attributes:
        output_dir: Base output directory for reports.
        reports_dir: Directory for detailed failure reports.
        reports: List of all normalization reports.
    """
    
    def __init__(self, output_dir: Path):
        """Initialize NormalizationReporter.
        
        Args:
            output_dir: Base output directory for all reports.
        """
        self.output_dir = Path(output_dir)
        self.reports_dir = self.output_dir / "normalization_reports"
        
        # Create directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
        # Track all reports
        self.reports: List[Dict[str, Any]] = []
        
        logger.info(f"Initialized NormalizationReporter at {self.output_dir}")
    
    def add_report(
        self,
        bug_slug: str,
        attempt_num: int,
        success: bool,
        strategy_used: Optional[NormalizationStrategy],
        match_quality: MatchQuality,
        match_details: Optional[MatchResult] = None,
        failure_reason: Optional[str] = None,
        requires_manual_review: bool = False
    ):
        """Add a normalization report.
        
        Args:
            bug_slug: Bug identifier.
            attempt_num: Attempt number.
            success: Whether normalization succeeded.
            strategy_used: Strategy that was used (if successful).
            match_quality: Quality of the match.
            match_details: Detailed match result.
            failure_reason: Reason for failure (if failed).
            requires_manual_review: Whether manual review is needed.
        """
        report = {
            'bug_slug': bug_slug,
            'attempt_num': attempt_num,
            'timestamp': datetime.now().isoformat(),
            'success': success,
            'strategy_used': strategy_used.value if strategy_used else None,
            'match_quality': match_quality.value,
            'failure_reason': failure_reason,
            'requires_manual_review': requires_manual_review
        }
        
        # Add match details if available
        if match_details:
            report['match_count'] = match_details.match_count
            report['match_metadata'] = match_details.metadata
        
        self.reports.append(report)
        
        # Generate detailed report if manual review is needed
        if requires_manual_review:
            self._generate_detailed_report(
                bug_slug=bug_slug,
                attempt_num=attempt_num,
                match_quality=match_quality,
                match_details=match_details,
                failure_reason=failure_reason
            )
        
        logger.debug(
            f"Added report for {bug_slug}/{attempt_num}: "
            f"success={success}, quality={match_quality.value}"
        )
    
    def save_failure_report(
        self,
        bug_slug: str,
        attempt_num: int,
        content: str
    ) -> Path:
        """Save a failure report to file.
        
        Args:
            bug_slug: Bug identifier.
            attempt_num: Attempt number.
            content: Report content.
            
        Returns:
            Path to saved report file.
        """
        report_path = self.reports_dir / f"{bug_slug}_{attempt_num}_failure.txt"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Saved failure report to {report_path}")
        return report_path
    
    def _generate_detailed_report(
        self,
        bug_slug: str,
        attempt_num: int,
        match_quality: MatchQuality,
        match_details: Optional[MatchResult],
        failure_reason: Optional[str]
    ):
        """Generate detailed failure report for manual review.
        
        Args:
            bug_slug: Bug identifier.
            attempt_num: Attempt number.
            match_quality: Quality of the match.
            match_details: Detailed match result.
            failure_reason: Reason for failure.
        """
        lines = []
        lines.append("=" * 80)
        lines.append("NORMALIZATION REPORT - REQUIRES MANUAL REVIEW")
        lines.append("=" * 80)
        lines.append(f"Bug: {bug_slug}")
        lines.append(f"Attempt: {attempt_num}")
        lines.append(f"Timestamp: {datetime.now().isoformat()}")
        lines.append(f"Match Quality: {match_quality.value}")
        lines.append("")
        
        if failure_reason:
            lines.append("Failure Reason:")
            lines.append(f"  {failure_reason}")
            lines.append("")
        
        # Add match-specific details
        if match_details:
            self._add_match_details_to_report(
                lines,
                match_quality,
                match_details
            )
        
        # Add suggested actions
        self._add_suggested_actions(lines, match_quality)
        
        lines.append("=" * 80)
        
        # Save report
        report_content = '\n'.join(lines)
        self.save_failure_report(bug_slug, attempt_num, report_content)
    
    def _add_match_details_to_report(
        self,
        lines: List[str],
        match_quality: MatchQuality,
        match_details: MatchResult
    ):
        """Add match details to report lines.
        
        Args:
            lines: Report lines list to append to.
            match_quality: Quality of the match.
            match_details: Detailed match result.
        """
        if match_quality == MatchQuality.EXACT_AMBIGUOUS:
            lines.append(f"Found {match_details.match_count} exact matches:")
            lines.append("")
            
            for i, match in enumerate(match_details.matches, 1):
                lines.append(f"Match {i}:")
                lines.append(
                    f"  Location: Lines {match['start_line']}-{match['end_line']}"
                )
                lines.append("  Context:")
                lines.append("  " + "-" * 76)
                
                # Add matched code snippet
                matched_lines = match['matched_text'].split('\n')
                for line in matched_lines[:10]:  # Show first 10 lines
                    lines.append(f"  {line}")
                
                if len(matched_lines) > 10:
                    lines.append(f"  ... ({len(matched_lines) - 10} more lines)")
                
                lines.append("  " + "-" * 76)
                lines.append("")
        
        elif match_quality == MatchQuality.NOT_FOUND:
            lines.append("ISSUE: Search block not found in source file.")
            lines.append("")
            
            if 'search_text_preview' in match_details.metadata:
                lines.append("Search Block Preview:")
                lines.append("-" * 80)
                preview = match_details.metadata['search_text_preview']
                for line in preview.split('\n')[:20]:
                    lines.append(line)
                lines.append("-" * 80)
                lines.append("")
        
        elif match_quality == MatchQuality.METHOD_NOT_FOUND:
            lines.append("ISSUE: Method not found in source file.")
            lines.append("")
            
            if 'method_signature' in match_details.metadata:
                method_sig = match_details.metadata['method_signature']
                lines.append(f"Method Signature: {method_sig}")
                lines.append("")
        
        # Add metadata (only if not already shown above)
        if match_details.metadata:
            # Filter out keys already displayed
            filtered_metadata = {
                k: v for k, v in match_details.metadata.items()
                if k not in ['search_text_preview', 'matched_text', 'method_signature']
            }
            
            if filtered_metadata:
                lines.append("Additional Metadata:")
                for key, value in filtered_metadata.items():
                    lines.append(f"  {key}: {value}")
                lines.append("")
    
    def _add_suggested_actions(
        self,
        lines: List[str],
        match_quality: MatchQuality
    ):
        """Add suggested actions to report lines.
        
        Args:
            lines: Report lines list to append to.
            match_quality: Quality of the match.
        """
        lines.append("Suggested Actions:")
        lines.append("")
        
        if match_quality == MatchQuality.EXACT_AMBIGUOUS:
            lines.extend([
                "1. Review all match locations above",
                "2. Determine which match is the intended target",
                "3. Consider adding more context to the SEARCH block",
                "4. Or manually specify the target line number",
                ""
            ])
        
        elif match_quality == MatchQuality.NOT_FOUND:
            lines.extend([
                "1. Verify the SEARCH block content matches the source file",
                "2. Check for whitespace differences (tabs vs spaces)",
                "3. Verify the method signature is correct",
                "4. Check if the source file has been modified",
                ""
            ])
        
        elif match_quality == MatchQuality.METHOD_NOT_FOUND:
            lines.extend([
                "1. Verify the method signature is correct",
                "2. Check if the method exists in the source file",
                "3. Check for typos in the method name or parameters",
                ""
            ])
        
        elif match_quality == MatchQuality.PARSE_ERROR:
            lines.extend([
                "1. Check the model output format",
                "2. Verify SEARCH/REPLACE block syntax",
                "3. Check for malformed method signatures",
                ""
            ])
    
    def generate_summary(self) -> Dict[str, Any]:
        """Generate batch normalization summary.
        
        Returns:
            Dictionary containing summary statistics.
        """
        total_patches = len(self.reports)
        
        if total_patches == 0:
            return {
                'total_patches': 0,
                'successful': 0,
                'success_rate': 0.0,
                'match_quality_breakdown': {},
                'requires_manual_review_count': 0,
                'requires_manual_review': []
            }
        
        # Calculate statistics
        successful = sum(1 for r in self.reports if r['success'])
        
        # Count by match quality
        quality_counts = {}
        for quality in MatchQuality:
            count = sum(
                1 for r in self.reports
                if r['match_quality'] == quality.value
            )
            quality_counts[quality.value] = count
        
        # Get bugs requiring manual review
        manual_review_bugs = [
            f"{r['bug_slug']}/{r['attempt_num']}"
            for r in self.reports
            if r['requires_manual_review']
        ]
        
        summary = {
            'total_patches': total_patches,
            'successful': successful,
            'success_rate': (successful / total_patches) * 100.0,
            'match_quality_breakdown': quality_counts,
            'requires_manual_review_count': len(manual_review_bugs),
            'requires_manual_review': manual_review_bugs,
            'timestamp': datetime.now().isoformat()
        }
        
        # Save summary to JSON
        summary_path = self.output_dir / "normalization_summary.json"
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"Normalization summary saved to {summary_path}")
        
        return summary
    
    def print_summary(self):
        """Print summary to console."""
        summary = self.generate_summary()
        
        print("\n" + "=" * 80)
        print("NORMALIZATION SUMMARY")
        print("=" * 80)
        print(f"Total Patches: {summary['total_patches']}")
        print(
            f"Successful: {summary['successful']} "
            f"({summary['success_rate']:.1f}%)"
        )
        print()
        print("Match Quality Breakdown:")
        
        for quality, count in summary['match_quality_breakdown'].items():
            print(f"  {quality}: {count}")
        
        print()
        print(
            f"Requires Manual Review: "
            f"{summary['requires_manual_review_count']}"
        )
        
        if summary['requires_manual_review']:
            print("  Bugs:")
            for bug in summary['requires_manual_review'][:10]:
                print(f"    - {bug}")
            
            if len(summary['requires_manual_review']) > 10:
                remaining = len(summary['requires_manual_review']) - 10
                print(f"    ... and {remaining} more")
        
        print("=" * 80 + "\n")
    
    def save_all_reports(self):
        """Save all reports to JSON file."""
        reports_path = self.output_dir / "all_normalization_reports.json"
        
        with open(reports_path, 'w', encoding='utf-8') as f:
            json.dump(self.reports, f, indent=2)
        
        logger.info(f"All reports saved to {reports_path}")
