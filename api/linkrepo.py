#!/usr/bin/env python3
"""
Link Kin to GitHub Repository

This script links a kin to a GitHub repository by:
1. Removing any existing .git directory in the kin
2. Cloning the GitHub repository
3. Moving all repository files to the kin root (overwriting conflicts)
4. Initializing git, committing all files, and pushing to the repository

Usage:
    python linkrepo.py <blueprint> <kin_id> <github_url> [--token TOKEN]

Options:
    --token TOKEN    GitHub personal access token for private repositories
                     (can also use GIT_TOKEN environment variable)
"""

import os
import sys
import shutil
import argparse
import subprocess
import logging
import tempfile
from urllib.parse import urlparse
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_app_data_dir():
    """Get the appropriate application data directory based on the platform."""
    if os.name == 'nt':  # Windows
        app_data = 'C:\\data\\KinOS'
        logger.info(f"Using Windows path: {app_data}")
    elif os.path.exists('/data'):
        app_data = '/data/KinOS'
        logger.info(f"Using Render data directory: {app_data}")
    elif os.name == 'posix':  # Linux/Mac
        app_data = os.path.join(os.path.expanduser('~'), '.kinos')
        logger.info(f"Using Linux/Mac home directory: {app_data}")
    else:  # Fallback
        app_data = os.path.join(os.path.expanduser('~'), '.kinos')
        logger.info(f"Using fallback directory: {app_data}")
    
    return app_data

def get_blueprints_dir():
    """Get the blueprints directory."""
    app_data_dir = get_app_data_dir()
    
    # Check both possible locations (with and without v2 prefix)
    v2_blueprints_dir = os.path.join(app_data_dir, "v2", "blueprints")
    direct_blueprints_dir = os.path.join(app_data_dir, "blueprints")
    
    # Prefer v2 path if it exists and has content
    if os.path.exists(v2_blueprints_dir) and os.listdir(v2_blueprints_dir):
        logger.info(f"Using v2 blueprints directory: {v2_blueprints_dir}")
        return v2_blueprints_dir
    
    # Fall back to direct path
    logger.info(f"Using direct blueprints directory: {direct_blueprints_dir}")
    return direct_blueprints_dir

def get_kin_path(blueprint, kin_id):
    """Get the full path to a kin directory."""
    blueprints_dir = get_blueprints_dir()
    if kin_id == "template":
        return os.path.join(blueprints_dir, blueprint, "template")
    else:
        return os.path.join(blueprints_dir, blueprint, "kins", kin_id)

