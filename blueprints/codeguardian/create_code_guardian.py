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
        return 'C:\\data\\KinOS'
    elif os.path.exists('/data'):
        return '/data/KinOS'
    else:  # Linux/Mac
        return os.path.join(os.path.expanduser('~'), '.kinos')

def get_blueprints_dir():
    """Get the blueprints directory."""
    app_data_dir = get_app_data_dir()
    
    # Define the v2 blueprints directory path
    v2_blueprints_dir = os.path.join(app_data_dir, 'v2', 'blueprints')
    
    # Create the directory if it doesn't exist
    try:
        # Create the v2 directory first
        v2_dir = os.path.join(app_data_dir, 'v2')
        if not os.path.exists(v2_dir):
            print(f"Creating v2 directory: {v2_dir}")
            os.makedirs(v2_dir, exist_ok=True)
        
        # Then create the blueprints directory
        if not os.path.exists(v2_blueprints_dir):
            print(f"Creating v2 blueprints directory: {v2_blueprints_dir}")
            os.makedirs(v2_blueprints_dir, exist_ok=True)
    except Exception as e:
        print(f"Error creating blueprints directory: {str(e)}")
    
    return v2_blueprints_dir

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
        try:
            print(f"Removing existing directory: {target_dir}")
            shutil.rmtree(target_dir)
        except Exception as e:
            print(f"Error removing existing directory: {str(e)}")
            # Continue anyway, git clone might handle this
    
    # Create parent directory if it doesn't exist
    parent_dir = os.path.dirname(target_dir)
    if not os.path.exists(parent_dir):
        try:
            print(f"Creating parent directory: {parent_dir}")
            os.makedirs(parent_dir, exist_ok=True)
        except Exception as e:
            print(f"Error creating parent directory: {str(e)}")
            raise Exception(f"Failed to create parent directory: {str(e)}")
    
    # Clone the repository
    try:
        print(f"Running git clone command...")
        result = subprocess.run(
            ['git', 'clone', github_url, target_dir],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"Error cloning repository: {result.stderr}")
            raise Exception(f"Failed to clone repository: {result.stderr}")
        
        print(f"Repository cloned successfully.")
        
        # Verify the repository was cloned
        if not os.path.exists(target_dir):
            print(f"Error: Target directory doesn't exist after git clone: {target_dir}")
            raise Exception(f"Target directory doesn't exist after git clone")
        
        # List contents of cloned repository
        repo_contents = os.listdir(target_dir)
        print(f"Repository contents: {repo_contents}")
        
        return True
    except subprocess.SubprocessError as e:
        print(f"Subprocess error during git clone: {str(e)}")
        raise Exception(f"Subprocess error during git clone: {str(e)}")
    except Exception as e:
        print(f"Unexpected error during git clone: {str(e)}")
        raise

