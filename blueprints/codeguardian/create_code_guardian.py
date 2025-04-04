#!/usr/bin/env python3
"""
create_code_guardian.py - Create a CodeGuardian kin for a GitHub repository

Usage:
    python create_code_guardian.py <github_url> [<kin_name>]

Example:
    python create_code_guardian.py https://github.com/Universal-Basic-Compute/kinos10 KinosGuardian
"""

import os
import sys
import shutil
import subprocess
import re
import json
from urllib.parse import urlparse
from datetime import datetime

def get_app_data_dir():
    """Get the application data directory."""
    # Check for environment variable first
    app_data_dir = os.environ.get("KINOS_DATA_DIR")
    if app_data_dir:
        return app_data_dir
    
    # Default locations based on OS
    if os.name == 'nt':  # Windows
        return os.path.join(os.environ.get('APPDATA', ''), 'KinOS')
    else:  # Linux/Mac
        return os.path.join(os.path.expanduser('~'), '.kinos')

def get_blueprints_dir():
    """Get the blueprints directory."""
    return os.path.join(get_app_data_dir(), 'v2', 'blueprints')

def get_local_template_dir():
    """Get the local template directory."""
    # Get the directory of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # The template directory is in the same directory as the script
    return os.path.join(script_dir, 'template')

def sanitize_name(name):
    """Sanitize a name to be used as a kin ID."""
    # Remove special characters and replace spaces with underscores
    sanitized = re.sub(r'[^\w\s-]', '', name)
    sanitized = re.sub(r'[\s-]+', '_', sanitized)
    return sanitized

def extract_repo_info(github_url):
    """Extract repository information from a GitHub URL."""
    parsed_url = urlparse(github_url)
    path_parts = parsed_url.path.strip('/').split('/')
    
    if len(path_parts) < 2:
        raise ValueError("Invalid GitHub URL format. Expected format: https://github.com/owner/repo")
    
    owner = path_parts[0]
    repo = path_parts[1]
    
    return {
        'owner': owner,
        'repo': repo,
        'full_name': f"{owner}/{repo}"
    }

def clone_repository(github_url, target_dir):
    """Clone a GitHub repository to a target directory."""
    print(f"Cloning repository {github_url} to {target_dir}...")
    
    # Remove target directory if it exists
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)
    
    # Clone the repository
    result = subprocess.run(
        ['git', 'clone', github_url, target_dir],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"Error cloning repository: {result.stderr}")
        raise Exception(f"Failed to clone repository: {result.stderr}")
    
    print(f"Repository cloned successfully.")
    return True

def create_code_guardian(github_url, kin_name=None):
    """Create a CodeGuardian kin for a GitHub repository."""
    # Extract repository information
    repo_info = extract_repo_info(github_url)
    
    # Generate kin name if not provided
    if not kin_name:
        kin_name = f"{sanitize_name(repo_info['repo'])}Guardian"
    
    # Get paths
    blueprints_dir = get_blueprints_dir()
    # Use local template directory instead
    codeguardian_template_dir = get_local_template_dir()
    codeguardian_kins_dir = os.path.join(blueprints_dir, 'codeguardian')
    kin_dir = os.path.join(codeguardian_kins_dir, kin_name)
    sources_dir = os.path.join(kin_dir, 'sources')
    repo_dir = os.path.join(sources_dir, 'repo')
    
    # Check if template exists
    if not os.path.exists(codeguardian_template_dir):
        print(f"Error: CodeGuardian template not found at {codeguardian_template_dir}")
        return False
    
    # Create kin directory
    print(f"Creating CodeGuardian kin '{kin_name}' for repository {repo_info['full_name']}...")
    
    # Create kin directory structure
    os.makedirs(kin_dir, exist_ok=True)
    
    # Copy template files
    for item in os.listdir(codeguardian_template_dir):
        source = os.path.join(codeguardian_template_dir, item)
        destination = os.path.join(kin_dir, item)
        
        if os.path.isdir(source):
            shutil.copytree(source, destination, dirs_exist_ok=True)
        else:
            shutil.copy2(source, destination)
    
    # Create sources directory if it doesn't exist
    os.makedirs(sources_dir, exist_ok=True)
    
    # Clone the repository
    clone_repository(github_url, repo_dir)
    
    # Create a README.md file in the sources directory
    with open(os.path.join(sources_dir, 'README.md'), 'w') as f:
        f.write(f"""# {kin_name} - CodeGuardian for {repo_info['full_name']}

This CodeGuardian kin was created to analyze and explain the codebase of [{repo_info['full_name']}]({github_url}).

## Repository Information
- Owner: {repo_info['owner']}
- Repository: {repo_info['repo']}
- GitHub URL: {github_url}

## Creation Information
- Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- CodeGuardian Version: 1.0.0

## Usage
Ask this CodeGuardian about the structure, functionality, and design patterns of the {repo_info['repo']} codebase.
""")
    
    # Create a kinos.txt file with repository information
    with open(os.path.join(kin_dir, 'kinos.txt'), 'w') as f:
        f.write(f"""# {kin_name} - CodeGuardian for {repo_info['full_name']}

This CodeGuardian is specialized in analyzing and explaining the codebase of {repo_info['full_name']}.

## Repository Information
- Owner: {repo_info['owner']}
- Repository: {repo_info['repo']}
- GitHub URL: {github_url}

## Creation Information
- Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
""")
    
    # Update map.json with repository information
    map_path = os.path.join(kin_dir, 'map.json')
    if os.path.exists(map_path):
        with open(map_path, 'r') as f:
            map_data = json.load(f)
        
        # Update map data
        map_data['name'] = kin_name
        map_data['description'] = f"CodeGuardian for {repo_info['full_name']}"
        
        # Add repository component
        repo_component = {
            "id": "repository",
            "name": repo_info['repo'],
            "description": f"Source code from {repo_info['full_name']}",
            "files": [
                {
                    "path": "sources/README.md",
                    "description": "Information about this CodeGuardian instance"
                }
            ]
        }
        
        # Add repository component to components list
        map_data['components'].append(repo_component)
        
        # Add relationship between core and repository
        map_data['relationships'].append({
            "source": "core",
            "target": "repository",
            "type": "analyzes",
            "description": "Core identity analyzes the repository"
        })
        
        # Write updated map data
        with open(map_path, 'w') as f:
            json.dump(map_data, f, indent=2)
    
    print(f"CodeGuardian kin '{kin_name}' created successfully at {kin_dir}")
    print(f"Repository cloned to {repo_dir}")
    print(f"\nYou can now interact with this CodeGuardian to analyze the {repo_info['repo']} codebase.")
    
    return True

def main():
    """Main function."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    github_url = sys.argv[1]
    kin_name = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        create_code_guardian(github_url, kin_name)
    except Exception as e:
        print(f"Error creating CodeGuardian: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
