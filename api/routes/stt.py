from flask import Blueprint, request, jsonify
import requests
from config import logger
from services.stt_service import transcribe_audio

stt_bp = Blueprint('stt', __name__)

@stt_bp.route('/stt', methods=['POST'])
def speech_to_text():
    """
    Endpoint to convert speech to text using OpenAI's Whisper API.
    """
    try:
        # Check if file is in request
        if 'file' not in request.files:
            return jsonify({"error": "No audio file provided"}), 400
        
        audio_file = request.files['file']
        if audio_file.filename == '':
            return jsonify({"error": "No audio file selected"}), 400
        
        # Get optional parameters
        model = request.form.get('model', 'whisper-1')
        language = request.form.get('language', None)
        prompt = request.form.get('prompt', None)
        response_format = request.form.get('response_format', 'json')
        
        # Log the request
        logger.info(f"STT request received with model: {model}, language: {language}")
        
        # Prepare request to OpenAI API
        url, headers, form_data, files = transcribe_audio(
            audio_file, model, language, prompt, response_format
        )
        
        # Make request to OpenAI API
        response = requests.post(
            url,
            headers=headers,
            data=form_data,
            files={"file": (audio_file.filename, audio_file, audio_file.content_type)}
        )
        
        # Check for errors
        if response.status_code != 200:
            logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
            return jsonify({
                "error": "Error transcribing audio",
                "details": response.text
            }), response.status_code
        
        # Return the transcription result
        return response.json()
        
    except Exception as e:
        logger.error(f"Error in STT endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500
