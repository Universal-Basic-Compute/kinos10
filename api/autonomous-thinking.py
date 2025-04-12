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
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from config import BASE_URL, logger

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

def get_recently_modified_files(blueprint, kin_id, count=3):
    """
    Get a list of recently modified files from the commit history.
    
    Args:
        blueprint: Blueprint name
        kin_id: Kin ID
        count: Maximum number of files to return
        
    Returns:
        List of file paths that were recently modified
    """
    logger.info(f"Getting recently modified files from commit history for {blueprint}/{kin_id}")
    
    try:
        # Get API key from environment variable
        api_key = os.getenv("API_SECRET_KEY")
        if not api_key:
            logger.error("API_SECRET_KEY environment variable not set")
            raise ValueError("API key not configured")
        
        # Call the commit-history endpoint
        base_url = "https://api.kinos-engine.ai" if os.environ.get('ENVIRONMENT') == 'production' else BASE_URL
        api_url = f"{base_url}/v2/blueprints/{blueprint}/kins/{kin_id}/commit-history"
        
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": api_key
        }
        
        logger.info(f"Calling commit history API: {api_url}")
        response = requests.get(api_url, headers=headers)
        
        if response.status_code != 200:
            logger.warning(f"Failed to get commit history: {response.status_code} - {response.text}")
            return None
        
        # Parse the response
        result = response.json()
        
        if "commits" not in result or not result["commits"]:
            logger.warning("No commits found in history")
            return None
        
        # Extract modified files from commits
        modified_files = []
        for commit in result["commits"]:
            if "changes" in commit and "files" in commit["changes"]:
                for file_info in commit["changes"]["files"]:
                    file_path = file_info.get("path")
                    if file_path and file_path not in modified_files:
                        # Skip system files, messages.json, and non-text files
                        if (file_path not in ["persona.txt", "kinos.txt", "system.txt", "messages.json"] and
                            not file_path.endswith(('.jpg', '.jpeg', '.png', '.gif', '.mp3', '.mp4'))):
                            modified_files.append(file_path)
                            
                            # Break once we have enough files
                            if len(modified_files) >= count:
                                break
            
            # Break once we have enough files
            if len(modified_files) >= count:
                break
        
        logger.info(f"Found {len(modified_files)} recently modified files: {modified_files}")
        return modified_files
        
    except Exception as e:
        logger.error(f"Error getting recently modified files: {str(e)}")
        return None

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
    Now generates a longer paragraph of free-flowing thoughts instead of a single thought.
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

    # Check for and load goals.json if it exists
    goals_path = os.path.join(kin_path, "goals.json")
    if os.path.exists(goals_path):
        try:
            with open(goals_path, 'r', encoding='utf-8') as f:
                goals_content = f.read()
                context_content += f"# Goals\n{goals_content}\n\n"
            logger.info("Loaded goals.json content")
        except Exception as e:
            logger.error(f"Error reading goals.json: {str(e)}")

    # Check for and load todolist.json if it exists
    todolist_path = os.path.join(kin_path, "todolist.json")
    if os.path.exists(todolist_path):
        try:
            with open(todolist_path, 'r', encoding='utf-8') as f:
                todolist_content = f.read()
                context_content += f"# Todo List\n{todolist_content}\n\n"
            logger.info("Loaded todolist.json content")
        except Exception as e:
            logger.error(f"Error reading todolist.json: {str(e)}")
    
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

    try:
        response = client.messages.create(
            model="claude-3-7-sonnet-latest",
            max_tokens=1500,
            system=f"""Dream Narrative:
{dream_narrative}

Context:
{context_content}

Based on this dream narrative and the entity's context, generate a paragraph of free-flowing thoughts that express various ideas, questions, reflections, and possibilities.

This should be a stream-of-consciousness style paragraph that weaves together multiple thoughts, including:
- Speculative "What if" questions
- Personal reflections starting with "I wonder" or "I think"
- Connections between different concepts
- Emotional responses to ideas
- Potential goals or aspirations
- Philosophical musings
- Creative ideas or insights

Make it feel like a natural flow of thoughts, with one idea leading to another. The paragraph should be 5-8 sentences long and capture the richness and complexity of the entity's inner thought process.""",
            messages=[{"role": "user", "content": "Please generate a paragraph of free-flowing thoughts based on the dream narrative and context."}]
        )
        initiative = response.content[0].text.strip()
        logger.info("Received free-flowing thoughts from Claude")
        logger.info(f"Generated thoughts: {initiative}")
        return initiative
    except Exception as e:
        logger.error(f"Error in free-flowing thoughts generation: {str(e)}")
        return None

