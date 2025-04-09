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
import json
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
        result = subprocess.run(
            ["git", "--version"],
            check=True,
            capture_output=True,
            text=True
        )
        logger.info(f"Git is installed: {result.stdout.strip()}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logger.error(f"Git is not installed or not in PATH: {str(e)}")
        
        # On Linux/Docker, try to find git in common locations
        if os.name == 'posix':
            common_git_paths = [
                "/usr/bin/git",
                "/usr/local/bin/git",
                "/bin/git"
            ]
            
            for git_path in common_git_paths:
                if os.path.exists(git_path):
                    logger.info(f"Found git at {git_path}, but it's not in PATH")
                    
            # Check if we can install git
            try:
                logger.info("Attempting to install git...")
                # Fix: Use separate commands instead of &&
                update_result = subprocess.run(
                    ["apt-get", "update", "-y"],
                    check=True,
                    capture_output=True,
                    text=True
                )
                logger.info(f"apt-get update result: {update_result.stdout}")
                
                install_result = subprocess.run(
                    ["apt-get", "install", "-y", "git"],
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
                return True
            except Exception as install_error:
                logger.error(f"Failed to install git: {str(install_error)}")
        
        return False

def link_repository(kin_path, github_url, token=None, username=None):
    """
    Link a kin to a GitHub repository.
    
    Args:
        kin_path: Path to the kin directory
        github_url: URL of the GitHub repository
        token: Optional GitHub personal access token
        username: Optional GitHub username
        
    Returns:
        Boolean indicating success
    """
    # Check if git is installed
    if not check_git_installed():
        logger.error("Git is not installed or not in PATH")
        return False
    
    # Log environment information for debugging
    logger.info(f"Operating system: {os.name}")
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"Kin path: {kin_path}")
    
    # Check if kin path exists
    if not os.path.exists(kin_path):
        logger.error(f"Kin path does not exist: {kin_path}")
        return False
    
    # Create a temporary directory for cloning
    with tempfile.TemporaryDirectory() as temp_dir:
        logger.info(f"Created temporary directory: {temp_dir}")
        
        # If token is provided, modify the repo URL to include it
        clone_url = github_url
        if "github.com" in github_url:
            # Get username from parameter or environment
            if not username:
                username = os.getenv("GIT_USERNAME")
                if username:
                    logger.info(f"Using GitHub username from environment variable")
            
            # Get token from parameter or environment
            if not token:
                token = os.getenv("GIT_TOKEN")
                if token:
                    logger.info(f"Using GitHub token from environment variable")
            
            # Construct authentication URL if we have credentials
            if username and token:
                # For GitHub, insert the username and token into the URL
                # Convert https://github.com/user/repo to https://username:token@github.com/user/repo
                parsed_url = urlparse(github_url)
                clone_url = f"https://{username}:{token}@{parsed_url.netloc}{parsed_url.path}"
                # Use a masked URL for logging to avoid exposing the credentials
                safe_clone_url = github_url
                logger.info(f"Using authenticated URL for private repository")
            elif token:
                # If we only have a token, try using it directly
                parsed_url = urlparse(github_url)
                clone_url = f"https://{token}@{parsed_url.netloc}{parsed_url.path}"
                safe_clone_url = github_url
                logger.info(f"Using token-only authentication for repository")
            else:
                safe_clone_url = github_url
                logger.warning("No authentication credentials provided for GitHub repository")
        else:
            safe_clone_url = github_url
        
        # Clone the repository to the temporary directory
        logger.info(f"Cloning repository: {safe_clone_url}")
        try:
            # First, try to verify git is working
            git_version = subprocess.run(
                ["git", "--version"],
                check=True,
                capture_output=True,
                text=True
            )
            logger.info(f"Git version before clone: {git_version.stdout.strip()}")
            
            # Then attempt the clone
            clone_result = subprocess.run(
                ["git", "clone", clone_url, temp_dir],
                check=True,
                capture_output=True,
                text=True
            )
            logger.info(f"Repository cloned successfully to temporary directory")
            logger.info(f"Clone output: {clone_result.stdout}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Git clone failed: {e.stderr}")
            logger.error(f"Command that failed: git clone {safe_clone_url} {temp_dir}")
            
            # Try with --verbose flag for more information
            try:
                logger.info("Retrying clone with --verbose flag...")
                verbose_result = subprocess.run(
                    ["git", "clone", "--verbose", clone_url, temp_dir],
                    check=True,
                    capture_output=True,
                    text=True
                )
                logger.info(f"Verbose clone output: {verbose_result.stdout}")
            except subprocess.CalledProcessError as verbose_e:
                logger.error(f"Verbose git clone also failed: {verbose_e.stderr}")
            
            return False
        
        # Remove .git directory from the temporary clone with error handling
        temp_git_dir = os.path.join(temp_dir, ".git")
        if os.path.exists(temp_git_dir):
            try:
                shutil.rmtree(temp_git_dir)
                logger.info("Removed .git directory from cloned repository")
            except (PermissionError, OSError) as e:
                logger.warning(f"Permission error removing .git directory: {str(e)}")
                logger.info("Attempting to remove files individually...")
                
                # Try to remove files individually
                for root, dirs, files in os.walk(temp_git_dir, topdown=False):
                    for name in files:
                        try:
                            file_path = os.path.join(root, name)
                            os.chmod(file_path, 0o666)  # Make file writable
                            os.unlink(file_path)
                        except Exception as e:
                            logger.warning(f"Could not remove file {name}: {str(e)}")
                    
                    for name in dirs:
                        try:
                            dir_path = os.path.join(root, name)
                            os.rmdir(dir_path)
                        except Exception as e:
                            logger.warning(f"Could not remove directory {name}: {str(e)}")
                
                # Try to remove the main .git directory
                try:
                    os.rmdir(temp_git_dir)
                    logger.info("Successfully removed .git directory after individual cleanup")
                except Exception as e:
                    logger.warning(f"Could not completely remove .git directory: {str(e)}")
                    logger.info("Continuing with remaining files...")
        
        # Remove existing .git directory from kin if it exists
        kin_git_dir = os.path.join(kin_path, ".git")
        if os.path.exists(kin_git_dir):
            try:
                shutil.rmtree(kin_git_dir)
                logger.info("Removed existing .git directory from kin")
            except (PermissionError, OSError) as e:
                logger.warning(f"Permission error removing existing .git directory: {str(e)}")
                logger.info("Attempting to remove files individually...")
                
                # Try to remove files individually
                for root, dirs, files in os.walk(kin_git_dir, topdown=False):
                    for name in files:
                        try:
                            file_path = os.path.join(root, name)
                            os.chmod(file_path, 0o666)  # Make file writable
                            os.unlink(file_path)
                        except Exception as e:
                            logger.warning(f"Could not remove file {name}: {str(e)}")
                    
                    for name in dirs:
                        try:
                            dir_path = os.path.join(root, name)
                            os.rmdir(dir_path)
                        except Exception as e:
                            logger.warning(f"Could not remove directory {name}: {str(e)}")
                
                # Try to remove the main .git directory
                try:
                    os.rmdir(kin_git_dir)
                    logger.info("Successfully removed existing .git directory after individual cleanup")
                except Exception as e:
                    logger.warning(f"Could not completely remove existing .git directory: {str(e)}")
                    logger.info("Continuing with remaining files...")
        
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
            ["git", "config", "user.email", "reynolds.nicorr@gmail.com"],
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
            
        # Create repo_config.json to indicate this is a linked repository
        repo_config = {
            "IS_REPO_LINKED": "true",
            "repository_url": github_url,
            "linked_at": datetime.now().isoformat()
        }
        repo_config_path = os.path.join(kin_path, "repo_config.json")
        with open(repo_config_path, 'w') as f:
            json.dump(repo_config, f, indent=2)
        logger.info(f"Created repo_config.json to mark repository as linked")
            
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
        try:
            subprocess.run(
                ["git", "push", "-u", "origin", "master"],
                cwd=kin_path,
                check=True,
                capture_output=True,
                text=True
            )
        except subprocess.CalledProcessError:
            # Try with 'main' branch if 'master' fails
            logger.info("Push to 'master' failed, trying 'main' branch")
            subprocess.run(
                ["git", "push", "-u", "origin", "main"],
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

def sync_repository(kin_path):
    """
    Synchronize a kin's repository with GitHub by pulling, merging, and pushing.
    
    Args:
        kin_path: Path to the kin directory
        
    Returns:
        Dictionary with status and details of the operation
    """
    # Check if git is installed
    if not check_git_installed():
        logger.error("Git is not installed or not in PATH")
        return {"success": False, "error": "Git is not installed or not in PATH"}
    
    # Check if kin path exists
    if not os.path.exists(kin_path):
        logger.error(f"Kin path does not exist: {kin_path}")
        return {"success": False, "error": f"Kin path does not exist: {kin_path}"}
    
    # Check if this is a git repository
    git_dir = os.path.join(kin_path, ".git")
    if not os.path.exists(git_dir):
        logger.error(f"Not a git repository: {kin_path}")
        return {"success": False, "error": "Not a git repository"}
    
    # Check if repo_config.json exists
    repo_config_path = os.path.join(kin_path, "repo_config.json")
    if not os.path.exists(repo_config_path):
        logger.error(f"repo_config.json not found: {kin_path}")
        return {"success": False, "error": "Repository not linked (repo_config.json not found)"}
    
    # Load repo_config.json
    try:
        with open(repo_config_path, 'r') as f:
            repo_config = json.load(f)
        
        # Check if repository is linked
        if repo_config.get('IS_REPO_LINKED', 'false').lower() != 'true':
            logger.error(f"Repository not linked according to repo_config.json")
            return {"success": False, "error": "Repository not linked"}
        
        # Get repository URL
        repo_url = repo_config.get('repository_url')
        if not repo_url:
            logger.error(f"Repository URL not found in repo_config.json")
            return {"success": False, "error": "Repository URL not found in repo_config.json"}
    except Exception as e:
        logger.error(f"Error reading repo_config.json: {str(e)}")
        return {"success": False, "error": f"Error reading repo_config.json: {str(e)}"}
    
    # Initialize result dictionary
    result = {
        "success": True,
        "operations": [],
        "repository_url": repo_url
    }
    
    try:
        # Configure Git user email and name
        subprocess.run(
            ["git", "config", "user.email", "reynolds.nicorr@gmail.com"],
            cwd=kin_path,
            check=True,
            capture_output=True,
            text=True
        )
        logger.info("Set Git user email to reynolds.nicorr@gmail.com")
        
        subprocess.run(
            ["git", "config", "user.name", "KinOS"],
            cwd=kin_path,
            check=True,
            capture_output=True,
            text=True
        )
        logger.info("Set Git user name to KinOS")
        
        # Get current branch
        branch_cmd = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=kin_path,
            check=True,
            capture_output=True,
            text=True
        )
        current_branch = branch_cmd.stdout.strip()
        result["branch"] = current_branch
        logger.info(f"Current branch: {current_branch}")
        
        # Fetch from remote
        logger.info(f"Fetching from remote...")
        fetch_cmd = subprocess.run(
            ["git", "fetch", "origin"],
            cwd=kin_path,
            check=True,
            capture_output=True,
            text=True
        )
        result["operations"].append({"operation": "fetch", "status": "success"})
        
        # Check if there are changes to pull
        diff_cmd = subprocess.run(
            ["git", "diff", f"HEAD..origin/{current_branch}", "--name-only"],
            cwd=kin_path,
            check=True,
            capture_output=True,
            text=True
        )
        
        changes_to_pull = diff_cmd.stdout.strip()
        if changes_to_pull:
            # There are changes to pull
            logger.info(f"Changes to pull: {changes_to_pull}")
            
            # Pull changes
            logger.info(f"Pulling changes from remote...")
            pull_cmd = subprocess.run(
                ["git", "pull", "origin", current_branch],
                cwd=kin_path,
                check=True,
                capture_output=True,
                text=True
            )
            result["operations"].append({
                "operation": "pull", 
                "status": "success",
                "files_changed": changes_to_pull.count('\n') + 1 if changes_to_pull else 0,
                "message": "Changes pulled successfully"
            })
        else:
            logger.info("No changes to pull")
            result["operations"].append({
                "operation": "pull", 
                "status": "success",
                "files_changed": 0,
                "message": "No changes to pull"
            })
        
        # Check if there are local changes to commit
        status_cmd = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=kin_path,
            check=True,
            capture_output=True,
            text=True
        )
        
        local_changes = status_cmd.stdout.strip()
        if local_changes:
            # There are local changes to commit
            logger.info(f"Local changes to commit: {local_changes}")
            
            # Add all changes
            add_cmd = subprocess.run(
                ["git", "add", "."],
                cwd=kin_path,
                check=True,
                capture_output=True,
                text=True
            )
            
            # Commit changes
            commit_cmd = subprocess.run(
                ["git", "commit", "-m", "Auto-commit during repository sync"],
                cwd=kin_path,
                check=True,
                capture_output=True,
                text=True
            )
            
            # Count files changed
            files_changed = len([line for line in local_changes.split('\n') if line.strip()])
            
            result["operations"].append({
                "operation": "commit", 
                "status": "success",
                "files_changed": files_changed,
                "message": "Local changes committed"
            })
        else:
            logger.info("No local changes to commit")
            result["operations"].append({
                "operation": "commit", 
                "status": "success",
                "files_changed": 0,
                "message": "No local changes to commit"
            })
        
        # Push changes
        logger.info(f"Pushing changes to remote...")
        push_cmd = subprocess.run(
            ["git", "push", "origin", current_branch],
            cwd=kin_path,
            check=True,
            capture_output=True,
            text=True
        )
        result["operations"].append({
            "operation": "push", 
            "status": "success",
            "message": "Changes pushed to remote"
        })
        
        logger.info("Repository synchronized successfully")
        return result
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Git command failed: {e.stderr}")
        return {
            "success": False, 
            "error": f"Git command failed: {e.stderr}",
            "operations": result.get("operations", [])
        }
    except Exception as e:
        logger.error(f"Error synchronizing repository: {str(e)}")
        return {
            "success": False, 
            "error": f"Error synchronizing repository: {str(e)}",
            "operations": result.get("operations", [])
        }

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
