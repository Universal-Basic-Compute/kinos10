import os
import json
import logging
import anthropic
import datetime
from config import MODEL, logger
from services.llm_service import LLMProvider

def get_llm_client(provider=None, model=None):
    """
    Get the appropriate LLM client based on provider and model.
    
    Args:
        provider: The provider to use (claude, openai, or deepseek)
        model: The model to use
        
    Returns:
        An instance of the appropriate LLM provider
    """
    # If model is specified but provider isn't, infer provider from model name
    if not provider and model:
        if model.startswith("gpt-") or model.startswith("o"):
            provider = "openai"
        elif model.startswith("claude-"):
            provider = "claude"
        elif model.startswith("deepseek"):
            provider = "deepseek"
        elif model.startswith("gemini"):
            provider = "gemini"
    
    # Get the provider from the LLMProvider factory
    from services.llm_service import LLMProvider
    return LLMProvider.get_provider(provider)

# Initialize Anthropic client for backward compatibility
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

def call_claude_with_context(selected_files, kin_path, message_content, images=None, model=None, history_length=25, is_new_message=True, addSystem=None, mode=None, channel_messages=None, channel_id=None, provider=None, stream=False, max_output_tokens=4000):
    """
    Call LLM API with the selected context files, user message, and optional images.
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
        channel_messages: Optional list of messages from a specific channel
        channel_id: Optional channel ID
        provider: Optional LLM provider to use ("claude" or "openai")
        stream: Whether to stream the response (default: False)
        max_output_tokens: Maximum number of tokens to generate in the response (default: 4000)
    
    Returns:
        LLM response as a string or a generator if stream=True
    """
    # Get the provider based on model or default
    if not provider: # provider is None
        if model: # model is not None
            if model.startswith("gpt-") or model.startswith("o"):
                provider = "openai"
            elif model.startswith("claude-"):
                provider = "claude"
            elif model.startswith("deepseek"):
                provider = "deepseek"
            elif model.startswith("gemini"):
                provider = "gemini"
            elif model.startswith("local"):
                provider = "local"
    
    # Get the appropriate LLM client
    llm_client = get_llm_client(provider, model)
    # Create a list to track temporary files that need to be deleted
    temp_files = []
    
    # Import re module for regex pattern matching
    import re
    
    # Look for system tags in the message content and extract them
    system_tag_pattern = r'<system>(.*?)</system>'
    system_instructions = None
    if message_content and '<system>' in message_content:
        # Extract content from system tags
        system_matches = re.findall(system_tag_pattern, message_content, re.DOTALL)
        if system_matches:
            # Join all system instructions
            system_instructions = "\n".join(system_matches)
            # Remove system tags from message content
            message_content = re.sub(system_tag_pattern, '', message_content, flags=re.DOTALL).strip()
            
            # If there's additional system instructions, append them
            if addSystem:
                system_instructions += f"\n\n{addSystem}"
                addSystem = None  # Clear addSystem since we've incorporated it
            
            # If message is now empty after removing system tags, use a default message
            if not message_content:
                message_content = "Hello"
    
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
        
        # If analysis mode is active (either explicitly set or detected in message),
        # add analysis mode content but keep core files
        is_analysis_mode = (mode == 'analysis' or 'analysis' in message_content.lower())
        
        if is_analysis_mode:
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
            file_contents.append(f"# Active Mode: analysis\n{analysis_content}")
            logger.info(f"Added analysis mode content while keeping core files in context")
        # If not analysis mode, add the specified mode file to the context
        elif mode:
            mode_file_path = os.path.join(kin_path, f"modes/{mode}.txt")
            if os.path.exists(mode_file_path):
                try:
                    with open(mode_file_path, 'r', encoding='utf-8') as f:
                        mode_content = f.read()
                    file_contents.append(f"# Active Mode: {mode}\n{mode_content}")
                    logger.info(f"Added mode file for {mode} to context")
                except Exception as e:
                    logger.error(f"Error reading mode file {mode_file_path}: {str(e)}")
        
        # Combine file contents into a single context string
        context = "\n\n".join(file_contents)
        
        # Append additional system text if provided
        if addSystem:
            context += f"\n\n# Additional System Instructions\n{addSystem}"
            logger.info("Added custom system instructions to context")
            
        # Add system instructions extracted from message if present
        if system_instructions:
            context += f"\n\n# System Instructions from Message\n{system_instructions}"
            logger.info("Added system instructions extracted from message tags")

        # If interacting with a specific channel (not main), add main channel's history to system context
        if channel_id and channel_id != "main":
            main_messages_file = os.path.join(kin_path, "messages.json")
            if os.path.exists(main_messages_file):
                try:
                    with open(main_messages_file, 'r', encoding='utf-8') as f_main:
                        main_channel_all_messages = json.load(f_main)
                        # Get last 'history_length' messages from main channel
                        main_recent_messages = main_channel_all_messages[-history_length:] if len(main_channel_all_messages) > history_length else main_channel_all_messages
                        if main_recent_messages:
                            main_history_text = "\n".join([f"{m.get('role')}: {m.get('content')}" for m in main_recent_messages])
                            context += f"\n\n# Main Channel Conversation History (for broader context):\n{main_history_text}"
                            logger.info(f"Added last {len(main_recent_messages)} messages from main channel to system context.")
                except Exception as e_main_msg:
                    logger.error(f"Error reading main messages.json for channel context: {str(e_main_msg)}")
    
        # Initialize messages array for the current channel's conversation
        messages = []
        
        # Use channel-specific messages if provided (for current channel history)
        if channel_messages:
            # Use the provided channel messages
            recent_messages = channel_messages
            logger.info(f"Using {len(recent_messages)} provided channel messages for current conversation history.")
        else:
            # Determine which messages file to use based on channel_id for current conversation history
            current_channel_messages_file_path = ""
            if channel_id and channel_id != "main":
                # Get channel path
                from services.file_service import get_channel_path
                channel_path = get_channel_path(kin_path, channel_id)
                current_channel_messages_file_path = os.path.join(channel_path, "messages.json")
                logger.info(f"Using specific channel messages file for conversation history: {current_channel_messages_file_path}")
            else: # main channel or channel_id is None
                current_channel_messages_file_path = os.path.join(kin_path, "messages.json")
                logger.info(f"Using main messages file for conversation history: {current_channel_messages_file_path}")
            
            # Load conversation history from the determined messages file
            recent_messages = [] # Initialize recent_messages
            if os.path.exists(current_channel_messages_file_path):
                try:
                    with open(current_channel_messages_file_path, 'r', encoding='utf-8') as f:
                        message_data = json.load(f)
                        # Limit to specified number of recent messages for the current channel
                        recent_messages = message_data[-history_length:] if len(message_data) > history_length else message_data
                except Exception as e:
                    logger.error(f"Error reading messages file {current_channel_messages_file_path}: {str(e)}")
                    # recent_messages remains empty as initialized
            # else: recent_messages remains empty as initialized
        
        # Add each message from the current channel's history as a proper message object
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
        
        # Ensure the user message is always included as the last message
        # First, check if the message is already in the messages array
        message_already_included = False
        for i, msg in enumerate(messages):
            if msg.get('role') == 'user' and msg.get('content') == message_content:
                message_already_included = True
                # Move this message to the end of the array if it's not already there
                if i < len(messages) - 1:
                    messages.append(messages.pop(i))
                break

        # If the message is not already included, add it
        if not message_already_included:
            messages.append({
                "role": "user",
                "content": message_content
            })
            
        # Add this debug log to see what's being sent to Claude
        logger.info(f"All messages being sent to Claude: {json.dumps([{'role': m.get('role'), 'content': m.get('content')[:100] + '...' if isinstance(m.get('content'), str) and len(m.get('content')) > 100 else m.get('content')} for m in messages], indent=2)}")
        
        # Use provided model if specified, otherwise use default from config
        model_to_use = model if model else MODEL
        logger.info(f"Calling LLM API with {len(messages)} messages" + (" and images in previous message" if images else "") + f", using model: {model_to_use}")
        logger.info(f"System context length: {len(context)} characters")
        logger.info(f"First few messages: {messages[:2] if len(messages) > 0 else 'No messages'}")
        
        # Add detailed logging of all messages being sent
        try:
            logger.info(f"Messages being sent to LLM: {json.dumps([{'role': m.get('role'), 'content_type': type(m.get('content')).__name__, 'content_length': len(str(m.get('content')))} for m in messages], indent=2)}")
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
            logger.info(f"LLM API request details:")
            logger.info(f"  Model: {model_to_use}")
            logger.info(f"  Provider: {provider}")
            logger.info(f"  System context length: {len(context)} characters")
            logger.info(f"  Number of messages: {len(messages)}")
            logger.info(f"  First message: {messages[0] if messages else 'No messages'}")
            logger.info(f"  Last message: {messages[-1] if messages else 'No messages'}")
            logger.info(f"  Streaming: {stream}")
            
            # Convert stream parameter to boolean if it's a string
            if isinstance(stream, str):
                stream = stream.lower() == 'true'
            
            # Log all messages being sent to LLM for better debugging
            try:
                logger.info(f"All messages being sent to LLM: {json.dumps([{'role': m.get('role'), 'content': m.get('content')[:100] + '...' if isinstance(m.get('content'), str) and len(m.get('content')) > 100 else m.get('content')} for m in messages], indent=2)}")
            except:
                logger.info("Could not serialize all messages for detailed logging")
            
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
            
            # Use the LLM client to generate a response
            if stream:
                # Return a generator for streaming responses
                logger.info("Using streaming response mode")
                return llm_client.generate_response(
                    messages=messages,
                    system=context,
                    max_tokens=max_output_tokens,
                    model=model_to_use,
                    stream=True
                )
            else:
                # Return a regular response
                logger.info("Using standard response mode")
                response_text = llm_client.generate_response(
                    messages=messages,
                    system=context,
                    max_tokens=max_output_tokens,
                    model=model_to_use,
                    stream=False
                )
                
                # Log the response
                logger.info(f"LLM response: {response_text[:500]}...")
                
                return response_text
        except Exception as e:
            logger.error(f"Error calling LLM API: {str(e)}")
            # Include the exception details in the returned message for debugging
            return f"I apologize, but I encountered an error: {str(e)}. Please try again."
    except Exception as e:
        logger.error(f"Error calling LLM API: {str(e)}")
        raise RuntimeError(f"LLM API call failed: {str(e)}")
    finally:
        # Clean up any temporary files
        for temp_file in temp_files:
            try:
                os.unlink(temp_file)
                logger.info(f"Deleted temporary file: {temp_file}")
            except Exception as e:
                logger.warning(f"Could not delete temporary file {temp_file}: {str(e)}")

