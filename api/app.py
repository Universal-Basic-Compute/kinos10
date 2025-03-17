from flask import Flask, request, jsonify
import os
import json
import logging
import anthropic
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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
