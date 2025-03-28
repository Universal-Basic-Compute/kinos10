import os
import requests
import logging
from config import logger

def generate_image(prompt, aspect_ratio="ASPECT_1_1", model="V_2", magic_prompt_option="AUTO"):
    """
    Generate an image using Ideogram API.
    
    Args:
        prompt: The text prompt for image generation
        aspect_ratio: Aspect ratio for the image (default: ASPECT_1_1)
        model: Model to use (default: V_2)
        magic_prompt_option: Magic prompt option (default: AUTO)
        
    Returns:
        Dictionary with image URL and metadata if successful, or error details
    """
    # Get API key from environment variable
    api_key = os.getenv("IDEOGRAM_API_KEY")
    if not api_key:
        logger.error("IDEOGRAM_API_KEY environment variable not set")
        raise ValueError("Ideogram API key not configured")
    
    # Prepare request to Ideogram API
    url = "https://api.ideogram.ai/generate"
    headers = {
        "Api-Key": api_key,
        "Content-Type": "application/json"
    }
    
    # Prepare payload
    payload = {
        "image_request": {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "model": model,
            "magic_prompt_option": magic_prompt_option
        }
    }
    
    logger.info(f"Sending image generation request to Ideogram with prompt: {prompt[:50]}...")
    
    try:
        # Make request to Ideogram API
        response = requests.post(url, json=payload, headers=headers)
        
        # Check for errors
        if response.status_code != 200:
            logger.error(f"Ideogram API error: {response.status_code} - {response.text}")
            return {
                "error": "Error generating image",
                "status_code": response.status_code,
                "details": response.text
            }
        
        # Parse response
        result = response.json()
        logger.info(f"Received response from Ideogram: {result}")
        
        # Return the result
        return result
    except Exception as e:
        logger.error(f"Error calling Ideogram API: {str(e)}")
        return {
            "error": f"Error calling Ideogram API: {str(e)}"
        }
