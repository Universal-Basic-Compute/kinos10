#!/usr/bin/env python3
"""
Message Analysis Tool

This script analyzes message history in all kins, extracts insights using Claude,
and saves them to insights.json files.

Usage:
    python analyze_messages.py [--blueprint blueprint] [--kin kin] [--min-messages MIN]
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime
import anthropic
from config import blueprintS_DIR, logger
from services.file_service import get_kin_path

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

def process_kin(blueprint, kin_id, min_messages, client):
    """
    Process a single kin, analyze messages if needed, and save insights.
    
    Args:
        blueprint: blueprint name
        kin_id: kin ID
        min_messages: Minimum number of messages required for analysis
        client: Anthropic client
    
    Returns:
        Boolean indicating success
    """
    try:
        # Get kin path
        kin_path = get_kin_path(blueprint, kin_id)
        if not os.path.exists(kin_path):
            logger.warning(f"kin path not found: {kin_path}")
            return False
        
        # Check for messages.json
        messages_file = os.path.join(kin_path, "messages.json")
        if not os.path.exists(messages_file):
            logger.info(f"No messages.json found for {blueprint}/{kin_id}")
            return False
        
        # Load messages
        with open(messages_file, 'r', encoding='utf-8') as f:
            messages = json.load(f)
        
        # Check if there are enough messages
        if len(messages) < min_messages:
            logger.info(f"Not enough messages in {blueprint}/{kin_id}: {len(messages)} < {min_messages}")
            return False
        
        # Check if insights.json already exists and when it was last modified
        insights_file = os.path.join(kin_path, "insights.json")
        should_analyze = True
        
        if os.path.exists(insights_file):
            # Compare modification times
            messages_mtime = os.path.getmtime(messages_file)
            insights_mtime = os.path.getmtime(insights_file)
            
            if insights_mtime > messages_mtime:
                logger.info(f"Insights already up to date for {blueprint}/{kin_id}")
                should_analyze = False
        
        if should_analyze:
            logger.info(f"Analyzing messages for {blueprint}/{kin_id} ({len(messages)} messages)")
            
            # Analyze messages
            analysis = analyze_messages(messages, client)
            
            # Add metadata
            analysis["metadata"] = {
                "blueprint": blueprint,
                "kin_id": kin_id,
                "message_count": len(messages),
                "generated_at": datetime.now().isoformat(),
                "model": "claude-3-7-sonnet-latest"
            }
            
            # Save insights
            with open(insights_file, 'w', encoding='utf-8') as f:
                json.dump(analysis, f, indent=2)
            
            logger.info(f"Saved insights for {blueprint}/{kin_id}")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error processing kin {blueprint}/{kin_id}: {str(e)}")
        return False

def process_all_kins(min_messages, specific_blueprint=None, specific_kin=None):
    """
    Process all kins across all blueprints, or specific ones if provided.
    
    Args:
        min_messages: Minimum number of messages required for analysis
        specific_blueprint: Optional blueprint to process
        specific_kin: Optional kin to process
    
    Returns:
        Tuple of (total_kins, analyzed_kins)
    """
    # Initialize Anthropic client
    client = get_anthropic_client()
    
    total_kins = 0
    analyzed_kins = 0
    
    # Get list of blueprints
    if specific_blueprint:
        blueprints = [specific_blueprint]
    else:
        blueprints = [d for d in os.listdir(blueprintS_DIR) 
                    if os.path.isdir(os.path.join(blueprintS_DIR, d))]
    
    for blueprint in blueprints:
        blueprint_dir = os.path.join(blueprintS_DIR, blueprint)
        
        # Process specific kin if provided
        if specific_kin:
            total_kins += 1
            if process_kin(blueprint, specific_kin, min_messages, client):
                analyzed_kins += 1
            continue
        
        # Process all kins for this blueprint
        kins_dir = os.path.join(blueprint_dir, "kins")
        if not os.path.exists(kins_dir):
            logger.info(f"No kins directory for blueprint: {blueprint}")
            continue
        
        # Get list of kins
        kins = [d for d in os.listdir(kins_dir) 
                   if os.path.isdir(os.path.join(kins_dir, d))]
        
        logger.info(f"Processing {len(kins)} kins for blueprint: {blueprint}")
        
        for kin_id in kins:
            total_kins += 1
            if process_kin(blueprint, kin_id, min_messages, client):
                analyzed_kins += 1
    
    return total_kins, analyzed_kins

def main():
    parser = argparse.ArgumentParser(description="Analyze message history and extract insights")
    parser.add_argument("--blueprint", help="Process only this specific blueprint")
    parser.add_argument("--kin", help="Process only this specific kin")
    parser.add_argument("--min-messages", type=int, default=20, 
                        help="Minimum number of messages required for analysis (default: 20)")
    
    args = parser.parse_args()
    
    # Setup logging
    global logger
    logger = setup_logging()
    
    logger.info("Starting message analysis")
    logger.info(f"Minimum messages: {args.min_messages}")
    if args.blueprint:
        logger.info(f"Limiting to blueprint: {args.blueprint}")
    if args.kin:
        logger.info(f"Limiting to kin: {args.kin}")
    
    # Process kins
    total, analyzed = process_all_kins(
        args.min_messages, 
        specific_blueprint=args.blueprint,
        specific_kin=args.kin
    )
    
    logger.info(f"Analysis complete. Processed {total} kins, analyzed {analyzed} kins.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
