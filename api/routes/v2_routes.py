from flask import Blueprint, request, jsonify, redirect, url_for
from config import logger

v2_bp = Blueprint('v2', __name__)

@v2_bp.route('/', methods=['GET'])
def api_root_v2():
    """
    Root endpoint for v2 API that returns API information.
    """
    from app import api_root
    return api_root()

@v2_bp.route('/health', methods=['GET'])
def health_check_v2():
    """
    Health check endpoint for v2 API.
    """
    from app import health_check
    return health_check()

@v2_bp.route('/blueprints', methods=['GET'])
def get_blueprints_v2():
    """
    V2 API endpoint to get a list of all blueprints.
    Maps to the original get_blueprints function.
    """
    from routes.projects import get_blueprints
    return get_blueprints()

@v2_bp.route('/blueprints/<blueprint>', methods=['GET'])
def get_blueprint_details_v2(blueprint):
    """
    V2 API endpoint to get details about a specific blueprint.
    """
    # This is a new endpoint that doesn't exist in v1
    # For now, just return basic information
    from routes.projects import get_blueprint_kins
    kins_response = get_blueprint_kins(blueprint)
    
    # If the response is an error, return it directly
    if isinstance(kins_response, tuple) and kins_response[1] != 200:
        return kins_response
    
    # Otherwise, extract the kins and return blueprint details
    import os
    from config import blueprintS_DIR
    
    blueprint_path = os.path.join(blueprintS_DIR, blueprint)
    if not os.path.exists(blueprint_path):
        return jsonify({"error": f"Blueprint '{blueprint}' not found"}), 404
    
    # Get basic blueprint details
    import datetime
    
    try:
        # Get creation and modification time of blueprint directory
        created_at = datetime.datetime.fromtimestamp(os.path.getctime(blueprint_path)).isoformat()
        updated_at = datetime.datetime.fromtimestamp(os.path.getmtime(blueprint_path)).isoformat()
        
        return jsonify({
            "id": blueprint,
            "name": blueprint.capitalize(),
            "description": f"The {blueprint} blueprint",
            "version": "1.0.0",
            "created_at": created_at,
            "updated_at": updated_at
        })
    except Exception as e:
        logger.error(f"Error getting blueprint details: {str(e)}")
        return jsonify({"error": str(e)}), 500

@v2_bp.route('/blueprints/<blueprint>/initialize', methods=['POST'])
def initialize_blueprint_v2(blueprint):
    """
    V2 API endpoint to initialize a blueprint.
    Maps to the original initialize_blueprint function.
    """
    from routes.projects import initialize_blueprint
    return initialize_blueprint(blueprint)

@v2_bp.route('/blueprints/<blueprint>/kins', methods=['GET'])
def get_blueprint_kins_v2(blueprint):
    """
    V2 API endpoint to get a list of kins for a blueprint.
    Maps to the original get_blueprint_kins function.
    """
    from routes.projects import get_blueprint_kins
    return get_blueprint_kins(blueprint)

@v2_bp.route('/blueprints/<blueprint>/kins', methods=['POST'])
def create_kin_v2(blueprint):
    """
    V2 API endpoint to create a new kin.
    Maps to the original create_kin function but adapts the request.
    """
    # Adapt the request format from v2 to v1
    from flask import request
    original_data = request.json or {}
    
    # Transform the request data
    v1_data = {
        "blueprint": blueprint,
        "kin_name": original_data.get("name", ""),
        "template_override": original_data.get("template_override")
    }
    
    # Create a new request context with the transformed data
    from werkzeug.local import LocalProxy
    request.json = v1_data
    
    # Call the original function
    from routes.projects import create_kin
    return create_kin()

