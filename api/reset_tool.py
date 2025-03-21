#!/usr/bin/env python3
"""
Reset Tool

This script provides command-line functionality to reset projects or customers
to their initial template state.

Usage:
    python reset_tool.py project <customer> <project_id>
    python reset_tool.py customer <customer>

Options:
    project     Reset a specific project
    customer    Reset a customer and all its projects
"""

import os
import sys
import argparse
import requests
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"reset_tool_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)
logger = logging.getLogger(__name__)

# API base URL
API_BASE_URL = "http://localhost:5000/api/proxy"  # Change this if your API is hosted elsewhere

def reset_project(customer, project_id):
    """Reset a project to its initial template state."""
    url = f"{API_BASE_URL}/projects/{customer}/{project_id}/reset"
    
    logger.info(f"Resetting project: {customer}/{project_id}")
    
    try:
        response = requests.post(url)
        response.raise_for_status()  # Raise exception for 4XX/5XX responses
        
        result = response.json()
        logger.info(f"Reset successful: {result.get('message', 'No message')}")
        return True
        
    except requests.exceptions.RequestException as e:
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_data = e.response.json()
                error_message = error_data.get('error', str(e))
            except:
                error_message = str(e)
        else:
            error_message = str(e)
            
        logger.error(f"Error resetting project: {error_message}")
        return False

def reset_customer(customer):
    """Reset a customer and all its projects to initial template state."""
    url = f"{API_BASE_URL}/customers/{customer}/reset"
    
    logger.info(f"Resetting customer: {customer}")
    
    try:
        response = requests.post(url)
        response.raise_for_status()  # Raise exception for 4XX/5XX responses
        
        result = response.json()
        logger.info(f"Reset successful: {result.get('message', 'No message')}")
        
        # Log details about reset projects
        projects_reset = result.get('projects_reset', 0)
        logger.info(f"Projects reset: {projects_reset}")
        
        if 'results' in result:
            for project_result in result['results']:
                status = project_result.get('status', 'unknown')
                project_id = project_result.get('project_id', 'unknown')
                message = project_result.get('message', 'No message')
                
                if status == 'success':
                    logger.info(f"Project {project_id}: {message}")
                else:
                    logger.warning(f"Project {project_id}: {message}")
        
        return True
        
    except requests.exceptions.RequestException as e:
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_data = e.response.json()
                error_message = error_data.get('error', str(e))
            except:
                error_message = str(e)
        else:
            error_message = str(e)
            
        logger.error(f"Error resetting customer: {error_message}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Reset projects or customers to initial template state")
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Project reset command
    project_parser = subparsers.add_parser('project', help='Reset a project')
    project_parser.add_argument('customer', help='Customer name')
    project_parser.add_argument('project_id', help='Project ID')
    
    # Customer reset command
    customer_parser = subparsers.add_parser('customer', help='Reset a customer and all its projects')
    customer_parser.add_argument('customer', help='Customer name')
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Execute the appropriate command
    if args.command == 'project':
        success = reset_project(args.customer, args.project_id)
    elif args.command == 'customer':
        success = reset_customer(args.customer)
    else:
        parser.print_help()
        return 1
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