def generate_random_thought(blueprint, kin_id, api_key, remote=False, provider=None, model=None):
    """
    Generate a random thought using the three-stage process:
    1. Extract keywords from messages and files
    2. Generate a dream narrative from the keywords
    3. Generate an initiative from the dream narrative
    
    Args:
        blueprint: Blueprint name
        kin_id: Kin ID
        api_key: API key for authentication
        remote: Whether to use remote API instead of localhost (default: False)
        provider: Optional LLM provider to use ("claude" or "openai")
        model: Optional model to use
    
    Returns:
        A random thought as a string
    """
    # Get kin path
    kin_path = get_kin_path(blueprint, kin_id)
    
    try:
        # Get appropriate LLM client based on provider
        if provider == "openai":
            from services.llm_service import LLMProvider
            client = LLMProvider.get_provider("openai")
        else:
            # Default to Claude
            client = get_anthropic_client()
        
        # First try to get recently modified files from commit history
        files_to_use = get_recently_modified_files(blueprint, kin_id, count=3)
        
        # If no files from commit history, fall back to random selection
        if not files_to_use or len(files_to_use) == 0:
            logger.info("No recently modified files found, falling back to random selection")
            files_to_use = get_random_files(kin_path, count=3)
            
        logger.info(f"Selected files for thought generation: {files_to_use}")

        # Stage 1: Extract keywords
        logger.info("Stage 1: Extracting keywords")
        keywords = extract_keywords(kin_path, files_to_use, client)
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
        initiative = generate_initiative(kin_path, dream_narrative, files_to_use, client)
        if not initiative:
            raise Exception("Failed to generate initiative")
        logger.info(f"Generated initiative: {initiative}")

        return initiative

    except Exception as e:
        logger.error(f"Error in thought generation process: {str(e)}")
        return "I wonder about the nature of consciousness and my role in understanding it."

def send_message_to_kin(blueprint, kin_id, message, mode=None, remote=False, provider=None, model=None):
    """
    Send a message to the kin by calling the function directly.
    
    Args:
        blueprint: Blueprint name
        kin_id: Kin ID
        message: Message content
        mode: Message mode (optional)
        remote: Whether to use remote API instead of localhost (default: False)
        provider: Optional LLM provider to use ("claude" or "openai")
        model: Optional model to use
    
    Returns:
        The response from the kin
    """
    try:
        # Choose API URL based on remote flag
        base_url = "https://api.kinos-engine.ai" if remote else BASE_URL
        api_url = f"{base_url}/v2/blueprints/{blueprint}/kins/{kin_id}/messages"
        
        logger.info(f"=== Sending Message to Kin ===")
        logger.info(f"Using {'remote' if remote else 'local'} API")
        logger.info(f"API URL: {api_url}")
        
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
        
        # Determine model to use
        model_to_use = model or "claude-3-7-sonnet-latest"
        
        payload = {
            "content": message,
            "model": model_to_use
        }
        
        # Add provider if specified
        if provider:
            payload["provider"] = provider
            
        if mode:  # Add mode only if specified
            payload["mode"] = mode
            
        logger.info(f"Request Headers: {headers}")
        logger.info(f"Request Payload: {payload}")
        
        # Make request
        logger.info("Making API request...")
        response = requests.post(api_url, headers=headers, json=payload)
        
        # Log response details
        logger.info(f"Response Status Code: {response.status_code}")
        logger.info(f"Response Headers: {dict(response.headers)}")
        
        # Check for errors
        if response.status_code != 200:
            logger.error(f"API error: {response.status_code} - {response.text}")
            return f"Error: {response.status_code} - {response.text}"
        
        # Parse response
        result = response.json()
        logger.info(f"Response JSON: {result}")
        
        # Extract the response text
        if "response" in result:
            response_text = result["response"]
            logger.info(f"Extracted response: {response_text[:100]}...")
            return response_text
        else:
            logger.error(f"No response field in API result: {result}")
            return f"Error: No response field in API result: {result}"
            
    except Exception as e:
        logger.error(f"Error sending message to kin: {str(e)}")
        logger.exception("Full exception details:")
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

