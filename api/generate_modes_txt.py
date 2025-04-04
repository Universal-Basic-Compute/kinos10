#!/usr/bin/env python3
"""
Modes.txt Generator

This script generates a modes.txt file for each blueprint template by making an API call
to Claude with the blueprint's modes, kinos.txt, system.txt, and persona.txt in context.

Usage:
    python generate_modes_txt.py [--blueprint BLUEPRINT] [--dry-run]

Options:
    --blueprint BLUEPRINT    Only generate for the specified blueprint
    --dry-run                Show what would be done without making changes
"""

import os
import sys
import json
import argparse
import logging
import anthropic
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"generate_modes_txt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
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

def get_anthropic_client():
    """Initialize and return the Anthropic client."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY environment variable not set")
        raise ValueError("Anthropic API key not configured")
    
    return anthropic.Anthropic(api_key=api_key)

def load_file_content(file_path):
    """Load the content of a file if it exists."""
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {str(e)}")
    return None

def get_mode_files(modes_dir):
    """Get a list of mode files from the modes directory."""
    mode_files = []
    if os.path.exists(modes_dir):
        for filename in os.listdir(modes_dir):
            if filename.endswith('.txt'):
                mode_files.append(os.path.join(modes_dir, filename))
    return mode_files

def generate_modes_txt(blueprint, template_dir, dry_run=False):
    """
    Generate a modes.txt file for a blueprint template.
    
    Args:
        blueprint: Blueprint name
        template_dir: Path to the template directory
        dry_run: If True, only show what would be done without making changes
    
    Returns:
        Boolean indicating success
    """
    logger.info(f"Generating modes.txt for blueprint: {blueprint}")
    
    # Check if template directory exists
    if not os.path.exists(template_dir):
        logger.error(f"Template directory not found: {template_dir}")
        return False
    
    # Get paths to key files
    modes_dir = os.path.join(template_dir, "modes")
    kinos_path = os.path.join(template_dir, "kinos.txt")
    system_path = os.path.join(template_dir, "system.txt")
    persona_path = os.path.join(template_dir, "persona.txt")
    
    # Check if modes directory exists
    if not os.path.exists(modes_dir):
        logger.warning(f"Modes directory not found: {modes_dir}")
        logger.info(f"Creating modes directory: {modes_dir}")
        if not dry_run:
            os.makedirs(modes_dir, exist_ok=True)
    
    # Get list of mode files
    mode_files = get_mode_files(modes_dir)
    if not mode_files:
        logger.warning(f"No mode files found in {modes_dir}")
        return False
    
    # Load content of mode files
    mode_contents = {}
    for mode_file in mode_files:
        mode_name = os.path.basename(mode_file).replace('.txt', '')
        content = load_file_content(mode_file)
        if content:
            mode_contents[mode_name] = content
    
    if not mode_contents:
        logger.warning(f"No valid mode content found for {blueprint}")
        return False
    
    # Load content of key files
    kinos_content = load_file_content(kinos_path) or ""
    system_content = load_file_content(system_path) or ""
    persona_content = load_file_content(persona_path) or ""
    
    # Prepare context for Claude
    context = f"""# Blueprint: {blueprint}

## Core Files

### kinos.txt
{kinos_content}

### system.txt
{system_content}

### persona.txt
{persona_content}

## Available Modes
"""

    # Add mode contents to context
    for mode_name, content in mode_contents.items():
        context += f"\n### {mode_name}.txt\n{content}\n"
    
    # Create prompt for Claude
    prompt = f"""Based on the blueprint information and available modes, create a comprehensive modes.txt file that:

1. Introduces the concept of modes and how they modify the AI's behavior
2. Lists each available mode with a brief description of its purpose and when to use it
3. Explains how users can switch between modes
4. Provides examples of mode switching commands

The modes.txt file should be concise but informative, helping users understand the different operational modes available for this blueprint.

Available modes: {', '.join(mode_contents.keys())}

Format the output as a well-structured markdown document with clear headings and sections.
"""

    # Get Anthropic client
    client = get_anthropic_client()
    
    try:
        # Call Claude API
        logger.info(f"Calling Claude API to generate modes.txt for {blueprint}")
        response = client.messages.create(
            model="claude-3-5-haiku-latest",
            max_tokens=4000,
            system=context,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        # Extract the response text
        if response.content and len(response.content) > 0:
            modes_txt_content = response.content[0].text
            
            # Path to modes.txt file
            modes_txt_path = os.path.join(template_dir, "modes.txt")
            
            # Log the content
            logger.info(f"Generated modes.txt content for {blueprint}:")
            logger.info(f"\n{modes_txt_content[:500]}...\n")
            
            # Write the content to modes.txt
            if not dry_run:
                try:
                    with open(modes_txt_path, 'w', encoding='utf-8') as f:
                        f.write(modes_txt_content)
                    logger.info(f"Successfully wrote modes.txt for {blueprint} to {modes_txt_path}")
                    return True
                except Exception as e:
                    logger.error(f"Error writing modes.txt for {blueprint}: {str(e)}")
                    return False
            else:
                logger.info(f"Dry run: Would write modes.txt for {blueprint} to {modes_txt_path}")
                return True
        else:
            logger.error(f"Empty response from Claude API for {blueprint}")
            return False
    except Exception as e:
        logger.error(f"Error calling Claude API for {blueprint}: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Generate modes.txt files for blueprint templates")
    parser.add_argument("--blueprint", help="Only generate for the specified blueprint")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    
    args = parser.parse_args()
    
    # Get blueprints directory
    blueprints_dir = get_blueprints_dir()
    
    # Get list of blueprints
    if args.blueprint:
        blueprints = [args.blueprint]
    else:
        blueprints = [d for d in os.listdir(blueprints_dir) 
                    if os.path.isdir(os.path.join(blueprints_dir, d))]
    
    logger.info(f"Processing {len(blueprints)} blueprints: {blueprints}")
    
    # Track results
    results = {
        "total": len(blueprints),
        "successful": 0,
        "failed": 0,
        "skipped": 0
    }
    
    # Process each blueprint
    for blueprint in blueprints:
        template_dir = os.path.join(blueprints_dir, blueprint, "template")
        
        # Check if template directory exists
        if not os.path.exists(template_dir):
            logger.warning(f"Template directory not found for {blueprint}: {template_dir}")
            results["skipped"] += 1
            continue
        
        # Generate modes.txt
        success = generate_modes_txt(blueprint, template_dir, args.dry_run)
        
        if success:
            results["successful"] += 1
        else:
            results["failed"] += 1
    
    # Log results
    logger.info(f"Results: {results}")
    
    return 0 if results["failed"] == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
