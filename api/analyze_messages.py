#!/usr/bin/env python3
"""
Message Analysis Tool

This script analyzes message history in all projects, extracts insights using Claude,
and saves them to insights.json files.

Usage:
    python analyze_messages.py [--customer CUSTOMER] [--project PROJECT] [--min-messages MIN]
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime
import anthropic
from config import CUSTOMERS_DIR, logger
from services.file_service import get_project_path

def setup_logging():
    """Configure logging for the script."""
    log_file = f"message_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file)
        ]
    )
    return logging.getLogger(__name__)

def get_anthropic_client():
    """Initialize and return the Anthropic client."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY environment variable not set")
        raise ValueError("Anthropic API key not configured")
    
    return anthropic.Anthropic(api_key=api_key)

def analyze_messages(messages, client):
    """
    Analyze messages using Claude to extract insights.
    
    Args:
        messages: List of message objects
        client: Anthropic client
    
    Returns:
        Dictionary with analysis results
    """
    # Format messages for Claude
    formatted_messages = []
    for msg in messages:
        role = msg.get('role', '')
        content = msg.get('content', '')
        timestamp = msg.get('timestamp', '')
        
        if role and content:
            formatted_messages.append(f"{role.capitalize()} ({timestamp}): {content}")
    
    messages_text = "\n\n".join(formatted_messages)
    
    # Create prompt for Claude
    prompt = f"""
    Please analyze the following conversation and provide:
    1. A concise summary of what the discussion was about
    2. Key insights and important points that emerged
    3. Any decisions or conclusions reached
    4. Any action items or next steps mentioned

    Format your response as JSON with the following structure:
    {{
        "summary": "Brief summary of the conversation",
        "insights": ["Insight 1", "Insight 2", ...],
        "decisions": ["Decision 1", "Decision 2", ...],
        "action_items": ["Action 1", "Action 2", ...]
    }}

    Here is the conversation:

    {messages_text}
    """
    
    try:
        # Call Claude API
        response = client.messages.create(
            model="claude-3-7-sonnet-latest",
            max_tokens=4000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        # Extract the JSON from Claude's response
        response_text = response.content[0].text
        
        # Find JSON in the response (it might be wrapped in markdown code blocks)
        import re
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```|```\s*([\s\S]*?)\s*```|(\{[\s\S]*\})', response_text)
        
        if json_match:
            # Get the first non-None group
            json_str = next(group for group in json_match.groups() if group is not None)
            analysis = json.loads(json_str)
        else:
            # If no JSON found, try to parse the entire response
            try:
                analysis = json.loads(response_text)
            except:
                logger.warning("Could not extract JSON from Claude's response, using raw text")
                analysis = {
                    "summary": "Error parsing response",
                    "raw_response": response_text
                }
        
        return analysis
        
    except Exception as e:
        logger.error(f"Error calling Claude API: {str(e)}")
        return {
            "error": str(e),
            "summary": "Failed to analyze messages"
        }

def process_project(customer, project_id, min_messages, client):
    """
    Process a single project, analyze messages if needed, and save insights.
    
    Args:
        customer: Customer name
        project_id: Project ID
        min_messages: Minimum number of messages required for analysis
        client: Anthropic client
    
    Returns:
        Boolean indicating success
    """
    try:
        # Get project path
        project_path = get_project_path(customer, project_id)
        if not os.path.exists(project_path):
            logger.warning(f"Project path not found: {project_path}")
            return False
        
        # Check for messages.json
        messages_file = os.path.join(project_path, "messages.json")
        if not os.path.exists(messages_file):
            logger.info(f"No messages.json found for {customer}/{project_id}")
            return False
        
        # Load messages
        with open(messages_file, 'r', encoding='utf-8') as f:
            messages = json.load(f)
        
        # Check if there are enough messages
        if len(messages) < min_messages:
            logger.info(f"Not enough messages in {customer}/{project_id}: {len(messages)} < {min_messages}")
            return False
        
        # Check if insights.json already exists and when it was last modified
        insights_file = os.path.join(project_path, "insights.json")
        should_analyze = True
        
        if os.path.exists(insights_file):
            # Compare modification times
            messages_mtime = os.path.getmtime(messages_file)
            insights_mtime = os.path.getmtime(insights_file)
            
            if insights_mtime > messages_mtime:
                logger.info(f"Insights already up to date for {customer}/{project_id}")
                should_analyze = False
        
        if should_analyze:
            logger.info(f"Analyzing messages for {customer}/{project_id} ({len(messages)} messages)")
            
            # Analyze messages
            analysis = analyze_messages(messages, client)
            
            # Add metadata
            analysis["metadata"] = {
                "customer": customer,
                "project_id": project_id,
                "message_count": len(messages),
                "generated_at": datetime.now().isoformat(),
                "model": "claude-3-7-sonnet-latest"
            }
            
            # Save insights
            with open(insights_file, 'w', encoding='utf-8') as f:
                json.dump(analysis, f, indent=2)
            
            logger.info(f"Saved insights for {customer}/{project_id}")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error processing project {customer}/{project_id}: {str(e)}")
        return False

def process_all_projects(min_messages, specific_customer=None, specific_project=None):
    """
    Process all projects across all customers, or specific ones if provided.
    
    Args:
        min_messages: Minimum number of messages required for analysis
        specific_customer: Optional customer to process
        specific_project: Optional project to process
    
    Returns:
        Tuple of (total_projects, analyzed_projects)
    """
    # Initialize Anthropic client
    client = get_anthropic_client()
    
    total_projects = 0
    analyzed_projects = 0
    
    # Get list of customers
    if specific_customer:
        customers = [specific_customer]
    else:
        customers = [d for d in os.listdir(CUSTOMERS_DIR) 
                    if os.path.isdir(os.path.join(CUSTOMERS_DIR, d))]
    
    for customer in customers:
        customer_dir = os.path.join(CUSTOMERS_DIR, customer)
        
        # Process specific project if provided
        if specific_project:
            total_projects += 1
            if process_project(customer, specific_project, min_messages, client):
                analyzed_projects += 1
            continue
        
        # Process all projects for this customer
        projects_dir = os.path.join(customer_dir, "projects")
        if not os.path.exists(projects_dir):
            logger.info(f"No projects directory for customer: {customer}")
            continue
        
        # Get list of projects
        projects = [d for d in os.listdir(projects_dir) 
                   if os.path.isdir(os.path.join(projects_dir, d))]
        
        logger.info(f"Processing {len(projects)} projects for customer: {customer}")
        
        for project_id in projects:
            total_projects += 1
            if process_project(customer, project_id, min_messages, client):
                analyzed_projects += 1
    
    return total_projects, analyzed_projects

def main():
    parser = argparse.ArgumentParser(description="Analyze message history and extract insights")
    parser.add_argument("--customer", help="Process only this specific customer")
    parser.add_argument("--project", help="Process only this specific project")
    parser.add_argument("--min-messages", type=int, default=20, 
                        help="Minimum number of messages required for analysis (default: 20)")
    
    args = parser.parse_args()
    
    # Setup logging
    global logger
    logger = setup_logging()
    
    logger.info("Starting message analysis")
    logger.info(f"Minimum messages: {args.min_messages}")
    if args.customer:
        logger.info(f"Limiting to customer: {args.customer}")
    if args.project:
        logger.info(f"Limiting to project: {args.project}")
    
    # Process projects
    total, analyzed = process_all_projects(
        args.min_messages, 
        specific_customer=args.customer,
        specific_project=args.project
    )
    
    logger.info(f"Analysis complete. Processed {total} projects, analyzed {analyzed} projects.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
