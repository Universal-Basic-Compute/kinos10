#!/usr/bin/env python3
"""
Template Propagation Script

This script propagates changes from customer templates to their respective projects,
preserving project-specific files and changes.

Usage:
    python propagate_templates.py [--customer CUSTOMER] [--dry-run]

Options:
    --customer CUSTOMER    Only update projects for the specified customer
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
        logging.StreamHandler(),
        logging.FileHandler(f"template_propagation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
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

def get_customers_dir():
    """Get the customers directory."""
    return os.path.join(get_app_data_dir(), "customers")

def get_template_files(template_path):
    """Get a list of all files in the template directory."""
    template_files = []
    for root, _, files in os.walk(template_path):
        for file in files:
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, template_path)
            template_files.append(rel_path)
    return template_files

def should_update_file(template_file, project_file):
    """
    Determine if a project file should be updated from the template.
    
    Rules:
    1. If the file doesn't exist in the project, copy it from the template
    2. If the file is a system file (kinos.txt, system.txt, persona.txt), update it
    3. If the file is in a standard directory (modes/, adaptations/, sources/), update it
    4. Never update messages.json
    5. Otherwise, preserve the project file
    """
    # Never update messages.json
    if os.path.basename(template_file) == 'messages.json':
        return False
    
    # If the file doesn't exist in the project, copy it
    if not os.path.exists(project_file):
        return True
    
    # Always update system files
    system_files = ['kinos.txt', 'system.txt', 'persona.txt']
    if os.path.basename(template_file) in system_files:
        return True
    
    # Always update files in standard directories
    standard_dirs = ['modes/', 'adaptations/', 'sources/', 'knowledge/']
    if any(template_file.startswith(d) for d in standard_dirs):
        return True
    
    # Preserve project-specific files
    return False

def update_project(template_path, project_path, dry_run=False):
    """
    Update a project from its template, preserving project-specific files.
    
    Args:
        template_path: Path to the template directory
        project_path: Path to the project directory
        dry_run: If True, only show what would be done without making changes
    
    Returns:
        Tuple of (files_added, files_updated, files_preserved)
    """
    if not os.path.exists(template_path):
        logger.error(f"Template path does not exist: {template_path}")
        return (0, 0, 0)
    
    if not os.path.exists(project_path):
        logger.error(f"Project path does not exist: {project_path}")
        return (0, 0, 0)
    
    template_files = get_template_files(template_path)
    files_added = 0
    files_updated = 0
    files_preserved = 0
    
    # Ensure standard directories exist in the project
    standard_dirs = ['modes', 'adaptations', 'sources', 'knowledge']
    for dir_name in standard_dirs:
        dir_path = os.path.join(project_path, dir_name)
        if not os.path.exists(dir_path):
            logger.info(f"Creating standard directory: {dir_name}")
            if not dry_run:
                os.makedirs(dir_path, exist_ok=True)
    
    for rel_path in template_files:
        template_file = os.path.join(template_path, rel_path)
        project_file = os.path.join(project_path, rel_path)
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(project_file), exist_ok=True)
        
        if should_update_file(rel_path, project_file):
            if os.path.exists(project_file):
                action = "Updating"
                files_updated += 1
            else:
                action = "Adding"
                files_added += 1
                
            logger.info(f"{action} file: {rel_path}")
            
            if not dry_run:
                shutil.copy2(template_file, project_file)
        else:
            logger.debug(f"Preserving project file: {rel_path}")
            files_preserved += 1
    
    return (files_added, files_updated, files_preserved)

def propagate_templates(customer=None, dry_run=False):
    """
    Propagate template changes to all projects.
    
    Args:
        customer: If provided, only update projects for this customer
        dry_run: If True, only show what would be done without making changes
    """
    customers_dir = get_customers_dir()
    
    if not os.path.exists(customers_dir):
        logger.error(f"Customers directory not found: {customers_dir}")
        return
    
    # Get list of customers
    customers = [customer] if customer else os.listdir(customers_dir)
    
    total_projects = 0
    total_files_added = 0
    total_files_updated = 0
    total_files_preserved = 0
    
    for cust in customers:
        customer_dir = os.path.join(customers_dir, cust)
        if not os.path.isdir(customer_dir):
            continue
        
        template_path = os.path.join(customer_dir, "template")
        if not os.path.exists(template_path):
            logger.warning(f"Template not found for customer: {cust}")
            continue
        
        projects_dir = os.path.join(customer_dir, "projects")
        if not os.path.exists(projects_dir):
            logger.warning(f"Projects directory not found for customer: {cust}")
            continue
        
        # Get list of projects
        projects = os.listdir(projects_dir)
        if not projects:
            logger.info(f"No projects found for customer: {cust}")
            continue
        
        logger.info(f"Processing {len(projects)} projects for customer: {cust}")
        
        for project in projects:
            project_path = os.path.join(projects_dir, project)
            if not os.path.isdir(project_path):
                continue
            
            logger.info(f"Updating project: {cust}/{project}")
            
            files_added, files_updated, files_preserved = update_project(
                template_path, project_path, dry_run
            )
            
            logger.info(
                f"Project {cust}/{project}: "
                f"Added {files_added}, Updated {files_updated}, Preserved {files_preserved} files"
            )
            
            total_projects += 1
            total_files_added += files_added
            total_files_updated += files_updated
            total_files_preserved += files_preserved
    
    logger.info(
        f"Template propagation complete. "
        f"Processed {total_projects} projects: "
        f"Added {total_files_added}, Updated {total_files_updated}, Preserved {total_files_preserved} files"
    )
    
    if dry_run:
        logger.info("This was a dry run. No changes were made.")

def main():
    parser = argparse.ArgumentParser(description="Propagate template changes to projects")
    parser.add_argument("--customer", help="Only update projects for the specified customer")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    
    args = parser.parse_args()
    
    logger.info("Starting template propagation")
    if args.customer:
        logger.info(f"Limiting to customer: {args.customer}")
    if args.dry_run:
        logger.info("Dry run mode: no changes will be made")
    
    propagate_templates(args.customer, args.dry_run)

if __name__ == "__main__":
    main()
