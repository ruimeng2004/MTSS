"""Environment manager for Defects4J bug checkout and workspace management.

This module provides the EnvironmentManager class for managing Defects4J
environments, checking out bugs, and managing workspace directories.
"""

import logging
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


class EnvironmentManager:
    """Manages Defects4J environment and bug checkouts.
    
    This class handles verification of D4J installation, checking out bugs,
    managing workspace directories, and cleanup operations.
    
    Attributes:
        d4j_path: Path to Defects4J installation directory.
        workspace_dir: Base directory for bug checkouts.
        deprecated_bugs: Set of deprecated bug slugs.
    """
    
    # D4J v3.0 中已弃用的 bugs
    DEPRECATED_BUGS = {
        'Lang_18', 'Lang_25', 'Lang_48',
        'JacksonDatabind_65', 'JacksonDatabind_89'
    }
    
    def __init__(
        self,
        d4j_path: Optional[Path] = None,
        workspace_dir: Optional[Path] = None,
        deprecated_bugs: Optional[List[str]] = None
    ):
        """Initialize EnvironmentManager.
        
        Args:
            d4j_path: Path to Defects4J installation. If None, uses D4J_HOME
                environment variable or searches in PATH.
            workspace_dir: Base directory for bug checkouts. If None, creates
                a temporary directory.
            deprecated_bugs: List of deprecated bug slugs. If None, uses
                default deprecated bugs list.
        """
        # Set D4J path
        if d4j_path:
            self.d4j_path = Path(d4j_path)
        else:
            # Try to find D4J from environment or PATH
            self.d4j_path = self._find_d4j_path()
        
        # Set workspace directory
        if workspace_dir:
            self.workspace_dir = Path(workspace_dir)
        else:
            self.workspace_dir = Path('./d4j_workspace')
        
        # Create workspace directory if it doesn't exist
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        
        # Set deprecated bugs
        if deprecated_bugs:
            self.deprecated_bugs = set(deprecated_bugs)
        else:
            self.deprecated_bugs = self.DEPRECATED_BUGS.copy()
        
        logger.info(
            f"Initialized EnvironmentManager: d4j_path={self.d4j_path}, "
            f"workspace={self.workspace_dir}"
        )
    
    def _find_d4j_path(self) -> Optional[Path]:
        """Find Defects4J installation path.
        
        Tries to find D4J from:
        1. D4J_HOME environment variable
        2. defects4j command in PATH
        
        Returns:
            Path to D4J installation, or None if not found.
        """
        import os
        
        # Try D4J_HOME environment variable
        d4j_home = os.environ.get('D4J_HOME')
        if d4j_home:
            d4j_path = Path(d4j_home)
            if d4j_path.exists():
                logger.debug(f"Found D4J from D4J_HOME: {d4j_path}")
                return d4j_path
        
        # Try to find defects4j in PATH
        try:
            result = subprocess.run(
                ['which', 'defects4j'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                defects4j_bin = Path(result.stdout.strip())
                # D4J_HOME is typically the parent of framework/bin
                d4j_path = defects4j_bin.parent.parent
                logger.debug(f"Found D4J from PATH: {d4j_path}")
                return d4j_path
        except Exception as e:
            logger.debug(f"Could not find defects4j in PATH: {e}")
        
        logger.warning("Could not find Defects4J installation")
        return None
    
    def _get_d4j_command(self) -> str:
        """Get the defects4j command path.
        
        Returns:
            Path to defects4j command.
        """
        if self.d4j_path:
            return str(self.d4j_path / 'framework' / 'bin' / 'defects4j')
        return 'defects4j'
    
    def verify_installation(self) -> bool:
        """Verify that Defects4J is properly installed.
        
        Checks:
        1. D4J path exists
        2. defects4j command is executable
        3. Can run basic D4J commands
        
        Returns:
            True if D4J is properly installed, False otherwise.
        """
        logger.info("Verifying Defects4J installation...")
        
        # Check if D4J path exists
        if not self.d4j_path or not self.d4j_path.exists():
            logger.error(f"D4J path does not exist: {self.d4j_path}")
            return False
        
        # Try to run defects4j command
        try:
            d4j_cmd = self._get_d4j_command()
            
            result = subprocess.run(
                [d4j_cmd, 'info', '-p', 'Lang'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info("Defects4J installation verified successfully")
                return True
            else:
                logger.error(
                    f"defects4j command failed: {result.stderr}"
                )
                return False
                
        except FileNotFoundError:
            logger.error("defects4j command not found in PATH")
            return False
        except subprocess.TimeoutExpired:
            logger.error("defects4j command timed out")
            return False
        except Exception as e:
            logger.error(f"Error verifying D4J installation: {e}")
            return False
    
    def checkout_bug(
        self,
        bug_slug: str,
        version: str = 'b',
        work_dir: Optional[Path] = None
    ) -> Path:
        """Checkout a specific bug from Defects4J.
        
        Args:
            bug_slug: Bug identifier (e.g., "Chart_1", "Lang_10").
            version: Version to checkout ('b' for buggy, 'f' for fixed).
            work_dir: Directory to checkout into. If None, creates a
                subdirectory in workspace_dir.
        
        Returns:
            Path to the checked out repository.
            
        Raises:
            RuntimeError: If checkout fails.
        """
        # Parse bug slug
        parts = bug_slug.split('_')
        if len(parts) != 2:
            raise ValueError(f"Invalid bug slug format: {bug_slug}")
        
        project = parts[0]
        bug_id = parts[1]
        
        # Determine checkout directory
        if work_dir:
            checkout_dir = Path(work_dir)
        else:
            checkout_dir = self.workspace_dir / f"{bug_slug}_{version}"
        
        # Remove existing directory if it exists
        if checkout_dir.exists():
            logger.warning(
                f"Checkout directory already exists, removing: {checkout_dir}"
            )
            shutil.rmtree(checkout_dir)
        
        # Create parent directory
        checkout_dir.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(
            f"Checking out {bug_slug} (version={version}) to {checkout_dir}"
        )
        
        # Run defects4j checkout command
        try:
            d4j_cmd = self._get_d4j_command()
            
            result = subprocess.run(
                [
                    d4j_cmd,
                    'checkout',
                    '-p', project,
                    '-v', f'{bug_id}{version}',
                    '-w', str(checkout_dir)
                ],
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes timeout for checkout
            )
            
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout
                raise RuntimeError(
                    f"Failed to checkout {bug_slug}: {error_msg}"
                )
            
            logger.info(f"Successfully checked out {bug_slug} to {checkout_dir}")
            
            # Normalize line endings to LF for consistent patch application
            self._normalize_line_endings(checkout_dir)
            
            return checkout_dir
            
        except subprocess.TimeoutExpired:
            raise RuntimeError(
                f"Checkout of {bug_slug} timed out after 5 minutes"
            )
        except Exception as e:
            raise RuntimeError(f"Error checking out {bug_slug}: {e}")
    
    def _normalize_line_endings(self, repo_path: Path):
        """Normalize line endings in Java files to LF.
        
        Defects4J projects may use CRLF line endings which cause
        patch application to fail. This method converts all Java
        files to use LF line endings.
        
        Args:
            repo_path: Path to the checked out repository.
        """
        logger.debug(f"Normalizing line endings in {repo_path}")
        
        normalized_count = 0
        for java_file in repo_path.rglob('*.java'):
            try:
                # Read file in binary mode
                content = java_file.read_bytes()
                
                # Check if file has CRLF
                if b'\r\n' in content or b'\r' in content:
                    # Convert CRLF to LF
                    content_lf = content.replace(b'\r\n', b'\n').replace(b'\r', b'\n')
                    java_file.write_bytes(content_lf)
                    normalized_count += 1
            except Exception as e:
                logger.warning(
                    f"Failed to normalize line endings in {java_file}: {e}"
                )
        
        if normalized_count > 0:
            logger.info(
                f"Normalized line endings in {normalized_count} Java files"
            )
    
    def is_deprecated(self, bug_slug: str) -> bool:
        """Check if a bug is deprecated in D4J v3.0.
        
        Args:
            bug_slug: Bug identifier (e.g., "Chart_1").
            
        Returns:
            True if bug is deprecated, False otherwise.
        """
        return bug_slug in self.deprecated_bugs
    
    def cleanup(self, repo_path: Path, force: bool = False):
        """Clean up a checked out repository.
        
        Args:
            repo_path: Path to repository to clean up.
            force: If True, removes directory even if it's not in workspace.
        
        Raises:
            ValueError: If repo_path is not in workspace and force=False.
        """
        repo_path = Path(repo_path)
        
        # Safety check: ensure repo is in workspace directory
        if not force:
            try:
                repo_path.relative_to(self.workspace_dir)
            except ValueError:
                raise ValueError(
                    f"Repository {repo_path} is not in workspace directory "
                    f"{self.workspace_dir}. Use force=True to override."
                )
        
        if repo_path.exists():
            logger.info(f"Cleaning up repository: {repo_path}")
            shutil.rmtree(repo_path)
        else:
            logger.debug(f"Repository does not exist: {repo_path}")
    
    def get_bug_info(self, bug_slug: str) -> Optional[dict]:
        """Get information about a bug from Defects4J.
        
        Args:
            bug_slug: Bug identifier (e.g., "Chart_1").
            
        Returns:
            Dictionary with bug information, or None if bug not found.
        """
        parts = bug_slug.split('_')
        if len(parts) != 2:
            logger.error(f"Invalid bug slug format: {bug_slug}")
            return None
        
        project = parts[0]
        bug_id = parts[1]
        
        try:
            d4j_cmd = self._get_d4j_command()
            result = subprocess.run(
                [d4j_cmd, 'info', '-p', project, '-b', bug_id],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.error(f"Failed to get info for {bug_slug}")
                return None
            
            # Parse output (simplified - actual parsing would be more complex)
            info = {
                'bug_slug': bug_slug,
                'project': project,
                'bug_id': bug_id,
                'raw_output': result.stdout
            }
            
            return info
            
        except Exception as e:
            logger.error(f"Error getting bug info for {bug_slug}: {e}")
            return None
    
    def compile_bug(self, repo_path: Path) -> bool:
        """Compile a checked out bug.
        
        Args:
            repo_path: Path to checked out repository.
            
        Returns:
            True if compilation succeeded, False otherwise.
        """
        logger.info(f"Compiling bug at {repo_path}")
        
        try:
            d4j_cmd = self._get_d4j_command()
            result = subprocess.run(
                [d4j_cmd, 'compile'],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes timeout
            )
            
            if result.returncode == 0:
                logger.info("Compilation successful")
                return True
            else:
                logger.error(f"Compilation failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("Compilation timed out after 10 minutes")
            return False
        except Exception as e:
            logger.error(f"Error during compilation: {e}")
            return False
    
    def get_workspace_size(self) -> int:
        """Get total size of workspace directory in bytes.
        
        Returns:
            Total size in bytes.
        """
        import os
        
        total_size = 0
        
        for dirpath, dirnames, filenames in os.walk(self.workspace_dir):
            for filename in filenames:
                filepath = Path(dirpath) / filename
                try:
                    total_size += filepath.stat().st_size
                except Exception:
                    pass
        
        return total_size
    
    def cleanup_all(self):
        """Clean up entire workspace directory.
        
        Warning: This removes all checked out repositories!
        """
        if self.workspace_dir.exists():
            logger.warning(f"Cleaning up entire workspace: {self.workspace_dir}")
            shutil.rmtree(self.workspace_dir)
            self.workspace_dir.mkdir(parents=True, exist_ok=True)
