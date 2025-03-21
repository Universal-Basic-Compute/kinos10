import os
import json
import logging
import anthropic
import datetime
from config import MODEL, logger

# Initialize Anthropic client
try:
    # Set API key from environment variable
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY environment variable not set")
    
    # Create a minimal client
    client = anthropic.Anthropic(api_key=api_key)
    logger.info("Anthropic client initialized successfully")
except Exception as e:
    logger.error(f"Error initializing Anthropic client: {str(e)}")
    raise RuntimeError(f"Could not initialize Anthropic client: {str(e)}")

def call_claude_with_context(selected_files, project_path, message_content, images=None, model=None, history_length=25, is_new_message=True):
    """
    Call Claude API directly with the selected context files, user message, and optional images.
    Also includes conversation history from messages.json as actual messages.
    
    Args:
        selected_files: List of files to include in the context
        project_path: Path to the project directory
        message_content: User message content
        images: List of base64-encoded images
        model: Optional model to use (defaults to MODEL from config)
        history_length: Number of recent messages to include in context (default: 25)
        is_new_message: Whether this is a new message not yet in messages.json (default: True)
    
    Returns:
        Claude response as a string
    """
    # Load content of selected files
    file_contents = []
    for file in selected_files:
        file_path = os.path.join(project_path, file)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                file_contents.append(f"# File: {file}\n{content}")
            except Exception as e:
                logger.error(f"Error reading file {file_path}: {str(e)}")
    
    # Combine file contents into a single context string
    context = "\n\n".join(file_contents)
    
    try:
        # Initialize messages array
        messages = []
        
        # Load conversation history from messages.json and add as actual messages
        messages_file = os.path.join(project_path, "messages.json")
        if os.path.exists(messages_file):
            try:
                with open(messages_file, 'r', encoding='utf-8') as f:
                    message_data = json.load(f)
                    
                    # Limit to specified number of recent messages
                    recent_messages = message_data[-history_length:] if len(message_data) > history_length else message_data
                    
                    # Add each message as a proper message object
                    for msg in recent_messages:
                        role = msg.get('role', '')
                        content = msg.get('content', '')
                        
                        # Only add if it has valid role and content
                        if role in ['user', 'assistant'] and content:
                            # Skip if this is the same as the current message we're about to add
                            if is_new_message and role == 'user' and content == message_content:
                                logger.info("Skipping duplicate message from history")
                                continue
                            
                            messages.append({
                                "role": role,
                                "content": content
                            })
            except Exception as e:
                logger.error(f"Error reading messages.json: {str(e)}")
        
        # If there are images, create a separate message with just the images
        if images and len(images) > 0:
            # Create an image-only message that will appear before the text message
            image_message_parts = []
            
            # Add a minimal text part to the image message
            image_message_parts.append({
                "type": "text",
                "text": "Here are some images for reference:"
            })
            
            # Add image parts
            for img_base64 in images:
                try:
                    # Clean up the base64 data
                    if ',' in img_base64:
                        # Extract the base64 part after the comma
                        img_base64 = img_base64.split(',', 1)[1]
                    
                    # Create image content part
                    image_message_parts.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",  # Default to JPEG
                            "data": img_base64
                        }
                    })
                    logger.info(f"Added image to previous message, data length: {len(img_base64)}")
                except Exception as e:
                    logger.error(f"Error processing image: {str(e)}")
            
            # Add the image message as a user message
            messages.append({
                "role": "user",
                "content": image_message_parts
            })
        
        # Add the current message as the final message only if it's a new message
        # This prevents duplication when loading from messages.json in other contexts
        if is_new_message:
            messages.append({
                "role": "user",
                "content": message_content
            })
        
        # Call Claude API with system message as a separate parameter
        # Use provided model if specified, otherwise use default from config
        model_to_use = model if model else MODEL
        logger.info(f"Calling Claude API with {len(messages)} messages" + (" and images in previous message" if images else "") + f", using model: {model_to_use}")
        response = client.messages.create(
            model=model_to_use,
            max_tokens=4000,
            system=context,  # Pass context as system parameter
            messages=messages
        )
        
        # Extract the response text
        claude_response = response.content[0].text
        logger.info(f"Received response from Claude: {claude_response[:100]}...")
        return claude_response
    except Exception as e:
        logger.error(f"Error calling Claude API: {str(e)}")
        raise RuntimeError(f"Claude API call failed: {str(e)}")

def build_context(customer, project_id, message, attachments=None, project_path=None, model=None):
    """
    Build context by determining which files should be included.
    Uses Claude to select relevant files based on the message.
    
    Args:
        customer: Customer name
        project_id: Project ID
        message: User message content
        attachments: Optional list of attachments
        project_path: Optional project path (if already known)
        model: Optional model to use (defaults to MODEL from config)
    """
    # Move import inside function to avoid circular imports
    from services.file_service import get_project_path
    
    if not project_path:
        project_path = get_project_path(customer, project_id)
    
    # Check if persona.txt exists, if so use it instead of kinos.txt and system.txt
    persona_file = os.path.join(project_path, "persona.txt")
    
    # Special handling for duogaming - include character persona adaptation
    if customer == "duogaming":
        core_files = ["persona.txt", "map.json", "adaptations/character_persona.txt"]
        logger.info("Using persona.txt and character_persona.txt for DuoGaming context")
    elif os.path.exists(persona_file):
        # Use persona.txt instead of kinos.txt and system.txt
        core_files = ["persona.txt", "map.json"]
        logger.info("Using persona.txt for context")
    else:
        # Use traditional core files
        core_files = ["kinos.txt", "system.txt", "map.json"]
        logger.info("Using traditional core files for context")
    
    # Get all available files in the project
    available_files = []
    for root, dirs, files in os.walk(project_path):
        for file in files:
            rel_path = os.path.relpath(os.path.join(root, file), project_path)
            if rel_path not in core_files:  # Skip core files as we'll add them separately
                available_files.append(rel_path)
    
    # If there are no additional files, just return core files
    if not available_files:
        logger.info(f"No additional files found for {customer}/{project_id}, using core files only")
        return core_files
    
    # Prepare the prompt for Claude to select relevant files
    selection_prompt = f"""
    You are the Context Builder component of KinOS. Your task is to select the most relevant files to include in the context window based on the user's message.
    
    User message: {message}
    
    Available files (excluding core files that are always included):
    {json.dumps(available_files, indent=2)}
    
    Please select the files that would be most relevant to include in the context to help generate a good response to this message.
    Return your answer as a JSON array of file paths, sorted by relevance. Include only files that are directly relevant to the message.
    """
    
    try:
        # Call Claude to select relevant files
        model_to_use = model if model else MODEL
        response = client.messages.create(
            model=model_to_use,
            max_tokens=1000,
            messages=[
                {"role": "user", "content": selection_prompt}
            ]
        )
        
        # Extract the JSON array from Claude's response
        response_text = response.content[0].text
        # Find JSON array in the response
        import re
        json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
        
        if json_match:
            selected_files = json.loads(json_match.group(0))
            logger.info(f"Claude selected files: {selected_files}")
        else:
            logger.warning("Could not extract JSON from Claude's response, using empty list")
            selected_files = []
            
    except Exception as e:
        logger.error(f"Error calling Claude for file selection: {str(e)}")
        selected_files = []
    
    # Combine core files with selected files
    all_files = core_files + selected_files
    
    return all_files
