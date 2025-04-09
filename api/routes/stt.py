from flask import Blueprint, request, jsonify
import requests
import re
from config import logger
from services.stt_service import transcribe_audio

stt_bp = Blueprint('stt', __name__)

@stt_bp.route('/stt', methods=['POST'])
def speech_to_text():
    """
    Endpoint to convert speech to text using OpenAI's Whisper API.
    Detects and filters out code blocks from transcription.
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
        
        # Parse the response
        result = response.json()
        
        # Check if the transcription contains code blocks and filter them out
        if 'text' in result:
            # Pattern for code blocks with language specification: ```language ... ```
            code_block_pattern = r'```[\w\+\-\#]*\s*[\s\S]*?```'
            
            # Find all code blocks in the transcription
            code_blocks = re.findall(code_block_pattern, result['text'])
            
            if code_blocks:
                logger.info(f"Detected {len(code_blocks)} code blocks in transcription")
                
                # Replace code blocks with placeholders
                filtered_text = result['text']
                for i, block in enumerate(code_blocks):
                    placeholder = f"[CODE_BLOCK_{i+1}]"
                    filtered_text = filtered_text.replace(block, placeholder)
                
                # Add the filtered text and code blocks to the result
                result['original_text'] = result['text']
                result['text'] = filtered_text
                result['code_blocks_detected'] = True
                result['code_blocks_count'] = len(code_blocks)
                
                logger.info(f"Filtered out code blocks from transcription")
            else:
                result['code_blocks_detected'] = False
        
        # Return the transcription result
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in STT endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500
