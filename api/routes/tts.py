from flask import Blueprint, request, jsonify, Response, stream_with_context
import requests
from config import logger
from services.tts_service import text_to_speech_request

tts_bp = Blueprint('tts', __name__)

@tts_bp.route('/tts', methods=['POST'])
def text_to_speech():
    """
    Endpoint to convert text to speech using ElevenLabs API.
    Streams the audio response back to the client.
    """
    try:
        # Get request data
        data = request.json
        text = data.get('text')
        
        # Check for both voiceId and voice_id parameters
        voice_id = data.get('voiceId', data.get('voice_id', 'IKne3meq5aSn9XLyUdCD'))  # Default ElevenLabs voice ID
        model = data.get('model', 'eleven_flash_v2_5')  # Default model
        
        # Validate required parameters
        if not text:
            return jsonify({"error": "Text is required"}), 400
        
        # Log the voice ID being used
        logger.info(f"Using voice ID: {voice_id} for TTS request")
        
        # Prepare request to ElevenLabs API
        url, headers, payload = text_to_speech_request(text, voice_id, model)
        
        logger.info(f"Calling ElevenLabs TTS API for text: {text[:50]}...")
        
        # Make request to ElevenLabs API with streaming
        elevenlabs_response = requests.post(
            url,
            json=payload,
            headers=headers,
            stream=True  # Enable streaming
        )
        
        # Check for errors
        if elevenlabs_response.status_code != 200:
            logger.error(f"ElevenLabs API error: {elevenlabs_response.status_code} - {elevenlabs_response.text}")
            return jsonify({
                "error": "Error generating speech",
                "details": elevenlabs_response.text
            }), elevenlabs_response.status_code
        
        # Stream the response back to the client
        def generate():
            for chunk in elevenlabs_response.iter_content(chunk_size=4096):
                yield chunk
        
        # Return a streaming response
        return Response(
            stream_with_context(generate()),
            content_type='audio/mpeg',
            headers={
                'Content-Disposition': 'attachment; filename="speech.mp3"'
            }
        )
        
    except Exception as e:
        logger.error(f"Error in TTS endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500
