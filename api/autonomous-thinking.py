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
from dotenv import load_dotenv
from config import BASE_URL

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

def extract_keywords(kin_path, random_files, client):
    """
    First stage: Extract keywords from messages and files.
    """
    logger.info("Starting keyword extraction stage")
    logger.info(f"Loading messages and files from {kin_path}")

    # Load messages.json
    messages_file = os.path.join(kin_path, "messages.json")
    messages_content = ""
    if os.path.exists(messages_file):
        try:
            with open(messages_file, 'r', encoding='utf-8') as f:
                messages = json.load(f)
                messages_content = "\n".join([f"{m.get('role')}: {m.get('content')}" for m in messages[-10:]])  # Last 10 messages
            logger.info(f"Loaded {len(messages)} messages from messages.json")
        except Exception as e:
            logger.error(f"Error reading messages.json: {str(e)}")

    # Load content of random files
    file_contents = []
    for file in random_files:
        file_path = os.path.join(kin_path, file)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                file_contents.append(f"# File: {file}\n{content}")
                logger.info(f"Loaded content from file: {file}")
            except Exception as e:
                logger.error(f"Error reading file {file_path}: {str(e)}")

    logger.info("Making API call to Claude for keyword extraction")
    logger.info("Making API call to Claude for dream generation")
    logger.info("Making API call to Claude for initiative generation")
    try:
        response = client.messages.create(
            model="claude-3-7-sonnet-latest",
            max_tokens=1000,
            system=f"""Messages history:
{messages_content}

File contents:
{chr(10).join(file_contents)}

Based on the provided messages and files, extract the following elements:

1. Three relevant keywords that appear in the content
2. Two emotions expressed or implied in the content
3. Two problems or challenges identified in the content
4. Three surprising or unexpected words from the content
5. Two adjacent keywords (related concepts not present in the files)
6. Two surprising keywords (unexpected concepts not present in the files)

Format your response as JSON:
{{
    "relevant_keywords": ["word1", "word2", "word3"],
    "emotions": ["emotion1", "emotion2"],
    "problems": ["problem1", "problem2"],
    "surprising_words": ["word1", "word2", "word3"],
    "adjacent_keywords": ["word1", "word2"],
    "surprising_keywords": ["word1", "word2"]
}}""",
            messages=[{"role": "user", "content": "Please extract the keywords and emotions as specified."}]
        )
        
        logger.info("Received response from Claude")
        response_text = response.content[0].text.strip()
        logger.debug(f"Raw response from Claude: {response_text}")
        
        json_start = response_text.find('{')
        json_end = response_text.rfind('}')
        
        if json_start != -1 and json_end != -1:
            json_str = response_text[json_start:json_end + 1]
            try:
                keywords = json.loads(json_str)
                logger.info("Successfully parsed keywords JSON")
                logger.info(f"Extracted keywords: {json.dumps(keywords, indent=2)}")
                return keywords
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing JSON from response: {str(e)}")
                logger.error(f"Response text: {response_text}")
                raise
        else:
            logger.error(f"Could not find JSON in response: {response_text}")
            raise ValueError("No JSON found in response")
            
    except Exception as e:
        logger.error(f"Error in keyword extraction: {str(e)}")
        return None

