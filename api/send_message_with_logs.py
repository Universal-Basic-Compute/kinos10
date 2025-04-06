#!/usr/bin/env python3
"""
Direct Message Sender (with logging)

This script sends a message directly to a kin and shows the API logs.
Run this while your API server is running locally to see the full Claude API logs.

Usage:
    python send_message_with_logs.py <blueprint> <kin_id> "<message>"
"""

import os
import sys
import json
import requests
import argparse
from dotenv import load_dotenv
from config import BASE_URL

def send_message(blueprint, kin_id, message, api_key):
    """Send a message to a kin and return the response."""
    # API endpoint - use BASE_URL from config
    api_url = f"{BASE_URL}/kins/{blueprint}/{kin_id}/messages"
    
    # Prepare headers and payload
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": api_key
    }
    
    payload = {
        "content": message,
        "model": "claude-3-7-sonnet-latest"  # Use Sonnet for better responses
    }
    
    print(f"Sending message to {blueprint}/{kin_id}: {message}")
    print(f"API URL: {api_url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print("\nSending request... Check your API server console for detailed logs!\n")
    
    # Make the request
    response = requests.post(api_url, headers=headers, json=payload)
    
    # Check for errors
    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}")
        return None
    
    # Return the response
    return response.json()

def main():
    parser = argparse.ArgumentParser(description="Send a message and see API logs")
    parser.add_argument("blueprint", help="Blueprint name")
    parser.add_argument("kin_id", help="Kin ID")
    parser.add_argument("message", help="Message content")
    
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    # Get API key
    api_key = os.getenv("API_SECRET_KEY")
    if not api_key:
        print("Error: API_SECRET_KEY environment variable not set")
        return 1
    
    # Send the message
    result = send_message(args.blueprint, args.kin_id, args.message, api_key)
    
    if result:
        print("\n--- Response ---")
        if "response" in result:
            print(result["response"])
        else:
            print(f"Unexpected response format: {json.dumps(result, indent=2)}")
        print("--- End of Response ---")
        return 0
    else:
        return 1

if __name__ == "__main__":
    sys.exit(main())
