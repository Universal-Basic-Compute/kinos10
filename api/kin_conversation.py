#!/usr/bin/env python3
"""
Kin Conversation Script

This script initiates a conversation between two kins, with one starting and the other responding.
The conversation continues for a specified number of exchanges.

Usage:
    python kin_conversation.py <blueprint1> <kin_id1> <blueprint2> <kin_id2> [--message "Initial message"] 
                              [--conversation-length N] [--wait-time SECONDS]
                              [--telegram-token TOKEN] [--telegram-chat-id CHAT_ID]

Example:
    python kin_conversation.py therapykindouble WarmMink92 therapykindouble CoolFox45 --conversation-length 5 --wait-time 30
"""

import os
import sys
import json
import time
import random
import argparse
import requests
import logging
from datetime import datetime
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_api_key():
    """Get API key from environment variable."""
    # Load environment variables from .env file
    load_dotenv()
    
    # Also try to load from the parent directory (where the .env file might be)
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    load_dotenv(os.path.join(parent_dir, '.env'))
    
    api_key = os.getenv("API_SECRET_KEY")
    if not api_key:
        logger.error("API_SECRET_KEY environment variable not set")
        raise ValueError("API key not configured")
    return api_key

def generate_random_thought(blueprint, kin_id, api_key, remote=False):
    """
    Generate a random thought for a kin using the autonomous thinking endpoint.
    
    Args:
        blueprint: Blueprint name
        kin_id: Kin ID
        api_key: API key for authentication
        remote: Whether to use remote API instead of localhost (default: False)
    
    Returns:
        A random thought as a string
    """
    # Choose API URL based on remote flag
    base_url = "https://api.kinos-engine.ai" if remote else BASE_URL
    api_url = f"{base_url}/v2/blueprints/{blueprint}/kins/{kin_id}/autonomous_thinking"
    
    # Prepare request
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": api_key
    }
    
    payload = {
        "iterations": 1,
        "wait_time": 1  # Minimal wait time since we only need one thought
    }
    
    try:
        # Make request
        logger.info(f"Generating random thought for {blueprint}/{kin_id}")
        response = requests.post(api_url, headers=headers, json=payload)
        
        # Check for errors
        if response.status_code != 200:
            logger.error(f"API error: {response.status_code} - {response.text}")
            return f"Hello, I'm {kin_id} from the {blueprint} blueprint. Let's have a conversation."
        
        # Parse response
        result = response.json()
        
        # The autonomous thinking endpoint starts a background process and doesn't return the thought directly
        # So we need to wait a moment and then get the latest message from the kin
        logger.info("Waiting for thought generation...")
        time.sleep(5)  # Wait for the thought to be generated
        
        # Get the latest message
        messages_url = f"https://api.kinos-engine.ai/v2/blueprints/{blueprint}/kins/{kin_id}/messages"
        messages_response = requests.get(messages_url, headers=headers)
        
        if messages_response.status_code != 200:
            logger.error(f"API error getting messages: {messages_response.status_code} - {messages_response.text}")
            return f"Hello, I'm {kin_id} from the {blueprint} blueprint. Let's have a conversation."
        
        messages_data = messages_response.json()
        
        # Get the latest user message (which should be the thought)
        for message in reversed(messages_data.get("messages", [])):
            if message.get("role") == "user":
                thought = message.get("content", "")
                if thought:
                    logger.info(f"Generated thought: {thought}")
                    return thought
        
        # Fallback if no thought was found
        return f"Hello, I'm {kin_id} from the {blueprint} blueprint. Let's have a conversation."
        
    except Exception as e:
        logger.error(f"Error generating random thought: {str(e)}")
        return f"Hello, I'm {kin_id} from the {blueprint} blueprint. Let's have a conversation."

