#!/usr/bin/env python3
"""
Context Updater CLI Tool

This script allows you to call the context updater (Aider) directly from the command line
for a specific blueprint, kin, and message.

Usage:
    python update_context.py <blueprint> <kin_id> "<message>"

Example:
    python update_context.py kinos template "Remember that users prefer concise responses."
"""

import os
import sys
import json
import argparse
import subprocess
from config import blueprintS_DIR, logger
from services.file_service import get_kin_path
from services.claude_service import build_context
from services.aider_service import call_aider_with_context

def update_context(blueprint, kin_id, message, stream=False):
    """
    Update context files for a specific blueprint, kin, and message.
    
    Args:
        blueprint: blueprint name
        kin_id: kin ID
        message: Message content
        stream: Whether to stream the response (default: False)
    
    Returns:
        If stream=False: Aider response as a string
        If stream=True: Generator yielding response chunks
    """
    # Validate blueprint
    if not os.path.exists(os.path.join(blueprintS_DIR, blueprint)):
        print(f"Error: blueprint '{blueprint}' not found")
        return None
    
    # Get kin path
    kin_path = get_kin_path(blueprint, kin_id)
    if not os.path.exists(kin_path):
        print(f"Error: kin '{kin_id}' not found for blueprint '{blueprint}'")
        return None
    
    print(f"Updating context for {blueprint}/{kin_id}")
    print(f"Message: {message}")
    
    # Build context (select relevant files)
    selected_files, _ = build_context(blueprint, kin_id, message, kin_path=kin_path, history_length=2)
    print(f"Selected files for context: {selected_files}")
    
    # Check if messages.json is in the selected files
    messages_json_path = None
    for file_path in selected_files:
        if file_path.endswith('messages.json'):
            messages_json_path = os.path.join(kin_path, file_path)
            break
    
    # Create a temporary file with only the last 20 messages if messages.json is selected
    temp_messages_file = None
    if messages_json_path and os.path.exists(messages_json_path):
        try:
            # Load the original messages.json
            with open(messages_json_path, 'r', encoding='utf-8') as f:
                messages = json.load(f)
            
            # Take only the last 20 messages
            last_messages = messages[-20:] if len(messages) > 20 else messages
            
            # Create a temporary file
            import tempfile
            temp_messages_file = tempfile.NamedTemporaryFile(mode='w+', encoding='utf-8', suffix='.json', delete=False)
            json.dump(last_messages, temp_messages_file)
            temp_messages_file.close()
            
            # Replace the original messages.json path with the temporary file path in selected_files
            for i, file_path in enumerate(selected_files):
                if file_path.endswith('messages.json'):
                    # Use a relative path from kin_path
                    rel_temp_path = os.path.relpath(temp_messages_file.name, kin_path)
                    selected_files[i] = rel_temp_path
                    print(f"Using temporary messages file with last 20 messages: {rel_temp_path}")
                    break
        except Exception as e:
            print(f"Error creating temporary messages file: {str(e)}")
            # If there's an error, continue with the original messages.json
    
    # Call Aider with the selected context
    try:
        aider_response = call_aider_with_context(kin_path, selected_files, message, stream=stream)
        
        # Clean up the temporary file
        if temp_messages_file:
            try:
                os.unlink(temp_messages_file.name)
                print(f"Deleted temporary messages file: {temp_messages_file.name}")
            except Exception as e:
                print(f"Error deleting temporary file: {str(e)}")
        
        if not stream:
            print("Context update completed successfully")
        return aider_response
    except subprocess.TimeoutExpired:
        # Clean up the temporary file even if there's an error
        if temp_messages_file:
            try:
                os.unlink(temp_messages_file.name)
                print(f"Deleted temporary messages file: {temp_messages_file.name}")
            except Exception as e:
                print(f"Error deleting temporary file: {str(e)}")
        
        print("Error: Aider process timed out after 5 minutes")
        return None
    except Exception as e:
        # Clean up the temporary file even if there's an error
        if temp_messages_file:
            try:
                os.unlink(temp_messages_file.name)
                print(f"Deleted temporary messages file: {temp_messages_file.name}")
            except Exception as file_e:
                print(f"Error deleting temporary file: {str(file_e)}")
        
        print(f"Error updating context: {str(e)}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Update context files for a specific blueprint and kin")
    parser.add_argument("blueprint", help="blueprint name")
    parser.add_argument("kin_id", help="kin ID")
    parser.add_argument("message", help="Message content")
    parser.add_argument("--output", "-o", help="Output file for Aider response (default: print to stdout)")
    parser.add_argument("--stream", "-s", action="store_true", help="Stream the response in real-time")
    
    args = parser.parse_args()
    
    # Call the update_context function
    response = update_context(args.blueprint, args.kin_id, args.message, stream=args.stream)
    
    if response:
        if args.stream:
            # For streaming, print each chunk as it comes
            print("\n--- Aider Response (streaming) ---")
            for chunk in response:
                print(chunk, end='', flush=True)
            print("\n--- End of Response ---")
        elif args.output:
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
