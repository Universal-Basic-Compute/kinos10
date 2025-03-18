from flask import Flask, request, jsonify
import os
import json
import logging
import anthropic
import datetime
import subprocess
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

def call_claude_with_context(selected_files, project_path, message_content):
    """
    Call Claude API directly with the selected context files and user message.
    
    Args:
        selected_files: List of files to include in the context
        project_path: Path to the project directory
        message_content: User message content
    
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
    
    # Create the prompt for Claude
    prompt = f"""
# Context
The following files provide context for my request:

{context}

# Request
{message_content}
"""
    
    try:
        # Call Claude API
        logger.info("Calling Claude API with context")
        response = client.messages.create(
            model=MODEL,
            max_tokens=4000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        # Extract the response text
        claude_response = response.content[0].text
        logger.info(f"Received response from Claude: {claude_response[:100]}...")
        return claude_response
    except Exception as e:
        logger.error(f"Error calling Claude API: {str(e)}")
        raise RuntimeError(f"Claude API call failed: {str(e)}")

# Get application data directory
def get_app_data_dir():
    """Get the appropriate application data directory based on the platform."""
    if os.name == 'nt':  # Windows
        app_data = os.path.join(os.environ.get('APPDATA', ''), 'KinOS')
    elif os.name == 'posix':  # Linux/Mac
        app_data = os.path.join(os.path.expanduser('~'), '.kinos')
    else:  # Fallback
        app_data = os.path.join(os.path.expanduser('~'), '.kinos')
    
    # Create directory if it doesn't exist
    os.makedirs(app_data, exist_ok=True)
    return app_data

# Constants
CUSTOMERS_DIR = os.path.join(get_app_data_dir(), "customers")
# Ensure customers directory exists
os.makedirs(CUSTOMERS_DIR, exist_ok=True)
MODEL = "claude-3-7-sonnet-latest"

def get_project_path(customer, project_id):
    """Get the full path to a project directory."""
    if project_id == "template":
        return os.path.join(CUSTOMERS_DIR, customer, "template")
    else:
        return os.path.join(CUSTOMERS_DIR, customer, "projects", project_id)

def initialize_project(customer, project_name, template_override=None):
    """
    Initialize a new project for a customer.
    Copies the template directory to create a new project.
    """
    # Validate customer exists
    customer_dir = os.path.join(CUSTOMERS_DIR, customer)
    if not os.path.exists(customer_dir):
        raise ValueError(f"Customer '{customer}' not found")
    
    # Get template path (either default or override)
    template_path = os.path.join(customer_dir, "template")
    if template_override and os.path.exists(os.path.join(CUSTOMERS_DIR, template_override, "template")):
        template_path = os.path.join(CUSTOMERS_DIR, template_override, "template")
    
    if not os.path.exists(template_path):
        raise ValueError(f"Template not found at {template_path}")
    
    # Create projects directory if it doesn't exist
    projects_dir = os.path.join(customer_dir, "projects")
    os.makedirs(projects_dir, exist_ok=True)
    
    # Generate a unique project ID
    import uuid
    project_id = str(uuid.uuid4())
    
    # Create project directory
    project_dir = os.path.join(projects_dir, project_id)
    
    # Copy template to project directory
    import shutil
    shutil.copytree(template_path, project_dir)
    
    # Create messages.json file
    messages_file = os.path.join(project_dir, "messages.json")
    with open(messages_file, 'w') as f:
        json.dump([], f)
    
    # Create thoughts.txt file
    thoughts_file = os.path.join(project_dir, "thoughts.txt")
    with open(thoughts_file, 'w') as f:
        f.write(f"# Thoughts for project: {project_name}\nCreated: {datetime.datetime.now().isoformat()}\n\n")
    
    # Update system.txt with project name if needed
    system_file = os.path.join(project_dir, "system.txt")
    if os.path.exists(system_file):
        with open(system_file, 'r') as f:
            system_content = f.read()
        
        # Replace placeholder if present
        if "{{PROJECT_NAME}}" in system_content:
            system_content = system_content.replace("{{PROJECT_NAME}}", project_name)
            with open(system_file, 'w') as f:
                f.write(system_content)
    
    return project_id

def load_file_content(project_path, file_path):
    """Load the content of a file from the project."""
    full_path = os.path.join(project_path, file_path)
    if not os.path.exists(full_path) or not os.path.isfile(full_path):
        logger.warning(f"File not found: {full_path}")
        return None
    
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading file {full_path}: {str(e)}")
        return None

def build_context(customer, project_id, message, attachments=None):
    """
    Build context by determining which files should be included.
    Uses Claude to select relevant files based on the message.
    """
    project_path = get_project_path(customer, project_id)
    
    # Check if persona.txt exists, if so use it instead of kinos.txt and system.txt
    persona_file = os.path.join(project_path, "persona.txt")
    if os.path.exists(persona_file):
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
            if file not in core_files:  # Skip core files as we'll add them separately
                rel_path = os.path.relpath(os.path.join(root, file), project_path)
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
        response = client.messages.create(
            model=MODEL,
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

@app.route('/api/projects', methods=['POST'])
def create_project():
    """
    Endpoint to initialize a new project.
    """
    try:
        data = request.json
        project_name = data.get('project_name', '')
        customer = data.get('customer', '')
        template_override = data.get('template_override')
        
        if not project_name:
            return jsonify({"error": "Project name is required"}), 400
        
        if not customer:
            return jsonify({"error": "Customer is required"}), 400
        
        project_id = initialize_project(customer, project_name, template_override)
        
        return jsonify({
            "project_id": project_id,
            "customer": customer,
            "status": "created"
        })
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error creating project: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/projects/<customer>/<project_id>/messages', methods=['GET'])
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
    cmd = ["aider", "--sonnet", "--yes-always", f"--anthropic-api-key={api_key}"]
    
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
        result = subprocess.run(
            cmd,
            cwd=project_path,  # Run in the project directory
            input=message_content,
            text=True,
            capture_output=True,
            check=True
        )
        
        # Save Aider logs to a file in the project directory
        aider_logs_file = os.path.join(project_path, "aider_logs.txt")
        with open(aider_logs_file, 'a') as f:
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
        with open(aider_logs_file, 'a') as f:
            f.write(f"\n--- Aider error at {datetime.datetime.now().isoformat()} ---\n")
            f.write(f"Command: {' '.join(safe_cmd)}\n")
            f.write(f"Input: {message_content}\n")
            f.write(f"Error (exit code {e.returncode}):\n{e.stderr}\n")
            if e.stdout:
                f.write(f"Output before error:\n{e.stdout}\n")
            f.write("--- End of Aider error ---\n\n")
        
        raise RuntimeError(f"Aider command failed: {e.stderr}")

@app.route('/api/projects/<customer>/<project_id>/messages', methods=['POST'])
def send_message(customer, project_id):
    """
    Endpoint to send a message to a project.
    Accepts customer, project_id, message content, and optional attachments.
    """
    try:
        # Parse request data
        data = request.json
        message_content = data.get('content', '')
        attachments = data.get('attachments', [])
        
        # Validate customer and project
        if not os.path.exists(os.path.join(CUSTOMERS_DIR, customer)):
            return jsonify({"error": f"Customer '{customer}' not found"}), 404
            
        project_path = get_project_path(customer, project_id)
        if not os.path.exists(project_path):
            return jsonify({"error": f"Project '{project_id}' not found for customer '{customer}'"}), 404
        
        # Store the user message in messages.json immediately
        messages_file = os.path.join(project_path, "messages.json")
        
        # Load existing messages
        if os.path.exists(messages_file):
            with open(messages_file, 'r') as f:
                messages = json.load(f)
        else:
            messages = []
        
        # Add user message
        user_message = {
            "role": "user",
            "content": message_content,
            "timestamp": datetime.datetime.now().isoformat()
        }
        messages.append(user_message)
        
        # Save updated messages with user message immediately
        with open(messages_file, 'w') as f:
            json.dump(messages, f, indent=2)
        
        # Build context (select relevant files)
        selected_files = build_context(customer, project_id, message_content, attachments)
        
        # Log the selected files
        logger.info(f"Selected files for context: {selected_files}")
        
        # Call Claude and Aider with the selected context
        try:
            # Call Claude directly for a response
            claude_response = call_claude_with_context(selected_files, project_path, message_content)
            
            # Call Aider in parallel for file updates (don't wait for response)
            import threading
            def run_aider():
                try:
                    aider_response = call_aider_with_context(project_path, selected_files, message_content)
                    logger.info("Aider processing completed")
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
            messages.append(assistant_message)
            
            # Save updated messages with assistant response
            with open(messages_file, 'w') as f:
                json.dump(messages, f, indent=2)
            
            # Return the Claude response directly in the API response
            return jsonify({
                "status": "completed",
                "message_id": str(len(messages) - 1),
                "response": claude_response
            })
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return jsonify({"error": f"Error processing message: {str(e)}"}), 500
        
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        return jsonify({"error": str(e)}), 500

def initialize_customer_templates():
    """
    Initialize customer templates by copying them from the project directory
    to the app data location if they don't exist yet.
    """
    # Path to templates in the project
    project_templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "customers")
    
    # Check if project templates directory exists
    if not os.path.exists(project_templates_dir):
        logger.warning(f"Project templates directory not found: {project_templates_dir}")
        return
    
    # Custom copy function to skip .git directory and handle permission errors
    def custom_copy_tree(src, dst):
        try:
            os.makedirs(dst, exist_ok=True)
            
            # Get list of items to copy (excluding .git)
            items_to_copy = [item for item in os.listdir(src) if item != '.git']
            
            for item in items_to_copy:
                s = os.path.join(src, item)
                d = os.path.join(dst, item)
                
                try:
                    if os.path.isdir(s):
                        custom_copy_tree(s, d)
                    else:
                        import shutil
                        shutil.copy2(s, d)
                except PermissionError:
                    logger.warning(f"Permission error copying {s} to {d}, skipping")
                except Exception as e:
                    logger.warning(f"Error copying {s} to {d}: {str(e)}, skipping")
        except Exception as e:
            logger.warning(f"Error in custom_copy_tree for {src} to {dst}: {str(e)}")
    
    # Get list of customers from project templates
    for customer in os.listdir(project_templates_dir):
        customer_dir = os.path.join(CUSTOMERS_DIR, customer)
        
        # Create customer directory if it doesn't exist
        if not os.path.exists(customer_dir):
            logger.info(f"Creating customer directory: {customer_dir}")
            os.makedirs(customer_dir, exist_ok=True)
        
        # Create projects directory if it doesn't exist
        projects_dir = os.path.join(customer_dir, "projects")
        if not os.path.exists(projects_dir):
            logger.info(f"Creating projects directory: {projects_dir}")
            os.makedirs(projects_dir, exist_ok=True)
        
        # Copy template if it doesn't exist
        customer_template_dir = os.path.join(project_templates_dir, customer, "template")
        if os.path.exists(customer_template_dir) and os.path.isdir(customer_template_dir):
            # Destination in app data
            dest_template_dir = os.path.join(customer_dir, "template")
            
            # Only copy if destination doesn't exist
            if not os.path.exists(dest_template_dir):
                logger.info(f"Copying template for customer {customer} to app data")
                # Use custom copy function instead of shutil.copytree
                custom_copy_tree(customer_template_dir, dest_template_dir)

# Initialize customer templates
initialize_customer_templates()

@app.route('/api/projects/<path:project_path>/files', methods=['GET'])
def get_project_files(project_path):
    """
    Endpoint to get a list of files in a project.
    Project path can be either:
    - customer/template
    - customer/project_id
    """
    try:
        # Parse the project path
        parts = project_path.split('/')
        if len(parts) != 2:
            return jsonify({"error": "Invalid project path format"}), 400
            
        customer, project_id = parts
        
        # Validate customer
        if not os.path.exists(os.path.join(CUSTOMERS_DIR, customer)):
            return jsonify({"error": f"Customer '{customer}' not found"}), 404
            
        # Get the full project path
        full_project_path = get_project_path(customer, project_id)
        if not os.path.exists(full_project_path):
            return jsonify({"error": f"Project '{project_id}' not found for customer '{customer}'"}), 404
        
        # Check for .gitignore file
        gitignore_path = os.path.join(full_project_path, '.gitignore')
        ignore_patterns = []
        if os.path.exists(gitignore_path):
            try:
                with open(gitignore_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            ignore_patterns.append(line)
            except Exception as e:
                logger.warning(f"Error reading .gitignore: {str(e)}")
        
        # Function to check if a file should be ignored
        def should_ignore(file_path):
            # Common version control and editor files to always ignore
            always_ignore = [
                '.git', '.svn', '.hg',           # Version control
                '.vscode', '.idea', '.vs',       # Editors
                '__pycache__', '*.pyc', '*.pyo', # Python
                '.DS_Store',                     # macOS
                '.aider*'                        # Aider files
            ]
            
            # Check against always-ignore patterns first
            for pattern in always_ignore:
                if pattern.endswith('/'):
                    # Directory pattern
                    dir_pattern = pattern[:-1]
                    if file_path == dir_pattern or file_path.startswith(f"{dir_pattern}/"):
                        return True
                elif pattern.startswith('*.'):
                    # File extension pattern
                    if file_path.endswith(pattern[1:]):
                        return True
                elif '*' in pattern:
                    # Simple wildcard pattern (e.g., .aider*)
                    prefix = pattern.split('*')[0]
                    suffix = pattern.split('*')[1]
                    if file_path.startswith(prefix) and file_path.endswith(suffix):
                        return True
                elif file_path == pattern or file_path.startswith(f"{pattern}/"):
                    # Exact match or directory
                    return True
            
            # Always include .gitignore itself
            if file_path == '.gitignore':
                return False
                
            # Then check against gitignore patterns
            for pattern in ignore_patterns:
                # Simple pattern matching (can be expanded for more complex gitignore rules)
                if pattern.endswith('/'):
                    # Directory pattern
                    dir_pattern = pattern[:-1]
                    if file_path == dir_pattern or file_path.startswith(f"{dir_pattern}/"):
                        return True
                elif pattern.startswith('*.'):
                    # File extension pattern
                    if file_path.endswith(pattern[1:]):
                        return True
                elif file_path == pattern:
                    # Exact match
                    return True
                elif pattern.startswith('**/'):
                    # Recursive wildcard
                    if file_path.endswith(pattern[3:]):
                        return True
            return False
        
        # Get list of files
        files = []
        for root, dirs, filenames in os.walk(full_project_path):
            # Filter directories to avoid walking into ignored directories
            dirs[:] = [d for d in dirs if not should_ignore(os.path.relpath(os.path.join(root, d), full_project_path))]
            
            for filename in filenames:
                file_path = os.path.join(root, filename)
                rel_path = os.path.relpath(file_path, full_project_path)
                
                # Skip ignored files
                if should_ignore(rel_path):
                    continue
                    
                files.append({
                    "path": rel_path,
                    "type": "file",
                    "last_modified": datetime.datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
                })
        
        return jsonify({"files": files})
        
    except Exception as e:
        logger.error(f"Error getting project files: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/projects/<path:project_path>/files/<path:file_path>', methods=['GET'])
def get_file_content(project_path, file_path):
    """
    Endpoint to get the content of a file.
    Project path can be either:
    - customer/template
    - customer/project_id
    """
    try:
        # Parse the project path
        parts = project_path.split('/')
        if len(parts) != 2:
            return jsonify({"error": "Invalid project path format"}), 400
            
        customer, project_id = parts
        
        # Validate customer
        if not os.path.exists(os.path.join(CUSTOMERS_DIR, customer)):
            return jsonify({"error": f"Customer '{customer}' not found"}), 404
            
        # Get the full project path
        full_project_path = get_project_path(customer, project_id)
        if not os.path.exists(full_project_path):
            return jsonify({"error": f"Project '{project_id}' not found for customer '{customer}'"}), 404
        
        # Get file content
        file_full_path = os.path.join(full_project_path, file_path)
        
        # Security check to prevent directory traversal
        if not os.path.abspath(file_full_path).startswith(os.path.abspath(full_project_path)):
            return jsonify({"error": "Invalid file path"}), 403
        
        if not os.path.exists(file_full_path) or not os.path.isfile(file_full_path):
            # For .gitignore specifically, return a 404 but with a proper content type
            # so the client can handle it gracefully
            if file_path == '.gitignore':
                return "", 404, {'Content-Type': 'text/plain; charset=utf-8'}
            return jsonify({"error": f"File '{file_path}' not found"}), 404
        
        # Read file content
        with open(file_full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Determine content type based on file extension
        extension = os.path.splitext(file_path)[1].lower()
        if extension in ['.jpg', '.jpeg', '.png', '.gif']:
            # For images, return base64 encoded data
            import base64
            with open(file_full_path, 'rb') as f:
                content = base64.b64encode(f.read()).decode('utf-8')
            return jsonify({"content": content, "type": "image"})
        else:
            # For text files, return the content directly
            return content, 200, {'Content-Type': 'text/plain; charset=utf-8'}
        
    except Exception as e:
        logger.error(f"Error getting file content: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/projects/<customer>/projects', methods=['GET'])
def get_customer_projects(customer):
    """
    Endpoint to get a list of projects for a customer.
    """
    try:
        # Validate customer
        customer_dir = os.path.join(CUSTOMERS_DIR, customer)
        if not os.path.exists(customer_dir):
            return jsonify({"error": f"Customer '{customer}' not found"}), 404
        
        # Get list of projects
        projects = ["template"]  # Always include template
        
        # Add other projects if they exist
        projects_dir = os.path.join(customer_dir, "projects")
        if os.path.exists(projects_dir):
            for project_id in os.listdir(projects_dir):
                project_path = os.path.join(projects_dir, project_id)
                if os.path.isdir(project_path):
                    projects.append(project_id)
        
        return jsonify({"projects": projects})
        
    except Exception as e:
        logger.error(f"Error getting customer projects: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/customers/<customer>/initialize', methods=['POST'])
def initialize_customer(customer):
    """
    Endpoint to manually initialize a customer.
    """
    try:
        # Path to templates in the project
        project_templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "customers")
        customer_template_dir = os.path.join(project_templates_dir, customer, "template")
        
        # Check if customer template exists in project
        if not os.path.exists(customer_template_dir) or not os.path.isdir(customer_template_dir):
            return jsonify({"error": f"Customer template '{customer}' not found in project"}), 404
        
        # Create customer directory if it doesn't exist
        customer_dir = os.path.join(CUSTOMERS_DIR, customer)
        if not os.path.exists(customer_dir):
            logger.info(f"Creating customer directory: {customer_dir}")
            os.makedirs(customer_dir, exist_ok=True)
        
        # Create projects directory if it doesn't exist
        projects_dir = os.path.join(customer_dir, "projects")
        if not os.path.exists(projects_dir):
            logger.info(f"Creating projects directory: {projects_dir}")
            os.makedirs(projects_dir, exist_ok=True)
        
        # Copy template (overwrite if exists)
        dest_template_dir = os.path.join(customer_dir, "template")
        if os.path.exists(dest_template_dir):
            import shutil
            try:
                shutil.rmtree(dest_template_dir)
            except PermissionError:
                logger.warning(f"Permission error removing {dest_template_dir}, trying to remove files individually")
                # Try to remove files individually
                for root, dirs, files in os.walk(dest_template_dir, topdown=False):
                    for name in files:
                        try:
                            os.remove(os.path.join(root, name))
                        except:
                            pass
                    for name in dirs:
                        try:
                            os.rmdir(os.path.join(root, name))
                        except:
                            pass
                try:
                    os.rmdir(dest_template_dir)
                except:
                    pass
        
        logger.info(f"Copying template for customer {customer} to app data")
        
        # Custom copy function to skip .git directory and handle permission errors
        def custom_copy_tree(src, dst):
            try:
                os.makedirs(dst, exist_ok=True)
                
                # Get list of items to copy (excluding .git)
                items_to_copy = [item for item in os.listdir(src) if item != '.git']
                
                for item in items_to_copy:
                    s = os.path.join(src, item)
                    d = os.path.join(dst, item)
                    
                    try:
                        if os.path.isdir(s):
                            custom_copy_tree(s, d)
                        else:
                            import shutil
                            shutil.copy2(s, d)
                    except PermissionError:
                        logger.warning(f"Permission error copying {s} to {d}, skipping")
                    except Exception as e:
                        logger.warning(f"Error copying {s} to {d}: {str(e)}, skipping")
            except Exception as e:
                logger.warning(f"Error in custom_copy_tree for {src} to {dst}: {str(e)}")
        
        # Use custom copy function instead of shutil.copytree
        custom_copy_tree(customer_template_dir, dest_template_dir)
        
        return jsonify({"status": "success", "message": f"Customer '{customer}' initialized"})
        
    except Exception as e:
        logger.error(f"Error initializing customer: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/projects/<customer>/<project_id>/aider_logs', methods=['GET'])
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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
