import os
import requests
import logging
from config import logger

def text_to_speech_request(text, voice_id='UgBBYS2sOqTuMpoF3BR0', model='eleven_flash_v2_5'):
    """
    Prepare a request to the ElevenLabs API for text-to-speech conversion.
    
    Args:
        text: The text to convert to speech
        voice_id: ElevenLabs voice ID
        model: ElevenLabs model to use
        
    Returns:
        Tuple of (url, headers, payload) for making the request
    """
    # Get API key from environment variable
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        logger.error("ELEVENLABS_API_KEY environment variable not set")
        raise ValueError("ElevenLabs API key not configured")
    
    # Prepare request to ElevenLabs API
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream?output_format=mp3_44100_128"
    headers = {
        'Accept': 'audio/mpeg',
        'Content-Type': 'application/json',
        'xi-api-key': api_key
    }
    payload = {
        'text': text,
        'model_id': model,
        'voice_settings': {
            'stability': 0.5,
            'similarity_boost': 0.5
        },
        'optimize_streaming_latency': 3  # Use max latency optimizations
    }
    
    logger.info(f"Prepared ElevenLabs TTS request for text: {text[:50]}...")
    
    return url, headers, payload
