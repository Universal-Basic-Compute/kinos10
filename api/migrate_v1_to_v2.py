#!/usr/bin/env python3
"""
V1 to V2 API Migration Script

This script migrates data from the v1 API structure to the v2 API structure,
converting from the old terminology (customers/projects) to the new terminology (blueprints/kins).

Usage:
    python migrate_v1_to_v2.py [--dry-run]

Options:
    --dry-run    Show what would be done without making changes
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
        logging.FileHandler(f"migration_v1_to_v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
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

def migrate_v1_to_v2(dry_run=False):
    """
    Migrate data from v1 API structure to v2 API structure.
    
    Args:
        dry_run: If True, only show what would be done without making changes
    
    Returns:
        Tuple of (success, message)
    """
    app_data_dir = get_app_data_dir()
    
    # Define paths for v1 and v2 structures
    # V1 uses "customers" directory
    v1_customers_dir = os.path.join(app_data_dir, "customers")
    # V2 uses "blueprints" directory
    v2_blueprints_dir = os.path.join(app_data_dir, "v2", "blueprints")
    
    # Check if v1 directory exists
    if not os.path.exists(v1_customers_dir):
        logger.error(f"V1 customers directory not found: {v1_customers_dir}")
        return False, f"V1 customers directory not found: {v1_customers_dir}"
    
    # Create v2 directory structure if it doesn't exist
    if not dry_run:
        os.makedirs(v2_blueprints_dir, exist_ok=True)
        logger.info(f"Created v2 blueprints directory: {v2_blueprints_dir}")
    else:
        logger.info(f"Would create v2 blueprints directory: {v2_blueprints_dir}")
    
    # Get list of customers (blueprints in v2)
    customers = [d for d in os.listdir(v1_customers_dir) 
                if os.path.isdir(os.path.join(v1_customers_dir, d))]
    
    if not customers:
        logger.warning("No customers found in v1 directory")
        return True, "No customers found to migrate"
    
    logger.info(f"Found {len(customers)} customers to migrate: {customers}")
    
    # Track migration statistics
    stats = {
        "blueprints_total": len(customers),
        "blueprints_migrated": 0,
        "templates_migrated": 0,
        "kins_total": 0,
        "kins_migrated": 0,
        "errors": []
    }
    
    # Process each customer (blueprint in v2)
    for customer in customers:
        logger.info(f"Processing customer: {customer} (will become blueprint)")
        
        v1_customer_dir = os.path.join(v1_customers_dir, customer)
        v2_blueprint_dir = os.path.join(v2_blueprints_dir, customer)
        
        # Create v2 blueprint directory
        if not dry_run:
            os.makedirs(v2_blueprint_dir, exist_ok=True)
            logger.info(f"Created v2 blueprint directory: {v2_blueprint_dir}")
        else:
            logger.info(f"Would create v2 blueprint directory: {v2_blueprint_dir}")
        
        # Migrate template
        v1_template_dir = os.path.join(v1_customer_dir, "template")
        v2_template_dir = os.path.join(v2_blueprint_dir, "template")
        
        if os.path.exists(v1_template_dir):
            if not dry_run:
                # Copy template directory
                if os.path.exists(v2_template_dir):
                    logger.warning(f"V2 template directory already exists, removing: {v2_template_dir}")
                    try:
                        shutil.rmtree(v2_template_dir)
                    except PermissionError:
                        logger.warning(f"Permission error removing {v2_template_dir}, trying to remove files individually")
                        # Try to remove files individually
                        for root, dirs, files in os.walk(v2_template_dir, topdown=False):
                            for name in files:
                                try:
                                    file_path = os.path.join(root, name)
                                    os.chmod(file_path, 0o777)  # Try to change permissions
                                    os.unlink(file_path)
                                except Exception as e:
                                    logger.warning(f"Could not remove file {name}: {str(e)}")
                            for name in dirs:
                                try:
                                    dir_path = os.path.join(root, name)
                                    os.chmod(dir_path, 0o777)  # Try to change permissions
                                    os.rmdir(dir_path)
                                except Exception as e:
                                    logger.warning(f"Could not remove directory {name}: {str(e)}")
                        try:
                            os.rmdir(v2_template_dir)
                        except Exception as e:
                            logger.warning(f"Could not completely remove directory {v2_template_dir}: {str(e)}")
                            logger.warning(f"Will attempt to continue with migration anyway")
                
                logger.info(f"Copying template from {v1_template_dir} to {v2_template_dir}")
                shutil.copytree(v1_template_dir, v2_template_dir)
                stats["templates_migrated"] += 1
            else:
                logger.info(f"Would copy template from {v1_template_dir} to {v2_template_dir}")
                stats["templates_migrated"] += 1
        else:
            logger.warning(f"Template directory not found for customer {customer}")
            stats["errors"].append(f"Template directory not found for customer {customer}")
        
        # Migrate projects (kins in v2)
        # V1 uses "projects" directory
        v1_projects_dir = os.path.join(v1_customer_dir, "projects")
        # V2 uses "kins" directory
        v2_kins_dir = os.path.join(v2_blueprint_dir, "kins")
        
        if os.path.exists(v1_projects_dir):
            # Create v2 kins directory
            if not dry_run:
                os.makedirs(v2_kins_dir, exist_ok=True)
                logger.info(f"Created v2 kins directory: {v2_kins_dir}")
            else:
                logger.info(f"Would create v2 kins directory: {v2_kins_dir}")
            
            # Get list of projects (kins in v2)
            projects = [d for d in os.listdir(v1_projects_dir) 
                       if os.path.isdir(os.path.join(v1_projects_dir, d))]
            
            stats["kins_total"] += len(projects)
            logger.info(f"Found {len(projects)} projects for customer {customer}")
            
            # Process each project (kin in v2)
            for project in projects:
                logger.info(f"Processing project: {customer}/{project} (will become kin)")
                
                v1_project_dir = os.path.join(v1_projects_dir, project)
                v2_kin_dir = os.path.join(v2_kins_dir, project)
                
                if not dry_run:
                    # Copy project directory
                    if os.path.exists(v2_kin_dir):
                        logger.warning(f"V2 kin directory already exists, removing: {v2_kin_dir}")
                        try:
                            shutil.rmtree(v2_kin_dir)
                        except PermissionError:
                            logger.warning(f"Permission error removing {v2_kin_dir}, trying to remove files individually")
                            # Try to remove files individually
                            for root, dirs, files in os.walk(v2_kin_dir, topdown=False):
                                for name in files:
                                    try:
                                        file_path = os.path.join(root, name)
                                        os.chmod(file_path, 0o777)  # Try to change permissions
                                        os.unlink(file_path)
                                    except Exception as e:
                                        logger.warning(f"Could not remove file {name}: {str(e)}")
                                for name in dirs:
                                    try:
                                        dir_path = os.path.join(root, name)
                                        os.chmod(dir_path, 0o777)  # Try to change permissions
                                        os.rmdir(dir_path)
                                    except Exception as e:
                                        logger.warning(f"Could not remove directory {name}: {str(e)}")
                            try:
                                os.rmdir(v2_kin_dir)
                            except Exception as e:
                                logger.warning(f"Could not completely remove directory {v2_kin_dir}: {str(e)}")
                                logger.warning(f"Will attempt to continue with migration anyway")
                    
                    logger.info(f"Copying project from {v1_project_dir} to {v2_kin_dir}")
                    shutil.copytree(v1_project_dir, v2_kin_dir)
                    stats["kins_migrated"] += 1
                else:
                    logger.info(f"Would copy project from {v1_project_dir} to {v2_kin_dir}")
                    stats["kins_migrated"] += 1
        else:
            logger.warning(f"Projects directory not found for customer {customer}")
        
        stats["blueprints_migrated"] += 1
    
    # Create symbolic links or junctions for backward compatibility
    # Link from old customers to v2/blueprints
    v1_to_v2_customers_link = os.path.join(app_data_dir, "customers_v2")
    # Link from old structure to new structure for API compatibility
    v1_api_link = os.path.join(app_data_dir, "v1")
    
    if not dry_run:
        # Create customers_v2 link
        if os.path.exists(v1_to_v2_customers_link):
            logger.warning(f"Customers v2 link already exists, removing: {v1_to_v2_customers_link}")
            if os.path.islink(v1_to_v2_customers_link) or os.path.isdir(v1_to_v2_customers_link):
                try:
                    if os.name == 'nt':  # Windows
                        os.rmdir(v1_to_v2_customers_link)
                    else:
                        os.unlink(v1_to_v2_customers_link)
                except PermissionError as e:
                    logger.warning(f"Permission error removing link {v1_to_v2_customers_link}: {str(e)}")
                    logger.warning("Will attempt to continue with migration anyway")
        
        # Create v1 API link
        if os.path.exists(v1_api_link):
            logger.warning(f"V1 API link already exists, removing: {v1_api_link}")
            if os.path.islink(v1_api_link) or os.path.isdir(v1_api_link):
                try:
                    if os.name == 'nt':  # Windows
                        os.rmdir(v1_api_link)
                    else:
                        os.unlink(v1_api_link)
                except PermissionError as e:
                    logger.warning(f"Permission error removing link {v1_api_link}: {str(e)}")
                    logger.warning("Will attempt to continue with migration anyway")
        
        # Create symbolic links or junctions
        try:
            if os.name == 'nt':  # Windows
                # Use directory junction on Windows
                import subprocess
                subprocess.run(['mklink', '/J', v1_to_v2_customers_link, v2_blueprints_dir], shell=True, check=True)
                logger.info(f"Created directory junction from {v1_to_v2_customers_link} to {v2_blueprints_dir}")
                
                subprocess.run(['mklink', '/J', v1_api_link, v1_customers_dir], shell=True, check=True)
                logger.info(f"Created directory junction from {v1_api_link} to {v1_customers_dir}")
            else:
                # Use symbolic link on Unix-like systems
                os.symlink(v2_blueprints_dir, v1_to_v2_customers_link)
                logger.info(f"Created symbolic link from {v1_to_v2_customers_link} to {v2_blueprints_dir}")
                
                os.symlink(v1_customers_dir, v1_api_link)
                logger.info(f"Created symbolic link from {v1_api_link} to {v1_customers_dir}")
        except Exception as e:
            logger.error(f"Error creating symbolic links: {str(e)}")
            stats["errors"].append(f"Error creating symbolic links: {str(e)}")
    else:
        logger.info(f"Would create symbolic link from {v1_to_v2_customers_link} to {v2_blueprints_dir}")
        logger.info(f"Would create symbolic link from {v1_api_link} to {v1_customers_dir}")
    
    # Log migration statistics
    logger.info(f"Migration statistics: {stats}")
    
    # Create a migration report
    report = f"""