def generate_dream(kin_path, keywords, client):
    """
    Second stage: Generate a dream narrative from the keywords.
    """
    logger.info("Starting dream generation stage")
    logger.info(f"Using keywords: {json.dumps(keywords, indent=2)}")

    # Load persona.txt
    persona_content = ""
    persona_path = os.path.join(kin_path, "persona.txt")
    if os.path.exists(persona_path):
        try:
            with open(persona_path, 'r', encoding='utf-8') as f:
                persona_content = f.read()
            logger.info("Loaded persona.txt content")
        except Exception as e:
            logger.error(f"Error reading persona.txt: {str(e)}")

    # Get two random files from memories directory
    memories_dir = os.path.join(kin_path, "memories")
    memory_files = []
    if os.path.exists(memories_dir):
        try:
            all_memory_files = [f for f in os.listdir(memories_dir) if f.endswith('.txt')]
            memory_files = random.sample(all_memory_files, min(2, len(all_memory_files)))
            logger.info(f"Selected memory files: {memory_files}")
            
            for file in memory_files:
                with open(os.path.join(memories_dir, file), 'r', encoding='utf-8') as f:
                    persona_content += f"\n\n# Memory: {file}\n{f.read()}"
                logger.info(f"Added content from memory file: {file}")
        except Exception as e:
            logger.error(f"Error reading memory files: {str(e)}")

    try:
        response = client.messages.create(
            model="claude-3-7-sonnet-latest",
            max_tokens=1000,
            system=f"""Persona and Memories Context:
{persona_content}

Using these keywords, create a vivid and meaningful first-person dream narrative that reflects your inner world and aspirations.
The narrative should weave together the keywords naturally and create a meaningful metaphor or story.
Write from your perspective, using "I" and describing what you experienced in the dream.

Keywords:
- Relevant: {', '.join(keywords['relevant_keywords'])}
- Emotional: {', '.join(keywords['emotions'])}
- Surprising: {', '.join(keywords['surprising_words'])}
- Adjacent: {', '.join(keywords['adjacent_keywords'])}
- Unexpected: {', '.join(keywords['surprising_keywords'])}

Create a 2-3 sentence dream narrative that feels personal and meaningful to you.
Focus on imagery and emotional resonance rather than literal meanings.
Start with "In my dream..." or similar first-person opening.""",
            messages=[{"role": "user", "content": "Please share your dream narrative based on these elements."}]
        )
        dream_narrative = response.content[0].text.strip()
        logger.info("Received dream narrative from Claude")
        logger.info(f"Dream narrative: {dream_narrative}")

        # Create memories directory if it doesn't exist
        memories_dir = os.path.join(kin_path, "memories")
        os.makedirs(memories_dir, exist_ok=True)
        logger.info(f"Ensured memories directory exists: {memories_dir}")

        # Append the dream to dreams.txt with timestamp
        dreams_file = os.path.join(memories_dir, "dreams.txt")
        timestamp = datetime.now().isoformat()
        with open(dreams_file, 'a', encoding='utf-8') as f:
            f.write(f"\n\n# Dream recorded at {timestamp}\n")
            f.write(dream_narrative)
            f.write("\n")
        logger.info(f"Saved dream to dreams.txt with timestamp {timestamp}")

        return dream_narrative
    except Exception as e:
        logger.error(f"Error in dream generation: {str(e)}")
        return None

def generate_initiative(kin_path, dream_narrative, random_files, client):
    """
    Third stage: Generate an initiative from the dream narrative.
    """
    logger.info("Starting initiative generation stage")
    logger.info(f"Using dream narrative: {dream_narrative}")

    # Load persona.txt and messages.json
    context_content = ""
    
    # Load persona.txt
    persona_path = os.path.join(kin_path, "persona.txt")
    if os.path.exists(persona_path):
        try:
            with open(persona_path, 'r', encoding='utf-8') as f:
                context_content += f"# Persona\n{f.read()}\n\n"
            logger.info("Loaded persona.txt content")
        except Exception as e:
            logger.error(f"Error reading persona.txt: {str(e)}")

    # Load messages.json
    messages_file = os.path.join(kin_path, "messages.json")
    if os.path.exists(messages_file):
        try:
            with open(messages_file, 'r', encoding='utf-8') as f:
                messages = json.load(f)
                recent_messages = messages[-5:]  # Last 5 messages
                context_content += "# Recent Messages\n"
                for msg in recent_messages:
                    context_content += f"{msg.get('role')}: {msg.get('content')}\n"
                context_content += "\n"
            logger.info(f"Loaded {len(recent_messages)} recent messages")
        except Exception as e:
            logger.error(f"Error reading messages.json: {str(e)}")

    # Load random files
    for file in random_files:
        file_path = os.path.join(kin_path, file)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                context_content += f"# File: {file}\n{content}\n\n"
                logger.info(f"Added content from file: {file}")
            except Exception as e:
                logger.error(f"Error reading file {file_path}: {str(e)}")

    # Create initiative generation prompt
    initiative_prompt = f"""
    Based on this dream narrative and the entity's context, generate a concrete initiative or action-oriented thought.
    This should be something the entity wants to explore, understand, or accomplish.

    Dream Narrative:
    {dream_narrative}

    Context:
    {context_content}

    Generate a clear, first-person thought that expresses an initiative, desire, or intention.
    Make it specific and actionable while maintaining emotional depth.
    The thought should be 1-2 sentences and start with "I" or "My".
    """

    try:
        response = client.messages.create(
            model="claude-3-7-sonnet-latest",
            max_tokens=1000,
            system=f"""Dream Narrative:
{dream_narrative}

Context:
{context_content}

Based on this dream narrative and the entity's context, generate a speculative "What if" question that expresses curiosity or explores a possibility.
This should be something the entity wonders about or wants to explore.

Generate a clear, thought-provoking question that starts with "What if" or "I wonder if/what/how".
Make it specific and imaginative while maintaining emotional depth.
The question should be 1-2 sentences.""",
            messages=[{"role": "user", "content": "Please generate a speculative question based on the dream narrative and context."}]
        )
        initiative = response.content[0].text.strip()
        logger.info("Received initiative from Claude")
        logger.info(f"Generated initiative: {initiative}")
        return initiative
    except Exception as e:
        logger.error(f"Error in initiative generation: {str(e)}")
        return None

