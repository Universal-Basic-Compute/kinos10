#!/usr/bin/env python3
"""
KinOS API CLI - Command Line Interface for the KinOS API
Usage: kinos_cli.py [options] <command> [<args>...]

Commands:
  customers                     List all customers
  create-analysis-mode          Create analysis mode files for customers
  analyze <customer> <project>  Send an analysis request to a project
  projects [<customer>]         List projects (for a specific customer if provided)
  reset <customer> [<project>]  Reset a project or all projects for a customer
  modes <customer> <project>    List available modes for a project

Options:
  -h, --help                    Show this help message and exit
  -u, --url URL                 API base URL [default: http://localhost:5000]
  -k, --api-key KEY             API key to use for authentication
  -v, --verbose                 Enable verbose output
"""

import sys
import json
import argparse
import requests
from urllib.parse import urljoin

def main():
    # Create the main parser
    parser = argparse.ArgumentParser(description='KinOS API CLI')
    parser.add_argument('-u', '--url', default='http://localhost:5000', help='API base URL')
    parser.add_argument('-k', '--api-key', help='API key to use for authentication')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Customers command
    customers_parser = subparsers.add_parser('customers', help='List all customers')
    
    # Create analysis mode command
    analysis_mode_parser = subparsers.add_parser('create-analysis-mode', help='Create analysis mode files for customers')
    analysis_mode_parser.add_argument('--customers', nargs='+', help='Specific customers to process')
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Send an analysis request to a project')
    analyze_parser.add_argument('customer', help='Customer name')
    analyze_parser.add_argument('project', help='Project ID')
    analyze_parser.add_argument('--message', '-m', required=True, help='Message to analyze')
    analyze_parser.add_argument('--model', default='claude-3-5-haiku-latest', help='Model to use')
    
    # Projects command
    projects_parser = subparsers.add_parser('projects', help='List projects')
    projects_parser.add_argument('customer', nargs='?', help='Customer name (optional)')
    
    # Reset command
    reset_parser = subparsers.add_parser('reset', help='Reset a project or all projects for a customer')
    reset_parser.add_argument('customer', help='Customer name')
    reset_parser.add_argument('project', nargs='?', help='Project ID (optional, if not provided all projects will be reset)')
    
    # Modes command
    modes_parser = subparsers.add_parser('modes', help='List available modes for a project')
    modes_parser.add_argument('customer', help='Customer name')
    modes_parser.add_argument('project', help='Project ID')
    
    # Parse arguments
    args = parser.parse_args()
    
    # If no command is provided, show help
    if not args.command:
        parser.print_help()
        return 1
    
    # Prepare base URL and headers
    base_url = args.url
    headers = {'Content-Type': 'application/json'}
    params = {}
    
    # Add API key if provided
    if args.api_key:
        params['api_key'] = args.api_key
    
    # Process commands
    try:
        if args.command == 'customers':
            response = requests.get(urljoin(base_url, 'customers'), params=params)
            handle_response(response, args.verbose)
            
        elif args.command == 'create-analysis-mode':
            data = {}
            if args.customers:
                data['customers'] = args.customers
                
            response = requests.post(
                urljoin(base_url, 'customers/create_analysis_mode'),
                json=data,
                headers=headers,
                params=params
            )
            handle_response(response, args.verbose)
            
        elif args.command == 'analyze':
            data = {
                'message': args.message,
                'model': args.model
            }
            
            response = requests.post(
                urljoin(base_url, f'projects/{args.customer}/{args.project}/analysis'),
                json=data,
                headers=headers,
                params=params
            )
            handle_response(response, args.verbose)
            
        elif args.command == 'projects':
            if args.customer:
                response = requests.get(
                    urljoin(base_url, f'projects/{args.customer}/projects'),
                    params=params
                )
            else:
                response = requests.get(urljoin(base_url, 'projects/all'), params=params)
                
            handle_response(response, args.verbose)
            
        elif args.command == 'reset':
            if args.project:
                response = requests.post(
                    urljoin(base_url, f'projects/{args.customer}/{args.project}/reset'),
                    headers=headers,
                    params=params
                )
            else:
                response = requests.post(
                    urljoin(base_url, f'customers/{args.customer}/reset'),
                    headers=headers,
                    params=params
                )
                
            handle_response(response, args.verbose)
            
        elif args.command == 'modes':
            response = requests.get(
                urljoin(base_url, f'projects/{args.customer}/{args.project}/modes'),
                params=params
            )
            handle_response(response, args.verbose)
            
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
        
    return 0

def handle_response(response, verbose=False):
    """Handle API response, print result or error"""
    if verbose:
        print(f"Status code: {response.status_code}")
        print(f"Headers: {json.dumps(dict(response.headers), indent=2)}")
        
    try:
        # Try to parse as JSON
        data = response.json()
        print(json.dumps(data, indent=2))
    except ValueError:
        # Not JSON, print as text
        print(response.text)
        
    # Raise exception for error status codes
    response.raise_for_status()

if __name__ == "__main__":
    sys.exit(main())