def create_code_guardian(github_url, kin_name=None):
    """Create a CodeGuardian kin for a GitHub repository."""
    # Extract repository information
    repo_info = extract_repo_info(github_url)
    
    # Generate kin name if not provided
    if not kin_name:
        kin_name = f"{sanitize_name(repo_info['repo'])}Guardian"
    
    # Get paths
    blueprints_dir = get_blueprints_dir()
    codeguardian_template_dir = get_local_template_dir()
    
    # Print all paths for debugging
    print(f"Blueprints directory: {blueprints_dir}")
    print(f"Template directory: {codeguardian_template_dir}")
    
    # Ensure the codeguardian directory exists in blueprints
    codeguardian_dir = os.path.join(blueprints_dir, 'codeguardian')
    if not os.path.exists(codeguardian_dir):
        print(f"Creating codeguardian directory: {codeguardian_dir}")
        os.makedirs(codeguardian_dir, exist_ok=True)
    
    # Verify the directory was created
    if not os.path.exists(codeguardian_dir):
        print(f"Error: Failed to create codeguardian directory at {codeguardian_dir}")
        return False
    
    # Now define the kin directory path
    kin_dir = os.path.join(codeguardian_dir, "kins", kin_name)
    sources_dir = os.path.join(kin_dir, 'sources')
    repo_dir = os.path.join(sources_dir, 'repo')
    
    print(f"Kin directory will be: {kin_dir}")
    print(f"Sources directory will be: {sources_dir}")
    print(f"Repository directory will be: {repo_dir}")
    
    # Check if template exists
    if not os.path.exists(codeguardian_template_dir):
        print(f"Error: CodeGuardian template not found at {codeguardian_template_dir}")
        return False
    
    # Create kin directory
    print(f"Creating CodeGuardian kin '{kin_name}' for repository {repo_info['full_name']}...")
    
    # Create kin directory structure with explicit checks
    try:
        os.makedirs(kin_dir, exist_ok=True)
        print(f"Created kin directory: {kin_dir}")
        
        # Verify the directory was created
        if not os.path.exists(kin_dir):
            print(f"Error: Failed to create kin directory at {kin_dir}")
            return False
    except Exception as e:
        print(f"Error creating kin directory: {str(e)}")
        return False
    
    # Copy template files with error handling
    try:
        print(f"Copying template files from {codeguardian_template_dir} to {kin_dir}")
        template_items = os.listdir(codeguardian_template_dir)
        print(f"Template directory contains: {template_items}")
        
        for item in template_items:
            source = os.path.join(codeguardian_template_dir, item)
            destination = os.path.join(kin_dir, item)
            
            try:
                if os.path.isdir(source):
                    print(f"Copying directory: {item}")
                    shutil.copytree(source, destination, dirs_exist_ok=True)
                else:
                    print(f"Copying file: {item}")
                    shutil.copy2(source, destination)
            except Exception as e:
                print(f"Error copying {item}: {str(e)}")
    except Exception as e:
        print(f"Error copying template files: {str(e)}")
        return False
    
    # Create sources directory if it doesn't exist
    try:
        print(f"Creating sources directory: {sources_dir}")
        os.makedirs(sources_dir, exist_ok=True)
        
        # Verify the directory was created
        if not os.path.exists(sources_dir):
            print(f"Error: Failed to create sources directory at {sources_dir}")
            return False
    except Exception as e:
        print(f"Error creating sources directory: {str(e)}")
        return False
    
    # Clone the repository with error handling
    try:
        clone_repository(github_url, repo_dir)
        
        # Verify the repository was cloned
        if not os.path.exists(repo_dir) or not os.listdir(repo_dir):
            print(f"Error: Repository directory is empty or doesn't exist: {repo_dir}")
            return False
    except Exception as e:
        print(f"Error cloning repository: {str(e)}")
        return False
    
    # Create a README.md file in the sources directory with error handling
    readme_path = os.path.join(sources_dir, 'README.md')
    try:
        print(f"Creating README.md at {readme_path}")
        with open(readme_path, 'w') as f:
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
        
        # Verify the file was created
        if not os.path.exists(readme_path):
            print(f"Error: Failed to create README.md at {readme_path}")
    except Exception as e:
        print(f"Error creating README.md: {str(e)}")
    
    # Create a kinos.txt file with repository information with error handling
    kinos_path = os.path.join(kin_dir, 'kinos.txt')
    try:
        print(f"Creating kinos.txt at {kinos_path}")
        with open(kinos_path, 'w') as f:
            f.write(f"""# {kin_name} - CodeGuardian for {repo_info['full_name']}

This CodeGuardian is specialized in analyzing and explaining the codebase of {repo_info['full_name']}.

## Repository Information
- Owner: {repo_info['owner']}
- Repository: {repo_info['repo']}
- GitHub URL: {github_url}

## Creation Information
- Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
""")
        
        # Verify the file was created
        if not os.path.exists(kinos_path):
            print(f"Error: Failed to create kinos.txt at {kinos_path}")
    except Exception as e:
        print(f"Error creating kinos.txt: {str(e)}")
    
    # Update map.json with repository information with error handling
    map_path = os.path.join(kin_dir, 'map.json')
    try:
        if os.path.exists(map_path):
            print(f"Updating map.json at {map_path}")
            try:
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
                
                print(f"Successfully updated map.json")
            except json.JSONDecodeError as e:
                print(f"Error parsing map.json: {str(e)}")
            except Exception as e:
                print(f"Error updating map.json: {str(e)}")
        else:
            print(f"Warning: map.json not found at {map_path}")
    except Exception as e:
        print(f"Error handling map.json: {str(e)}")
    
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
