from flask import Flask, request
import os
import shutil
from config import logger, CUSTOMERS_DIR
from routes.projects import projects_bp
from routes.messages import messages_bp
from routes.files import files_bp
from routes.tts import tts_bp
from routes.debug import debug_bp
from services.file_service import initialize_customer_templates

# Initialize Flask app
app = Flask(__name__)

@app.before_request
def log_request_info():
    """Log details about each request."""
    logger.info(f"Request: {request.method} {request.path} from {request.remote_addr}")

@app.after_request
def log_response_info(response):
    """Log details about each response."""
    logger.info(f"Response: {response.status_code}")
    return response

# Register blueprints
app.register_blueprint(projects_bp)
app.register_blueprint(messages_bp)
app.register_blueprint(files_bp)
app.register_blueprint(tts_bp)
app.register_blueprint(debug_bp)

# Initialize customer templates
initialize_customer_templates()

# Specifically check for duogaming customer
duogaming_template = os.path.join(CUSTOMERS_DIR, "duogaming", "template")
if not os.path.exists(duogaming_template) or not os.listdir(duogaming_template):
    logger.warning("DuoGaming template not found or empty, attempting to initialize specifically")
    
    # Source template in project
    project_duogaming_template = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                             "customers", "duogaming", "template")
    
    if os.path.exists(project_duogaming_template):
        # Create customer directory if needed
        duogaming_dir = os.path.join(CUSTOMERS_DIR, "duogaming")
        os.makedirs(duogaming_dir, exist_ok=True)
        
        # Create projects directory if needed
        duogaming_projects_dir = os.path.join(duogaming_dir, "projects")
        os.makedirs(duogaming_projects_dir, exist_ok=True)
        
        # Copy template
        if os.path.exists(duogaming_template):
            shutil.rmtree(duogaming_template)
        
        logger.info(f"Copying DuoGaming template from {project_duogaming_template} to {duogaming_template}")
        shutil.copytree(project_duogaming_template, duogaming_template)
        
        # Verify template was copied
        if os.path.exists(duogaming_template):
            template_files = os.listdir(duogaming_template)
            logger.info(f"DuoGaming template files: {template_files}")
    else:
        logger.error("DuoGaming template not found in project directory")

if __name__ == '__main__':
    # Get port from environment variable (for Render compatibility)
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
