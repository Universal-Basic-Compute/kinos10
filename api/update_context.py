#!/usr/bin/env python3
"""
Context Updater CLI Tool

This script allows you to call the context updater (Aider) directly from the command line
for a specific customer, project, and message.

Usage:
    python update_context.py <customer> <project_id> "<message>"

Example:
    python update_context.py kinos template "Remember that users prefer concise responses."
"""

import os
import sys
import json
import argparse
from config import CUSTOMERS_DIR, logger
from services.file_service import get_project_path
from services.claude_service import build_context
from services.aider_service import call_aider_with_context

def update_context(customer, project_id, message):
    """
    Update context files for a specific customer, project, and message.
    
    Args:
        customer: Customer name
        project_id: Project ID
        message: Message content
    
    Returns:
        Aider response as a string
    """
    # Validate customer
    if not os.path.exists(os.path.join(CUSTOMERS_DIR, customer)):
        print(f"Error: Customer '{customer}' not found")
        return None
    
    # Get project path
    project_path = get_project_path(customer, project_id)
    if not os.path.exists(project_path):
        print(f"Error: Project '{project_id}' not found for customer '{customer}'")
        return None
    
    print(f"Updating context for {customer}/{project_id}")
    print(f"Message: {message}")
    
    # Build context (select relevant files)
    selected_files = build_context(customer, project_id, message, project_path=project_path)
    print(f"Selected files for context: {selected_files}")
    
    # Call Aider with the selected context
    try:
        aider_response = call_aider_with_context(project_path, selected_files, message)
        print("Context update completed successfully")
        return aider_response
    except Exception as e:
        print(f"Error updating context: {str(e)}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Update context files for a specific customer and project")
    parser.add_argument("customer", help="Customer name")
    parser.add_argument("project_id", help="Project ID")
    parser.add_argument("message", help="Message content")
    parser.add_argument("--output", "-o", help="Output file for Aider response (default: print to stdout)")
    
    args = parser.parse_args()
    
    # Call the update_context function
    response = update_context(args.customer, args.project_id, args.message)
    
    if response:
        if args.output:
            # Write response to file
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(response)
            print(f"Response written to {args.output}")
        else:
            # Print response to stdout
            print("\n--- Aider Response ---")
            print(response)
            print("--- End of Response ---")
    
    return 0 if response else 1

if __name__ == "__main__":
    sys.exit(main())