@v2_bp.route('/blueprints/<blueprint>/kins/<kin_id>', methods=['GET'])
def get_kin_details_v2(blueprint, kin_id):
    """
    V2 API endpoint to get details about a specific kin.
    """
    # This is a new endpoint that doesn't exist in v1
    import os
    import json
    from config import blueprintS_DIR
    from services.file_service import get_kin_path
    
    # Get the kin path
    kin_path = get_kin_path(blueprint, kin_id)
    if not os.path.exists(kin_path):
        return jsonify({"error": f"Kin '{kin_id}' not found for blueprint '{blueprint}'"}), 404
    
    # Get kin details
    import datetime
    
    try:
        # Get creation and modification time of kin directory
        created_at = datetime.datetime.fromtimestamp(os.path.getctime(kin_path)).isoformat()
        updated_at = datetime.datetime.fromtimestamp(os.path.getmtime(kin_path)).isoformat()
        
        # Try to get kin name from kin_info.json if it exists
        kin_name = kin_id
        kin_info_path = os.path.join(kin_path, "kin_info.json")
        if os.path.exists(kin_info_path):
            try:
                with open(kin_info_path, 'r') as f:
                    kin_info = json.load(f)
                    kin_name = kin_info.get('name', kin_id)
            except:
                logger.warning(f"Could not read kin_info.json for {blueprint}/{kin_id}")
        
        return jsonify({
            "id": kin_id,
            "name": kin_name,
            "blueprint_id": blueprint,
            "created_at": created_at,
            "updated_at": updated_at
        })
    except Exception as e:
        logger.error(f"Error getting kin details: {str(e)}")
        return jsonify({"error": str(e)}), 500

@v2_bp.route('/blueprints/<blueprint>/kins/<kin_id>/rename', methods=['POST'])
def rename_kin_v2(blueprint, kin_id):
    """
    V2 API endpoint to rename a kin.
    Maps to the original rename_kin function.
    """
    from routes.projects import rename_kin
    return rename_kin(blueprint, kin_id)

@v2_bp.route('/blueprints/<blueprint>/kins/<kin_id>/messages', methods=['GET'])
def get_messages_v2(blueprint, kin_id):
    """
    V2 API endpoint to get messages for a kin.
    Maps to the original get_messages function.
    """
    from routes.messages import get_messages
    return get_messages(blueprint, kin_id)

@v2_bp.route('/blueprints/<blueprint>/kins/<kin_id>/messages', methods=['POST'])
def send_message_v2(blueprint, kin_id):
    """
    V2 API endpoint to send a message to a kin.
    Maps to the original send_message function.
    """
    from routes.messages import send_message
    return send_message(blueprint, kin_id)

@v2_bp.route('/blueprints/<blueprint>/kins/<kin_id>/analysis', methods=['POST'])
def analyze_message_v2(blueprint, kin_id):
    """
    V2 API endpoint to analyze a message with Claude without saving it.
    Maps to the original analyze_message function.
    """
    from routes.messages import analyze_message
    return analyze_message(blueprint, kin_id)

@v2_bp.route('/blueprints/<blueprint>/kins/<kin_id>/aider_logs', methods=['GET'])
def get_aider_logs_v2(blueprint, kin_id):
    """
    V2 API endpoint to get Aider logs for a kin.
    Maps to the original get_aider_logs function.
    """
    from routes.messages import get_aider_logs
    return get_aider_logs(blueprint, kin_id)

@v2_bp.route('/blueprints/<blueprint>/kins/<kin_id>/files', methods=['GET'])
def get_kin_files_v2(blueprint, kin_id):
    """
    V2 API endpoint to get a list of files in a kin.
    Maps to the original get_kin_files function.
    """
    from routes.files import get_kin_files
    return get_kin_files(f"{blueprint}/{kin_id}")

@v2_bp.route('/blueprints/<blueprint>/kins/<kin_id>/files/<path:file_path>', methods=['GET'])
def get_file_content_v2(blueprint, kin_id, file_path):
    """
    V2 API endpoint to get the content of a file.
    Maps to the original get_file_content function.
    """
    from routes.files import get_file_content
    return get_file_content(f"{blueprint}/{kin_id}", file_path)

@v2_bp.route('/blueprints/<blueprint>/kins/<kin_id>/content', methods=['GET'])
def get_kin_content_v2(blueprint, kin_id):
    """
    V2 API endpoint to get the content of all files in a kin folder as JSON.
    Maps to the original get_kin_content function.
    """
    from routes.files import get_kin_content
    return get_kin_content(f"{blueprint}/{kin_id}")