Migration Report
===============

Completed at: {datetime.now().isoformat()}
Dry run: {dry_run}

Statistics:
- Customers → Blueprints: {stats['blueprints_migrated']}/{stats['blueprints_total']} migrated
- Templates: {stats['templates_migrated']} migrated
- Projects → Kins: {stats['kins_migrated']}/{stats['kins_total']} migrated
- Errors: {len(stats['errors'])}

Errors:
{chr(10).join(['- ' + err for err in stats['errors']])}

Paths:
- V1 customers directory: {v1_customers_dir}
- V2 blueprints directory: {v2_blueprints_dir}
- Customers v2 link: {v1_to_v2_customers_link}
- V1 API link: {v1_api_link}

Terminology Changes:
- "customers" -> "blueprints"
- "projects" -> "kins"
"""
    
    report_file = f"migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    logger.info(f"Migration report saved to {report_file}")
    
    return True, f"Migration {'simulation' if dry_run else 'execution'} completed. See {report_file} for details."

def main():
    parser = argparse.ArgumentParser(description="Migrate data from v1 API structure to v2 API structure")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    
    args = parser.parse_args()
    
    logger.info("Starting v1 to v2 API migration")
    if args.dry_run:
        logger.info("Dry run mode: no changes will be made")
    
    success, message = migrate_v1_to_v2(args.dry_run)
    
    if success:
        logger.info(message)
        return 0
    else:
        logger.error(message)
        return 1

if __name__ == "__main__":
    sys.exit(main())
