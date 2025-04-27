import os
import subprocess
import datetime
import json
import logging
import tempfile
import shutil
from config import logger, BASE_URL
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from git_utils import find_git_executable, run_git_command, check_git_installed, configure_git_for_merge

# Git functionality is now imported from git_utils.py

def call_aider_with_context(kin_path, selected_files, message_content, stream=False, addSystem=None, provider=None, model=None):
    """
    Call Aider CLI with the selected context files and user message.
    
    Args:
        kin_path: Path to the kin directory
        selected_files: List of files to include in the context
        message_content: User message content
        stream: Whether to stream the response (default: False)
        addSystem: Optional additional system instructions
        provider: Optional LLM provider to use ("claude" or "openai")
        model: Optional model to use
    
    Returns:
        If stream=False: Aider response as a string
        If stream=True: Generator yielding response chunks
    """
    # Set UTF-8 mode for Windows console
    env = os.environ.copy()
    if os.name == 'nt':  # Windows
        env['PYTHONIOENCODING'] = 'utf-8'
        # Force terminal to use UTF-8
        env['PYTHONUTF8'] = '1'
        # Set console code page to UTF-8
        try:
            subprocess.run(['chcp', '65001'], shell=True, check=False)
            logger.info("Set Windows console to UTF-8 mode (code page 65001)")
        except Exception as e:
            logger.warning(f"Could not set Windows console code page: {str(e)}")
            
    # Get the appropriate API key based on provider
    api_key = None
    
    if provider == "openai" or (model and (model.startswith("gpt-") or model.startswith("o"))):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        # Select the appropriate model flag based on the model name
        if model:
            if model.startswith("gpt-4o") or model == "o4":
                aider_model_flag = "--4o"
            elif model.startswith("gpt-4-turbo") or model == "gpt-4-0125-preview":
                aider_model_flag = "--4-turbo"
            elif model.startswith("gpt-3.5") or model == "gpt-35-turbo":
                aider_model_flag = "--35turbo"
            elif model == "o4-mini" or model == "o4-mini-2025-04-16":
                aider_model_flag = "--model o4-mini"  # Use --model flag for o4-mini
            elif model.startswith("o1-mini"):
                aider_model_flag = "--o1-mini"
            elif model.startswith("o1-preview"):
                aider_model_flag = "--o1-preview"
            elif model == "o3-mini":  # Add support for o3-mini
                aider_model_flag = "--model o3-mini"  # Use --model flag for o3-mini
            else:
                # For any other model, use the --model flag with the model name
                aider_model_flag = f"--model {model}"
                logger.info(f"Using custom model with --model flag: {model}")
        else:
            # Default to GPT-4o if no specific model is provided
            aider_model_flag = "--4o"
    else:
        # Default to Claude
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        
        # Select the appropriate Claude model flag
        if model:
            if model.startswith("claude-3-sonnet") or model == "claude-3-5-sonnet-20240620":
                aider_model_flag = "--sonnet"
            elif model.startswith("claude-3-haiku"):
                aider_model_flag = "--haiku"
            elif model.startswith("claude-3-opus"):
                aider_model_flag = "--opus"
            else:
                # Default to Sonnet for unknown Claude models
                aider_model_flag = "--sonnet"
        else:
            # Default to Sonnet if no specific model is provided
            aider_model_flag = "--sonnet"
    
    # Check if this is a linked repository
    is_repo_linked = False
    repo_config_path = os.path.join(kin_path, "repo_config.json")
    if os.path.exists(repo_config_path):
        try:
            with open(repo_config_path, 'r') as f:
                repo_config = json.load(f)
                is_repo_linked = repo_config.get('IS_REPO_LINKED', 'false').lower() == 'true'
                logger.info(f"Repository linked status: {is_repo_linked}")
        except Exception as e:
            logger.warning(f"Error reading repo_config.json: {str(e)}")
    
    # If repository is linked, pull changes before Aider call
    if is_repo_linked:
        logger.info("Repository is linked. Pulling changes before Aider call...")
        try:
            # Check if git is installed
            if not check_git_installed():
                logger.warning("Git executable not found, cannot pull changes")
            else:
                # Configure Git for merge strategy
                configure_git_for_merge(kin_path)
                
                # Try to pull changes from the remote repository
                try:
                    run_git_command(
                        ["git", "pull", "--force", "origin", "master"],
                        cwd=kin_path
                    )
                    logger.info("Changes pulled from remote repository before Aider call")
                except subprocess.CalledProcessError:
                    # Try with main branch if master fails
                    try:
                        run_git_command(
                            ["git", "pull", "--force", "origin", "main"],
                            cwd=kin_path
                        )
                        logger.info("Changes pulled from remote repository (main branch) before Aider call")
                    except subprocess.CalledProcessError as e:
                        logger.warning(f"Error pulling from remote repository: {str(e)}")
        except Exception as e:
            logger.warning(f"Error pulling changes before Aider call: {str(e)}")
    
    # Build the command
    if provider == "openai" or (model and (model.startswith("gpt-") or model.startswith("o"))):
        if aider_model_flag.startswith("--model"):
            # Handle the case where we need to use --model flag
            model_name = aider_model_flag.split(" ")[1]  # Extract the model name
            cmd = ["aider", "--model", model_name, "--yes-always", f"--openai-api-key={api_key}", "--message", str(message_content)]
        else:
            # Use the standard flag approach
            cmd = ["aider", aider_model_flag, "--yes-always", f"--openai-api-key={api_key}", "--message", str(message_content)]
    else:
        cmd = ["aider", aider_model_flag, "--yes-always", f"--anthropic-api-key={api_key}", "--message", str(message_content)]
    
    # Always add messages.json as --read
    messages_file = "messages.json"
    messages_path = os.path.join(kin_path, messages_file)
    
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
    
    # Always add kinos.txt and system.txt as --read if they exist
    kinos_file = "kinos.txt"
    kinos_path = os.path.join(kin_path, kinos_file)
    if os.path.exists(kinos_path) and kinos_file not in selected_files:
        cmd.extend(["--read", kinos_file])
        logger.info(f"Added kinos.txt as --read file (core system file)")
        
    system_file = "system.txt"
    system_path = os.path.join(kin_path, system_file)
    if os.path.exists(system_path) and system_file not in selected_files:
        cmd.extend(["--read", system_file])
        logger.info(f"Added system.txt as --read file (core system file)")
        
    # Also check for persona.txt as an alternative to kinos.txt and system.txt
    persona_file = "persona.txt"
    persona_path = os.path.join(kin_path, persona_file)
    if os.path.exists(persona_path) and persona_file not in selected_files:
        cmd.extend(["--read", persona_file])
        logger.info(f"Added persona.txt as --read file (core system file)")
    
    # Create a temporary file for addSystem if provided
    temp_system_file = None
    if addSystem:
        import tempfile
        temp_system_file = os.path.join(kin_path, "temp_system_instructions.txt")
        try:
            with open(temp_system_file, 'w', encoding='utf-8') as f:
                f.write(f"# Additional System Instructions\n\n{addSystem}")
            cmd.extend(["--read", "temp_system_instructions.txt"])
            logger.info(f"Created temporary file for additional system instructions")
        except Exception as e:
            logger.error(f"Error creating temporary system file: {str(e)}")
            temp_system_file = None
    
    # Determine which files are from the template
    # Extract blueprint and kin from kin_path
    parts = os.path.normpath(kin_path).split(os.sep)
    # Find the index of "blueprints" in the path
    try:
        blueprints_index = parts.index("blueprints")
        if len(parts) > blueprints_index + 2:
            blueprint = parts[blueprints_index + 1]
            # Check if this is a template or regular kin
            if parts[blueprints_index + 2] == "template":
                # This is already a template, all files are template files
                template_files = selected_files
            else:
                # This is a kin, get template files from blueprint template
                template_path = os.path.join(os.sep.join(parts[:blueprints_index + 2]), blueprint, "template")
                template_files = []
                if os.path.exists(template_path):
                    # Get all files in the template directory
                    for root, _, files in os.walk(template_path):
                        for file in files:
                            rel_path = os.path.relpath(os.path.join(root, file), template_path)
                            template_files.append(rel_path)
                logger.info(f"Found {len(template_files)} files in template")
        else:
            # Path doesn't contain enough parts, assume no template files
            template_files = []
            logger.warning("Could not determine blueprint/kin from path, treating all files as kin files")
    except ValueError:
        # "blueprints" not found in path
        template_files = []
        logger.warning("'blueprints' not found in path, treating all files as kin files")
    
    # Add all selected files to the command
    for file in selected_files:
        file_path = os.path.join(kin_path, file)
        if os.path.exists(file_path):
            # Use --read for system files, template files, and specific known files
            if (file in ["kinos.txt", "system.txt", "persona.txt"] or 
                file in template_files or 
                file.startswith("modes/") or 
                file.startswith("adaptations/") or
                file.startswith("knowledge/") or
                file.startswith("sources/")):  # Add sources/ directory as read-only
                cmd.extend(["--read", file])
                logger.info(f"Added {file} as --read (non-editable) file")
            else:
                cmd.extend(["--file", file])
                logger.info(f"Added {file} as --file (editable) file")
    
    # Log the command (without API key for security)
    safe_cmd = [c for c in cmd if not c.startswith("--anthropic-api-key=")]
    logger.info(f"Executing Aider command: {' '.join(safe_cmd)}")
    
    # Log the breakdown of editable vs non-editable files
    read_files = [c for c in cmd if c not in ["--read", "--file"] and cmd[cmd.index(c)-1] == "--read"]
    file_files = [c for c in cmd if c not in ["--read", "--file"] and cmd[cmd.index(c)-1] == "--file"]
    logger.info(f"Non-editable files (--read): {read_files}")
    logger.info(f"Editable files (--file): {file_files}")
    
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
    aider_logs_file = os.path.join(kin_path, "aider_logs.txt")
    with open(aider_logs_file, 'a', encoding='utf-8') as f:
        f.write(f"\n--- Aider run at {datetime.datetime.now().isoformat()} ---\n")
        f.write(f"Command: {' '.join(safe_cmd)}\n")
        f.write(f"Input: {static_prompt}\n")
    
    try:
        # Run Aider in the kin directory with the static prompt as input
        # Set encoding to utf-8 explicitly to handle emojis and other special characters
        if stream:
            # Use Popen for streaming
            process = subprocess.Popen(
                cmd,
                cwd=kin_path,  # Run in the kin directory
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',  # Add explicit UTF-8 encoding
                errors='replace',  # Replace invalid characters instead of failing
                bufsize=1,  # Line buffered
                env=env  # Add the environment variables
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
                
                # If repository is linked, push changes after Aider call
                if is_repo_linked:
                    logger.info("Repository is linked. Pushing changes after Aider call...")
                    try:
                        # Check if git is installed
                        if not check_git_installed():
                            logger.warning("Git executable not found, cannot push changes")
                            yield "Warning: Git executable not found, cannot push changes"
                        else:
                            # Configure Git for merge strategy
                            configure_git_for_merge(kin_path)
                            
                            # Add all files
                            run_git_command(
                                ["git", "add", "."],
                                cwd=kin_path
                            )
                            
                            # Commit changes if there are any
                            try:
                                run_git_command(
                                    ["git", "commit", "-m", "Auto-commit after Aider call"],
                                    cwd=kin_path
                                )
                                logger.info("Changes committed after Aider call")
                            except subprocess.CalledProcessError:
                                # No changes to commit is not an error
                                logger.info("No changes to commit after Aider call")
                            
                            # Push changes with force flag
                            try:
                                run_git_command(
                                    ["git", "push", "--force", "origin", "master"],
                                    cwd=kin_path
                                )
                                logger.info("Changes force-pushed to remote repository after Aider call")
                            except subprocess.CalledProcessError:
                                # Try with main branch if master fails
                                try:
                                    run_git_command(
                                        ["git", "push", "--force", "origin", "main"],
                                        cwd=kin_path
                                    )
                                    logger.info("Changes force-pushed to remote repository (main branch) after Aider call")
                                except subprocess.CalledProcessError as e:
                                    logger.warning(f"Error pushing to remote repository: {str(e)}")
                                    yield "Warning: Failed to push changes to remote repository"
                    except Exception as e:
                        logger.warning(f"Error pushing changes after Aider call: {str(e)}")
                        yield f"Warning: Error pushing changes: {str(e)}"
                
                # If there was an error, yield it as well
                if stderr_output:
                    yield f"\nErrors occurred:\n{stderr_output}"
            
            return generate_output()
        else:
            # Use run for non-streaming (original behavior)
            result = subprocess.run(
                cmd,
                cwd=kin_path,  # Run in the kin directory
                input=static_prompt,
                text=True,
                encoding='utf-8',  # Add explicit UTF-8 encoding
                errors='replace',  # Replace invalid characters instead of failing
                capture_output=True,
                check=True,
                timeout=600,  # Increase to a 10-minute timeout
                env=env  # Add the environment variables
            )
            
            # Save Aider logs to a file in the kin directory
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
            
            # If repository is linked, push changes after Aider call
            if is_repo_linked:
                logger.info("Repository is linked. Pushing changes after Aider call...")
                try:
                    # Check if git is installed
                    if not check_git_installed():
                        logger.warning("Git executable not found, cannot push changes")
                        return result.stdout  # Return early if Git not found
                    
                    # Configure Git for merge strategy
                    configure_git_for_merge(kin_path)
                    
                    # Add all files
                    run_git_command(
                        ["git", "add", "."],
                        cwd=kin_path
                    )
                    
                    # Commit changes if there are any
                    try:
                        run_git_command(
                            ["git", "commit", "-m", "Auto-commit after Aider call"],
                            cwd=kin_path
                        )
                        logger.info("Changes committed after Aider call")
                    except subprocess.CalledProcessError:
                        # No changes to commit is not an error
                        logger.info("No changes to commit after Aider call")
                    
                    # Push changes with force flag
                    try:
                        run_git_command(
                            ["git", "push", "--force", "origin", "master"],
                            cwd=kin_path
                        )
                        logger.info("Changes pushed to remote repository after Aider call")
                    except subprocess.CalledProcessError:
                        # Try with main branch if master fails
                        try:
                            run_git_command(
                                ["git", "push", "--force", "origin", "main"],
                                cwd=kin_path
                            )
                            logger.info("Changes force-pushed to remote repository (main branch) after Aider call")
                        except subprocess.CalledProcessError as e:
                            logger.warning(f"Error pushing to remote repository: {str(e)}")
                except Exception as e:
                    logger.warning(f"Error pushing changes after Aider call: {str(e)}")
            
            # Return the stdout from Aider
            return result.stdout
    except subprocess.TimeoutExpired as e:
        logger.error(f"Aider command timed out after {e.timeout} seconds")
        
        # Save timeout error logs
        with open(aider_logs_file, 'a', encoding='utf-8') as f:
            f.write(f"Error: Command timed out after {e.timeout} seconds\n")
            f.write("--- End of Aider timeout error ---\n\n")
        
        # Clean up temporary file if it exists
        if temp_system_file and os.path.exists(temp_system_file):
            try:
                os.remove(temp_system_file)
                logger.info(f"Removed temporary system file")
            except Exception as e:
                logger.error(f"Error removing temporary system file: {str(e)}")
        
        raise RuntimeError(f"Aider command timed out after {e.timeout} seconds")
        
    except subprocess.TimeoutExpired as e:
        logger.error(f"Aider command timed out after {e.timeout} seconds")
        
        # Save timeout error logs
        with open(aider_logs_file, 'a', encoding='utf-8') as f:
            f.write(f"Error: Command timed out after {e.timeout} seconds\n")
            f.write("--- End of Aider timeout error ---\n\n")
        
        # Clean up temporary file if it exists
        if temp_system_file and os.path.exists(temp_system_file):
            try:
                os.remove(temp_system_file)
                logger.info(f"Removed temporary system file")
            except Exception as e:
                logger.error(f"Error removing temporary system file: {str(e)}")
        
        raise RuntimeError(f"Aider command timed out after {e.timeout} seconds")
        
    except subprocess.TimeoutExpired as e:
        logger.error(f"Aider command timed out after {e.timeout} seconds")
        
        # Save timeout error logs
        with open(aider_logs_file, 'a', encoding='utf-8') as f:
            f.write(f"Error: Command timed out after {e.timeout} seconds\n")
            f.write("--- End of Aider timeout error ---\n\n")
        
        # Clean up temporary file if it exists
        if temp_system_file and os.path.exists(temp_system_file):
            try:
                os.remove(temp_system_file)
                logger.info(f"Removed temporary system file")
            except Exception as e:
                logger.error(f"Error removing temporary system file: {str(e)}")
        
        raise RuntimeError(f"Aider command timed out after {e.timeout} seconds")
        
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
