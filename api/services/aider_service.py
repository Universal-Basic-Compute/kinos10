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
    env["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY", "") # Ensure GOOGLE_API_KEY is in env for Aider
    
    # Determine Aider's actual LLM configuration
    aider_llm_provider_for_aider_internal_use = provider
    aider_llm_model_for_aider_internal_use = model

    if provider == "local":
        logger.info("Application provider is 'local'. Determining LLM for Aider's internal use.")
        aider_llm_provider_for_aider_internal_use = "gemini" # Default for Aider
        aider_llm_model_for_aider_internal_use = "gemini-2.5-flash-preview-05-20" # Default model for Aider

        if model and "/" in model:
            local_prefix, actual_model_for_aider = model.split("/", 1)
            if local_prefix == "local":
                aider_llm_model_for_aider_internal_use = actual_model_for_aider
                if actual_model_for_aider.startswith("gpt-") or actual_model_for_aider.startswith("o"):
                    aider_llm_provider_for_aider_internal_use = "openai"
                elif actual_model_for_aider.startswith("claude-"):
                    aider_llm_provider_for_aider_internal_use = "claude"
                elif actual_model_for_aider.startswith("deepseek"):
                    aider_llm_provider_for_aider_internal_use = "deepseek"
                # If gemini, it's already the default
        logger.info(f"Aider will internally use provider: '{aider_llm_provider_for_aider_internal_use}' and model: '{aider_llm_model_for_aider_internal_use}' based on 'local' app provider.")

    # Override to Gemini if Claude was selected, to avoid Anthropic billing issues
    if aider_llm_provider_for_aider_internal_use == "claude":
        logger.warning("Anthropic provider was indicated for Aider; overriding to Gemini due to billing/configuration.")
        aider_llm_provider_for_aider_internal_use = "gemini"
        # If the original model was Claude-specific, ensure we use a Gemini model name.
        # Setting to a default Gemini model; the Gemini block will handle prefixing if needed.
        if aider_llm_model_for_aider_internal_use and aider_llm_model_for_aider_internal_use.startswith("claude-"):
            aider_llm_model_for_aider_internal_use = "gemini-2.5-flash-preview-05-20"

    cmd_aider_auth_parts = []

    if aider_llm_provider_for_aider_internal_use == "openai" or \
       (aider_llm_model_for_aider_internal_use and (aider_llm_model_for_aider_internal_use.startswith("gpt-") or aider_llm_model_for_aider_internal_use.startswith("o"))):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key: raise ValueError("OPENAI_API_KEY environment variable not set for Aider's OpenAI use.")
        current_aider_model_name = aider_llm_model_for_aider_internal_use or "gpt-4o"
        aider_model_flag = f"--model {current_aider_model_name}"
        cmd_aider_auth_parts = [f"--openai-api-key={api_key}"]
        logger.info(f"Aider configured for OpenAI with model: {current_aider_model_name}")

    elif aider_llm_provider_for_aider_internal_use == "deepseek" or \
         (aider_llm_model_for_aider_internal_use and aider_llm_model_for_aider_internal_use.startswith("deepseek")):
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key: raise ValueError("DEEPSEEK_API_KEY environment variable not set for Aider's DeepSeek use.")
        env["DEEPSEEK_API_KEY"] = api_key
        current_aider_model_name = aider_llm_model_for_aider_internal_use or "deepseek-chat"
        if "/" not in current_aider_model_name and aider_llm_provider_for_aider_internal_use == "deepseek": # ensure prefix for deepseek
             current_aider_model_name = f"deepseek/{current_aider_model_name}"
        aider_model_flag = f"--model {current_aider_model_name}"
        logger.info(f"Aider configured for DeepSeek with model: {current_aider_model_name}")

    elif aider_llm_provider_for_aider_internal_use == "claude" or \
         (aider_llm_model_for_aider_internal_use and aider_llm_model_for_aider_internal_use.startswith("claude-")):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key: raise ValueError("ANTHROPIC_API_KEY environment variable not set for Aider's Claude use.")
        current_aider_model_name = aider_llm_model_for_aider_internal_use or "claude-3-sonnet-20240229"
        # Aider generally expects model names like "claude-3-opus-20240229" directly.
        # No specific "anthropic/" prefix is usually needed unless Aider's internal mapping changes.
        aider_model_flag = f"--model {current_aider_model_name}"
        cmd_aider_auth_parts = [f"--anthropic-api-key={api_key}"]
        logger.info(f"Aider configured for Anthropic/Claude with model: {current_aider_model_name}")

    else: # Default to Gemini for Aider
        # This block handles explicit "gemini" provider or models starting with "gemini",
        # and also serves as the final fallback default.
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key: raise ValueError("GOOGLE_API_KEY environment variable not set for Aider's Gemini use (default).")
        # GOOGLE_API_KEY is already added to env
        
        # Determine the model name for Gemini
        if aider_llm_provider_for_aider_internal_use == "gemini" or \
           (aider_llm_model_for_aider_internal_use and aider_llm_model_for_aider_internal_use.startswith("gemini")):
            current_aider_model_name = aider_llm_model_for_aider_internal_use or "gemini-2.5-flash-preview-05-20" # Default if only "gemini" provider specified
        else: # Fallback default if provider was something else not caught above (e.g. "local" without specific model type)
            current_aider_model_name = "gemini-2.5-flash-preview-05-20" # General default Gemini model for Aider

        # Ensure Gemini model names are prefixed with "gemini/" for Aider
        if not current_aider_model_name.startswith("gemini/"):
            current_aider_model_name = f"gemini/{current_aider_model_name}"
            
        aider_model_flag = f"--model {current_aider_model_name}"
        # cmd_aider_auth_parts remains empty as GOOGLE_API_KEY is passed via env
        logger.info(f"Aider configured for Gemini (default or explicit) with model: {current_aider_model_name}")
    
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
                
                # Determine the branch to pull
                determined_branch_for_pull = None
                repo_config_file = os.path.join(kin_path, "repo_config.json")
                if os.path.exists(repo_config_file):
                    try:
                        with open(repo_config_file, 'r', encoding='utf-8') as f_config:
                            config_data = json.load(f_config)
                            determined_branch_for_pull = config_data.get('branch_name')
                            if determined_branch_for_pull:
                                logger.info(f"Using branch '{determined_branch_for_pull}' from repo_config.json for pull.")
                    except Exception as e_config:
                        logger.warning(f"Error reading branch_name from repo_config.json: {str(e_config)}. Will try to use current git branch.")
                
                if not determined_branch_for_pull:
                    logger.info("Branch not found in repo_config.json or error reading it. Determining current branch from git for pull.")
                    try:
                        # Use run_git_command to get current branch
                        branch_cmd_result = run_git_command(
                            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                            cwd=kin_path,
                            check=True 
                        )
                        determined_branch_for_pull = branch_cmd_result.stdout.strip()
                        if not determined_branch_for_pull: # Should not happen if check=True worked
                             # This case should ideally not be reached if check=True is effective
                            logger.warning("git rev-parse returned empty branch name, defaulting to 'master'.")
                            determined_branch_for_pull = "master"
                        else:
                            logger.info(f"Determined current branch for pull: {determined_branch_for_pull}")
                    except Exception as e_branch_cmd:
                        logger.warning(f"Could not determine current git branch: {str(e_branch_cmd)}. Aider will proceed without pull if this was the only way to determine branch.")
                        # Keep determined_branch_for_pull as None or a sensible default if essential
                        # For safety, if we can't determine, maybe don't pull. Or default to 'master'.
                        # Given the original code had master/main fallbacks, defaulting to master here if all else fails.
                        if not determined_branch_for_pull: # If it's still None
                            logger.warning("Defaulting to 'master' for pull as branch could not be determined.")
                            determined_branch_for_pull = "master"


                if determined_branch_for_pull:
                    try:
                        logger.info(f"Attempting to pull from origin/{determined_branch_for_pull}...")
                        run_git_command(
                            ["git", "pull", "--force", "origin", determined_branch_for_pull],
                            cwd=kin_path
                        )
                        logger.info(f"Changes pulled from remote repository (branch '{determined_branch_for_pull}') before Aider call.")
                    except subprocess.CalledProcessError as e_pull:
                        # Log the error from stderr for more details
                        detailed_error = e_pull.stderr if hasattr(e_pull, 'stderr') and e_pull.stderr else str(e_pull)
                        logger.warning(f"Error pulling from remote repository branch '{determined_branch_for_pull}': {detailed_error}. Aider will proceed with local files.")
                else:
                    logger.info("No specific branch determined for pull. Aider will proceed with local files.")
        except Exception as e:
            logger.warning(f"Error during pre-Aider git pull process: {str(e)}")
    
    # Build the command for Aider
    # Define the weak model to be used by Aider
    aider_weak_model_name = "gemini/gemini-2.5-flash-preview-05-20"
    logger.info(f"Aider will use weak model: {aider_weak_model_name}")
    cmd = ["aider", aider_model_flag, "--weak-model", aider_weak_model_name, "--yes-always"] + cmd_aider_auth_parts + ["--message", str(message_content)]
    
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
        temp_system_file = os.path.join(kin_path, "addSystem.txt")
        try:
            with open(temp_system_file, 'w', encoding='utf-8') as f:
                f.write(f"# Additional System Instructions\n\n{addSystem}")
            cmd.extend(["--read", "addSystem.txt"])
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
                            
                            # Determine the target branch for push from repo_config.json
                            target_branch_for_push = None
                            repo_config_file_path = os.path.join(kin_path, "repo_config.json")
                            if os.path.exists(repo_config_file_path):
                                try:
                                    with open(repo_config_file_path, 'r', encoding='utf-8') as f_config:
                                        config_data = json.load(f_config)
                                        target_branch_for_push = config_data.get('branch_name')
                                        if target_branch_for_push:
                                            logger.info(f"Using branch '{target_branch_for_push}' from repo_config.json for push.")
                                        else:
                                            logger.warning("branch_name not found in repo_config.json. Push will be skipped.")
                                except Exception as e_config_push:
                                    logger.warning(f"Error reading repo_config.json for push: {str(e_config_push)}. Push will be skipped.")
                            else:
                                logger.warning("repo_config.json not found. Push will be skipped.")

                            if target_branch_for_push:
                                try:
                                    run_git_command(
                                        ["git", "push", "--force", "origin", target_branch_for_push],
                                        cwd=kin_path
                                    )
                                    logger.info(f"Changes force-pushed to remote repository (branch '{target_branch_for_push}') after Aider call")
                                except subprocess.CalledProcessError as e_push_final:
                                    detailed_error_push = e_push_final.stderr if hasattr(e_push_final, 'stderr') and e_push_final.stderr else str(e_push_final)
                                    logger.warning(f"Error pushing to remote repository branch '{target_branch_for_push}': {detailed_error_push}")
                                    yield f"Warning: Failed to push changes to remote repository branch '{target_branch_for_push}'"
                                except Exception as e_push_general:
                                    logger.warning(f"General error pushing changes after Aider call to branch '{target_branch_for_push}': {str(e_push_general)}")
                                    yield f"Warning: Error pushing changes to branch '{target_branch_for_push}': {str(e_push_general)}"
                            else:
                                logger.warning("Target branch for push could not be determined from repo_config.json. Skipping push.")
                                yield "Warning: Could not determine branch to push to from repo_config.json. Changes were not pushed."
                    except Exception as e:
                        logger.warning(f"Error in post-Aider git push process: {str(e)}")
                        yield f"Warning: Error in git push process: {str(e)}"
                
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
                    
                    # Determine the target branch for push from repo_config.json
                    target_branch_for_push = None
                    repo_config_file_path = os.path.join(kin_path, "repo_config.json")
                    if os.path.exists(repo_config_file_path):
                        try:
                            with open(repo_config_file_path, 'r', encoding='utf-8') as f_config:
                                config_data = json.load(f_config)
                                target_branch_for_push = config_data.get('branch_name')
                                if target_branch_for_push:
                                    logger.info(f"Using branch '{target_branch_for_push}' from repo_config.json for push.")
                                else:
                                    logger.warning("branch_name not found in repo_config.json for push. Push will be skipped.")
                        except Exception as e_config_push:
                            logger.warning(f"Error reading repo_config.json for push: {str(e_config_push)}. Push will be skipped.")
                    else:
                        logger.warning("repo_config.json not found for push. Push will be skipped.")

                    if target_branch_for_push:
                        try:
                            run_git_command(
                                ["git", "push", "--force", "origin", target_branch_for_push],
                                cwd=kin_path
                            )
                            logger.info(f"Changes force-pushed to remote repository (branch '{target_branch_for_push}') after Aider call")
                        except subprocess.CalledProcessError as e_push_final:
                            detailed_error_push = e_push_final.stderr if hasattr(e_push_final, 'stderr') and e_push_final.stderr else str(e_push_final)
                            logger.warning(f"Error pushing to remote repository branch '{target_branch_for_push}': {detailed_error_push}")
                        except Exception as e_push_general:
                            logger.warning(f"General error pushing changes after Aider call to branch '{target_branch_for_push}': {str(e_push_general)}")
                    else:
                        logger.warning("Target branch for push could not be determined from repo_config.json. Skipping push.")
                except Exception as e:
                    logger.warning(f"Error in post-Aider git push process: {str(e)}")
            
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
