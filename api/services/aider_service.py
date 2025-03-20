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
    
    # Add all selected files to the command
    for file in selected_files:
        file_path = os.path.join(project_path, file)
        if os.path.exists(file_path):
            cmd.extend(["--file", file])
    
    # Log the command (without API key for security)
    safe_cmd = [c for c in cmd if not c.startswith("--anthropic-api-key=")]
    logger.info(f"Executing Aider command: {' '.join(safe_cmd)}")
    
    try:
        # Run Aider in the project directory with the user message as input
        # Set encoding to utf-8 explicitly to handle emojis and other special characters
        result = subprocess.run(
            cmd,
            cwd=project_path,  # Run in the project directory
            input=message_content,
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
            f.write(f"Input: {message_content}\n")
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
            f.write(f"Input: {message_content}\n")
            f.write(f"Error (exit code {e.returncode}):\n{e.stderr}\n")
            if e.stdout:
                f.write(f"Output before error:\n{e.stdout}\n")
            f.write("--- End of Aider error ---\n\n")
        
        raise RuntimeError(f"Aider command failed: {e.stderr}")
