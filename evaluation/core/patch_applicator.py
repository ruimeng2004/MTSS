"""Patch applicator for applying normalized patches to repositories.

This module provides the PatchApplicator class for applying unified diff
patches to code repositories using git apply or patch command.
"""

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from evaluation.core.data_structures import ApplyResult, NormalizedPatch

logger = logging.getLogger(__name__)


class PatchApplicator:
    """Applies normalized patches to code repositories.
    
    This class handles applying unified diff patches to repositories using
    either git apply or the patch command. It also supports rollback to
    restore the original state.
    
    Attributes:
        repo_path: Path to the code repository.
        backup_dir: Directory for storing backups before applying patches.
    """
    
    def __init__(self, repo_path: Path):
        """Initialize PatchApplicator.
        
        Args:
            repo_path: Path to the code repository where patches will be
                applied.
        
        Raises:
            ValueError: If repo_path doesn't exist or is not a directory.
        """
        self.repo_path = Path(repo_path)
        
        if not self.repo_path.exists():
            raise ValueError(f"Repository path does not exist: {repo_path}")
        
        if not self.repo_path.is_dir():
            raise ValueError(f"Repository path is not a directory: {repo_path}")
        
        # Create backup directory
        self.backup_dir = self.repo_path / ".patch_backup"
        self.backup_dir.mkdir(exist_ok=True)
        
        logger.info(f"Initialized PatchApplicator for: {self.repo_path}")
    
    def apply(self, patch: NormalizedPatch) -> ApplyResult:
        """Apply a normalized patch to the repository.
        
        Tries multiple strategies in order:
        1. git apply (preferred)
        2. patch command (fallback)
        
        Args:
            patch: Normalized patch to apply.
        
        Returns:
            ApplyResult with success status and details.
        """
        logger.info(
            f"Applying patch for {patch.bug_slug} "
            f"(attempt {patch.attempt_num})"
        )
        
        # Check for empty patch
        if not patch.diff_content or not patch.diff_content.strip():
            logger.error("Cannot apply empty patch")
            return ApplyResult(
                success=False,
                method="none",
                error_message="Patch content is empty - no changes to apply"
            )
        
        # Backup affected files before applying
        self._backup_files(patch.target_files)
        
        # Try git apply first
        result = self.apply_with_git(patch.diff_content)
        if result.success:
            logger.info("Patch applied successfully using git apply")
            return result
        
        logger.warning(f"git apply failed: {result.error_message}")
        
        # Rollback and try patch command
        self.rollback()
        result = self.apply_with_patch(patch.diff_content)
        if result.success:
            logger.info("Patch applied successfully using patch command")
            return result
        
        logger.error(f"All patch application methods failed")
        return result
    
    def apply_with_git(self, diff_content: str) -> ApplyResult:
        """Apply patch using git apply command.
        
        Args:
            diff_content: Unified diff content.
        
        Returns:
            ApplyResult with success status and details.
        """
        logger.debug("Attempting to apply patch with git apply")
        
        # Write diff to temporary file
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.patch',
            delete=False
        ) as f:
            f.write(diff_content)
            patch_file = Path(f.name)
        
        try:
            # Try different -p values to handle various path prefixes
            # Standard git patches have "a/" and "b/" prefixes
            # -p0: Keep full path (a/src/main/java/Foo.java → a/src/main/java/Foo.java) 
            # -p1: Strip one level (a/src/main/java/Foo.java → src/main/java/Foo.java) ← Most common!
            # -p2: Strip two levels (a/src/main/java/Foo.java → main/java/Foo.java)
            # -p3: Strip three levels (a/src/main/java/Foo.java → java/Foo.java)
            # -p4: Strip four levels (a/src/main/java/Foo.java → Foo.java)
            
            # Try -p1 first (most common for git patches), then others
            for p_value in [1, 0, 2, 3, 4]:
                result = subprocess.run(
                    ['git', 'apply', f'-p{p_value}', '--verbose', str(patch_file)],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    # Extract applied files from git apply output
                    applied_files = self._extract_applied_files_from_git(
                        result.stdout
                    )
                    
                    logger.debug(f"git apply succeeded with -p{p_value}")
                    return ApplyResult(
                        success=True,
                        method='git_apply',
                        applied_files=applied_files,
                        stdout=result.stdout,
                        stderr=result.stderr
                    )
                else:
                    logger.debug(f"git apply with -p{p_value} failed, trying next...")
            
            # All attempts failed
            return ApplyResult(
                success=False,
                method='git_apply',
                error_message=result.stderr or result.stdout,
                stdout=result.stdout,
                stderr=result.stderr
            )
        
        except subprocess.TimeoutExpired:
            return ApplyResult(
                success=False,
                method='git_apply',
                error_message='git apply timed out after 30 seconds'
            )
        except FileNotFoundError:
            return ApplyResult(
                success=False,
                method='git_apply',
                error_message='git command not found'
            )
        except Exception as e:
            return ApplyResult(
                success=False,
                method='git_apply',
                error_message=f'Unexpected error: {str(e)}'
            )
        finally:
            # Clean up temporary patch file
            try:
                patch_file.unlink()
            except Exception:
                pass
    
    def apply_with_patch(self, diff_content: str) -> ApplyResult:
        """Apply patch using patch command.
        
        Args:
            diff_content: Unified diff content.
        
        Returns:
            ApplyResult with success status and details.
        """
        logger.debug("Attempting to apply patch with patch command")
        
        # Write diff to temporary file
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.patch',
            delete=False
        ) as f:
            f.write(diff_content)
            patch_file = Path(f.name)
        
        try:
            # Try different -p values to handle various path prefixes
            # -p0: no stripping
            # -p1: strip one level (most common for git-style patches)
            # -p2: strip two levels
            # -p3: strip three levels
            # -p4: strip four levels
            for p_value in [0, 1, 2, 3, 4]:
                result = subprocess.run(
                    ['patch', f'-p{p_value}', '-u', '-N', '-i', str(patch_file)],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    # Extract applied files from patch output
                    applied_files = self._extract_applied_files_from_patch(
                        result.stdout
                    )
                    
                    logger.debug(f"patch command succeeded with -p{p_value}")
                    return ApplyResult(
                        success=True,
                        method='patch',
                        applied_files=applied_files,
                        stdout=result.stdout,
                        stderr=result.stderr
                    )
                else:
                    logger.debug(f"patch with -p{p_value} failed, trying next...")
                    # Rollback any partial changes before trying next p_value
                    self.rollback()
            
            # All attempts failed
            return ApplyResult(
                success=False,
                method='patch',
                error_message=result.stderr or result.stdout,
                stdout=result.stdout,
                stderr=result.stderr
            )
        
        except subprocess.TimeoutExpired:
            return ApplyResult(
                success=False,
                method='patch',
                error_message='patch command timed out after 30 seconds'
            )
        except FileNotFoundError:
            return ApplyResult(
                success=False,
                method='patch',
                error_message='patch command not found'
            )
        except Exception as e:
            return ApplyResult(
                success=False,
                method='patch',
                error_message=f'Unexpected error: {str(e)}'
            )
        finally:
            # Clean up temporary patch file
            try:
                patch_file.unlink()
            except Exception:
                pass
    
    def rollback(self):
        """Rollback to original state by restoring backed up files.
        
        Restores all files that were backed up before applying the patch.
        """
        logger.info("Rolling back to original state")
        
        if not self.backup_dir.exists():
            logger.warning("No backup directory found, nothing to rollback")
            return
        
        # Restore all backed up files
        for backup_file in self.backup_dir.iterdir():
            if backup_file.is_file():
                # Extract original path from backup filename
                # Backup format: filename.ext.backup
                original_name = backup_file.name
                if original_name.endswith('.backup'):
                    original_name = original_name[:-7]  # Remove .backup
                
                # Find the original file path
                original_path = self._find_original_path(original_name)
                
                if original_path:
                    try:
                        shutil.copy2(backup_file, original_path)
                        logger.debug(f"Restored: {original_path}")
                    except Exception as e:
                        logger.error(
                            f"Failed to restore {original_path}: {e}"
                        )
        
        # Clean up backup directory
        try:
            shutil.rmtree(self.backup_dir)
            self.backup_dir.mkdir(exist_ok=True)
            logger.info("Rollback completed")
        except Exception as e:
            logger.error(f"Failed to clean up backup directory: {e}")
    
    def _backup_files(self, target_files: list):
        """Backup files before applying patch.
        
        Args:
            target_files: List of file paths to backup.
        """
        for file_path_str in target_files:
            file_path = self.repo_path / file_path_str
            
            if not file_path.exists():
                logger.warning(f"Target file does not exist: {file_path}")
                continue
            
            # Create backup with unique name
            backup_name = f"{file_path.name}.backup"
            backup_path = self.backup_dir / backup_name
            
            # If backup already exists, add counter
            counter = 1
            while backup_path.exists():
                backup_name = f"{file_path.name}.backup.{counter}"
                backup_path = self.backup_dir / backup_name
                counter += 1
            
            try:
                shutil.copy2(file_path, backup_path)
                logger.debug(f"Backed up: {file_path} -> {backup_path}")
            except Exception as e:
                logger.error(f"Failed to backup {file_path}: {e}")
    
    def _find_original_path(self, filename: str) -> Optional[Path]:
        """Find the original path of a backed up file.
        
        Args:
            filename: Name of the backed up file.
        
        Returns:
            Path to the original file, or None if not found.
        """
        # Search for the file in the repository
        for file_path in self.repo_path.rglob(filename):
            if file_path.is_file() and file_path != self.backup_dir / filename:
                return file_path
        
        return None
    
    def _extract_applied_files_from_git(self, output: str) -> list:
        """Extract list of applied files from git apply output.
        
        Args:
            output: stdout from git apply command.
        
        Returns:
            List of file paths that were modified.
        """
        applied_files = []
        
        for line in output.split('\n'):
            # git apply output format: "Checking patch path/to/file..."
            if 'Checking patch' in line:
                # Extract file path
                parts = line.split('Checking patch')
                if len(parts) > 1:
                    file_path = parts[1].strip().rstrip('...')
                    applied_files.append(file_path)
        
        return applied_files
    
    def _extract_applied_files_from_patch(self, output: str) -> list:
        """Extract list of applied files from patch command output.
        
        Args:
            output: stdout from patch command.
        
        Returns:
            List of file paths that were modified.
        """
        applied_files = []
        
        for line in output.split('\n'):
            # patch output format: "patching file path/to/file"
            if 'patching file' in line:
                # Extract file path
                parts = line.split('patching file')
                if len(parts) > 1:
                    file_path = parts[1].strip()
                    applied_files.append(file_path)
        
        return applied_files
    
    def cleanup(self):
        """Clean up backup directory and temporary files."""
        if self.backup_dir.exists():
            try:
                shutil.rmtree(self.backup_dir)
                logger.debug("Cleaned up backup directory")
            except Exception as e:
                logger.error(f"Failed to clean up backup directory: {e}")
