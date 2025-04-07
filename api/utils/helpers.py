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
        '.aider*',                       # Aider files
        'aider_logs.txt',                # Aider logs
        'messages.json',                 # Messages file (handled separately)
        'system.txt',                    # System file (handled separately)
        '.gitignore'                     # Git ignore file
    ]

    # Check against always-ignore patterns first
    for pattern in always_ignore:
        # Directory pattern (e.g. .git/)
        if pattern.endswith('/'):
            dir_pattern = pattern[:-1]
            if file_path.startswith(dir_pattern + os.sep) or file_path == dir_pattern:
                return True
                
        # File extension pattern (e.g. *.pyc)
        elif pattern.startswith('*.'):
            if file_path.endswith(pattern[1:]):
                return True
                
        # Wildcard prefix pattern (e.g. .aider*)
        elif '*' in pattern:
            prefix = pattern.split('*')[0]
            if file_path.startswith(prefix):
                return True
                
        # Exact match
        elif file_path == pattern or file_path.startswith(pattern + os.sep):
            return True

    # Then check against gitignore patterns if provided
    if ignore_patterns:
        for pattern in ignore_patterns:
            if pattern.endswith('/'):
                if file_path.startswith(pattern[:-1] + os.sep):
                    return True
            elif pattern.startswith('*.'):
                if file_path.endswith(pattern[1:]):
                    return True
            elif file_path == pattern:
                return True
            elif pattern.startswith('**/'):
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
