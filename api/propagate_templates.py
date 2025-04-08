#!/usr/bin/env python3
"""
Template Propagation Script

This script propagates changes from blueprint templates to their respective kins,
preserving kin-specific files and changes.

Usage:
    python propagate_templates.py [--blueprint blueprint] [--dry-run]

Options:
    --blueprint blueprint    Only update kins for the specified blueprint
    --dry-run             Show what would be done without making changes
"""

import os
import sys
import shutil
import argparse
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
        # Removed the FileHandler to prevent creating a log file
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

def get_template_files(template_path):
    """Get a list of all files in the template directory."""
    template_files = []
    for root, _, files in os.walk(template_path):
        for file in files:
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, template_path)
            template_files.append(rel_path)
    return template_files

def should_update_file(template_file, kin_file):
    """
    Determine if a kin file should be updated from the template.
    
    Rules:
    1. If the file doesn't exist in the kin, copy it from the template
    2. If the file is a system file (kinos.txt, system.txt, persona.txt), update it
    3. If the file is in a standard directory (modes/, adaptations/, sources/), update it
    4. Never update messages.json or any .json file
    5. Otherwise, preserve the kin file
    """
    # Never update messages.json or any .json file
    if os.path.basename(template_file) == 'messages.json' or template_file.endswith('.json'):
        return False
    
    # If the file doesn't exist in the kin, copy it
    if not os.path.exists(kin_file):
        return True
    
    # Always update system files
    system_files = ['kinos.txt', 'system.txt', 'persona.txt']
    if os.path.basename(template_file) in system_files:
        return True
    
    # Always update files in standard directories
    standard_dirs = ['modes/', 'adaptations/', 'sources/', 'knowledge/', 'memories/', 'images/', 'examples/', 'templates/']
    if any(template_file.startswith(d) for d in standard_dirs):
        return True
    
    # Preserve kin-specific files
    return False

def update_kin(template_path, kin_path, dry_run=False):
    """
    Update a kin from its template, preserving kin-specific files.
    
    Args:
        template_path: Path to the template directory
        kin_path: Path to the kin directory
        dry_run: If True, only show what would be done without making changes
    
    Returns:
        Tuple of (files_added, files_updated, files_preserved)
    """
    if not os.path.exists(template_path):
        logger.error(f"Template path does not exist: {template_path}")
        return (0, 0, 0)
    
    if not os.path.exists(kin_path):
        logger.error(f"kin path does not exist: {kin_path}")
        return (0, 0, 0)
    
    template_files = get_template_files(template_path)
    files_added = 0
    files_updated = 0
    files_preserved = 0
    
    # Ensure standard directories exist in the kin
    standard_dirs = ['modes', 'adaptations', 'sources', 'knowledge']
    for dir_name in standard_dirs:
        dir_path = os.path.join(kin_path, dir_name)
        if not os.path.exists(dir_path):
            logger.info(f"Creating standard directory: {dir_name}")
            if not dry_run:
                os.makedirs(dir_path, exist_ok=True)
    
    for rel_path in template_files:
        template_file = os.path.join(template_path, rel_path)
        kin_file = os.path.join(kin_path, rel_path)
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(kin_file), exist_ok=True)
        
        if should_update_file(rel_path, kin_file):
            if os.path.exists(kin_file):
                action = "Updating"
                files_updated += 1
            else:
                action = "Adding"
                files_added += 1
                
            logger.info(f"{action} file: {rel_path}")
            
            if not dry_run:
                shutil.copy2(template_file, kin_file)
        else:
            logger.debug(f"Preserving kin file: {rel_path}")
            files_preserved += 1
    
    return (files_added, files_updated, files_preserved)

def propagate_templates(blueprint=None, dry_run=False):
    """
    Propagate template changes to all kins.
    
    Args:
        blueprint: If provided, only update kins for this blueprint
        dry_run: If True, only show what would be done without making changes
    """
    blueprints_dir = get_blueprints_dir()
    
    if not os.path.exists(blueprints_dir):
        logger.error(f"blueprints directory not found: {blueprints_dir}")
        return
    
    # Get list of blueprints
    blueprints = [blueprint] if blueprint else os.listdir(blueprints_dir)
    
    # Initialize template from source code first
    kin_templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "blueprints")
    for cust in blueprints:
        blueprint_template_dir = os.path.join(kin_templates_dir, cust, "template")
        if os.path.exists(blueprint_template_dir):
            # Copy template to app data
            dest_template_dir = os.path.join(blueprints_dir, cust, "template")
            if os.path.exists(dest_template_dir):
                shutil.rmtree(dest_template_dir)
            shutil.copytree(blueprint_template_dir, dest_template_dir)
            logger.info(f"Initialized template for blueprint {cust} from source code")
    
    total_kins = 0
    total_files_added = 0
    total_files_updated = 0
    total_files_preserved = 0
    
    for cust in blueprints:
        blueprint_dir = os.path.join(blueprints_dir, cust)
        if not os.path.isdir(blueprint_dir):
            continue
        
        template_path = os.path.join(blueprint_dir, "template")
        if not os.path.exists(template_path):
            logger.warning(f"Template not found for blueprint: {cust}")
            continue
        
        kins_dir = os.path.join(blueprint_dir, "kins")
        if not os.path.exists(kins_dir):
            logger.warning(f"kins directory not found for blueprint: {cust}")
            continue
        
        # Get list of kins
        kins = os.listdir(kins_dir)
        if not kins:
            logger.info(f"No kins found for blueprint: {cust}")
            continue
        
        logger.info(f"Processing {len(kins)} kins for blueprint: {cust}")
        
        for kin in kins:
            kin_path = os.path.join(kins_dir, kin)
            if not os.path.isdir(kin_path):
                continue
            
            logger.info(f"Updating kin: {cust}/{kin}")
            
            files_added, files_updated, files_preserved = update_kin(
                template_path, kin_path, dry_run
            )
            
            logger.info(
                f"kin {cust}/{kin}: "
                f"Added {files_added}, Updated {files_updated}, Preserved {files_preserved} files"
            )
            
            total_kins += 1
            total_files_added += files_added
            total_files_updated += files_updated
            total_files_preserved += files_preserved
    
    logger.info(
        f"Template propagation complete. "
        f"Processed {total_kins} kins: "
        f"Added {total_files_added}, Updated {total_files_updated}, Preserved {total_files_preserved} files"
    )
    
    if dry_run:
        logger.info("This was a dry run. No changes were made.")

def main():
    parser = argparse.ArgumentParser(description="Propagate template changes to kins")
    parser.add_argument("--blueprint", help="Only update kins for the specified blueprint")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    
    args = parser.parse_args()
    
    logger.info("Starting template propagation")
    if args.blueprint:
        logger.info(f"Limiting to blueprint: {args.blueprint}")
    if args.dry_run:
        logger.info("Dry run mode: no changes will be made")
    
    propagate_templates(args.blueprint, args.dry_run)

if __name__ == "__main__":
    main()
