import os
import json
import datetime
import logging
from config import logger

def should_ignore_file(file_path, ignore_patterns=None):
    """
    Check if a file should be ignored based on common patterns and .gitignore.
    
    Args:
        file_path: Relative path of the file to check
        ignore_patterns: Optional list of patterns from .gitignore
        
    Returns:
        Boolean indicating if the file should be ignored
    """
    # Common version control and editor files to always ignore
    always_ignore = [
        '.git', '.svn', '.hg',           # Version control
        '.vscode', '.idea', '.vs',       # Editors
        '__pycache__', '*.pyc', '*.pyo', # Python
        '.DS_Store',                     # macOS
        '.aider*'                        # Aider files
    ]
    
    if ignore_patterns is None:
        ignore_patterns = []
    
    # Check against always-ignore patterns first
    for pattern in always_ignore:
        if pattern.endswith('/'):
            # Directory pattern
            dir_pattern = pattern[:-1]
            if file_path == dir_pattern or file_path.startswith(f"{dir_pattern}/"):
                return True
        elif pattern.startswith('*.'):
            # File extension pattern
            if file_path.endswith(pattern[1:]):
                return True
        elif '*' in pattern:
            # Simple wildcard pattern (e.g., .aider*)
            prefix = pattern.split('*')[0]
            suffix = pattern.split('*')[1]
            if file_path.startswith(prefix) and file_path.endswith(suffix):
                return True
        elif file_path == pattern or file_path.startswith(f"{pattern}/"):
            # Exact match or directory
            return True
    
    # Always include .gitignore itself
    if file_path == '.gitignore':
        return False
        
    # Then check against gitignore patterns
    for pattern in ignore_patterns:
        # Simple pattern matching (can be expanded for more complex gitignore rules)
        if pattern.endswith('/'):
            # Directory pattern
            dir_pattern = pattern[:-1]
            if file_path == dir_pattern or file_path.startswith(f"{dir_pattern}/"):
                return True
        elif pattern.startswith('*.'):
            # File extension pattern
            if file_path.endswith(pattern[1:]):
                return True
        elif file_path == pattern:
            # Exact match
            return True
        elif pattern.startswith('**/'):
            # Recursive wildcard
            if file_path.endswith(pattern[3:]):
                return True
    return False

def load_gitignore(kin_path):
    """
    Load patterns from .gitignore file.
    
    Args:
        kin_path: Path to the kin directory
        
    Returns:
        List of ignore patterns
    """
    gitignore_path = os.path.join(kin_path, '.gitignore')
    ignore_patterns = []
    
    if os.path.exists(gitignore_path):
        try:
            with open(gitignore_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        ignore_patterns.append(line)
        except Exception as e:
            logger.warning(f"Error reading .gitignore: {str(e)}")
    
    return ignore_patterns
