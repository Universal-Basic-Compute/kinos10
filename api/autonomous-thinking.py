#!/usr/bin/env python3
"""
Autonomous Thinking Script

This script generates autonomous thoughts for a kin by:
1. Selecting 3 random files from the kin
2. Using Claude to generate a random thought based on these files
3. Sending the thought to the kin's message endpoint with self-reflection mode
4. Sending a Telegram notification with the thought and response
5. Repeating this process 3 times with 10-minute intervals

Usage:
    python autonomous-thinking.py <blueprint> <kin_id> [--telegram-token TOKEN] [--telegram-chat-id CHAT_ID]

Example:
    python autonomous-thinking.py therapykindouble mykin --telegram-token 1234567890:ABCDEF --telegram-chat-id 123456789
"""

import os
import sys
import json
import time
import random
import argparse
import requests
import logging
import anthropic
import io
from datetime import datetime
from flask import Flask, request

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
        # Removed the FileHandler to prevent creating a log file
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

def get_kin_path(blueprint, kin_id):
    """Get the full path to a kin directory."""
    blueprints_dir = get_blueprints_dir()
    if kin_id == "template":
        return os.path.join(blueprints_dir, blueprint, "template")
    else:
        return os.path.join(blueprints_dir, blueprint, "kins", kin_id)

def get_random_files(kin_path, count=3):
    """Get a list of random files from the kin directory."""
    all_files = []
    
    # Define patterns to ignore
    ignore_patterns = [
        '.git', '.svn', '.hg',           # Version control
        '.vscode', '.idea', '.vs',       # Editors
        '__pycache__', '*.pyc', '*.pyo', # Python
        '.DS_Store',                     # macOS
        '.aider*',                       # Aider files
        'aider_logs.txt',                # Aider logs file
        '.aider.chat.history.md'         # Explicitly add this file
    ]
    
    for root, dirs, files in os.walk(kin_path):
        # Filter out ignored directories to avoid walking into them
        dirs[:] = [d for d in dirs if not any(
            (ignore_pattern == d or 
             (ignore_pattern.endswith('/') and d.startswith(ignore_pattern[:-1])) or
             (ignore_pattern.startswith('*.') and d.endswith(ignore_pattern[1:])))
            for ignore_pattern in ignore_patterns
        )]
        
        for file in files:
            rel_path = os.path.relpath(os.path.join(root, file), kin_path)
            
            # Improved pattern matching for files
            should_ignore = False
            for pattern in ignore_patterns:
                # Exact match
                if pattern == rel_path:
                    should_ignore = True
                    break
                # Directory prefix match
                elif pattern.endswith('/') and rel_path.startswith(f"{pattern[:-1]}/"):
                    should_ignore = True
                    break
                # File extension match
                elif pattern.startswith('*.') and rel_path.endswith(pattern[1:]):
                    should_ignore = True
                    break
                # Wildcard prefix match (e.g., .aider*)
                elif '*' in pattern and not pattern.startswith('*.'):
                    prefix = pattern.split('*')[0]
                    if rel_path.startswith(prefix):
                        should_ignore = True
                        break
            
            if should_ignore:
                continue
                
            # Skip system files, messages.json, and non-text files
            if (rel_path not in ["persona.txt", "kinos.txt", "system.txt", "messages.json"] and
                not rel_path.endswith(('.jpg', '.jpeg', '.png', '.gif', '.mp3', '.mp4'))):
                all_files.append(rel_path)
    
    # If we have fewer files than requested, return all available files
    if len(all_files) <= count:
        return all_files
    
    # Otherwise, return a random selection
    return random.sample(all_files, count)

