from flask import Blueprint, request, jsonify
import os
import json
import datetime
import threading
import base64
from config import blueprintS_DIR, logger
from services.file_service import get_kin_path
from services.claude_service import call_claude_with_context, build_context
from services.aider_service import call_aider_with_context

messages_bp = Blueprint('messages', __name__)

@messages_bp.route('/kins/<blueprint>/<kin_id>/messages', methods=['GET'])
def get_messages(blueprint, kin_id):
    """
    Endpoint to get messages for a kin.
    Optionally filters by timestamp.
    """
    try:
        since = request.args.get('since')
        
        # Validate blueprint and kin
        if not os.path.exists(os.path.join(blueprintS_DIR, blueprint)):
            return jsonify({"error": f"blueprint '{blueprint}' not found"}), 404
            
        kin_path = get_kin_path(blueprint, kin_id)
        if not os.path.exists(kin_path):
            return jsonify({"error": f"kin '{kin_id}' not found for blueprint '{blueprint}'"}), 404
        
        # Load messages
        messages_file = os.path.join(kin_path, "messages.json")
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
        
        return jsonify({"messages": messages})
        
    except Exception as e:
        logger.error(f"Error getting messages: {str(e)}")
        return jsonify({"error": str(e)}), 500

@messages_bp.route('/kins/<blueprint>/<kin_id>/messages', methods=['POST'])
def send_message(blueprint, kin_id):
    """
    Endpoint to send a message to a kin.
    Accepts both original format and new format with username, character, etc.
    If the kin doesn't exist, it will be created from the template.
    """
    try:
        # Parse request data
        data = request.json
        
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
        
        # Initialize saved_images list to track saved image paths
        saved_images = []
        
        # Validate blueprint
        if not os.path.exists(os.path.join(blueprintS_DIR, blueprint)):
            return jsonify({"error": f"blueprint '{blueprint}' not found"}), 404
            
        kin_path = get_kin_path(blueprint, kin_id)
        
        # Track if we need to create a new kin
        kin_created = False
        
        # First, check if we need to create a new kin
        if not os.path.exists(kin_path) and kin_id != "template":
            logger.info(f"kin '{kin_id}' not found for blueprint '{blueprint}', creating it from template")
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
                logger.info(f"kin directory contents: {dir_contents}")
            else:
                logger.error(f"kin directory does not exist after creation: {kin_path}")
        
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
        
        # Now that we've ensured the kin exists, proceed with message handling
        messages_file = os.path.join(kin_path, "messages.json")
        
        # Load existing messages
        if os.path.exists(messages_file):
            with open(messages_file, 'r') as f:
                messages = json.load(f)
        else:
            # If messages.json doesn't exist (which shouldn't happen now), create it
            messages = []
            with open(messages_file, 'w') as f:
                json.dump(messages, f)
        
        # Prepare user message object (but don't add to messages.json yet)
        user_message = {
            "role": "user",
            "content": message_content,
            "timestamp": datetime.datetime.now().isoformat()
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
        
        # Build context (select relevant files)
        selected_files, selected_mode = build_context(blueprint, kin_id, message_content, attachments, kin_path, model, mode, addSystem, history_length=2)
        
        # Add saved image files to selected files for context
        for img_path in saved_images:
            if img_path not in selected_files:
                selected_files.append(img_path)
        
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
                mode=selected_mode  # Pass the selected mode
            )
            
            # Create assistant message object
            assistant_message = {
                "role": "assistant",
                "content": claude_response,
                "timestamp": datetime.datetime.now().isoformat()
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
                "response": claude_response
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

@messages_bp.route('/kins/<blueprint>/<kin_id>/analysis', methods=['POST'])
def analyze_message(blueprint, kin_id):
    """
    Endpoint to analyze a message with Claude without saving it or triggering context updates.
    Similar to the send_message endpoint but doesn't save messages or call Aider.
    """
    try:
        # Parse request data
        data = request.json
        
        # Support both formats: new format with 'message' and original format with 'content'
        message_content = data.get('message', data.get('content', ''))
        
        # Support both formats: new format with 'screenshot' and original format with 'images'
        images = data.get('images', [])
        if 'screenshot' in data and data['screenshot']:
            # Add screenshot to images array if it's not empty
            images.append(data['screenshot'])
        
        # Get optional fields from new format
        model = data.get('model', '')  # Optional model parameter
        history_length = data.get('history_length', 25)  # Default to 25 messages
        addSystem = data.get('addSystem', None)  # Optional additional system instructions
        
        # Original format attachments
        attachments = data.get('attachments', [])
        
        # Validate blueprint
        if not os.path.exists(os.path.join(blueprintS_DIR, blueprint)):
            return jsonify({"error": f"blueprint '{blueprint}' not found"}), 404
            
        kin_path = get_kin_path(blueprint, kin_id)
        
        # Check if kin exists
        if not os.path.exists(kin_path):
            return jsonify({"error": f"kin '{kin_id}' not found for blueprint '{blueprint}'"}), 404
        
        # Build context (select relevant files)
        selected_files, selected_mode = build_context(blueprint, kin_id, message_content, attachments, kin_path, model, None, addSystem)
        
        # Log the selected files and mode
        logger.info(f"Selected files for analysis context: {selected_files}")
        if selected_mode:
            logger.info(f"Selected mode: {selected_mode}")
        
        # Call Claude with the selected context
        try:
            # Pass is_new_message=False to use existing messages from messages.json
            claude_response = call_claude_with_context(
                selected_files, 
                kin_path, 
                message_content, 
                images, 
                model,
                history_length,
                is_new_message=False,  # Don't treat as a new message
                addSystem=addSystem,
                mode=selected_mode  # Pass the selected mode
            )
            
            # Return the Claude response directly in the API response
            response_data = {
                "status": "completed",
                "response": claude_response
            }
            
            # Add selected_mode if one was determined
            if selected_mode:
                response_data["mode"] = selected_mode
                
            return jsonify(response_data)
            
        except Exception as e:
            logger.error(f"Error processing analysis: {str(e)}")
            return jsonify({"error": f"Error processing analysis: {str(e)}"}), 500
        
    except Exception as e:
        logger.error(f"Error processing analysis request: {str(e)}")
        return jsonify({"error": str(e)}), 500

@messages_bp.route('/kins/<blueprint>/<kin_id>/aider_logs', methods=['GET'])
def get_aider_logs(blueprint, kin_id):
    """
    Endpoint to get Aider logs for a kin.
    """
    try:
        # Validate blueprint and kin
        if not os.path.exists(os.path.join(blueprintS_DIR, blueprint)):
            return jsonify({"error": f"blueprint '{blueprint}' not found"}), 404
            
        kin_path = get_kin_path(blueprint, kin_id)
        if not os.path.exists(kin_path):
            return jsonify({"error": f"kin '{kin_id}' not found for blueprint '{blueprint}'"}), 404
        
        # Get Aider logs
        aider_logs_file = os.path.join(kin_path, "aider_logs.txt")
        if not os.path.exists(aider_logs_file):
            return jsonify({"logs": "No Aider logs found for this kin."}), 200
        
        # Read logs
        with open(aider_logs_file, 'r', encoding='utf-8') as f:
            logs = f.read()
        
        return jsonify({"logs": logs})
        
    except Exception as e:
        logger.error(f"Error getting Aider logs: {str(e)}")
        return jsonify({"error": str(e)}), 500