def send_message(blueprint, kin_id, message, api_key):
    """
    Send a message to a kin and get the response.
    
    Args:
        blueprint: Blueprint name
        kin_id: Kin ID
        message: Message content
        api_key: API key for authentication
    
    Returns:
        The kin's response as a string
    """
    # API endpoint
    api_url = f"https://api.kinos-engine.ai/v2/blueprints/{blueprint}/kins/{kin_id}/messages"
    
    # Prepare request
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": api_key
    }
    
    payload = {
        "content": message
    }
    
    try:
        # Make request
        logger.info(f"Sending message to {blueprint}/{kin_id}: {message[:50]}...")
        response = requests.post(api_url, headers=headers, json=payload)
        
        # Check for errors
        if response.status_code != 200:
            logger.error(f"API error: {response.status_code} - {response.text}")
            return f"I'm sorry, I couldn't process that message properly."
        
        # Parse response
        result = response.json()
        
        # Extract the response text
        if "response" in result:
            kin_response = result["response"]
            logger.info(f"Received response from {blueprint}/{kin_id}: {kin_response[:50]}...")
            return kin_response
        else:
            logger.error(f"No response field in result: {result}")
            return f"I'm sorry, I couldn't process that message properly."
            
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        return f"I'm sorry, I couldn't process that message properly due to an error: {str(e)}"

