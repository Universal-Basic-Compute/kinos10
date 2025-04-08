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

def call_claude_with_context(selected_files, kin_path, message_content, images=None, model=None, history_length=25, is_new_message=True, addSystem=None, mode=None):
    """
    Call Claude API directly with the selected context files, user message, and optional images.
    Also includes conversation history from messages.json as actual messages.
    
    Args:
        selected_files: List of files to include in the context
        kin_path: Path to the kin directory
        message_content: User message content
        images: List of base64-encoded images
        model: Optional model to use (defaults to MODEL from config)
        history_length: Number of recent messages to include in context (default: 25)
        is_new_message: Whether this is a new message not yet in messages.json (default: True)
        addSystem: Optional additional text to append to the system prompt
        mode: Optional mode to use for this interaction
    
    Returns:
        Claude response as a string
    """
    # Create a list to track temporary files that need to be deleted
    temp_files = []
    
    try:
        # Load content of selected files
        file_contents = []
        for file in selected_files:
            file_path = os.path.join(kin_path, file)
            if os.path.exists(file_path) and os.path.isfile(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    file_contents.append(f"# File: {file}\n{content}")
                except Exception as e:
                    logger.error(f"Error reading file {file_path}: {str(e)}")
        
        # If a specific mode is provided, add the corresponding mode file to the context
        if mode:
            mode_file_path = os.path.join(kin_path, f"modes/{mode}.txt")
            if os.path.exists(mode_file_path):
                try:
                    with open(mode_file_path, 'r', encoding='utf-8') as f:
                        mode_content = f.read()
                    file_contents.append(f"# Active Mode: {mode}\n{mode_content}")
                    logger.info(f"Added mode file for {mode} to context")
                except Exception as e:
                    logger.error(f"Error reading mode file {mode_file_path}: {str(e)}")
        
        # Check if we need to add dynamic analysis mode content
        if 'analysis' in message_content.lower():
            # Create dynamic analysis mode content
            analysis_content = """# Analysis Mode: Informative Responses Without Memorization

In this mode, you provide information and analysis without memorizing the content of the exchange. This mode is designed for:

1. Answering administrative or debugging questions
2. Providing explanations about your internal functioning
3. Assisting with moderation and supervision
4. Allowing exploratory interactions without impact on your long-term memory

## Specific Guidelines

When operating in this mode:

- Respond with precision and honesty to questions asked
- Explain your reasoning and internal processes if requested
- Provide complete information about your configuration and capabilities
- Do not initiate the creation or modification of memory files
- Do not consider this conversation as something that should influence your future interactions

## Practical Applications

This mode is particularly useful for:
- System administrators checking your configuration
- Moderators evaluating your behavior
- Users wanting to understand your capabilities without modifying your behavior
- Testing and debugging your functioning

Your goal is to provide useful and accurate information while maintaining a clear separation between this interaction and your long-term memory.
"""
            # Add the analysis content to file_contents
            file_contents.append(f"# File: analysis.txt\n{analysis_content}")
            logger.info(f"Added dynamic analysis mode content")
        
        # Combine file contents into a single context string
        context = "\n\n".join(file_contents)
        
        # Append additional system text if provided
        if addSystem:
            context += f"\n\n# Additional System Instructions\n{addSystem}"
            logger.info("Added custom system instructions to context")
    
        # Initialize messages array
        messages = []
        
        # Load conversation history from messages.json and add as actual messages
        messages_file = os.path.join(kin_path, "messages.json")
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
        logger.info(f"System context length: {len(context)} characters")
        logger.info(f"First few messages: {messages[:2] if len(messages) > 0 else 'No messages'}")
        
        # Add detailed logging of all messages being sent
        try:
            logger.info(f"Messages being sent to Claude: {json.dumps([{'role': m.get('role'), 'content_type': type(m.get('content')).__name__, 'content_length': len(str(m.get('content')))} for m in messages], indent=2)}")
        except:
            logger.info("Could not serialize messages for logging")
        
        # Ensure the user message is always included
        if not any(msg.get('role') == 'user' for msg in messages):
            logger.warning("No user message found in messages array, adding one")
            messages.append({
                "role": "user",
                "content": message_content
            })
        
        try:
            # Log the full request details
            logger.info(f"Claude API request details:")
            logger.info(f"  Model: {model_to_use}")
            logger.info(f"  System context length: {len(context)} characters")
            logger.info(f"  Number of messages: {len(messages)}")
            logger.info(f"  First message: {messages[0] if messages else 'No messages'}")
            logger.info(f"  Last message: {messages[-1] if messages else 'No messages'}")
            
            # Validate messages to ensure no empty content blocks
            validated_messages = []
            for msg in messages:
                if isinstance(msg.get('content'), str):
                    # For string content, ensure it's not empty or just whitespace
                    if msg.get('content') and msg.get('content').strip():
                        validated_messages.append(msg)
                    else:
                        logger.warning(f"Skipping message with empty content: {msg}")
                elif isinstance(msg.get('content'), list):
                    # For content blocks, ensure text blocks have non-whitespace content
                    valid_content_blocks = []
                    for block in msg.get('content', []):
                        if block.get('type') == 'text':
                            if block.get('text') and block.get('text').strip():
                                valid_content_blocks.append(block)
                            else:
                                logger.warning(f"Skipping empty text block: {block}")
                        else:
                            # Keep non-text blocks (like images)
                            valid_content_blocks.append(block)
                    
                    if valid_content_blocks:
                        validated_msg = msg.copy()
                        validated_msg['content'] = valid_content_blocks
                        validated_messages.append(validated_msg)
                    else:
                        logger.warning(f"Skipping message with no valid content blocks: {msg}")
                else:
                    logger.warning(f"Skipping message with invalid content format: {msg}")

            # Replace the original messages with the validated ones
            if validated_messages:
                messages = validated_messages
                logger.info(f"Using {len(messages)} validated messages after filtering empty content")
            else:
                # If all messages were filtered out, add a default message
                logger.warning("All messages were filtered out due to empty content, adding default message")
                messages = [{"role": "user", "content": "Hello, please help me."}]
            
            response = client.messages.create(
                model=model_to_use,
                max_tokens=4000,
                system=context,  # Pass context as system parameter
                messages=messages
            )
            
            # Log the complete raw response
            logger.info(f"Claude API raw response: {response}")
            
            # Log specific parts of the response
            logger.info(f"Response ID: {response.id}")
            logger.info(f"Response model: {response.model}")
            logger.info(f"Response role: {response.role}")
            logger.info(f"Response stop_reason: {response.stop_reason}")
            logger.info(f"Response content length: {len(response.content) if response.content else 0}")
            
            # Log usage information if available
            if hasattr(response, 'usage'):
                logger.info(f"Response usage: {response.usage}")
                if hasattr(response.usage, 'input_tokens'):
                    logger.info(f"Input tokens: {response.usage.input_tokens}")
                if hasattr(response.usage, 'output_tokens'):
                    logger.info(f"Output tokens: {response.usage.output_tokens}")
            
            # Check for empty content with end_turn stop reason
            if response.stop_reason == 'end_turn' and (not response.content or len(response.content) == 0):
                logger.warning("Claude returned empty content with stop_reason='end_turn'")
                logger.warning("This usually indicates Claude had nothing to respond to or the message was unclear")
                # Try to recover by sending a simpler message
                if is_new_message:
                    logger.info("Attempting recovery by sending a simplified message")
                    recovery_response = client.messages.create(
                        model=model_to_use,
                        max_tokens=4000,
                        system="You are a helpful AI assistant.",
                        messages=[{"role": "user", "content": "Please respond to this: " + message_content}]
                    )
                    if recovery_response.content and len(recovery_response.content) > 0:
                        logger.info("Recovery successful, using simplified response")
                        response = recovery_response
            
            # Log the content structure
            if response.content:
                for i, content_item in enumerate(response.content):
                    logger.info(f"Content item {i} type: {type(content_item)}")
                    logger.info(f"Content item {i} dir: {dir(content_item)}")
                    logger.info(f"Content item {i} repr: {repr(content_item)}")
                    
                    # Try to access as dictionary
                    try:
                        if hasattr(content_item, '__dict__'):
                            logger.info(f"Content item {i} __dict__: {content_item.__dict__}")
                    except:
                        pass
            
            # Extract the response text with better error handling
            if response.content and len(response.content) > 0:
                # Check if the content has a 'text' attribute or if it's a dictionary with a 'text' key
                if hasattr(response.content[0], 'text'):
                    claude_response = response.content[0].text
                    logger.info(f"Received response from Claude: {claude_response[:100]}...")
                    return claude_response
                elif isinstance(response.content[0], dict) and 'text' in response.content[0]:
                    claude_response = response.content[0]['text']
                    logger.info(f"Extracted text from content dict: {claude_response[:100]}...")
                    return claude_response
                # Try to access text attribute through different methods
                elif hasattr(response.content[0], 'get') and callable(response.content[0].get):
                    text = response.content[0].get('text')
                    if text:
                        logger.info(f"Extracted text using get() method: {text[:100]}...")
                        return text
                else:
                    # Try to extract text from the content in a different way
                    logger.warning(f"Content object doesn't have 'text' attribute: {response.content[0]}")
                    # Try to convert to dictionary and extract text
                    try:
                        content_dict = vars(response.content[0])
                        logger.info(f"Content object attributes: {content_dict.keys()}")
                        if 'text' in content_dict:
                            claude_response = content_dict['text']
                            logger.info(f"Extracted text from content dict: {claude_response[:100]}...")
                            return claude_response
                        elif hasattr(content_dict, 'type') and content_dict.get('type') == 'text':
                            claude_response = content_dict.get('text', '')
                            logger.info(f"Extracted text from content type=text: {claude_response[:100]}...")
                            return claude_response
                        
                        # Try to access any attribute that might contain the text
                        for key, value in content_dict.items():
                            if isinstance(value, str) and len(value) > 10:
                                logger.info(f"Found potential text in attribute '{key}': {value[:100]}...")
                                return value
                    except Exception as extract_error:
                        logger.error(f"Error extracting text from content: {str(extract_error)}")
                    
                    # Try to stringify the content object itself
                    try:
                        content_str = str(response.content[0])
                        if len(content_str) > 10 and content_str != str(type(response.content[0])):
                            logger.info(f"Using string representation of content: {content_str[:100]}...")
                            return content_str
                    except Exception as str_error:
                        logger.error(f"Error converting content to string: {str(str_error)}")
                    
                    # If we can't extract text, return a generic response
                    logger.error(f"Could not extract text from Claude response: {response.content}")
                    return "I apologize, but I couldn't generate a proper response. Please try again."
            else:
                logger.error(f"Claude returned an empty response: {response}")
                
                # Check if there were output tokens despite empty content
                if hasattr(response, 'usage') and response.usage and hasattr(response.usage, 'output_tokens') and response.usage.output_tokens > 0:
                    logger.warning(f"Claude returned {response.usage.output_tokens} output tokens but empty content array")
                    
                    # For image generation, use a default artistic prompt
                    return "A beautiful, detailed illustration in a professional style with vibrant colors and balanced composition."
                else:
                    # Check if this is an end_turn with empty content
                    if hasattr(response, 'stop_reason') and response.stop_reason == 'end_turn':
                        logger.warning("Claude returned stop_reason='end_turn' with empty content")
                        return "I understand your message, but I'm not sure what specific information you're looking for. Could you please provide more details or clarify your question?"
                    else:
                        # Return a more specific error message
                        return "I apologize, but I couldn't generate a response due to an empty content array. Please try again."
        except Exception as e:
            logger.error(f"Error calling Claude API: {str(e)}")
            # Include the exception details in the returned message for debugging
            return f"I apologize, but I encountered an error: {str(e)}. Please try again."
    except Exception as e:
        logger.error(f"Error calling Claude API: {str(e)}")
        raise RuntimeError(f"Claude API call failed: {str(e)}")
    finally:
        # Clean up any temporary files
        for temp_file in temp_files:
            try:
                os.unlink(temp_file)
                logger.info(f"Deleted temporary file: {temp_file}")
            except Exception as e:
                logger.warning(f"Could not delete temporary file {temp_file}: {str(e)}")

def build_context(blueprint, kin_id, message, attachments=None, kin_path=None, model=None, mode=None, addSystem=None, history_length=2, min_files=5, max_files=15):
    """
    Build context by determining which files should be included.
    Uses Claude to select relevant files based on the message, map.json, and recent conversation history.
    
    Args:
        blueprint: blueprint name
        kin_id: kin ID
        message: User message content
        attachments: Optional list of attachments to always include in context
        kin_path: Optional kin path (if already known)
        model: Optional model to use (ignored - always uses claude-3-5-haiku-latest)
        mode: Optional mode parameter
        addSystem: Optional additional system instructions
        history_length: Number of recent messages to include for context (default: 2)
        min_files: Minimum number of files to include in context (default: 5)
        max_files: Maximum number of files to include in context (default: 15)
        
    Returns:
        Tuple of (selected_files, selected_mode) where selected_mode may be None
    """
    # Import modules needed within this function
    import re
    
    # Debug print to help identify the issue
    print("Starting build_context function")
        
    # Move import inside function to avoid circular imports
    from services.file_service import get_kin_path
        
    # Import json here to ensure it's available
    import json
        
    if not kin_path:
        kin_path = get_kin_path(blueprint, kin_id)
    
    # Check if persona.txt exists, if so use it instead of kinos.txt and system.txt
    persona_file = os.path.join(kin_path, "persona.txt")
    
    # Special handling for duogaming - include character persona adaptation
    if blueprint == "duogaming":
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
    
    # Initialize list of attachment files if provided
    attachment_files = []
    if attachments and isinstance(attachments, list):
        for attachment in attachments:
            # Check if attachment is a string (file path)
            if isinstance(attachment, str):
                attachment_files.append(attachment)
            # If attachment is a dict with a 'path' key
            elif isinstance(attachment, dict) and 'path' in attachment:
                attachment_files.append(attachment['path'])
        
        if attachment_files:
            logger.info(f"Including {len(attachment_files)} attachments in context: {attachment_files}")
    
    # Get all available files in the kin
    available_files = []
    for root, dirs, files in os.walk(kin_path):
        for file in files:
            rel_path = os.path.relpath(os.path.join(root, file), kin_path)
            if rel_path not in core_files and rel_path not in attachment_files:  # Skip core files and attachments
                available_files.append(rel_path)
    
    # If there are no additional files, just return core files plus attachments
    if not available_files:
        logger.info(f"No additional files found for {blueprint}/{kin_id}, using core files and attachments only")
        return core_files + attachment_files
    
    # Load map.json content to include in system prompt
    map_content = ""
    map_file_path = os.path.join(kin_path, "map.json")
    if os.path.exists(map_file_path):
        try:
            with open(map_file_path, 'r', encoding='utf-8') as f:
                map_content = f.read()
            logger.info("Successfully loaded map.json for context builder")
        except Exception as e:
            logger.error(f"Error reading map.json: {str(e)}")
    
    # Load modes.txt content if it exists
    modes_content = ""
    modes_file_path = os.path.join(kin_path, "modes.txt")
    if os.path.exists(modes_file_path):
        try:
            with open(modes_file_path, 'r', encoding='utf-8') as f:
                modes_content = f.read()
            logger.info("Successfully loaded modes.txt for context builder")
        except Exception as e:
            logger.error(f"Error reading modes.txt: {str(e)}")
    
    # If modes.txt doesn't exist but there are mode files, try to generate it
    if not modes_content and os.path.exists(os.path.join(kin_path, "modes")):
        try:
            # Import the generate_modes_txt function
            from generate_modes_txt import generate_modes_txt
            
            # Get the blueprint name from the kin_path
            parts = os.path.normpath(kin_path).split(os.sep)
            # Find the index of "blueprints" in the path
            try:
                blueprints_index = parts.index("blueprints")
                if len(parts) > blueprints_index + 1:
                    blueprint = parts[blueprints_index + 1]
                    # Check if this is a template
                    if parts[blueprints_index + 2] == "template":
                        # Generate modes.txt for this template
                        logger.info(f"Attempting to generate modes.txt for {blueprint}")
                        generate_modes_txt(blueprint, kin_path, dry_run=False)
                        
                        # Try to load the generated file
                        if os.path.exists(modes_file_path):
                            with open(modes_file_path, 'r', encoding='utf-8') as f:
                                modes_content = f.read()
                            logger.info("Successfully generated and loaded modes.txt for context builder")
            except (ValueError, IndexError):
                logger.warning("Could not determine blueprint from path for modes.txt generation")
        except Exception as e:
            logger.error(f"Error generating modes.txt: {str(e)}")
    
    # Add mode information to the prompt if provided
    mode_info = f"\nMode: {mode}" if mode else ""
    
    # If mode is 'analysis', we'll handle it dynamically in call_claude_with_context
    if mode == 'analysis':
        logger.info("Analysis mode detected - will add dynamic analysis content")
    
    # Load recent message history
    recent_messages = []
    messages_file = os.path.join(kin_path, "messages.json")
    if os.path.exists(messages_file):
        try:
            with open(messages_file, 'r', encoding='utf-8') as f:
                messages = json.load(f)
                if messages:
                    recent_messages = messages[-history_length:] if len(messages) >= history_length else messages
        except Exception as e:
            logger.error(f"Error reading messages.json: {str(e)}")
    
    # Format the last messages for inclusion in the prompt
    last_messages_text = ""
    if recent_messages:
        last_messages_text = "\n\nRecent conversation history:\n"
        for msg in recent_messages:
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            timestamp = msg.get('timestamp', '')
            last_messages_text += f"{role.capitalize()} ({timestamp}): {content}\n\n"
    
    # Create a minimal system prompt that includes map.json and modes.json content
    system_prompt = f"""You are the Context Builder for KinOS. Select the most relevant files based on the user's message.

MAP.JSON CONTENT:
{map_content}
"""

    # Add modes.txt content if it exists
    if modes_content:
        system_prompt += f"""
MODES.TXT CONTENT:
{modes_content}

IMPORTANT: Based on the user's message, you should always suggest one appropriate mode from modes.txt that would be most relevant for handling this request.
First line of your response should be "SELECTED_MODE: [mode_name]" followed by a blank line.
"""

    system_prompt += """
After the mode selection (if applicable), provide a JSON array of {min_files}-{max_files} files that are most relevant to the user's message, focusing on quality over quantity."""

    # Create a user message for file selection
    selection_prompt = f"""User message: {message}{mode_info}

{last_messages_text}Available files (excluding core files that are always included):
{json.dumps(available_files, indent=2)}

Note: Core system files are already included automatically.
Return your answer as a JSON array of file paths only."""
    
    try:
        # Always use claude-3-7-sonnet-latest for context building
        context_builder_model = "claude-3-7-sonnet-latest"
        logger.info(f"Using {context_builder_model} for context building (ignoring model parameter: {model})")
        
        # Call Claude to select relevant files with map.json in system prompt
        logger.info(f"Making Claude API call for context building with:")
        logger.info(f"  Model: {context_builder_model}")
        logger.info(f"  System prompt: {system_prompt}")
        logger.info(f"  User message: {selection_prompt}")
        
        response = client.messages.create(
            model=context_builder_model,
            max_tokens=1000,
            system=system_prompt,
            messages=[
                {"role": "user", "content": selection_prompt}
            ]
        )
        
        # Log the full response
        logger.info(f"Claude context builder response: {response}")
        
        # Extract the response text
        response_text = response.content[0].text
        logger.info(f"Claude context builder response text: {response_text}")
        
        # Debug print before processing selected mode and JSON array
        print("About to process selected mode and JSON array")
        
        # Extract the selected mode if present
        selected_mode = None
        if modes_content:
            # Look for "SELECTED_MODE:" in the response text
            if "SELECTED_MODE:" in response_text:
                # Split by newlines and find the line with SELECTED_MODE
                for line in response_text.split('\n'):
                    if "SELECTED_MODE:" in line:
                        # Extract the mode name after the colon
                        selected_mode = line.split(':', 1)[1].strip()
                        logger.info(f"Claude selected mode: {selected_mode}")
                        break
        
        # Find JSON array in the response
        json_array_start = response_text.find('[')
        json_array_end = response_text.rfind(']')
        
        selected_files = []
        if json_array_start != -1 and json_array_end != -1 and json_array_end > json_array_start:
            json_match = response_text[json_array_start:json_array_end+1]
            
            # Try to parse the JSON array
            try:
                selected_files = json.loads(json_match)
                logger.info(f"Claude selected files: {selected_files}")
            except json.JSONDecodeError as e:
                logger.warning(f"Could not parse JSON from Claude's response: {e}")
        else:
            logger.warning("Could not extract JSON from Claude's response, using empty list")
            
    except Exception as e:
        logger.error(f"Error calling Claude for file selection: {str(e)}")
        # Print the full exception traceback for debugging
        import traceback
        print(f"Exception in build_context: {str(e)}")
        print(traceback.format_exc())
        selected_files = []
        selected_mode = None
    
    # Combine core files, attachments, and selected files
    all_files = core_files + attachment_files + selected_files
    
    # If a mode was explicitly provided, use that instead of the selected one
    if mode:
        selected_mode = mode
    
    return all_files, selected_mode