@v2_bp.route('/blueprints/<blueprint>/kins/<kin_id>/images', methods=['POST'])
def generate_kin_image_v2(blueprint, kin_id):
    """
    V2 API endpoint to generate an image based on a message.
    Maps to the original generate_kin_image function.
    """
    from routes.projects import generate_kin_image
    return generate_kin_image(blueprint, kin_id)

@v2_bp.route('/blueprints/<blueprint>/kins/<kin_id>/image', methods=['POST'])
def generate_kin_image_singular_v2(blueprint, kin_id):
    """
    V2 API endpoint to generate an image based on a message (singular form).
    Maps to the original generate_kin_image function.
    """
    from routes.projects import generate_kin_image
    return generate_kin_image(blueprint, kin_id)

@v2_bp.route('/tts', methods=['POST'])
def text_to_speech_v2():
    """
    V2 API endpoint for text-to-speech.
    Maps to the original text_to_speech function.
    """
    from routes.tts import text_to_speech
    return text_to_speech()

@v2_bp.route('/stt', methods=['POST'])
def speech_to_text_v2():
    """
    V2 API endpoint for speech-to-text.
    Maps to the original speech_to_text function.
    """
    from routes.stt import speech_to_text
    return speech_to_text()

@v2_bp.route('/blueprints/<blueprint>/reset', methods=['POST'])
def reset_blueprint_v2(blueprint):
    """
    V2 API endpoint to reset a blueprint and all its kins.
    Maps to the original reset_blueprint function.
    """
    from routes.projects import reset_blueprint
    return reset_blueprint(blueprint)

@v2_bp.route('/blueprints/<blueprint>/kins/<kin_id>/reset', methods=['POST'])
def reset_kin_v2(blueprint, kin_id):
    """
    V2 API endpoint to reset a kin to its initial template state.
    Maps to the original reset_kin function.
    """
    from routes.projects import reset_kin
    return reset_kin(blueprint, kin_id)

@v2_bp.route('/blueprints/<blueprint>/kins/<kin_id>/build', methods=['POST'])
def build_kin_v2(blueprint, kin_id):
    """
    V2 API endpoint to send a message to Aider for file creation/modification.
    Maps to the original build_kin function.
    """
    from routes.projects import build_kin
    return build_kin(blueprint, kin_id)

@v2_bp.route('/blueprints/<blueprint>/kins/<kin_id>/autonomous_thinking', methods=['POST'])
def trigger_autonomous_thinking_v2(blueprint, kin_id):
    """
    V2 API endpoint to trigger autonomous thinking for a kin.
    Maps to the original trigger_autonomous_thinking function.
    """
    from routes.projects import trigger_autonomous_thinking
    return trigger_autonomous_thinking(blueprint, kin_id)

@v2_bp.route('/blueprints/<blueprint>/kins/<kin_id>/modes', methods=['GET'])
def get_kin_modes_v2(blueprint, kin_id):
    """
    V2 API endpoint to get available modes for a kin.
    Maps to the original get_kin_modes function.
    """
    from routes.projects import get_kin_modes
    return get_kin_modes(blueprint, kin_id)

@v2_bp.route('/blueprints/codeguardian/create', methods=['POST'])
def create_code_guardian_v2():
    """
    V2 API endpoint to create a CodeGuardian kin for a GitHub repository.
    Maps to the original create_code_guardian_api function.
    """
    from routes.projects import create_code_guardian_api
    return create_code_guardian_api()

@v2_bp.route('/<path:undefined_route>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def catch_all_v2(undefined_route):
    """Catch-all route for undefined v2 API endpoints."""
    logger.warning(f"Undefined v2 API route accessed: {undefined_route}")
    return jsonify({
        "error": "Not Found",
        "message": f"The requested v2 endpoint '/{undefined_route}' does not exist.",
        "documentation_url": "https://api.kinos-engine.ai/v2"
    }), 404
