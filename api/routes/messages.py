from flask import Blueprint, request, jsonify
import os
import json
import datetime
import threading
import base64
import re
import requests
import subprocess
import shutil
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from config import blueprintS_DIR, logger

def extract_and_save_url_content(url, kin_path):
    """
    Extract content from a URL and save it to the sources directory.
    Returns the relative path to the saved file.
    """
    try:
        # Regular URL - proceed with normal scraping
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
            
        # Get text content
        text = soup.get_text()
        
        # Clean up text
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        # Create sources directory if it doesn't exist
        sources_dir = os.path.join(kin_path, "sources")
        os.makedirs(sources_dir, exist_ok=True)
        
        # Create filename from URL
        parsed_url = urlparse(url)
        filename = f"{parsed_url.netloc}{parsed_url.path}".replace('/', '-')
        if not filename.endswith('.txt'):
            filename += '.txt'
            
        # Ensure filename isn't too long
        if len(filename) > 200:
            filename = filename[:197] + '...'
            
        filepath = os.path.join(sources_dir, filename)
        
        # Save content
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"Source URL: {url}\nExtracted on: {datetime.datetime.now().isoformat()}\n\n")
            f.write(text)
            
        # Initialize git repo if it doesn't exist
        git_dir = os.path.join(kin_path, ".git")
        if not os.path.exists(git_dir):
            try:
                subprocess.run(
                    ["git", "init"],
                    cwd=kin_path,
                    check=True,
                    capture_output=True,
                    text=True
                )
                logger.info(f"Initialized git repository in {kin_path}")
                
                # Configure git user if initializing new repo
                subprocess.run(
                    ["git", "config", "user.name", "KinOS"],
                    cwd=kin_path,
                    check=True,
                    capture_output=True,
                    text=True
                )
                subprocess.run(
                    ["git", "config", "user.email", "kinos@example.com"],
                    cwd=kin_path,
                    check=True,
                    capture_output=True,
                    text=True
                )
                logger.info("Configured git user settings")
            except Exception as e:
                logger.warning(f"Error initializing git repository: {str(e)}")

        # Add and commit the new files
        try:
            # Add all files
            subprocess.run(
                ["git", "add", "."],
                cwd=kin_path,
                check=True,
                capture_output=True,
                text=True
            )
            
            # Commit changes
            subprocess.run(
                ["git", "commit", "-m", "Added source content from URL"],
                cwd=kin_path,
                check=True,
                capture_output=True,
                text=True
            )
            logger.info("Added and committed source files to git")
        except Exception as e:
            logger.warning(f"Error adding/committing to git: {str(e)}")

        # Return relative path from kin directory
        return os.path.join("sources", filename)
            
    except Exception as e:
        logger.error(f"Error extracting content from URL {url}: {str(e)}")
        return None
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
        
        # Log the blueprint being accessed
        logger.info(f"Attempting to access blueprint: {blueprint}")
        logger.info(f"blueprintS_DIR path: {blueprintS_DIR}")
        
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
            
        # Get kin path before processing addContext
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
        
        # Initialize saved_images list to track saved image paths
        saved_images = []
        
        # Check if blueprint exists with detailed logging
        blueprint_path = os.path.join(blueprintS_DIR, blueprint)
        logger.info(f"Full blueprint path: {blueprint_path}")
        logger.info(f"Directory exists: {os.path.exists(blueprint_path)}")

        if os.path.exists(blueprint_path):
            logger.info(f"Blueprint directory contents: {os.listdir(blueprint_path)}")

        if not os.path.exists(blueprint_path):
            logger.error(f"Blueprint '{blueprint}' not found at path: {blueprint_path}")
            logger.error(f"Available blueprints: {os.listdir(blueprintS_DIR)}")
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
        data = request.json or {}  # Use empty dict if None
        
        # Support both formats: new format with 'message' and original format with 'content'
        message_content = data.get('message', data.get('content', ''))
        
        # Log the message content to verify it's being passed correctly
        logger.info(f"Analysis request with message: {message_content[:100]}...")
        
        # Validate required parameters
        if not message_content:
            # Check if it's in the query parameters (for GET requests)
            message_content = request.args.get('message', '')
            if not message_content:
                return jsonify({"error": "Message is required"}), 400
        
        # Validate required parameters
        if not message_content:
            return jsonify({"error": "Message is required"}), 400
        
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

        # Support both formats: new format with 'screenshot' and original format with 'images'
        images = data.get('images', [])
        if data.get('screenshot'):  # Add null check here
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
        selected_files, selected_mode = build_context(
            blueprint, 
            kin_id, 
            message_content, 
            attachments, 
            kin_path, 
            model, 
            "analysis",  # Explicitly set mode to "analysis"
            addSystem, 
            history_length=2,
            min_files=min_files,
            max_files=max_files
        )
        
        # Log the selected files and mode
        logger.info(f"Selected files for analysis context: {selected_files}")
        logger.info(f"Analysis request with message: {message_content[:100]}...")
        
        # Call Claude with the selected context
        try:
            # Pass is_new_message=False to use existing messages from messages.json
            claude_response = call_claude_with_context(
                selected_files, 
                kin_path, 
                message_content,  # Make sure this is the actual user message
                images, 
                model,
                history_length,
                is_new_message=False,  # Don't treat as a new message
                addSystem=addSystem,
                mode="analysis"  # Explicitly set mode to "analysis"
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