def build_context(blueprint, kin_id, message, attachments=None, kin_path=None, model=None, mode=None, addSystem=None, history_length=2, min_files=5, max_files=15, provider=None, max_output_tokens=1000):
    """
    Build context by determining which files should be included.
    Uses LLM to select relevant files based on the message, map.json, and recent conversation history.
    
    Args:
        blueprint: blueprint name
        kin_id: kin ID
        message: User message content
        attachments: Optional list of attachments to always include in context
        kin_path: Optional kin path (if already known)
        model: Optional model to use
        mode: Optional mode parameter
        addSystem: Optional additional system instructions
        history_length: Number of recent messages to include for context (default: 2)
        min_files: Minimum number of files to include in context (default: 4)
        max_files: Maximum number of files to include in context (default: 8)
        provider: Optional LLM provider to use ("claude" or "openai")
        max_output_tokens: Maximum number of tokens to generate in the context building response (default: 1000)
        
    Returns:
        Tuple of (selected_files, selected_mode) where selected_mode may be None
    """
    # Determine provider based on model if not explicitly provided
    if not provider and model:
        if model.startswith("gpt-"):
            provider = "openai"
        elif model.startswith("claude-"):
            provider = "claude"
        elif model.startswith("gemini"):
            provider = "gemini"
    
    # Get the LLM client
    llm_client = get_llm_client(provider, model)
    # Import modules needed within this function
    import re
    
    # Debug print to help identify the issue
    print("Starting build_context function")
        
    # Move import inside function to avoid circular imports
    from services.file_service import get_kin_path
    from utils.helpers import should_ignore_file, load_gitignore
        
    # Import json here to ensure it's available
    import json
        
    if not kin_path:
        kin_path = get_kin_path(blueprint, kin_id)
    
    # Define file extensions to exclude
    excluded_extensions = [
        # Images
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.svg', '.ico',
        # Videos
        '.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv', '.webm',
        # Logs
        '.log', '.logs',
        # Other binary files
        '.pdf', '.zip', '.rar', '.tar', '.gz', '.7z',
        # Audio files
        '.mp3', '.wav', '.ogg', '.flac', '.aac',
        # Executable files
        '.exe', '.dll', '.so', '.bin'
    ]
    
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
    
    # Load gitignore patterns
    ignore_patterns = load_gitignore(kin_path)
    
    # Get all available files in the kin
    available_files = []
    for root, dirs, files in os.walk(kin_path):
        # Filter out ignored directories to avoid walking into them
        dirs[:] = [d for d in dirs if not should_ignore_file(os.path.relpath(os.path.join(root, d), kin_path), ignore_patterns)]
        
        for file in files:
            rel_path = os.path.relpath(os.path.join(root, file), kin_path)
            # Skip core files, attachments, and files that should be ignored
            if (rel_path not in core_files and 
                rel_path not in attachment_files and 
                not should_ignore_file(rel_path, ignore_patterns)):
                
                # Check if the file has an excluded extension
                _, ext = os.path.splitext(rel_path.lower())
                if ext in excluded_extensions:
                    logger.info(f"Excluding file with excluded extension: {rel_path}")
                    continue
                
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
        # Choose appropriate model for context building
        if provider == "openai":
            context_builder_model = "gpt-4o"
        elif provider == "claude": # Explicitly check for Claude if it's the intended provider
            context_builder_model = "claude-sonnet-4-20250514"
        else: # Default to Gemini (covers provider == "gemini" or provider is None/unrecognized)
            context_builder_model = "gemini-2.5-pro-preview-03-25"
            
        logger.info(f"Using {context_builder_model} for context building with provider: {provider or 'gemini (default)'}")
        
        # Call LLM to select relevant files with map.json in system prompt
        logger.info(f"Making LLM API call for context building with:")
        logger.info(f"  Model: {context_builder_model}")
        logger.info(f"  Provider: {provider}")
        logger.info(f"  System prompt: {system_prompt}")
        logger.info(f"  User message: {selection_prompt}")
        
        # Use the LLM provider abstraction to generate the response
        response_text = llm_client.generate_response(
            messages=[{"role": "user", "content": selection_prompt}],
            system=system_prompt,
            max_tokens=max_output_tokens,
            model=context_builder_model
        )
        
        # Log the response
        logger.info(f"LLM context builder response text: {response_text}")
        
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
                # Try to clean up the JSON string
                try:
                    # Remove any control characters
                    import re
                    cleaned_json = re.sub(r'[\x00-\x1F\x7F]', '', json_match)
                    # Try to parse again
                    selected_files = json.loads(cleaned_json)
                    logger.info(f"Successfully parsed JSON after cleaning: {selected_files}")
                except json.JSONDecodeError as e2:
                    logger.error(f"Still could not parse JSON after cleaning: {e2}")
                    # Fall back to a simple regex-based extraction
                    try:
                        # Look for patterns like "file.txt", "path/to/file.md", etc.
                        file_matches = re.findall(r'"([^"]+\.[^"]+)"', response_text)
                        if file_matches:
                            selected_files = file_matches
                            logger.info(f"Extracted files using regex: {selected_files}")
                        else:
                            logger.warning("Could not extract files using regex, using empty list")
                    except Exception as e3:
                        logger.error(f"Error in regex extraction: {e3}")
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
