import os
import subprocess
import datetime
import logging
from config import logger

def call_aider_with_context(project_path, selected_files, message_content):
    """
    Call Aider CLI with the selected context files and user message.
    
    Args:
        project_path: Path to the project directory
        selected_files: List of files to include in the context
        message_content: User message content
    
    Returns:
        Aider response as a string
    """
    # Get the Anthropic API key from environment
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")
    
    # Build the command
    cmd = ["aider", "--haiku", "--yes-always", f"--anthropic-api-key={api_key}"]
    
    # Always add messages.json as --read
    messages_file = "messages.json"
    messages_path = os.path.join(project_path, messages_file)
    if os.path.exists(messages_path):
        cmd.extend(["--read", messages_file])
        logger.info(f"Added messages.json as --read file")
    
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
    
    # Static prompt for the context builder
    static_prompt = """
    Your goal is to create and update files to store memories, knowledge, and learning from conversations in a structured way. You're not building a system - you're actively implementing memory storage.
    
    You should work autonomously without asking for confirmations. Analyze the conversation history and:
    
    1. Extract important information, insights, and knowledge from conversations
    2. Store this information in appropriate files with clear organization
    3. Update existing knowledge files with new information
    4. Create new specialized files when needed for specific topics
    5. Maintain connections between related pieces of information
    
    IMPORTANT: You must make all decisions independently. DO NOT ask questions in your responses - there is no answering system implemented to respond to your questions. Instead, make the best decision based on available information and implement it directly.
    
    Focus on being practical and efficient. Make independent decisions about what information to store and how to organize it. Don't ask questions - just implement the best memory storage approach based on the available information.
    
    Remember: Your job is to actively create and update real files that enable the AI to remember, learn, and adapt based on conversations.
    """
    
    try:
        # Run Aider in the project directory with the static prompt as input
        # Set encoding to utf-8 explicitly to handle emojis and other special characters
        result = subprocess.run(
            cmd,
            cwd=project_path,  # Run in the project directory
            input=static_prompt,
            text=True,
            encoding='utf-8',  # Add explicit UTF-8 encoding
            capture_output=True,
            check=True
        )
        
        # Save Aider logs to a file in the project directory
        aider_logs_file = os.path.join(project_path, "aider_logs.txt")
        with open(aider_logs_file, 'a', encoding='utf-8') as f:  # Add explicit UTF-8 encoding
            f.write(f"\n--- Aider run at {datetime.datetime.now().isoformat()} ---\n")
            f.write(f"Command: {' '.join(safe_cmd)}\n")
            f.write(f"Input: {static_prompt}\n")
            f.write(f"Output:\n{result.stdout}\n")
            if result.stderr:
                f.write(f"Errors:\n{result.stderr}\n")
            f.write("--- End of Aider run ---\n\n")
        
        # Return the stdout from Aider
        return result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"Aider command failed with exit code {e.returncode}")
        logger.error(f"Stderr: {e.stderr}")
        
        # Save error logs
        aider_logs_file = os.path.join(project_path, "aider_logs.txt")
        with open(aider_logs_file, 'a', encoding='utf-8') as f:  # Add explicit UTF-8 encoding
            f.write(f"\n--- Aider error at {datetime.datetime.now().isoformat()} ---\n")
            f.write(f"Command: {' '.join(safe_cmd)}\n")
            f.write(f"Input: {static_prompt}\n")
            f.write(f"Error (exit code {e.returncode}):\n{e.stderr}\n")
            if e.stdout:
                f.write(f"Output before error:\n{e.stdout}\n")
            f.write("--- End of Aider error ---\n\n")
        
        raise RuntimeError(f"Aider command failed: {e.stderr}")
