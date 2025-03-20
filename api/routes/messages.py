from flask import Blueprint, request, jsonify
import os
import json
import datetime
import threading
import base64
from config import CUSTOMERS_DIR, logger
from services.file_service import get_project_path
from services.claude_service import call_claude_with_context, build_context
from services.aider_service import call_aider_with_context

messages_bp = Blueprint('messages', __name__)

@messages_bp.route('/projects/<customer>/<project_id>/messages', methods=['GET'])
def get_messages(customer, project_id):
    """
    Endpoint to get messages for a project.
    Optionally filters by timestamp.
    """
    try:
        since = request.args.get('since')
        
        # Validate customer and project
        if not os.path.exists(os.path.join(CUSTOMERS_DIR, customer)):
            return jsonify({"error": f"Customer '{customer}' not found"}), 404
            
        project_path = get_project_path(customer, project_id)
        if not os.path.exists(project_path):
            return jsonify({"error": f"Project '{project_id}' not found for customer '{customer}'"}), 404
        
        # Load messages
        messages_file = os.path.join(project_path, "messages.json")
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

@messages_bp.route('/projects/<customer>/<project_id>/messages', methods=['POST'])
def send_message(customer, project_id):
    """
    Endpoint to send a message to a project.
    Accepts both original format and new format with username, character, etc.
    If the project doesn't exist, it will be created from the template.
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
        
        # Original format attachments
        attachments = data.get('attachments', [])
        
        # Initialize saved_images list to track saved image paths
        saved_images = []
        
        # Validate customer
        if not os.path.exists(os.path.join(CUSTOMERS_DIR, customer)):
            return jsonify({"error": f"Customer '{customer}' not found"}), 404
            
        project_path = get_project_path(customer, project_id)
        
        # Track if we need to create a new project
        project_created = False
        
        # First, check if we need to create a new project
        if not os.path.exists(project_path) and project_id != "template":
            logger.info(f"Project '{project_id}' not found for customer '{customer}', creating it from template")
            project_created = True
            
            # Create projects directory if it doesn't exist
            projects_dir = os.path.join(CUSTOMERS_DIR, customer, "projects")
            os.makedirs(projects_dir, exist_ok=True)
            logger.info(f"Created or verified projects directory: {projects_dir}")
            
            # Create project directory
            os.makedirs(project_path, exist_ok=True)
            logger.info(f"Created project directory: {project_path}")
            
            # Copy template to project directory
            template_path = os.path.join(CUSTOMERS_DIR, customer, "template")
            logger.info(f"Looking for template at: {template_path}")
            
            if not os.path.exists(template_path):
                # Check if we need to initialize the customer template first
                logger.warning(f"Template not found for customer '{customer}', attempting to initialize")
                
                # Try to initialize the customer template
                project_templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "customers")
                customer_template_dir = os.path.join(project_templates_dir, customer, "template")
                
                if os.path.exists(customer_template_dir):
                    logger.info(f"Found template in project directory, copying to app data")
                    # Create customer directory if needed
                    customer_dir = os.path.join(CUSTOMERS_DIR, customer)
                    os.makedirs(customer_dir, exist_ok=True)
                    
                    # Copy template from project directory to app data
                    import shutil
                    shutil.copytree(customer_template_dir, template_path)
                    logger.info(f"Initialized template for customer '{customer}'")
                else:
                    logger.error(f"No template found for customer '{customer}' in project directory")
                    return jsonify({"error": f"Template not found for customer '{customer}'"}), 404
            
            # Verify template exists after potential initialization
            if not os.path.exists(template_path):
                return jsonify({"error": f"Template not found for customer '{customer}'"}), 404
            
            # List template contents for debugging
            template_contents = os.listdir(template_path)
            logger.info(f"Template contents: {template_contents}")
            
            # Use a more robust copy method
            import shutil
            for item in os.listdir(template_path):
                s = os.path.join(template_path, item)
                d = os.path.join(project_path, item)
                try:
                    if os.path.isdir(s):
                        shutil.copytree(s, d)
                    else:
                        shutil.copy2(s, d)
                    logger.info(f"Copied {s} to {d}")
                except Exception as copy_error:
                    logger.error(f"Error copying {s} to {d}: {str(copy_error)}")
            
            # Create messages.json file
            messages_file = os.path.join(project_path, "messages.json")
            with open(messages_file, 'w') as f:
                json.dump([], f)
            logger.info(f"Created messages.json file")
            
            # Create thoughts.txt file
            thoughts_file = os.path.join(project_path, "thoughts.txt")
            with open(thoughts_file, 'w') as f:
                f.write(f"# Thoughts for project: {project_id}\nCreated: {datetime.datetime.now().isoformat()}\n\n")
            logger.info(f"Created thoughts.txt file")
            
            # Create images directory
            images_dir = os.path.join(project_path, "images")
            os.makedirs(images_dir, exist_ok=True)
            logger.info(f"Created images directory: {images_dir}")
            
            logger.info(f"Successfully created project '{project_id}' for customer '{customer}'")
            
            # Verify project directory exists and check contents
            logger.info(f"Verifying project directory exists: {project_path}")
            if os.path.exists(project_path):
                dir_contents = os.listdir(project_path)
                logger.info(f"Project directory contents: {dir_contents}")
            else:
                logger.error(f"Project directory does not exist after creation: {project_path}")
        
        # Save images to project directory if any
        if images and len(images) > 0:
            # Create images directory if it doesn't exist
            images_dir = os.path.join(project_path, "images")
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
        
        # Now that we've ensured the project exists, proceed with message handling
        messages_file = os.path.join(project_path, "messages.json")
        
        # Load existing messages
        if os.path.exists(messages_file):
            with open(messages_file, 'r') as f:
                messages = json.load(f)
        else:
            # If messages.json doesn't exist (which shouldn't happen now), create it
            messages = []
            with open(messages_file, 'w') as f:
                json.dump(messages, f)
        
        # Add user message
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
            
        messages.append(user_message)
        
        # Save updated messages with user message immediately
        with open(messages_file, 'w') as f:
            json.dump(messages, f, indent=2)
        
        # Build context (select relevant files)
        selected_files = build_context(customer, project_id, message_content, attachments, project_path)
        
        # Add saved image files to selected files for context
        for img_path in saved_images:
            if img_path not in selected_files:
                selected_files.append(img_path)
        
        # Log the selected files
        logger.info(f"Selected files for context: {selected_files}")
        
        # Call Claude and Aider with the selected context
        try:
            # Call Claude directly for a response
            claude_response = call_claude_with_context(selected_files, project_path, message_content, images)
            
            # Call Aider in parallel for file updates (don't wait for response)
            def run_aider():
                try:
                    aider_response = call_aider_with_context(project_path, selected_files, message_content)
                    logger.info("Aider processing completed")
                    # Log the complete Aider response
                    logger.info(f"Aider response: {aider_response}")
                except Exception as e:
                    logger.error(f"Error in Aider thread: {str(e)}")
            
            # Start Aider in a separate thread
            aider_thread = threading.Thread(target=run_aider)
            aider_thread.start()
            
            # Add assistant response from Claude
            assistant_message = {
                "role": "assistant",
                "content": claude_response,
                "timestamp": datetime.datetime.now().isoformat()
            }
            
            # Add character if it was provided
            if character:
                assistant_message["character"] = character
                
            messages.append(assistant_message)
            
            # Save updated messages with assistant response
            with open(messages_file, 'w') as f:
                json.dump(messages, f, indent=2)
            
            # Return the Claude response directly in the API response
            response_data = {
                "status": "completed",
                "message_id": str(len(messages) - 1),
                "response": claude_response
            }
            
            # Add project_created flag if a new project was created
            if project_created:
                response_data["project_created"] = True
                
            return jsonify(response_data)
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return jsonify({"error": f"Error processing message: {str(e)}"}), 500
        
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        return jsonify({"error": str(e)}), 500

@messages_bp.route('/projects/<customer>/<project_id>/aider_logs', methods=['GET'])
def get_aider_logs(customer, project_id):
    """
    Endpoint to get Aider logs for a project.
    """
    try:
        # Validate customer and project
        if not os.path.exists(os.path.join(CUSTOMERS_DIR, customer)):
            return jsonify({"error": f"Customer '{customer}' not found"}), 404
            
        project_path = get_project_path(customer, project_id)
        if not os.path.exists(project_path):
            return jsonify({"error": f"Project '{project_id}' not found for customer '{customer}'"}), 404
        
        # Get Aider logs
        aider_logs_file = os.path.join(project_path, "aider_logs.txt")
        if not os.path.exists(aider_logs_file):
            return jsonify({"logs": "No Aider logs found for this project."}), 200
        
        # Read logs
        with open(aider_logs_file, 'r', encoding='utf-8') as f:
            logs = f.read()
        
        return jsonify({"logs": logs})
        
    except Exception as e:
        logger.error(f"Error getting Aider logs: {str(e)}")
        return jsonify({"error": str(e)}), 500
