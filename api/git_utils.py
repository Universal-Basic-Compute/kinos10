#!/usr/bin/env python3
"""
Git Utilities

This module provides robust Git command execution functions that handle various
environment configurations and edge cases.
"""

import os
import sys
import shutil
import subprocess
import logging
from config import logger

def find_git_executable():
    """
    Find the Git executable in the system.
    
    Returns:
        str: Path to Git executable, "git_with_shell" for shell=True usage, or None if not found
    """
    # First, try the direct approach that works in linkrepo.py
    try:
        # This is the simplest approach and should work if git is in PATH
        subprocess.run(
            ["git", "--version"],
            check=True,
            capture_output=True,
            text=True
        )
        logger.info("Git is available in PATH")
        return "git"  # Just return the command name
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logger.debug(f"Simple git check failed: {str(e)}")
    
    # If that fails, try with shell=True which might help in some environments
    try:
        subprocess.run(
            "git --version",
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        logger.info("Git is available when using shell=True")
        return "git_with_shell"  # Special return value for shell=True usage
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logger.debug(f"Shell git check failed: {str(e)}")
    
    # If both approaches fail, try specific paths
    git_paths = [
        "/usr/bin/git",
        "/usr/local/bin/git",
        "/bin/git",
        # Add more common paths for Render environment
        "/opt/render/project/bin/git",
        "/opt/render/bin/git",
        # Windows paths
        "C:\\Program Files\\Git\\bin\\git.exe",
        "C:\\Program Files (x86)\\Git\\bin\\git.exe"
    ]
    
    for path in git_paths:
        if os.path.exists(path):
            try:
                subprocess.run(
                    [path, "--version"],
                    check=True,
                    capture_output=True,
                    text=True
                )
                logger.info(f"Found Git at specific path: {path}")
                return path
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                logger.debug(f"Git at {path} exists but command failed: {str(e)}")
    
    # Last resort: try to find git using 'which' command
    try:
        result = subprocess.run(
            "which git",
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        git_path = result.stdout.strip()
        if git_path:
            logger.info(f"Found Git using 'which' command: {git_path}")
            return git_path
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logger.debug(f"Could not find Git using 'which' command: {str(e)}")
    
    # Try to install git if it's not found
    try:
        logger.info("Attempting to install git...")
        install_result = subprocess.run(
            "apt-get update && apt-get install -y git",
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        logger.info(f"Git installation result: {install_result.stdout}")
        
        # Check if git is now installed
        verify_result = subprocess.run(
            ["git", "--version"],
            check=True,
            capture_output=True,
            text=True
        )
        logger.info(f"Git is now installed: {verify_result.stdout.strip()}")
        return "git"
    except Exception as install_error:
        logger.error(f"Failed to install git: {str(install_error)}")
    
    # If we get here, we need to modify how we use git in the calling code
    logger.error("Git executable not found after trying all methods")
    logger.info("Will try to use 'git' with shell=True in git operations")
    return "git_with_shell"  # Special return value to indicate shell=True should be used

def check_git_installed():
    """
    Check if git is installed and available.
    
    Returns:
        bool: True if git is installed, False otherwise
    """
    git_exe = find_git_executable()
    return git_exe is not None and git_exe != ""

def run_git_command(command, cwd=None, check=True, capture_output=True):
    """
    Run a git command with robust error handling.
    
    Args:
        command: Git command as a list of strings or a single string for shell=True
        cwd: Working directory for the command
        check: Whether to raise an exception on command failure
        capture_output: Whether to capture command output
        
    Returns:
        subprocess.CompletedProcess: Result of the command
        
    Raises:
        subprocess.CalledProcessError: If the command fails and check=True
        FileNotFoundError: If git is not found
    """
    # Find git executable
    git_exe = find_git_executable()
    if not git_exe:
        raise FileNotFoundError("Git executable not found")
    
    # Determine whether to use shell=True
    use_shell = (git_exe == "git_with_shell")
    
    try:
        if use_shell:
            # Convert command list to string if needed
            if isinstance(command, list):
                command = " ".join(command)
            
            logger.info(f"Running git command with shell=True: {command}")
            result = subprocess.run(
                command,
                cwd=cwd,
                check=check,
                capture_output=capture_output,
                text=True,
                shell=True
            )
        else:
            # If command is a string, convert to list
            if isinstance(command, str):
                command = command.split()
            
            # Replace 'git' with the full path to git executable if needed
            if command[0] == 'git' and git_exe != 'git':
                command[0] = git_exe
            
            logger.info(f"Running git command: {command}")
            result = subprocess.run(
                command,
                cwd=cwd,
                check=check,
                capture_output=capture_output,
                text=True
            )
        
        return result
    except subprocess.CalledProcessError as e:
        logger.error(f"Git command failed: {e.stderr if hasattr(e, 'stderr') and e.stderr else str(e)}")
        raise
    except FileNotFoundError as e:
        logger.error(f"Git executable not found: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error running git command: {str(e)}")
        raise

def configure_git_for_merge(kin_path):
    """
    Configure Git to use merge strategy and prioritize our changes.
    
    Args:
        kin_path: Path to the kin directory
    """
    try:
        # Configure Git pull strategy
        run_git_command(
            ["git", "config", "pull.rebase", "false"],
            cwd=kin_path
        )
        logger.info("Configured Git to use merge strategy for pulls")
        
        # Configure Git to prioritize our changes in merges
        run_git_command(
            ["git", "config", "merge.ours.driver", "true"],
            cwd=kin_path
        )
        logger.info("Configured Git to prioritize our changes in merges")
        
        # Create a .gitattributes file to use the ours merge driver for conflicts
        gitattributes_path = os.path.join(kin_path, ".gitattributes")
        with open(gitattributes_path, 'w') as f:
            f.write("* merge=ours\n")
        logger.info("Created .gitattributes file to prioritize our changes")
        
        # Add the .gitattributes file to the repository
        run_git_command(
            ["git", "add", ".gitattributes"],
            cwd=kin_path
        )
    except Exception as e:
        logger.warning(f"Error configuring Git: {str(e)}")
