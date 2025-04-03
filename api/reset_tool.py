#!/usr/bin/env python3
"""
Reset Tool

This script provides command-line functionality to reset kins or blueprints
to their initial template state.

Usage:
    python reset_tool.py kin <blueprint> <kin_id>
    python reset_tool.py blueprint <blueprint>

Options:
    kin     Reset a specific kin
    blueprint    Reset a blueprint and all its kins
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

def reset_kin(blueprint, kin_id):
    """Reset a kin to its initial template state."""
    url = f"{API_BASE_URL}/kins/{blueprint}/{kin_id}/reset"
    
    logger.info(f"Resetting kin: {blueprint}/{kin_id}")
    
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
            
        logger.error(f"Error resetting kin: {error_message}")
        return False

def reset_blueprint(blueprint):
    """Reset a blueprint and all its kins to initial template state."""
    url = f"{API_BASE_URL}/blueprints/{blueprint}/reset"
    
    logger.info(f"Resetting blueprint: {blueprint}")
    
    try:
        response = requests.post(url)
        response.raise_for_status()  # Raise exception for 4XX/5XX responses
        
        result = response.json()
        logger.info(f"Reset successful: {result.get('message', 'No message')}")
        
        # Log details about reset kins
        kins_reset = result.get('kins_reset', 0)
        logger.info(f"kins reset: {kins_reset}")
        
        if 'results' in result:
            for kin_result in result['results']:
                status = kin_result.get('status', 'unknown')
                kin_id = kin_result.get('kin_id', 'unknown')
                message = kin_result.get('message', 'No message')
                
                if status == 'success':
                    logger.info(f"kin {kin_id}: {message}")
                else:
                    logger.warning(f"kin {kin_id}: {message}")
        
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
            
        logger.error(f"Error resetting blueprint: {error_message}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Reset kins or blueprints to initial template state")
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # kin reset command
    kin_parser = subparsers.add_parser('kin', help='Reset a kin')
    kin_parser.add_argument('blueprint', help='blueprint name')
    kin_parser.add_argument('kin_id', help='kin ID')
    
    # blueprint reset command
    blueprint_parser = subparsers.add_parser('blueprint', help='Reset a blueprint and all its kins')
    blueprint_parser.add_argument('blueprint', help='blueprint name')
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Execute the appropriate command
    if args.command == 'kin':
        success = reset_kin(args.blueprint, args.kin_id)
    elif args.command == 'blueprint':
        success = reset_blueprint(args.blueprint)
    else:
        parser.print_help()
        return 1
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