def send_telegram_notification(token, chat_id, sender_blueprint, sender_kin, receiver_blueprint, receiver_kin, message, response=None):
    """
    Send a notification to Telegram about a message exchange.
    
    Args:
        token: Telegram bot token
        chat_id: Telegram chat ID
        sender_blueprint: Blueprint name of the sender
        sender_kin: Kin ID of the sender
        receiver_blueprint: Blueprint name of the receiver
        receiver_kin: Kin ID of the receiver
        message: The message content
        response: Optional response content
    
    Returns:
        Boolean indicating success
    """
    if not token or not chat_id:
        logger.warning(f"Telegram token or chat ID not provided, skipping notification")
        return False
    
    # Telegram API endpoint
    api_url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    # Convert chat_id to integer if it's a string
    try:
        if isinstance(chat_id, str):
            chat_id = int(chat_id)
        logger.info(f"Using chat_id as integer: {chat_id}")
    except ValueError:
        logger.warning(f"Could not convert chat_id to integer, using as is: {chat_id}")
    
    # Prepare message
    if response:
        # This is a complete exchange (message and response)
        telegram_message = f"💬 *Message Exchange*\n\n"
        telegram_message += f"*From:* {sender_blueprint}/{sender_kin} ➡️ *To:* {receiver_blueprint}/{receiver_kin}\n\n"
        telegram_message += f"📤 *Message:*\n{message[:500]}...\n\n"
        telegram_message += f"📥 *Response:*\n{response[:500]}...\n"
    else:
        # This is just the initial message
        telegram_message = f"💬 *Conversation Started*\n\n"
        telegram_message += f"*From:* {sender_blueprint}/{sender_kin} ➡️ *To:* {receiver_blueprint}/{receiver_kin}\n\n"
        telegram_message += f"📤 *Initial Message:*\n{message[:500]}...\n"
    
    # Prepare request
    payload = {
        "chat_id": chat_id,
        "text": telegram_message,
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
        
        logger.info(f"Telegram notification sent successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error sending Telegram notification: {str(e)}")
        return False

def run_conversation(blueprint1, kin_id1, blueprint2, kin_id2, initial_message=None, conversation_length=3, wait_time=60, telegram_token=None, telegram_chat_id=None):
    """
    Run a conversation between two kins.
    
    Args:
        blueprint1: Blueprint name for first kin
        kin_id1: Kin ID for first kin
        blueprint2: Blueprint name for second kin
        kin_id2: Kin ID for second kin
        initial_message: Optional initial message (if None, generates a random thought)
        conversation_length: Number of exchanges in the conversation
        wait_time: Wait time between messages in seconds
        telegram_token: Optional Telegram bot token
        telegram_chat_id: Optional Telegram chat ID
    
    Returns:
        Boolean indicating success
    """
    try:
        # Get API key
        api_key = get_api_key()
        
        # Get initial message or generate random thought
        if initial_message:
            current_message = initial_message
            logger.info(f"Starting conversation with provided message: {current_message}")
        else:
            current_message = generate_random_thought(blueprint1, kin_id1, api_key)
            logger.info(f"Starting conversation with generated thought: {current_message}")
        
        # Log conversation start
        logger.info(f"# Conversation between {blueprint1}/{kin_id1} and {blueprint2}/{kin_id2}")
        logger.info(f"# Started at: {datetime.now().isoformat()}")
        logger.info(f"# Conversation length: {conversation_length} exchanges")
        logger.info(f"# Wait time: {wait_time} seconds\n")
        
        # First message from kin1 (thought or provided message)
        logger.info(f"## {blueprint1}/{kin_id1} (Initial)\n")
        logger.info(f"{current_message}\n")
        
        # Send Telegram notification for initial message
        if telegram_token and telegram_chat_id:
            send_telegram_notification(
                telegram_token, 
                telegram_chat_id, 
                blueprint1, 
                kin_id1, 
                blueprint2, 
                kin_id2, 
                current_message
            )
        
        # Run the conversation
        current_blueprint = blueprint2
        current_kin = kin_id2
        other_blueprint = blueprint1
        other_kin = kin_id1
        
        for i in range(conversation_length):
            logger.info(f"Exchange {i+1}/{conversation_length}")
            
            # Send message to current kin
            response = send_message(current_blueprint, current_kin, current_message, api_key)
            
            # Log the response
            logger.info(f"## {current_blueprint}/{current_kin}\n")
            logger.info(f"{response}\n")
            
            # Send Telegram notification for this exchange
            if telegram_token and telegram_chat_id:
                send_telegram_notification(
                    telegram_token, 
                    telegram_chat_id, 
                    other_blueprint, 
                    other_kin, 
                    current_blueprint, 
                    current_kin, 
                    current_message, 
                    response
                )
            
            # Update current message for next exchange
            current_message = response
            
            # Swap kins for next exchange
            current_blueprint, other_blueprint = other_blueprint, current_blueprint
            current_kin, other_kin = other_kin, current_kin
            
            # Wait before next exchange (unless it's the last one)
            if i < conversation_length - 1:
                logger.info(f"Waiting {wait_time} seconds before next exchange...")
                time.sleep(wait_time)
        
        logger.info(f"Conversation completed.")
        return True
        
    except Exception as e:
        logger.error(f"Error in conversation: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Run a conversation between two kins")
    parser.add_argument("blueprint1", help="Blueprint name for first kin")
    parser.add_argument("kin_id1", help="Kin ID for first kin")
    parser.add_argument("blueprint2", help="Blueprint name for second kin")
    parser.add_argument("kin_id2", help="Kin ID for second kin")
    parser.add_argument("--message", help="Initial message (if not provided, generates a random thought)")
    parser.add_argument("--conversation-length", type=int, default=3, help="Number of exchanges in the conversation (default: 3)")
    parser.add_argument("--wait-time", type=int, default=60, help="Wait time between messages in seconds (default: 60)")
    parser.add_argument("--telegram-token", help="Telegram bot token for notifications")
    parser.add_argument("--telegram-chat-id", help="Telegram chat ID for notifications")
    parser.add_argument("--remote", action="store_true", help="Use remote API instead of localhost")
    
    args = parser.parse_args()
    
    # Load environment variables from .env file
    load_dotenv()
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    load_dotenv(os.path.join(parent_dir, '.env'))
    
    # Get Telegram credentials from environment variables if not provided as arguments
    telegram_token = args.telegram_token or os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = args.telegram_chat_id or os.getenv("TELEGRAM_CHAT_ID")
    
    if telegram_token and telegram_chat_id:
        logger.info(f"Using Telegram credentials from {'arguments' if args.telegram_token else 'environment variables'}")
    else:
        logger.warning("Telegram credentials not found in arguments or environment variables")
    
    # Run the conversation
    success = run_conversation(
        args.blueprint1,
        args.kin_id1,
        args.blueprint2,
        args.kin_id2,
        args.message,
        args.conversation_length,
        args.wait_time,
        telegram_token,
        telegram_chat_id
    )
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
