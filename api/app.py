from flask import Flask, request, jsonify
import os
import json
import logging
import anthropic
import datetime
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

# Constants
CUSTOMERS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "customers")
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
    
    # Always include these core files
    core_files = ["kinos.txt", "system.txt", "map.json"]
    
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
        
        # Build context (select relevant files)
        selected_files = build_context(customer, project_id, message_content, attachments)
        
        # For now, just log the response
        logger.info(f"Message received for {customer}/{project_id}: {message_content}")
        logger.info(f"Selected files for context: {selected_files}")
        
        # TODO: In future implementations:
        # 1. Load content of selected files
        # 2. Construct full context
        # 3. Call LLM with context and message
        # 4. Process response and update files
        # 5. Store message in messages.json
        
        return jsonify({
            "status": "processing",
            "message_id": "temp-id-123",  # Generate a real ID in the full implementation
            "selected_files": selected_files  # Just for debugging
        })
        
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