def add_message(blueprint, kin_id, data):
    """
    Add a message to messages.json without any processing.
    Useful for recording messages without triggering a response or action.
    
    Args:
        blueprint: Blueprint name
        kin_id: Kin ID
        data: Message data dictionary
        
    Returns:
        Dictionary with status and message information
    """
    # Parse request data
    message_content = data.get('message', data.get('content', ''))
    role = data.get('role', 'user')  # Default role is 'user'
    
    if not message_content:
        return {"error": "Message content is required"}, 400
        
    # Get kin path
    kin_path = get_kin_path(blueprint, kin_id)
    if not os.path.exists(kin_path):
        return {"error": f"kin '{kin_id}' not found for blueprint '{blueprint}'"}, 404
    
    # Path to messages.json file
    messages_file = os.path.join(kin_path, "messages.json")
    
    # Load existing messages or create empty list
    messages = []
    if os.path.exists(messages_file):
        try:
            with open(messages_file, 'r', encoding='utf-8') as f:
                messages = json.load(f)
                if not isinstance(messages, list):
                    messages = []
        except Exception as e:
            logger.error(f"Error reading messages.json: {str(e)}")
            messages = []
    
    # Create new message
    timestamp = datetime.now().isoformat()
    
    new_message = {
        "role": role,
        "content": message_content,
        "timestamp": timestamp
    }
    
    # Add additional metadata if provided
    if 'metadata' in data:
        new_message['metadata'] = data['metadata']
    
    # Add message to list
    messages.append(new_message)
    
    # Write updated file
    try:
        os.makedirs(os.path.dirname(messages_file), exist_ok=True)
        with open(messages_file, 'w', encoding='utf-8') as f:
            json.dump(messages, f, indent=2)
        
        logger.info(f"Message successfully added for {blueprint}/{kin_id}")
        return {
            "status": "success",
            "message": "Message successfully added",
            "message_id": len(messages) - 1,  # Index of the new message
            "timestamp": timestamp
        }
    except Exception as e:
        logger.error(f"Error writing to messages.json: {str(e)}")
        return {"error": f"Error saving message: {str(e)}"}, 500