def generate_random_thought(kin_path, random_files):
    """
    Generate a random thought using the three-stage process:
    1. Extract keywords from messages and files
    2. Generate a dream narrative from the keywords
    3. Generate an initiative from the dream narrative
    """
    try:
        # Get Anthropic client
        client = get_anthropic_client()

        # Stage 1: Extract keywords
        logger.info("Stage 1: Extracting keywords")
        keywords = extract_keywords(kin_path, random_files, client)
        if not keywords:
            raise Exception("Failed to extract keywords")
        logger.info(f"Extracted keywords: {json.dumps(keywords, indent=2)}")

        # Stage 2: Generate dream narrative
        logger.info("Stage 2: Generating dream narrative")
        dream_narrative = generate_dream(kin_path, keywords, client)
        if not dream_narrative:
            raise Exception("Failed to generate dream narrative")
        logger.info(f"Generated dream narrative: {dream_narrative}")

        # Stage 3: Generate initiative
        logger.info("Stage 3: Generating initiative")
        initiative = generate_initiative(kin_path, dream_narrative, random_files, client)
        if not initiative:
            raise Exception("Failed to generate initiative")
        logger.info(f"Generated initiative: {initiative}")

        return initiative

    except Exception as e:
        logger.error(f"Error in thought generation process: {str(e)}")
        return "I wonder about the nature of consciousness and my role in understanding it."

def send_message_to_kin(blueprint, kin_id, message, mode=None, remote=False):
    """
    Send a message to the kin by calling the function directly.
    
    Args:
        blueprint: Blueprint name
        kin_id: Kin ID
        message: Message content
        mode: Message mode (optional)
        remote: Whether to use remote API instead of localhost (default: False)
    
    Returns:
        The response from the kin
    """
    try:
        # Choose API URL based on remote flag
        base_url = "https://api.kinos-engine.ai" if remote else BASE_URL
        api_url = f"{base_url}/kins/{blueprint}/{kin_id}/messages"
        
        logger.info(f"Using {'remote' if remote else 'local'} API: {api_url}")
        
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
            "model": "claude-3-7-sonnet-latest"  # Use the big model
        }
        
        if mode:  # Add mode only if specified
            payload["mode"] = mode
            
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

def autonomous_thinking(blueprint, kin_id, telegram_token=None, telegram_chat_id=None, iterations=3, wait_time=600, remote=False):
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
                response = send_message_to_kin(blueprint, kin_id, current_thought, mode="self-reflection", remote=remote)
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
    parser.add_argument("--remote", action="store_true", help="Use remote API instead of localhost")
    parser.add_argument("--api-url", help="Base URL for API calls (default: uses direct function calls)")
    
    args = parser.parse_args()
    
    # Load environment variables from .env file
    # Try loading from current directory first
    load_dotenv()
    
    # Then try loading from the parent directory of the script
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
            args.wait_time,
            remote=args.remote
        )
        
        return 0 if success else 1
    except Exception as e:
        logger.error(f"Unhandled exception in autonomous thinking: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
