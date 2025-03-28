import os
import subprocess
import datetime
import json
import logging
from config import logger

def call_aider_with_context(project_path, selected_files, message_content, stream=False, addSystem=None):
    """
    Call Aider CLI with the selected context files and user message.
    
    Args:
        project_path: Path to the project directory
        selected_files: List of files to include in the context
        message_content: User message content
        stream: Whether to stream the response (default: False)
        addSystem: Optional additional system instructions
    
    Returns:
        If stream=False: Aider response as a string
        If stream=True: Generator yielding response chunks
    """
    # Get the Anthropic API key from environment
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")
    
    # Build the command
    cmd = ["aider", "--sonnet", "--yes-always", "--restore-chat-history", f"--anthropic-api-key={api_key}"]
    
    # Always add messages.json as --read
    messages_file = "messages.json"
    messages_path = os.path.join(project_path, messages_file)
    
    # Get the last 2 messages from messages.json
    last_messages = []
    if os.path.exists(messages_path):
        try:
            with open(messages_path, 'r', encoding='utf-8') as f:
                messages = json.load(f)
                if messages:
                    last_messages = messages[-2:] if len(messages) >= 2 else messages
        except Exception as e:
            logger.error(f"Error reading messages.json: {str(e)}")
    
    # Format the last messages for inclusion in the prompt
    last_messages_text = ""
    if last_messages:
        last_messages_text = "\n\nLast messages:\n"
        for msg in last_messages:
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            timestamp = msg.get('timestamp', '')
            last_messages_text += f"{role.capitalize()} ({timestamp}): {content}\n\n"
    
    if os.path.exists(messages_path):
        cmd.extend(["--read", messages_file])
        logger.info(f"Added messages.json as --read file")
    
    # Create a temporary file for addSystem if provided
    temp_system_file = None
    if addSystem:
        import tempfile
        temp_system_file = os.path.join(project_path, "temp_system_instructions.txt")
        try:
            with open(temp_system_file, 'w', encoding='utf-8') as f:
                f.write(f"# Additional System Instructions\n\n{addSystem}")
            cmd.extend(["--read", "temp_system_instructions.txt"])
            logger.info(f"Created temporary file for additional system instructions")
        except Exception as e:
            logger.error(f"Error creating temporary system file: {str(e)}")
            temp_system_file = None
    
    # Add all selected files to the command
    for file in selected_files:
        file_path = os.path.join(project_path, file)
        if os.path.exists(file_path):
            # Use --read for system files, --file for others
            if file in ["kinos.txt", "system.txt", "persona.txt"]:
                cmd.extend(["--read", file])
            else:
                cmd.extend(["--file", file])
    
    # Log the command (without API key for security)
    safe_cmd = [c for c in cmd if not c.startswith("--anthropic-api-key=")]
    logger.info(f"Executing Aider command: {' '.join(safe_cmd)}")
    
    # Static prompt for the context builder with last messages appended
    static_prompt = f"""
    Your goal is to create and update files to store memories, knowledge, and learning from conversations in a structured way. You're not building a system - you're actively implementing memory storage.
    
    You should work autonomously without asking for confirmations. Analyze the conversation history and:
    
    1. Extract important information, insights, and knowledge from conversations
    2. Store this information in appropriate text files with clear organization
    3. Update existing knowledge files with new information
    4. Create new specialized text files when needed for specific topics
    5. Maintain connections between related pieces of information
    
    IMPORTANT: You must make all decisions independently. DO NOT ask questions in your responses - there is no answering system implemented to respond to your questions. Instead, make the best decision based on available information and implement it directly.
    
    IMPORTANT: You should ONLY create and modify TEXT FILES. Do NOT write code or create programming files. Focus exclusively on creating well-organized text documents (.txt, .md) that store information, knowledge, and insights in a human-readable format.
    
    Focus on being practical and efficient. Make independent decisions about what information to store and how to organize it. Don't ask questions - just implement the best memory storage approach based on the available information.
    
    Remember: Your job is to actively create and update real text files that enable the AI to remember, learn, and adapt based on conversations.
    
    Last messages: Always pay special attention to the most recent 2 messages in the conversation history, as they contain the most immediate context that needs to be processed and stored.{last_messages_text}
    """
    
    # Create a log file for this run
    aider_logs_file = os.path.join(project_path, "aider_logs.txt")
    with open(aider_logs_file, 'a', encoding='utf-8') as f:
        f.write(f"\n--- Aider run at {datetime.datetime.now().isoformat()} ---\n")
        f.write(f"Command: {' '.join(safe_cmd)}\n")
        f.write(f"Input: {static_prompt}\n")
    
    try:
        # Run Aider in the project directory with the static prompt as input
        # Set encoding to utf-8 explicitly to handle emojis and other special characters
        if stream:
            # Use Popen for streaming
            process = subprocess.Popen(
                cmd,
                cwd=project_path,  # Run in the project directory
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',  # Add explicit UTF-8 encoding
                bufsize=1  # Line buffered
            )
            
            # Send the static prompt to stdin and make sure to flush and close it
            process.stdin.write(static_prompt + "\n")
            process.stdin.flush()
            process.stdin.close()
            
            # Create a generator to yield output lines
            def generate_output():
                # Buffer for collecting the complete output
                complete_output = []
                
                # Read and yield stdout line by line
                for line in process.stdout:
                    complete_output.append(line)
                    yield line
                
                # After stdout is done, check stderr
                stderr_output = process.stderr.read()
                
                # Save complete logs
                with open(aider_logs_file, 'a', encoding='utf-8') as f:
                    f.write(f"Output:\n{''.join(complete_output)}\n")
                    if stderr_output:
                        f.write(f"Errors:\n{stderr_output}\n")
                    f.write("--- End of Aider run ---\n\n")
                
                # Clean up temporary file if it exists
                if temp_system_file and os.path.exists(temp_system_file):
                    try:
                        os.remove(temp_system_file)
                        logger.info(f"Removed temporary system file")
                    except Exception as e:
                        logger.error(f"Error removing temporary system file: {str(e)}")
                
                # If there was an error, yield it as well
                if stderr_output:
                    yield f"\nErrors occurred:\n{stderr_output}"
            
            return generate_output()
        else:
            # Use run for non-streaming (original behavior)
            result = subprocess.run(
                cmd,
                cwd=project_path,  # Run in the project directory
                input=static_prompt,
                text=True,
                encoding='utf-8',  # Add explicit UTF-8 encoding
                capture_output=True,
                check=True,
                timeout=300  # Add a 5-minute timeout
            )
            
            # Save Aider logs to a file in the project directory
            with open(aider_logs_file, 'a', encoding='utf-8') as f:
                f.write(f"Output:\n{result.stdout}\n")
                if result.stderr:
                    f.write(f"Errors:\n{result.stderr}\n")
                f.write("--- End of Aider run ---\n\n")
            
            # Clean up temporary file if it exists
            if temp_system_file and os.path.exists(temp_system_file):
                try:
                    os.remove(temp_system_file)
                    logger.info(f"Removed temporary system file")
                except Exception as e:
                    logger.error(f"Error removing temporary system file: {str(e)}")
            
            # Return the stdout from Aider
            return result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"Aider command failed with exit code {e.returncode}")
        logger.error(f"Stderr: {e.stderr}")
        
        # Save error logs
        with open(aider_logs_file, 'a', encoding='utf-8') as f:
            f.write(f"Error (exit code {e.returncode}):\n{e.stderr}\n")
            if e.stdout:
                f.write(f"Output before error:\n{e.stdout}\n")
            f.write("--- End of Aider error ---\n\n")
        
        # Clean up temporary file if it exists
        if temp_system_file and os.path.exists(temp_system_file):
            try:
                os.remove(temp_system_file)
                logger.info(f"Removed temporary system file")
            except Exception as e:
                logger.error(f"Error removing temporary system file: {str(e)}")
        
        raise RuntimeError(f"Aider command failed: {e.stderr}")