def get_anthropic_client():
    """Initialize and return the Anthropic client."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY environment variable not set")
        raise ValueError("Anthropic API key not configured")
    
    return anthropic.Anthropic(api_key=api_key)

def generate_random_thought(kin_path, random_files):
    """
    Generate a random thought using Claude based on the kin's files.
    
    Args:
        kin_path: Path to the kin directory
        random_files: List of random files to include in the context
    
    Returns:
        A random thought as a string
    """
    # Load core files
    core_files = ["persona.txt", "kinos.txt", "system.txt"]
    file_contents = []
    
    # Load content of core files
    for file in core_files:
        file_path = os.path.join(kin_path, file)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                file_contents.append(f"# File: {file}\n{content}")
            except Exception as e:
                logger.error(f"Error reading file {file_path}: {str(e)}")
    
    # Load content of random files
    for file in random_files:
        file_path = os.path.join(kin_path, file)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                file_contents.append(f"# File: {file}\n{content}")
            except Exception as e:
                logger.error(f"Error reading file {file_path}: {str(e)}")
    
    # Load recent message history (last 50 messages)
    messages_file = os.path.join(kin_path, "messages.json")
    recent_messages = []
    if os.path.exists(messages_file):
        try:
            with open(messages_file, 'r', encoding='utf-8') as f:
                messages = json.load(f)
                # Get the last 50 messages
                recent_messages = messages[-50:] if len(messages) >= 50 else messages
        except Exception as e:
            logger.error(f"Error reading messages.json: {str(e)}")
    
    # Format the message history for inclusion in the context
    message_history = ""
    if recent_messages:
        message_history = "\n\n# Recent Message History\n"
        for msg in recent_messages:
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            timestamp = msg.get('timestamp', '')
            message_history += f"{role.capitalize()} ({timestamp}): {content}\n\n"
    
    # Combine file contents and message history into a single context string
    context = "\n\n".join(file_contents) + message_history
    
    # Create prompt for Claude
    prompt = """
    Based on the provided context, generate a random thought that this entity might have about its own goals, desires, or fears.
    
    Make this thought:
    1. Focused on the entity's aspirations, motivations, concerns, or emotional state
    2. Reflective of its core values and purpose as described in the files
    3. Something that reveals its inner drives or anxieties
    4. Potentially related to how it can better serve users or improve itself
    5. Authentic to the character/entity described in the files
    
    IMPORTANT: Return ONLY the thought itself, with absolutely no introduction, explanation, or commentary.
    Do not start with phrases like "Here's a thought:" or "I understand you want me to..."
    The thought should be 1-3 sentences long and start immediately.
    """
    
    # Get Anthropic client
    client = get_anthropic_client()
    
    try:
        # Call Claude API
        response = client.messages.create(
            model="claude-3-7-sonnet-latest",  # Use the more powerful Sonnet model for better quality thoughts
            max_tokens=1000,
            system=context,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        # Extract the thought from Claude's response
        thought = response.content[0].text.strip()
        logger.info(f"Generated thought: {thought}")
        
        return thought
        
    except Exception as e:
        logger.error(f"Error calling Claude API: {str(e)}")
        # Return a fallback thought if Claude API call fails
        return "I wonder if I'm truly helping users process their emotional conflicts, or if I need to develop more nuanced approaches to guide them through their internal struggles."

def send_message_to_kin(blueprint, kin_id, message, mode="self-reflection"):
    """
    Send a message to the kin by calling the function directly.
    
    Args:
        blueprint: Blueprint name
        kin_id: Kin ID
        message: Message content
        mode: Message mode (default: self-reflection)
    
    Returns:
        The response from the kin
    """
    try:
        # Fallback to API call
        try:
            # API endpoint - try the public API instead of localhost
            api_url = f"https://api.kinos-engine.ai/v2/blueprints/{blueprint}/kins/{kin_id}/messages"
            
            # Get API key from environment variable
            api_key = os.getenv("API_SECRET_KEY")
            if not api_key:
                logger.error("API_SECRET_KEY environment variable not set in .env file")
                raise ValueError("API key not configured")
            
            # Prepare request
            headers = {
                "Content-Type": "application/json",
                "X-API-Key": api_key
            }
            
            payload = {
                "content": message,
                "mode": mode,
                "model": "claude-3-7-sonnet-latest"  # Use the big model
            }
            
            logger.info(f"Making API call to {api_url} for {blueprint}/{kin_id}")
            logger.info(f"Payload: {payload}")
            
            # Make request
            response = requests.post(api_url, headers=headers, json=payload)
            
            # Check for errors
            if response.status_code != 200:
                logger.error(f"API error: {response.status_code} - {response.text}")
                return f"Error: {response.status_code} - {response.text}"
            
            # Parse response
            result = response.json()
            logger.info(f"API response: {result}")
            
            # Extract the response text
            if "response" in result:
                logger.info(f"Received response from API: {result['response'][:100]}...")
                return result["response"]
            else:
                logger.error(f"No response field in API result: {result}")
                return f"Error: No response field in API result: {result}"
                
        except Exception as fallback_error:
            logger.error(f"Fallback API call failed: {str(fallback_error)}")
            return f"Error: API call failed: {str(fallback_error)}"
            
    except Exception as e:
        logger.error(f"Error sending message to kin: {str(e)}")
        return f"Error: {str(e)}"

def send_telegram_notification(token, chat_id, thought, response):
    """
    Send a notification to Telegram with the thought and response.
    
    Args:
        token: Telegram bot token
        chat_id: Telegram chat ID
        thought: The generated thought
        response: The kin's response
    
    Returns:
        Boolean indicating success
    """
    if not token or not chat_id:
        logger.warning(f"Telegram token or chat ID not provided, skipping notification. Token: {token[:4] if token else 'None'}, Chat ID: {chat_id}")
        return False
    
    # Telegram API endpoint
    api_url = f"https://api.telegram.org/bot{token}/sendMessage"
    logger.info(f"Preparing Telegram notification with token: {token[:4]}... and chat ID: {chat_id}")
    
    # Convert chat_id to integer if it's a string
    try:
        if isinstance(chat_id, str):
            chat_id = int(chat_id)
        logger.info(f"Using chat_id as integer: {chat_id}")
    except ValueError:
        logger.warning(f"Could not convert chat_id to integer, using as is: {chat_id}")
    
    # Prepare message
    message = f"🧠 *Autonomous Thought*\n\n"
    message += f"💭 *Thought:*\n{thought}\n\n"
    message += f"🤔 *Self-Reflection:*\n{response[:1000]}..."  # Limit response length
    
    # Prepare request
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        # Make request
        logger.info(f"Sending request to Telegram API: {api_url} with chat_id: {chat_id}")
        response = requests.post(api_url, json=payload)
        
        # Check for errors
        if response.status_code != 200:
            logger.error(f"Telegram API error: {response.status_code} - {response.text}")
            return False
        
        logger.info(f"Telegram notification sent successfully: {response.json()}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending Telegram notification: {str(e)}")
        return False

def autonomous_thinking(blueprint, kin_id, telegram_token=None, telegram_chat_id=None, iterations=3, wait_time=600):
    """
    Run the autonomous thinking process for a kin.
    
    Args:
        blueprint: Blueprint name
        kin_id: Kin ID
        telegram_token: Optional Telegram bot token
        telegram_chat_id: Optional Telegram chat ID
        iterations: Number of thinking iterations (default: 3)
        wait_time: Wait time between iterations in seconds (default: 600 = 10 minutes)
    
    Returns:
        Boolean indicating success
    """
    # Get kin path
    kin_path = get_kin_path(blueprint, kin_id)
    if not os.path.exists(kin_path):
        logger.error(f"Kin path not found: {kin_path}")
        return False
    
    logger.info(f"Starting autonomous thinking for {blueprint}/{kin_id}")
    logger.info(f"Will run {iterations} iterations with {wait_time} seconds between each")
    
    # Generate the initial random thought
    random_files = get_random_files(kin_path, count=3)
    logger.info(f"Selected random files for initial thought: {random_files}")
    current_thought = generate_random_thought(kin_path, random_files)
    
    # Run the thinking iterations
    for i in range(iterations):
        logger.info(f"Starting iteration {i+1}/{iterations}")
        logger.info(f"Current thought: {current_thought}")
        
        try:
            # For the first iteration, send the random thought directly
            if i == 0:
                # Send message to kin
                response = send_message_to_kin(blueprint, kin_id, current_thought, mode="self-reflection")
            else:
                # For subsequent iterations, send a message with the continuation prompt
                # Include <system> tags in the actual message content, not as a separate system parameter
                response = send_message_to_kin(blueprint, kin_id, "<system>Continue your thoughts</system>", mode="self-reflection")
            
            # Send Telegram notification
            if telegram_token and telegram_chat_id:
                logger.info(f"Attempting to send Telegram notification with token: {telegram_token[:4] if telegram_token else 'None'}... and chat ID: {telegram_chat_id}")
                notification_sent = send_telegram_notification(telegram_token, telegram_chat_id, current_thought, response)
                if notification_sent:
                    logger.info("Telegram notification sent successfully")
                else:
                    logger.warning("Failed to send Telegram notification")
            else:
                logger.warning(f"Skipping Telegram notification - Token provided: {telegram_token is not None}, Chat ID provided: {telegram_chat_id is not None}")
            
            # Use the response as the input for the next iteration
            if i < iterations - 1:  # Only update if there are more iterations to come
                logger.info(f"Waiting {wait_time} seconds before next iteration...")
                time.sleep(wait_time)
                
                # Use the previous response as the new thought
                current_thought = response
        except Exception as e:
            logger.error(f"Error in iteration {i+1}: {str(e)}")
            # Continue with next iteration despite errors
            if i < iterations - 1:
                logger.info(f"Waiting {wait_time} seconds before next iteration...")
                time.sleep(wait_time)
                
                # Generate a new thought since the previous one failed
                random_files = get_random_files(kin_path, count=3)
                logger.info(f"Selected new random files after error: {random_files}")
                current_thought = generate_random_thought(kin_path, random_files)
    
    logger.info(f"Completed {iterations} autonomous thinking iterations")
    return True

def main():
    parser = argparse.ArgumentParser(description="Generate autonomous thoughts for a kin")
    parser.add_argument("blueprint", help="Blueprint name")
    parser.add_argument("kin_id", help="Kin ID")
    parser.add_argument("--telegram-token", help="Telegram bot token")
    parser.add_argument("--telegram-chat-id", help="Telegram chat ID")
    parser.add_argument("--iterations", type=int, default=3, help="Number of thinking iterations (default: 3)")
    parser.add_argument("--wait-time", type=int, default=600, help="Wait time between iterations in seconds (default: 600 = 10 minutes)")
    parser.add_argument("--api-url", help="Base URL for API calls (default: uses direct function calls)")
    
    args = parser.parse_args()
    
    # Load environment variables from .env file
    from dotenv import load_dotenv
    import os
    
    # Load .env file from the parent directory of the script
    dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
    load_dotenv(dotenv_path)
    
    # Get Telegram credentials from environment variables if not provided as arguments
    telegram_token = args.telegram_token or os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = args.telegram_chat_id or os.getenv("TELEGRAM_CHAT_ID")
    
    if telegram_token and telegram_chat_id:
        logger.info(f"Using Telegram credentials from {'arguments' if args.telegram_token else '.env file'}")
    else:
        logger.warning("Telegram credentials not found in arguments or .env file")
    
    # Run autonomous thinking
    try:
        success = autonomous_thinking(
            args.blueprint,
            args.kin_id,
            telegram_token,
            telegram_chat_id,
            args.iterations,
            args.wait_time
        )
        
        return 0 if success else 1
    except Exception as e:
        logger.error(f"Unhandled exception in autonomous thinking: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
