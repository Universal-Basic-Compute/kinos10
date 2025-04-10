#!/usr/bin/env python3
"""
Initialize Atlas Blueprint

This script initializes the Atlas blueprint in the app data directory.
"""

import os
import sys
import shutil
import logging
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

def initialize_atlas_blueprint():
    """Initialize the Atlas blueprint."""
    # Get blueprints directory
    blueprints_dir = get_blueprints_dir()
    
    # Path to Atlas blueprint in source code
    script_dir = os.path.dirname(os.path.abspath(__file__))
    source_dir = os.path.join(os.path.dirname(script_dir), "blueprints", "atlas")
    
    logger.info(f"Looking for Atlas blueprint source at: {source_dir}")
    
    if not os.path.exists(source_dir):
        logger.error(f"Atlas blueprint source directory not found: {source_dir}")
        # Try alternative path
        alt_source_dir = os.path.join(script_dir, "blueprints", "atlas")
        logger.info(f"Trying alternative path: {alt_source_dir}")
        if os.path.exists(alt_source_dir):
            source_dir = alt_source_dir
            logger.info(f"Found Atlas blueprint at alternative path")
        else:
            logger.error(f"Atlas blueprint not found at alternative path either")
            return False
    
    # Create Atlas blueprint directory in app data
    atlas_dir = os.path.join(blueprints_dir, "atlas")
    os.makedirs(atlas_dir, exist_ok=True)
    logger.info(f"Created or verified Atlas blueprint directory: {atlas_dir}")
    
    # Create kins directory
    kins_dir = os.path.join(atlas_dir, "kins")
    os.makedirs(kins_dir, exist_ok=True)
    logger.info(f"Created or verified kins directory: {kins_dir}")
    
    # Copy template
    source_template_dir = os.path.join(source_dir, "template")
    dest_template_dir = os.path.join(atlas_dir, "template")
    
    # Check if source template exists
    if os.path.exists(source_template_dir):
        logger.info(f"Found template directory at: {source_template_dir}")
        
        # Remove existing template if it exists
        if os.path.exists(dest_template_dir):
            logger.info(f"Removing existing template directory: {dest_template_dir}")
            try:
                shutil.rmtree(dest_template_dir)
            except PermissionError:
                logger.warning(f"Permission error removing template directory, trying to remove files individually")
                # Try to remove files individually
                for root, dirs, files in os.walk(dest_template_dir, topdown=False):
                    for name in files:
                        try:
                            os.remove(os.path.join(root, name))
                        except:
                            pass
                    for name in dirs:
                        try:
                            os.rmdir(os.path.join(root, name))
                        except:
                            pass
                try:
                    os.rmdir(dest_template_dir)
                except:
                    logger.warning(f"Could not completely remove template directory")
        
        # Copy template directory
        logger.info(f"Copying template to: {dest_template_dir}")
        try:
            shutil.copytree(source_template_dir, dest_template_dir)
            logger.info(f"Copied Atlas template to {dest_template_dir}")
        except Exception as e:
            logger.error(f"Error copying template: {str(e)}")
            
            # Try custom copy method
            logger.info(f"Trying custom copy method")
            os.makedirs(dest_template_dir, exist_ok=True)
            
            for item in os.listdir(source_template_dir):
                s = os.path.join(source_template_dir, item)
                d = os.path.join(dest_template_dir, item)
                try:
                    if os.path.isdir(s):
                        shutil.copytree(s, d)
                    else:
                        shutil.copy2(s, d)
                    logger.info(f"Copied {s} to {d}")
                except Exception as copy_error:
                    logger.error(f"Error copying {s} to {d}: {str(copy_error)}")
    else:
        logger.warning(f"Source template directory not found: {source_template_dir}")
        
        # Create minimal template
        logger.info(f"Creating minimal template in: {dest_template_dir}")
        os.makedirs(dest_template_dir, exist_ok=True)
        
        # Copy system.txt if it exists
        system_file = os.path.join(source_dir, "system.txt")
        if os.path.exists(system_file):
            logger.info(f"Copying system.txt from: {system_file}")
            shutil.copy2(system_file, os.path.join(dest_template_dir, "system.txt"))
            logger.info(f"Copied system.txt to template")
        else:
            # Create a basic system.txt if it doesn't exist
            logger.info(f"Creating basic system.txt")
            with open(os.path.join(dest_template_dir, "system.txt"), 'w') as f:
                f.write("# ATLAS System: FICTRA Design Critic & Debate Partner\n\n")
                f.write("You are Atlas, an expert critic and debate partner for the FICTRA dual-token system.\n")
        
        # Create empty kinos.txt
        with open(os.path.join(dest_template_dir, "kinos.txt"), 'w') as f:
            f.write("# Atlas Blueprint\n")
        
        # Create modes directory
        modes_dir = os.path.join(dest_template_dir, "modes")
        os.makedirs(modes_dir, exist_ok=True)
        
        # Create analysis mode
        with open(os.path.join(modes_dir, "analysis.txt"), 'w') as f:
            f.write("# Analysis Mode: Informative Responses Without Memorization\n\n")
            f.write("In this mode, you provide information and analysis without memorizing the content of the exchange.\n")
            f.write("This mode is designed for:\n\n")
            f.write("1. Answering administrative or debugging questions\n")
            f.write("2. Providing explanations about your internal functioning\n")
            f.write("3. Assisting with moderation and supervision\n")
            f.write("4. Allowing exploratory interactions without impact on your long-term memory\n")
        
        logger.info(f"Created minimal Atlas template in {dest_template_dir}")
    
    # Verify template directory exists and has content
    if os.path.exists(dest_template_dir):
        template_files = os.listdir(dest_template_dir)
        logger.info(f"Template directory contents: {template_files}")
        
        if not template_files:
            logger.warning(f"Template directory is empty")
            return False
    else:
        logger.error(f"Template directory does not exist after initialization")
        return False
    
    logger.info(f"Atlas blueprint initialized successfully")
    return True

def main():
    logger.info("Starting Atlas blueprint initialization")
    success = initialize_atlas_blueprint()
    
    if success:
        logger.info("Atlas blueprint initialization completed successfully")
        return 0
    else:
        logger.error("Atlas blueprint initialization failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
