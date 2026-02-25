"""Input handler for reading and parsing fix result folders."""

import json
import logging
from pathlib import Path
from typing import List, Optional

from evaluation.core.data_structures import FixAttempt

logger = logging.getLogger(__name__)


class InputHandler:
    """Handles reading and parsing fix result folders."""
    
    def __init__(self, result_folder: Path):
        """Initialize InputHandler."""
        self.result_folder = Path(result_folder)
        
        if not self.result_folder.exists():
            raise ValueError(
                f"Result folder does not exist: {self.result_folder}"
            )
        
        if not self.result_folder.is_dir():
            raise ValueError(
                f"Result folder is not a directory: {self.result_folder}"
            )
        
        logger.info(f"Initialized InputHandler for: {self.result_folder}")

    
    def validate_structure(self) -> bool:
        """Validate the structure of the result folder.
        
        Returns:
            True if structure is valid, False otherwise.
        """
        try:
            bugs = self.list_bugs()
            
            if not bugs:
                logger.error("No bug folders found in result folder")
                return False
            
            logger.info(f"Found {len(bugs)} bug folders")
            
            valid_bugs = 0
            for bug_slug in bugs:
                attempts = self.list_attempts(bug_slug)
                if attempts:
                    valid_bugs += 1
                    logger.debug(
                        f"Bug {bug_slug} has {len(attempts)} attempts"
                    )
            
            if valid_bugs == 0:
                logger.error("No bugs with valid attempts found")
                return False
            
            logger.info(
                f"Structure validation passed: {valid_bugs} bugs with "
                f"attempts"
            )
            return True
            
        except Exception as e:
            logger.error(f"Structure validation failed: {e}")
            return False
    
    def list_bugs(self) -> List[str]:
        """List all bug slugs in the result folder.
        
        Returns:
            List of bug slugs (e.g., ["Chart_1", "Closure_10"]).
        """
        bugs = []
        
        try:
            for item in self.result_folder.iterdir():
                if not item.is_dir():
                    continue
                
                if '_' in item.name:
                    parts = item.name.split('_')
                    if len(parts) == 2 and parts[1].isdigit():
                        bugs.append(item.name)
                        logger.debug(f"Found bug: {item.name}")
            
            bugs.sort()
            logger.info(f"Listed {len(bugs)} bugs")
            return bugs
            
        except Exception as e:
            logger.error(f"Error listing bugs: {e}")
            return []
    
    def list_attempts(self, bug_slug: str) -> List[int]:
        """List all attempt numbers for a specific bug.
        
        Args:
            bug_slug: Bug identifier (e.g., "Chart_1").
        
        Returns:
            List of attempt numbers (e.g., [1, 2, 3]).
        """
        bug_dir = self.result_folder / bug_slug
        
        if not bug_dir.exists() or not bug_dir.is_dir():
            logger.warning(f"Bug directory not found: {bug_slug}")
            return []
        
        attempts = []
        
        try:
            for item in bug_dir.iterdir():
                if not item.is_dir():
                    continue
                
                if item.name.isdigit():
                    attempt_num = int(item.name)
                    
                    if self._validate_attempt_files(item):
                        attempts.append(attempt_num)
                        logger.debug(
                            f"Found valid attempt: {bug_slug}/{attempt_num}"
                        )
                    else:
                        logger.warning(
                            f"Attempt {bug_slug}/{attempt_num} missing "
                            f"required files"
                        )
            
            attempts.sort()
            logger.info(f"Listed {len(attempts)} attempts for {bug_slug}")
            return attempts
            
        except Exception as e:
            logger.error(f"Error listing attempts for {bug_slug}: {e}")
            return []
    
    def load_attempt(
        self, 
        bug_slug: str, 
        attempt_num: int
    ) -> Optional[FixAttempt]:
        """Load a specific fix attempt.
        
        Args:
            bug_slug: Bug identifier (e.g., "Chart_1").
            attempt_num: Attempt number (e.g., 1, 2, 3).
        
        Returns:
            FixAttempt object if successful, None if loading failed.
        """
        attempt_dir = self.result_folder / bug_slug / str(attempt_num)
        
        if not attempt_dir.exists() or not attempt_dir.is_dir():
            logger.error(
                f"Attempt directory not found: {bug_slug}/{attempt_num}"
            )
            return None
        
        try:
            model_output_path = attempt_dir / 'model_output.txt'
            if not model_output_path.exists():
                logger.error(
                    f"model_output.txt not found: {bug_slug}/{attempt_num}"
                )
                return None
            
            with open(model_output_path, 'r', encoding='utf-8') as f:
                model_output = f.read()
            
            query_path = attempt_dir / 'query.txt'
            if not query_path.exists():
                logger.error(
                    f"query.txt not found: {bug_slug}/{attempt_num}"
                )
                return None
            
            with open(query_path, 'r', encoding='utf-8') as f:
                query = f.read()
            
            result_json_path = attempt_dir / 'result.json'
            if not result_json_path.exists():
                logger.error(
                    f"result.json not found: {bug_slug}/{attempt_num}"
                )
                return None
            
            with open(result_json_path, 'r', encoding='utf-8') as f:
                result_json = json.load(f)
            
            fix_attempt = FixAttempt(
                bug_slug=bug_slug,
                attempt_num=attempt_num,
                attempt_dir=attempt_dir,
                model_output=model_output,
                query=query,
                result_json=result_json
            )
            
            logger.info(
                f"Loaded attempt: {bug_slug}/{attempt_num} "
                f"(modeling_type: {fix_attempt.modeling_type})"
            )
            
            return fix_attempt
            
        except json.JSONDecodeError as e:
            logger.error(
                f"Invalid JSON in result.json for "
                f"{bug_slug}/{attempt_num}: {e}"
            )
            return None
        except Exception as e:
            logger.error(
                f"Error loading attempt {bug_slug}/{attempt_num}: {e}"
            )
            return None
    
    def _validate_attempt_files(self, attempt_dir: Path) -> bool:
        """Validate that an attempt directory contains required files.
        
        Args:
            attempt_dir: Path to attempt directory.
        
        Returns:
            True if all required files exist, False otherwise.
        """
        required_files = ['model_output.txt', 'query.txt', 'result.json']
        
        for filename in required_files:
            file_path = attempt_dir / filename
            if not file_path.exists() or not file_path.is_file():
                return False
        
        return True
    
    def load_all_attempts(self, bug_slug: str) -> List[FixAttempt]:
        """Load all attempts for a specific bug.
        
        Args:
            bug_slug: Bug identifier (e.g., "Chart_1").
        
        Returns:
            List of FixAttempt objects.
        """
        attempt_nums = self.list_attempts(bug_slug)
        attempts = []
        
        for attempt_num in attempt_nums:
            fix_attempt = self.load_attempt(bug_slug, attempt_num)
            if fix_attempt:
                attempts.append(fix_attempt)
        
        logger.info(
            f"Loaded {len(attempts)} attempts for {bug_slug}"
        )
        
        return attempts
    
    def load_all_bugs(self) -> List[List[FixAttempt]]:
        """Load all attempts for all bugs in the result folder.
        
        Returns:
            List of lists, where each inner list contains all attempts
            for a single bug.
        """
        bugs = self.list_bugs()
        all_attempts = []
        
        for bug_slug in bugs:
            bug_attempts = self.load_all_attempts(bug_slug)
            if bug_attempts:
                all_attempts.append(bug_attempts)
        
        logger.info(
            f"Loaded attempts for {len(all_attempts)} bugs"
        )
        
        return all_attempts