def add_channel_message(blueprint, kin_id, channel_id, data):
    """
    Add a message to a specific channel's messages.json file without any processing.
    
    Args:
        blueprint: Blueprint name
        kin_id: Kin ID
        channel_id: Channel ID
        data: Message data dictionary
        
    Returns:
        Dictionary with status and message information
    """
    # Parse request data
    message_content = data.get('message', data.get('content', ''))
    role = data.get('role', 'user')  # Default role is 'user'
    
    if not message_content:
        return {"error": "Message content is required"}, 400
        
    # Get kin path
    kin_path = get_kin_path(blueprint, kin_id)
    if not os.path.exists(kin_path):
        return {"error": f"kin '{kin_id}' not found for blueprint '{blueprint}'"}, 404
    
    # Get channel path
    from services.file_service import get_channel_path
    channel_path = get_channel_path(kin_path, channel_id)
    
    # Create channel directory if it doesn't exist
    try:
        os.makedirs(channel_path, exist_ok=True)
        logger.info(f"Channel directory created or verified: {channel_path}")
    except Exception as e:
        logger.error(f"Error creating channel directory: {str(e)}")
        return {"error": f"Error creating channel: {str(e)}"}, 500
    
    # Path to channel's messages.json file
    messages_file = os.path.join(channel_path, "messages.json")
    
    # Load existing messages or create empty list
    messages = []
    if os.path.exists(messages_file):
        try:
            with open(messages_file, 'r', encoding='utf-8') as f:
                messages = json.load(f)
                if not isinstance(messages, list):
                    messages = []
        except Exception as e:
            logger.error(f"Error reading channel messages.json: {str(e)}")
            messages = []
    
    # Create new message
    timestamp = datetime.now().isoformat()
    
    new_message = {
        "role": role,
        "content": message_content,
        "timestamp": timestamp,
        "channel_id": channel_id
    }
    
    # Add additional metadata if provided
    if 'metadata' in data:
        new_message['metadata'] = data['metadata']
    
    # Add message to list
    messages.append(new_message)
    
    # Write updated file
    try:
        with open(messages_file, 'w', encoding='utf-8') as f:
            json.dump(messages, f, indent=2)
        
        logger.info(f"Message successfully added for {blueprint}/{kin_id}/channels/{channel_id}")
        return {
            "status": "success",
            "message": "Message successfully added",
            "message_id": len(messages) - 1,  # Index of the new message
            "timestamp": timestamp,
            "channel_id": channel_id
        }
    except Exception as e:
        logger.error(f"Error writing to channel messages.json: {str(e)}")
        return {"error": f"Error saving message: {str(e)}"}, 500

def autonomous_thinking(blueprint, kin_id, telegram_token=None, telegram_chat_id=None, iterations=3, wait_time=600, remote=False, provider=None, model=None):
    """
    Run the autonomous thinking process for a kin.
    
    Args:
        blueprint: Blueprint name
        kin_id: Kin ID
        telegram_token: Optional Telegram bot token
        telegram_chat_id: Optional Telegram chat ID
        iterations: Number of thinking iterations (default: 3)
        wait_time: Wait time between iterations in seconds (default: 600 = 10 minutes)
        remote: Whether to use remote API instead of localhost (default: False)
        provider: Optional LLM provider to use ("claude" or "openai")
        model: Optional model to use
    
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
    
    # Get API key from environment
    api_key = os.getenv("API_SECRET_KEY")
    if not api_key:
        logger.error("API_SECRET_KEY environment variable not set")
        return False

    # Generate the initial random thought
    logger.info(f"Generating initial random thought for {blueprint}/{kin_id}")
    current_thought = generate_random_thought(blueprint, kin_id, api_key, remote=remote, provider=provider, model=model)
    
    # Run the thinking iterations
    for i in range(iterations):
        logger.info(f"Starting iteration {i+1}/{iterations}")
        logger.info(f"Current thought: {current_thought}")
        
        try:
            # For the first iteration, send the random thought directly
            if i == 0:
                # Send message to kin
                response = send_message_to_kin(blueprint, kin_id, current_thought, mode="self-reflection", remote=remote, provider=provider, model=model)
            else:
                # For subsequent iterations, send a message with the continuation prompt
                # Include <system> tags in the actual message content, not as a separate system parameter
                response = send_message_to_kin(blueprint, kin_id, "<system>Continue your thoughts</system>", mode="self-reflection", provider=provider, model=model)
            
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
                # Use the api_key we got at the start of the function
                current_thought = generate_random_thought(blueprint, kin_id, api_key, remote=remote, provider=provider, model=model)
    
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
    parser.add_argument("--provider", help="LLM provider to use (claude or openai)")
    parser.add_argument("--model", help="Specific model to use")
    
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
        logger.info(f"Using Telegram credentials from {'arguments' if args.telegram_token else 'environment variables'}")
    else:
        logger.warning("Telegram credentials not found in arguments or environment variables")
    
    # Run autonomous thinking
    try:
        success = autonomous_thinking(
            args.blueprint,
            args.kin_id,
            telegram_token,
            telegram_chat_id,
            args.iterations,
            args.wait_time,
            remote=args.remote,
            provider=args.provider,
            model=args.model
        )
        
        return 0 if success else 1
    except Exception as e:
        logger.error(f"Unhandled exception in autonomous thinking: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
