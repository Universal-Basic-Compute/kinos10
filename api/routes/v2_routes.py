from flask import Blueprint, request, jsonify, redirect, url_for, current_app as app
import json
import os
import json
import datetime
import subprocess
import re
import base64
import threading
import requests
from config import logger, blueprintS_DIR
from services.file_service import get_kin_path, initialize_kin
from services.claude_service import call_claude_with_context, build_context
from services.aider_service import call_aider_with_context
from routes.messages import extract_and_save_url_content

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
    # Get the original data
    original_data = request.get_json() or {}
    
    # Transform the data to v1 format
    v1_data = {
        "blueprint": blueprint,
        "kin_name": original_data.get("name", ""),
        "template_override": original_data.get("template_override")
    }
    
    # Import the create_kin function
    from routes.projects import create_kin
    
    # Create a new request context with the transformed data
    with app.test_request_context(
        method='POST',
        path=f'/api/proxy/kins',
        data=json.dumps(v1_data),  # Use data instead of json
        content_type='application/json'  # Set content type explicitly
    ) as ctx:
        # Push the context
        ctx.push()
        try:
            # Call create_kin with the transformed data
            response = create_kin()
            return response
        finally:
            ctx.pop()

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
    
    Query parameters:
    - channel_id: Optional channel ID (if not provided, uses main channel)
    """
    # Check if channel_id is provided in query parameters
    channel_id = request.args.get('channel_id')
    
    if channel_id:
        # If channel_id is provided, use the channel-specific endpoint
        return get_channel_messages_v2(blueprint, kin_id, channel_id)
    else:
        # Otherwise, use the original function (main channel)
        from routes.messages import get_messages
        return get_messages(blueprint, kin_id)

@v2_bp.route('/blueprints/<blueprint>/kins/<kin_id>/channels/<channel_id>/messages', methods=['GET'])
def get_channel_messages_v2(blueprint, kin_id, channel_id):
    """
    V2 API endpoint to get messages for a specific channel.
    """
    try:
        since = request.args.get('since')
        
        # Validate blueprint and kin
        if not os.path.exists(os.path.join(blueprintS_DIR, blueprint)):
            return jsonify({"error": f"Blueprint '{blueprint}' not found"}), 404
            
        kin_path = get_kin_path(blueprint, kin_id)
        if not os.path.exists(kin_path):
            return jsonify({"error": f"Kin '{kin_id}' not found for blueprint '{blueprint}'"}), 404
        
        # Handle main channel specially
        if channel_id == "main":
            # Use the original get_messages function
            from routes.messages import get_messages
            return get_messages(blueprint, kin_id)
        
        # Get channel path
        from services.file_service import get_channel_path
        channel_path = get_channel_path(kin_path, channel_id)
        
        # Check if channel exists
        if not os.path.exists(channel_path):
            return jsonify({"error": f"Channel '{channel_id}' not found"}), 404
        
        # Load messages
        messages_file = os.path.join(channel_path, "messages.json")
        if not os.path.exists(messages_file):
            return jsonify({"messages": []}), 200
        
        with open(messages_file, 'r') as f:
            messages = json.load(f)
        
        # Filter by timestamp if provided
        if since:
            try:
                since_dt = datetime.datetime.fromisoformat(since)
                messages = [m for m in messages if datetime.datetime.fromisoformat(m.get('timestamp', '')) > since_dt]
            except ValueError:
                return jsonify({"error": "Invalid timestamp format"}), 400
        
        return jsonify({"messages": messages, "channel_id": channel_id})
        
    except Exception as e:
        logger.error(f"Error getting channel messages: {str(e)}")
        return jsonify({"error": str(e)}), 500

@v2_bp.route('/blueprints/<blueprint>/kins/<kin_id>/messages', methods=['POST'])
def send_message_v2(blueprint, kin_id):
    """
    V2 API endpoint to send a message to a kin.
    Maps to the original send_message function.
    
    Request body can include:
    - channel_id: Optional channel ID (if not provided, uses main channel)
    """
    # Get the original data
    original_data = request.get_json() or {}
    
    # Check if channel_id is provided in the request
    channel_id = original_data.get('channel_id')
    
    if channel_id:
        # If channel_id is provided, use the channel-specific endpoint
        return send_channel_message_v2(blueprint, kin_id, channel_id)
    else:
        # Otherwise, use the original function (main channel)
        from routes.messages import send_message
        return send_message(blueprint, kin_id)

@v2_bp.route('/blueprints/<blueprint>/kins/<kin_id>/channels/<channel_id>/messages', methods=['POST'])
def send_channel_message_v2(blueprint, kin_id, channel_id=None):
    """
    V2 API endpoint to send a message to a specific channel.
    """
    try:
        # Parse request data
        data = request.json or {}  # Add 'or {}' to handle None case
        
        # If channel_id is not in the URL, try to get it from the request body
        if channel_id is None:
            channel_id = data.get('channel_id')
            
            # If still None, use the main channel
            if channel_id is None:
                # Use the original send_message function
                from routes.messages import send_message
                return send_message(blueprint, kin_id)
        
        # Support both formats: new format with 'message' and original format with 'content'
        message_content = data.get('message', data.get('content', ''))
        
        # Support both formats: new format with 'screenshot' and original format with 'images'
        images = data.get('images', [])
        if 'screenshot' in data and data['screenshot']:
            # Add screenshot to images array if it's not empty
            images.append(data['screenshot'])
        
        # Get optional fields from new format
        username = data.get('username', '')
        character = data.get('character', '')
        token = data.get('token', '')  # Can be used for authentication in the future
        model = data.get('model', '')  # Optional model parameter
        history_length = data.get('history_length', 25)  # Default to 25 messages
        addSystem = data.get('addSystem', None)  # Optional additional system instructions
        
        # Ensure history_length is an integer and has a reasonable value (default: 25)
        try:
            history_length = int(history_length)
            if history_length < 0:
                history_length = 0
            elif history_length > 50:  # Set a reasonable upper limit
                history_length = 50
        except (ValueError, TypeError):
            history_length = 10  # Default if invalid value
        
        # Original format attachments
        attachments = data.get('attachments', [])
        
        # Get addContext parameter - list of files/directories to always include
        add_context = data.get('addContext', [])
        if add_context and not isinstance(add_context, list):
            # If it's not a list, convert it to a list with a single item
            add_context = [add_context]
        
        # Initialize saved_images list to track saved image paths
        saved_images = []
        
        # Validate blueprint
        if not os.path.exists(os.path.join(blueprintS_DIR, blueprint)):
            return jsonify({"error": f"Blueprint '{blueprint}' not found"}), 404
            
        kin_path = get_kin_path(blueprint, kin_id)
        
        # Process addContext to expand directories and verify files exist
        processed_add_context = []
        if add_context:
            for path in add_context:
                full_path = os.path.join(kin_path, path)
                if os.path.exists(full_path):
                    if os.path.isdir(full_path):
                        # If it's a directory, add all files in it
                        for root, _, files in os.walk(full_path):
                            for file in files:
                                file_path = os.path.join(root, file)
                                rel_path = os.path.relpath(file_path, kin_path)
                                processed_add_context.append(rel_path)
                                logger.info(f"Added file from directory in addContext: {rel_path}")
                    else:
                        # It's a file, add it directly
                        processed_add_context.append(path)
                        logger.info(f"Added file from addContext: {path}")
                else:
                    logger.warning(f"File or directory in addContext not found: {path}")

        # Add processed_add_context to attachments
        if processed_add_context:
            if not attachments:
                attachments = []
            attachments.extend(processed_add_context)
            logger.info(f"Added {len(processed_add_context)} files from addContext to attachments")
        
        # Track if we need to create a new kin
        kin_created = False
        
        # First, check if we need to create a new kin
        if not os.path.exists(kin_path) and kin_id != "template":
            # Create the kin from template
            logger.info(f"Kin '{kin_id}' not found for blueprint '{blueprint}', creating it from template")
            kin_created = True
            
            # Create kins directory if it doesn't exist
            kins_dir = os.path.join(blueprintS_DIR, blueprint, "kins")
            os.makedirs(kins_dir, exist_ok=True)
            logger.info(f"Created or verified kins directory: {kins_dir}")
            
            # Create kin directory
            os.makedirs(kin_path, exist_ok=True)
            logger.info(f"Created kin directory: {kin_path}")
            
            # Copy template to kin directory
            template_path = os.path.join(blueprintS_DIR, blueprint, "template")
            logger.info(f"Looking for template at: {template_path}")
            
            if not os.path.exists(template_path):
                # Check if we need to initialize the blueprint template first
                logger.warning(f"Template not found for blueprint '{blueprint}', attempting to initialize")
                
                # Try to initialize the blueprint template
                kin_templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "blueprints")
                blueprint_template_dir = os.path.join(kin_templates_dir, blueprint, "template")
                
                if os.path.exists(blueprint_template_dir):
                    logger.info(f"Found template in kin directory, copying to app data")
                    # Create blueprint directory if needed
                    blueprint_dir = os.path.join(blueprintS_DIR, blueprint)
                    os.makedirs(blueprint_dir, exist_ok=True)
                    
                    # Copy template from kin directory to app data
                    import shutil
                    shutil.copytree(blueprint_template_dir, template_path)
                    logger.info(f"Initialized template for blueprint '{blueprint}'")
                else:
                    logger.error(f"No template found for blueprint '{blueprint}' in kin directory")
                    return jsonify({"error": f"Template not found for blueprint '{blueprint}'"}), 404
            
            # Verify template exists after potential initialization
            if not os.path.exists(template_path):
                return jsonify({"error": f"Template not found for blueprint '{blueprint}'"}), 404
            
            # List template contents for debugging
            template_contents = os.listdir(template_path)
            logger.info(f"Template contents: {template_contents}")
            
            # Use a more robust copy method
            import shutil
            for item in os.listdir(template_path):
                s = os.path.join(template_path, item)
                d = os.path.join(kin_path, item)
                try:
                    if os.path.isdir(s):
                        shutil.copytree(s, d)
                    else:
                        shutil.copy2(s, d)
                    logger.info(f"Copied {s} to {d}")
                except Exception as copy_error:
                    logger.error(f"Error copying {s} to {d}: {str(copy_error)}")
            
            # Create messages.json file
            messages_file = os.path.join(kin_path, "messages.json")
            with open(messages_file, 'w') as f:
                json.dump([], f)
            logger.info(f"Created messages.json file")
            
            # Create thoughts.txt file
            thoughts_file = os.path.join(kin_path, "thoughts.txt")
            with open(thoughts_file, 'w') as f:
                f.write(f"# Thoughts for kin: {kin_id}\nCreated: {datetime.datetime.now().isoformat()}\n\n")
            logger.info(f"Created thoughts.txt file")
            
            # Create images directory
            images_dir = os.path.join(kin_path, "images")
            os.makedirs(images_dir, exist_ok=True)
            logger.info(f"Created images directory: {images_dir}")
            
            logger.info(f"Successfully created kin '{kin_id}' for blueprint '{blueprint}'")
            
            # Verify kin directory exists and check contents
            logger.info(f"Verifying kin directory exists: {kin_path}")
            if os.path.exists(kin_path):
                dir_contents = os.listdir(kin_path)
                logger.info(f"Kin directory contents: {dir_contents}")
            else:
                logger.error(f"Kin directory does not exist after creation: {kin_path}")
                return jsonify({"error": f"Failed to create kin directory"}), 500
        
        # Handle main channel specially
        if channel_id == "main":
            # Use the original send_message function
            from routes.messages import send_message
            return send_message(blueprint, kin_id)
        
        # Get channel path
        from services.file_service import get_channel_path
        channel_path = get_channel_path(kin_path, channel_id)
        
        # Check if channel exists, create it if not
        if not os.path.exists(channel_path):
            from services.file_service import create_channel
            channel_name = data.get('channel_name', f"Channel {channel_id}")
            create_channel(kin_path, channel_name, None, "direct", None, channel_id)
        
        # Save images to kin directory if any
        if images and len(images) > 0:
            # Create images directory if it doesn't exist
            images_dir = os.path.join(kin_path, "images")
            os.makedirs(images_dir, exist_ok=True)
            
            for i, img_base64 in enumerate(images):
                try:
                    # Clean up the base64 data
                    if ',' in img_base64:
                        # Extract the base64 part after the comma
                        img_base64 = img_base64.split(',', 1)[1]
                    
                    # Generate filename with date
                    date_str = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                    image_filename = f"{date_str}_{i}.jpg"
                    image_path = os.path.join(images_dir, image_filename)
                    
                    # Save the image
                    with open(image_path, 'wb') as f:
                        image_data = base64.b64decode(img_base64)
                        f.write(image_data)
                    
                    # Add relative path to saved images
                    saved_images.append(os.path.join("images", image_filename))
                    logger.info(f"Saved image to {image_path}")
                except Exception as e:
                    logger.error(f"Error saving image: {str(e)}")
        
        # Now that we've ensured the kin and channel exist, proceed with message handling
        messages_file = os.path.join(channel_path, "messages.json")
        
        # Load existing messages
        if os.path.exists(messages_file):
            with open(messages_file, 'r') as f:
                messages = json.load(f)
        else:
            # If messages.json doesn't exist, create it
            messages = []
            with open(messages_file, 'w') as f:
                json.dump(messages, f)
        
        # Prepare user message object
        user_message = {
            "role": "user",
            "content": message_content,
            "timestamp": datetime.datetime.now().isoformat(),
            "channel_id": channel_id  # Add channel_id to the message
        }
        
        # Add image paths to the message if any were saved
        if saved_images:
            user_message["images"] = saved_images
        
        # Add optional fields if they exist
        if username:
            user_message["username"] = username
        if character:
            user_message["character"] = character
        
        # Get optional mode parameter
        mode = data.get('mode', '')  # Get optional mode parameter
        
        # Check for URLs in the message
        url_pattern = r'https?://[^\s<>"]+|www\.[^\s<>"]+'
        urls = re.findall(url_pattern, message_content)
        
        # Extract content from URLs and add to attachments
        for url in urls:
            if not url.startswith('http'):
                url = 'https://' + url
            
            logger.info(f"Found URL in message: {url}")
            source_files = extract_and_save_url_content(url, kin_path)
            
            if source_files:
                logger.info(f"Saved URL content to: {source_files}")
                if not attachments:
                    attachments = []
                # Handle both single file and list of files
                if isinstance(source_files, list):
                    attachments.extend(source_files)
                else:
                    attachments.append(source_files)

        # Get optional parameters for context building
        min_files = data.get('min_files', 5)  # Default to 5
        max_files = data.get('max_files', 15)  # Default to 15
        
        # Validate the values
        try:
            min_files = int(min_files)
            max_files = int(max_files)
            if min_files < 1:
                min_files = 1
            if max_files < min_files:
                max_files = min_files
        except (ValueError, TypeError):
            min_files = 5
            max_files = 15

        # Build context (select relevant files)
        selected_files, selected_mode = build_context(
            blueprint, 
            kin_id, 
            message_content, 
            attachments, 
            kin_path, 
            model, 
            mode, 
            addSystem, 
            history_length=2,
            min_files=min_files,
            max_files=max_files
        )
        
        # Add saved image files to selected files for context
        for img_path in saved_images:
            if img_path not in selected_files:
                selected_files.append(img_path)
        
        # Add channel-specific messages to context
        # Load the last few messages from this channel
        channel_context = []
        if len(messages) > 0:
            # Get the last few messages (up to history_length)
            channel_context = messages[-min(history_length, len(messages)):]
        
        # Log the selected files and mode
        logger.info(f"Selected files for context: {selected_files}")
        if selected_mode:
            logger.info(f"Selected mode: {selected_mode}")
        
        # Call Claude and Aider with the selected context
        try:
            # Call Claude directly for a response
            # Pass is_new_message=True to indicate this message isn't in messages.json yet
            claude_response = call_claude_with_context(
                selected_files, 
                kin_path, 
                message_content, 
                images, 
                model,
                history_length,
                is_new_message=True,
                addSystem=addSystem,
                mode=selected_mode,  # Pass the selected mode
                channel_messages=channel_context  # Pass channel-specific messages
            )
            
            # Create assistant message object
            assistant_message = {
                "role": "assistant",
                "content": claude_response,
                "timestamp": datetime.datetime.now().isoformat(),
                "channel_id": channel_id  # Add channel_id to the message
            }
            
            # Add character if it was provided
            if character:
                assistant_message["character"] = character
            
            # NOW add both messages to the messages array and save to messages.json
            messages.append(user_message)
            messages.append(assistant_message)
            
            # Save updated messages with both user and assistant messages
            with open(messages_file, 'w') as f:
                json.dump(messages, f, indent=2)
            
            # Call Aider in parallel for file updates (don't wait for response)
            def run_aider():
                try:
                    aider_response = call_aider_with_context(kin_path, selected_files, message_content, addSystem=addSystem)
                    logger.info("Aider processing completed")
                    # Log the complete Aider response
                    logger.info(f"Aider response: {aider_response}")
                except Exception as e:
                    logger.error(f"Error in Aider thread: {str(e)}")
            
            # Start Aider in a separate thread
            aider_thread = threading.Thread(target=run_aider)
            aider_thread.start()
            
            # Return the Claude response directly in the API response
            response_data = {
                "status": "completed",
                "message_id": str(len(messages) - 1),
                "content": claude_response,  # Only include content field
                "channel_id": channel_id
            }
            
            # Add kin_created flag if a new kin was created
            if kin_created:
                response_data["kin_created"] = True
            
            # Add selected_mode if one was determined
            if selected_mode:
                response_data["mode"] = selected_mode
                
            return jsonify(response_data)
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return jsonify({"error": f"Error processing message: {str(e)}"}), 500
        
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        return jsonify({"error": str(e)}), 500

@v2_bp.route('/blueprints/<blueprint>/kins/<kin_id>/analysis', methods=['GET', 'POST'])
def analyze_message_v2(blueprint, kin_id):
    """
    V2 API endpoint to analyze a message with Claude without saving it.
    Supports both GET (with query params) and POST (with JSON body).
    """
    try:
        # Get message content from either query params (GET) or JSON body (POST)
        if request.method == 'GET':
            message_content = request.args.get('message', '')
            # Remove quotes if present (since query params might include them)
            message_content = message_content.strip('"\'')
            
            # Get other parameters from query string
            model = request.args.get('model', '')
            addSystem = request.args.get('addSystem', None)
            min_files = request.args.get('min_files', 5)
            max_files = request.args.get('max_files', 15)
            
            # Create a data dict to match POST format
            data = {
                'message': message_content,
                'model': model,
                'addSystem': addSystem,
                'min_files': min_files,
                'max_files': max_files,
                'content': message_content  # Add this for backward compatibility
            }
        else:  # POST
            data = request.get_json() or {}  # Use empty dict if None
            message_content = data.get('message', data.get('content', ''))
            # Ensure both message and content are set for backward compatibility
            data['message'] = message_content
            data['content'] = message_content

        # Validate required parameters
        if not message_content:
            return jsonify({"error": "Message is required"}), 400

        # Log the message content to verify it's being passed correctly
        logger.info(f"Analysis request with message: {message_content[:100]}...")

        # Call analyze_message directly with the parameters extracted from the request
        return analyze_message_with_params(blueprint, kin_id, message_content, data)

    except Exception as e:
        logger.error(f"Error in analyze_message_v2: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Add this helper function to handle the parameters directly
def analyze_message_with_params(blueprint, kin_id, message_content, data):
    """Helper function to call analyze_message with parameters instead of relying on request object"""
    from routes.messages import analyze_message
    
    # Create a new request context with the data
    with app.test_request_context(
        method='POST',
        path=f'/api/proxy/kins/{blueprint}/{kin_id}/analysis',
        json=data
    ) as ctx:
        # Push the context
        ctx.push()
        try:
            # Call analyze_message with the new context
            return analyze_message(blueprint, kin_id)
        finally:
            ctx.pop()

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

@v2_bp.route('/blueprints/<blueprint>/kins/<kin_id>/build', methods=['GET', 'POST'])
def build_kin_v2(blueprint, kin_id):
    """
    V2 API endpoint to send a message to Aider for file creation/modification.
    Maps to the original build_kin function.
    Supports both GET and POST methods.
    """
    from routes.projects import build_kin
    return build_kin(blueprint, kin_id)

@v2_bp.route('/blueprints/<blueprint>/kins/<kin_id>/listen', methods=['GET', 'POST'])
def listen_to_kin_v2(blueprint, kin_id):
    """
    V2 API endpoint that redirects /listen to /build.
    This is an alias for the build endpoint, allowing the kin to listen to user messages.
    Supports both GET and POST methods.
    """
    from routes.projects import build_kin
    return build_kin(blueprint, kin_id)

@v2_bp.route('/blueprints/<blueprint>/kins/<kin_id>/autonomous_thinking', methods=['GET', 'POST'])
def trigger_autonomous_thinking_v2(blueprint, kin_id):
    """
    V2 API endpoint to trigger autonomous thinking for a kin.
    Maps to the original trigger_autonomous_thinking function.
    Supports both GET and POST methods.
    """
    from routes.projects import trigger_autonomous_thinking
    return trigger_autonomous_thinking(blueprint, kin_id)

@v2_bp.route('/blueprints/<blueprint>/kins/<kin_id>/commit-history', methods=['GET'])
def get_commit_history_v2(blueprint, kin_id):
    """
    V2 API endpoint to get Git commit history for a kin.
    Returns commits ordered by date (latest first).
    """
    try:
        # Validate blueprint and kin
        if not os.path.exists(os.path.join(blueprintS_DIR, blueprint)):
            return jsonify({"error": f"Blueprint '{blueprint}' not found"}), 404
            
        kin_path = get_kin_path(blueprint, kin_id)
        if not os.path.exists(kin_path):
            return jsonify({"error": f"Kin '{kin_id}' not found for blueprint '{blueprint}'"}), 404
        
        # Check if .git directory exists
        git_dir = os.path.join(kin_path, ".git")
        if not os.path.exists(git_dir) or not os.path.isdir(git_dir):
            return jsonify({"error": "No Git repository found for this kin"}), 404
        
        # Get git commit history using git log
        try:
            # Use git log with --stat to get commit stats
            result = subprocess.run(
                ["git", "log", "--pretty=format:%s|%h|%ad", "--date=iso", "--stat", "-n", "50"],
                cwd=kin_path,
                text=True,
                capture_output=True,
                check=True
            )
                
            # Parse the output
            commits = []
            lines = result.stdout.strip().split('\n')
            current_commit = None
                
            for line in lines:
                if '|' in line:  # This is a commit line
                    if ' | ' not in line:  # This is a commit header line
                        message, short_hash, date = line.split('|')
                        current_commit = {
                            "message": message,
                            "hash": short_hash,
                            "date": date,
                            "changes": {
                                "files_changed": 0,
                                "insertions": 0,
                                "deletions": 0,
                                "files": []
                            }
                        }
                        commits.append(current_commit)
                    else:  # This is a file stats line
                        try:
                            # Parse the --stat output format which looks like:
                            # file.txt | 2 ++
                            # or
                            # file.txt | 4 ++--
                            file_path, changes = line.split(' | ')
                            file_path = file_path.strip()
                            changes = changes.strip()
                            
                            # Parse the changes
                            if changes:
                                # Extract numbers from changes (e.g., "2 ++" -> 2)
                                num_changes = int(''.join(c for c in changes if c.isdigit()) or 0)
                                insertions = changes.count('+')
                                deletions = changes.count('-')
                                
                                # Update commit stats
                                current_commit["changes"]["files_changed"] += 1
                                current_commit["changes"]["insertions"] += insertions
                                current_commit["changes"]["deletions"] += deletions
                                
                                # Add file info
                                current_commit["changes"]["files"].append({
                                    "path": file_path,
                                    "added": insertions,
                                    "deleted": deletions
                                })
                        except ValueError:
                            continue  # Skip malformed lines
                
            return jsonify({
                "commits": commits,
                "total": len(commits)
            })
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Git command failed: {e.stderr}")
            return jsonify({"error": f"Git command failed: {e.stderr}"}), 500
        
    except Exception as e:
        logger.error(f"Error getting Git history: {str(e)}")
        return jsonify({"error": str(e)}), 500

@v2_bp.route('/blueprints/<blueprint>/kins/<kin_id>/copy', methods=['POST'])
def copy_kin_v2(blueprint, kin_id):
    """
    V2 API endpoint to copy a kin to a new kin within the same blueprint.
    """
    try:
        # Parse request data
        data = request.json
        new_kin_name = data.get('new_name')
        
        if not new_kin_name:
            return jsonify({"error": "new_name is required"}), 400
            
        # Validate blueprint
        if not os.path.exists(os.path.join(blueprintS_DIR, blueprint)):
            return jsonify({"error": f"Blueprint '{blueprint}' not found"}), 404
            
        # Get source kin path
        source_kin_path = get_kin_path(blueprint, kin_id)
        if not os.path.exists(source_kin_path):
            return jsonify({"error": f"Source kin '{kin_id}' not found"}), 404
            
        # Initialize new kin with the provided name
        try:
            new_kin_id = initialize_kin(blueprint, new_kin_name)
            new_kin_path = get_kin_path(blueprint, new_kin_id)
            
            # Copy all files from source kin to new kin
            import shutil
            # Remove the newly created kin directory (from initialize_kin)
            shutil.rmtree(new_kin_path)
            # Copy the source kin directory to the new location
            shutil.copytree(source_kin_path, new_kin_path)
            
            # Update kin_info.json with new name
            kin_info_path = os.path.join(new_kin_path, "kin_info.json")
            kin_info = {
                "name": new_kin_name,
                "copied_from": kin_id,
                "created_at": datetime.datetime.now().isoformat(),
                "updated_at": datetime.datetime.now().isoformat()
            }
            with open(kin_info_path, 'w') as f:
                json.dump(kin_info, f, indent=2)
            
            return jsonify({
                "status": "success",
                "message": f"Kin '{kin_id}' copied to '{new_kin_name}'",
                "source_kin_id": kin_id,
                "new_kin_id": new_kin_id,
                "new_kin_name": new_kin_name
            })
            
        except Exception as e:
            logger.error(f"Error copying kin: {str(e)}")
            return jsonify({"error": f"Error copying kin: {str(e)}"}), 500
            
    except Exception as e:
        logger.error(f"Error in copy_kin endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500

@v2_bp.route('/blueprints/<blueprint>/kins/<kin_id>/modes', methods=['GET'])
def get_kin_modes_v2(blueprint, kin_id):
    """
    V2 API endpoint to get available modes for a kin.
    Maps to the original get_kin_modes function.
    """
    from routes.projects import get_kin_modes
    return get_kin_modes(blueprint, kin_id)

@v2_bp.route('/blueprints/<blueprint>/kins/<kin_id>/channels', methods=['GET'])
def get_channels_v2(blueprint, kin_id):
    """
    V2 API endpoint to get a list of channels for a kin.
    """
    try:
        # Validate blueprint and kin
        if not os.path.exists(os.path.join(blueprintS_DIR, blueprint)):
            return jsonify({"error": f"Blueprint '{blueprint}' not found"}), 404
            
        kin_path = get_kin_path(blueprint, kin_id)
        if not os.path.exists(kin_path):
            return jsonify({"error": f"Kin '{kin_id}' not found for blueprint '{blueprint}'"}), 404
        
        # Get channels
        from services.file_service import get_channels
        channels = get_channels(kin_path)
        
        return jsonify({"channels": channels})
        
    except Exception as e:
        logger.error(f"Error getting channels: {str(e)}")
        return jsonify({"error": str(e)}), 500

@v2_bp.route('/blueprints/<blueprint>/kins/<kin_id>/channels', methods=['POST'])
def create_channel_v2(blueprint, kin_id):
    """
    V2 API endpoint to create a new channel for a kin.
    """
    try:
        # Parse request data
        data = request.json
        channel_name = data.get('name', '')
        user_id = data.get('user_id')
        channel_type = data.get('type', 'direct')
        metadata = data.get('metadata', {})
        
        # Validate required parameters
        if not channel_name:
            return jsonify({"error": "Channel name is required"}), 400
        
        # Validate blueprint and kin
        if not os.path.exists(os.path.join(blueprintS_DIR, blueprint)):
            return jsonify({"error": f"Blueprint '{blueprint}' not found"}), 404
            
        kin_path = get_kin_path(blueprint, kin_id)
        if not os.path.exists(kin_path):
            return jsonify({"error": f"Kin '{kin_id}' not found for blueprint '{blueprint}'"}), 404
        
        # Create channel
        from services.file_service import create_channel
        channel_id = create_channel(kin_path, channel_name, user_id, channel_type, metadata)
        
        return jsonify({
            "status": "success",
            "message": f"Channel '{channel_name}' created",
            "channel_id": channel_id
        })
        
    except Exception as e:
        logger.error(f"Error creating channel: {str(e)}")
        return jsonify({"error": str(e)}), 500

@v2_bp.route('/blueprints/<blueprint>/kins/<kin_id>/channels/<channel_id>', methods=['GET'])
def get_channel_v2(blueprint, kin_id, channel_id):
    """
    V2 API endpoint to get details about a specific channel.
    """
    try:
        # Validate blueprint and kin
        if not os.path.exists(os.path.join(blueprintS_DIR, blueprint)):
            return jsonify({"error": f"Blueprint '{blueprint}' not found"}), 404
            
        kin_path = get_kin_path(blueprint, kin_id)
        if not os.path.exists(kin_path):
            return jsonify({"error": f"Kin '{kin_id}' not found for blueprint '{blueprint}'"}), 404
        
        # Handle main channel specially
        if channel_id == "main":
            main_channel = {
                "id": "main",
                "name": "Main Channel",
                "created_at": datetime.datetime.fromtimestamp(os.path.getctime(kin_path)).isoformat(),
                "updated_at": datetime.datetime.fromtimestamp(os.path.getmtime(kin_path)).isoformat(),
                "type": "main",
                "is_main": True
            }
            return jsonify(main_channel)
        
        # Get channel path
        from services.file_service import get_channel_path
        channel_path = get_channel_path(kin_path, channel_id)
        
        # Check if channel exists
        if not os.path.exists(channel_path):
            return jsonify({"error": f"Channel '{channel_id}' not found"}), 404
        
        # Get channel info
        channel_info_path = os.path.join(channel_path, "channel_info.json")
        if os.path.exists(channel_info_path):
            try:
                with open(channel_info_path, 'r', encoding='utf-8') as f:
                    channel_info = json.load(f)
                return jsonify(channel_info)
            except Exception as e:
                logger.error(f"Error loading channel info: {str(e)}")
                return jsonify({"error": f"Error loading channel info: {str(e)}"}), 500
        else:
            # Create basic channel info if file doesn't exist
            channel_info = {
                "id": channel_id,
                "name": f"Channel {channel_id}",
                "created_at": datetime.datetime.fromtimestamp(os.path.getctime(channel_path)).isoformat(),
                "updated_at": datetime.datetime.fromtimestamp(os.path.getmtime(channel_path)).isoformat(),
                "type": "unknown"
            }
            return jsonify(channel_info)
        
    except Exception as e:
        logger.error(f"Error getting channel: {str(e)}")
        return jsonify({"error": str(e)}), 500

@v2_bp.route('/blueprints/codeguardian/create', methods=['POST'])
def create_code_guardian_v2():
    """
    V2 API endpoint to create a CodeGuardian kin for a GitHub repository.
    Maps to the original create_code_guardian_api function.
    """
    from routes.projects import create_code_guardian_api
    return create_code_guardian_api()

@v2_bp.route('/blueprints/<blueprint>/kins/<kin_id>/channels/<channel_id>', methods=['PUT'])
def update_channel_v2(blueprint, kin_id, channel_id):
    """
    V2 API endpoint to update a channel.
    """
    try:
        # Parse request data
        data = request.json
        
        # Validate blueprint and kin
        if not os.path.exists(os.path.join(blueprintS_DIR, blueprint)):
            return jsonify({"error": f"Blueprint '{blueprint}' not found"}), 404
            
        kin_path = get_kin_path(blueprint, kin_id)
        if not os.path.exists(kin_path):
            return jsonify({"error": f"Kin '{kin_id}' not found for blueprint '{blueprint}'"}), 404
        
        # Cannot update the main channel
        if channel_id == "main":
            return jsonify({"error": "Cannot update the main channel"}), 400
        
        # Get channel path
        from services.file_service import get_channel_path
        channel_path = get_channel_path(kin_path, channel_id)
        
        # Check if channel exists
        if not os.path.exists(channel_path):
            return jsonify({"error": f"Channel '{channel_id}' not found"}), 404
        
        # Update channel info
        from utils.channel_utils import update_channel_info
        updated_info = update_channel_info(kin_path, channel_id, data)
        
        if updated_info:
            return jsonify({
                "status": "success",
                "message": f"Channel '{channel_id}' updated",
                "channel": updated_info
            })
        else:
            return jsonify({"error": "Failed to update channel info"}), 500
        
    except Exception as e:
        logger.error(f"Error updating channel: {str(e)}")
        return jsonify({"error": str(e)}), 500

@v2_bp.route('/blueprints/<blueprint>/kins/<kin_id>/channels/<channel_id>', methods=['DELETE'])
def delete_channel_v2(blueprint, kin_id, channel_id):
    """
    V2 API endpoint to delete a channel.
    """
    try:
        # Validate blueprint and kin
        if not os.path.exists(os.path.join(blueprintS_DIR, blueprint)):
            return jsonify({"error": f"Blueprint '{blueprint}' not found"}), 404
            
        kin_path = get_kin_path(blueprint, kin_id)
        if not os.path.exists(kin_path):
            return jsonify({"error": f"Kin '{kin_id}' not found for blueprint '{blueprint}'"}), 404
        
        # Cannot delete the main channel
        if channel_id == "main":
            return jsonify({"error": "Cannot delete the main channel"}), 400
        
        # Delete the channel
        from utils.channel_utils import delete_channel
        success = delete_channel(kin_path, channel_id)
        
        if success:
            return jsonify({
                "status": "success",
                "message": f"Channel '{channel_id}' deleted"
            })
        else:
            return jsonify({"error": "Failed to delete channel"}), 500
        
    except Exception as e:
        logger.error(f"Error deleting channel: {str(e)}")
        return jsonify({"error": str(e)}), 500

@v2_bp.route('/blueprints/<blueprint>/kins/<kin_id>/website/<path:path>', methods=['GET'])
def serve_kin_website_v2(blueprint, kin_id, path=''):
    """
    V2 API endpoint to serve files from a kin's website directory.
    Maps to the original serve_kin_website function.
    """
    from app import serve_kin_website
    return serve_kin_website(blueprint, kin_id, path)

@v2_bp.route('/blueprints/<blueprint>/kins/<kin_id>/website/start', methods=['POST'])
def start_website_server_v2(blueprint, kin_id):
    """
    V2 API endpoint to start the Next.js server for a kin's website.
    """
    try:
        # Parse request data
        data = request.json or {}
        port = data.get('port', 3000)
        
        # Start the server
        from app import start_kin_website_server
        process = start_kin_website_server(blueprint, kin_id, port)
        
        if process:
            return jsonify({
                "status": "success",
                "message": f"Next.js server started for {blueprint}/{kin_id} on port {port}",
                "pid": process.pid,
                "port": port
            })
        else:
            return jsonify({"error": "Failed to start Next.js server"}), 500
            
    except Exception as e:
        logger.error(f"Error starting website server: {str(e)}")
        return jsonify({"error": str(e)}), 500

@v2_bp.route('/blueprints/<blueprint>/kins/<kin_id>/website/status', methods=['GET'])
def check_website_status_v2(blueprint, kin_id):
    """
    V2 API endpoint to check the status of a kin's website.
    """
    try:
        # Get kin path
        from services.file_service import get_kin_path
        kin_path = get_kin_path(blueprint, kin_id)
        
        # Check if kin exists
        if not os.path.exists(kin_path):
            return jsonify({"error": f"Kin '{kin_id}' not found for blueprint '{blueprint}'"}), 404
        
        # Check if website directory exists
        website_dir = os.path.join(kin_path, "website")
        if not os.path.exists(website_dir):
            return jsonify({
                "status": "not_found",
                "message": "This kin doesn't have a website"
            })
        
        # Check if .next directory exists (indicating the website has been built)
        next_dir = os.path.join(website_dir, ".next")
        if not os.path.exists(next_dir):
            return jsonify({
                "status": "not_built",
                "message": "Website exists but hasn't been built yet"
            })
        
        # Check if the website is running
        # This is a simple check - in a real implementation, you'd want to track running processes
        try:
            response = requests.get(f"http://localhost:3000", timeout=1)
            if response.status_code == 200:
                return jsonify({
                    "status": "running",
                    "message": "Website is running",
                    "url": f"http://{blueprint}-{kin_id}.kinos-engine.ai"
                })
        except:
            pass
        
        return jsonify({
            "status": "built",
            "message": "Website is built but not running",
            "url": f"http://{blueprint}-{kin_id}.kinos-engine.ai"
        })
            
    except Exception as e:
        logger.error(f"Error checking website status: {str(e)}")
        return jsonify({"error": str(e)}), 500

@v2_bp.route('/blueprints/<blueprint>/kins/<kin_id>/link-repo', methods=['POST'])
def link_repository_v2(blueprint, kin_id):
    """
    V2 API endpoint to link a kin to a GitHub repository.
    
    Request Body:
    {
        "github_url": "https://github.com/username/repo",
        "token": "optional_github_token"  // Optional
    }
    """
    try:
        # Parse request data
        data = request.json
        github_url = data.get('github_url')
        token = data.get('token')
        
        # Validate required parameters
        if not github_url:
            return jsonify({"error": "GitHub URL is required"}), 400
            
        # Validate blueprint and kin
        if not os.path.exists(os.path.join(blueprintS_DIR, blueprint)):
            return jsonify({"error": f"Blueprint '{blueprint}' not found"}), 404
            
        kin_path = get_kin_path(blueprint, kin_id)
        if not os.path.exists(kin_path):
            return jsonify({"error": f"Kin '{kin_id}' not found for blueprint '{blueprint}'"}), 404
        
        # Import the link_repository function from linkrepo.py
        from linkrepo import link_repository
        
        # Link the repository
        success = link_repository(kin_path, github_url, token)
        
        if success:
            return jsonify({
                "status": "success",
                "message": f"Kin '{kin_id}' linked to GitHub repository: {github_url}",
                "blueprint": blueprint,
                "kin_id": kin_id,
                "github_url": github_url
            })
        else:
            return jsonify({"error": "Failed to link repository"}), 500
            
    except Exception as e:
        logger.error(f"Error linking repository: {str(e)}")
        return jsonify({"error": str(e)}), 500

@v2_bp.route('/<path:undefined_route>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def catch_all_v2(undefined_route):
    """Catch-all route for undefined v2 API endpoints."""
    logger.warning(f"Undefined v2 API route accessed: {undefined_route}")
    return jsonify({
        "error": "Not Found",
        "message": f"The requested v2 endpoint '/{undefined_route}' does not exist.",
        "documentation_url": "https://api.kinos-engine.ai/v2"
    }), 404