def check_git_installed():
    """Check if git is installed and available in the PATH."""
    try:
        subprocess.run(
            ["git", "--version"],
            check=True,
            capture_output=True,
            text=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def link_repository(kin_path, github_url, token=None):
    """
    Link a kin to a GitHub repository.
    
    Args:
        kin_path: Path to the kin directory
        github_url: URL of the GitHub repository
        token: Optional GitHub personal access token
        
    Returns:
        Boolean indicating success
    """
    # Check if git is installed
    if not check_git_installed():
        logger.error("Git is not installed or not in PATH")
        return False
    
    # Create a temporary directory for cloning
    with tempfile.TemporaryDirectory() as temp_dir:
        logger.info(f"Created temporary directory: {temp_dir}")
        
        # If token is provided, modify the repo URL to include it
        clone_url = github_url
        if token and "github.com" in github_url:
            # For GitHub, insert the token into the URL
            # Convert https://github.com/user/repo to https://token@github.com/user/repo
            parsed_url = urlparse(github_url)
            clone_url = f"https://{token}@{parsed_url.netloc}{parsed_url.path}"
            # Use a masked URL for logging to avoid exposing the token
            safe_clone_url = github_url
            logger.info(f"Using authenticated URL for private repository")
        else:
            safe_clone_url = github_url
        
        # Clone the repository to the temporary directory
        logger.info(f"Cloning repository: {safe_clone_url}")
        try:
            subprocess.run(
                ["git", "clone", clone_url, temp_dir],
                check=True,
                capture_output=True,
                text=True
            )
            logger.info(f"Repository cloned successfully to temporary directory")
        except subprocess.CalledProcessError as e:
            logger.error(f"Git clone failed: {e.stderr}")
            return False
        
        # Remove .git directory from the temporary clone
        temp_git_dir = os.path.join(temp_dir, ".git")
        if os.path.exists(temp_git_dir):
            shutil.rmtree(temp_git_dir)
            logger.info("Removed .git directory from cloned repository")
        
        # Remove existing .git directory from kin if it exists
        kin_git_dir = os.path.join(kin_path, ".git")
        if os.path.exists(kin_git_dir):
            shutil.rmtree(kin_git_dir)
            logger.info("Removed existing .git directory from kin")
        
        # Copy all files from the temporary directory to the kin directory
        logger.info(f"Copying repository files to kin directory: {kin_path}")
        for item in os.listdir(temp_dir):
            src = os.path.join(temp_dir, item)
            dst = os.path.join(kin_path, item)
            
            try:
                if os.path.isdir(src):
                    # If directory exists in kin, remove it first
                    if os.path.exists(dst):
                        shutil.rmtree(dst)
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
                logger.info(f"Copied {item} to kin directory")
            except Exception as e:
                logger.error(f"Error copying {item}: {str(e)}")
    
    # Initialize git repository in the kin directory
    logger.info("Initializing git repository in kin directory")
    try:
        subprocess.run(
            ["git", "init"],
            cwd=kin_path,
            check=True,
            capture_output=True,
            text=True
        )
        
        # Configure git user
        subprocess.run(
            ["git", "config", "user.name", "KinOS"],
            cwd=kin_path,
            check=True,
            capture_output=True,
            text=True
        )
        subprocess.run(
            ["git", "config", "user.email", "kinos@example.com"],
            cwd=kin_path,
            check=True,
            capture_output=True,
            text=True
        )
        
        # Add remote
        subprocess.run(
            ["git", "remote", "add", "origin", github_url],
            cwd=kin_path,
            check=True,
            capture_output=True,
            text=True
        )
        
        # Add all files
        subprocess.run(
            ["git", "add", "."],
            cwd=kin_path,
            check=True,
            capture_output=True,
            text=True
        )
        
        # Commit changes
        commit_message = f"Linked Kin {os.path.basename(kin_path)} to the GitHub repository"
        subprocess.run(
            ["git", "commit", "-m", commit_message],
            cwd=kin_path,
            check=True,
            capture_output=True,
            text=True
        )
        
        # If token is provided, modify the remote URL to include it
        if token and "github.com" in github_url:
            parsed_url = urlparse(github_url)
            remote_url = f"https://{token}@{parsed_url.netloc}{parsed_url.path}"
            subprocess.run(
                ["git", "remote", "set-url", "origin", remote_url],
                cwd=kin_path,
                check=True,
                capture_output=True,
                text=True
            )
        
        # Push to remote
        logger.info("Pushing changes to GitHub repository")
        subprocess.run(
            ["git", "push", "-u", "origin", "master"],
            cwd=kin_path,
            check=True,
            capture_output=True,
            text=True
        )
        
        logger.info("Successfully linked kin to GitHub repository")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Git command failed: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Error linking repository: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Link a kin to a GitHub repository")
    parser.add_argument("blueprint", help="Blueprint name")
    parser.add_argument("kin_id", help="Kin ID")
    parser.add_argument("github_url", help="GitHub repository URL")
    parser.add_argument("--token", help="GitHub personal access token for private repositories")
    
    args = parser.parse_args()
    
    # Get token from environment if not provided
    token = args.token or os.getenv("GIT_TOKEN")
    
    # Get kin path
    kin_path = get_kin_path(args.blueprint, args.kin_id)
    if not os.path.exists(kin_path):
        logger.error(f"Kin not found: {args.blueprint}/{args.kin_id}")
        return 1
    
    # Link repository
    success = link_repository(kin_path, args.github_url, token)
    
    if success:
        logger.info(f"Successfully linked {args.blueprint}/{args.kin_id} to {args.github_url}")
        return 0
    else:
        logger.error(f"Failed to link {args.blueprint}/{args.kin_id} to {args.github_url}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
