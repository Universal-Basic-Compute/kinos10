import os
import requests
import logging
from config import logger

def transcribe_audio(audio_file, model="whisper-1", language=None, prompt=None, response_format="json"):
    """
    Transcribe audio using OpenAI's Whisper API.
    
    Args:
        audio_file: The audio file data
        model: Model to use (default: whisper-1)
        language: Optional language code in ISO-639-1 format
        prompt: Optional text to guide the model's style
        response_format: Format of the output (default: json)
        
    Returns:
        Tuple of (url, headers, form_data, files) for making the request
    """
    # Get API key from environment variable
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY environment variable not set")
        raise ValueError("OpenAI API key not configured")
    
    # Prepare request to OpenAI API
    url = "https://api.openai.com/v1/audio/transcriptions"
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    
    # Prepare form data
    form_data = {
        "model": model
    }
    
    # Add optional parameters if provided
    if language:
        form_data["language"] = language
    if prompt:
        form_data["prompt"] = prompt
    if response_format:
        form_data["response_format"] = response_format
    
    logger.info(f"Sending transcription request to OpenAI with model: {model}")
    
    # Prepare files
    files = {
        "file": audio_file
    }
    
    logger.info(f"Sending transcription request to OpenAI with model: {model}")
    
    return url, headers, form_data, files
