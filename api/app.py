from flask import Flask, request, jsonify
import os
import shutil
import datetime
from flask_cors import CORS
from config import logger, CUSTOMERS_DIR
from routes.projects import projects_bp
from routes.messages import messages_bp
from routes.files import files_bp
from routes.tts import tts_bp
from routes.stt import stt_bp
from routes.debug import debug_bp
from services.file_service import initialize_customer_templates
from propagate_templates import propagate_templates

# Initialize Flask app
app = Flask(__name__)

# Configure CORS to allow requests from specific domains only
CORS(app, resources={
    r"/*": {
        "origins": [
            "http://localhost:3000",  # Keep for local development
            "http://localhost:3001",  # Keep for local development
            "https://kinos-engine.ai",
            "https://kinos10.onrender.com",
            "https://fictra-portal.vercel.app",
            "https://therapykin.ai",
            "https://www.therapykin.ai",
            "https://stridecoaching.ai", 
            "https://www.stridecoaching.ai",
            "https://duogaming.ai",
            "https://www.duogaming.ai",
            "https://konginvest.ai",
            "https://www.konginvest.ai"
        ]
    }
})

@app.before_request
def check_origin():
    """Check if the request origin is allowed."""
    origin = request.headers.get('Origin')
    if origin:
        allowed_origins = [
            "http://localhost:3000",
            "http://localhost:3001",
            "https://kinos-engine.ai",
            "https://kinos10.onrender.com",
            "https://fictra-portal.vercel.app",
            "https://therapykin.ai",
            "https://www.therapykin.ai",
            "https://stridecoaching.ai",
            "https://www.stridecoaching.ai",
            "https://duogaming.ai",
            "https://www.duogaming.ai",
            "https://konginvest.ai",
            "https://www.konginvest.ai"
        ]
        if origin not in allowed_origins:
            logger.warning(f"Blocked request from unauthorized origin: {origin}")
            return jsonify({"error": "Unauthorized origin"}), 403

@app.before_request
def verify_api_key():
    """Verify API key for all requests except health check and root endpoint."""
    # Skip verification for health check, root endpoint, and API documentation
    if request.path == '/health' or request.path == '/' or request.path == '/debug-api/debug':
        return None
        
    # Get API key from header or query parameter
    api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
    
    # Check if API key is valid
    if not api_key or api_key != API_KEY:
        logger.warning(f"Unauthorized access attempt from {request.remote_addr} to {request.path}")
        return jsonify({"error": "Unauthorized access"}), 401

@app.before_request
def log_request_info():
    """Log details about each request."""
    logger.info(f"Request: {request.method} {request.path} from {request.remote_addr}")

@app.after_request
def log_response_info(response):
    """Log details about each response."""
    logger.info(f"Response: {response.status_code}")
    return response

# Register blueprints in a specific order
app.register_blueprint(projects_bp)
app.register_blueprint(messages_bp)
app.register_blueprint(files_bp)
app.register_blueprint(tts_bp)
app.register_blueprint(stt_bp)
# Register debug_bp last with a url_prefix to avoid conflicts
app.register_blueprint(debug_bp, url_prefix='/debug-api')

@app.route('/', methods=['GET'])
def api_root():
    """
    Root endpoint that returns the API reference documentation.
    Note: This endpoint is exempt from API key verification.
    """
    # Check if the client wants HTML or JSON
    accept_header = request.headers.get('Accept', '')
    
    # If the client specifically wants JSON, return the old response
    if 'application/json' in accept_header and 'text/html' not in accept_header:
        return jsonify({
            "status": "running",
            "message": "KinOS API is running",
            "version": "1.0.0",
            "endpoints": {
                "health": "/health",
                "projects": "/projects",
                "messages": "/projects/{customer}/{project_id}/messages",
                "files": "/projects/{customer}/{project_id}/files"
            }
        }), 200
    
    # Otherwise, return the API reference documentation as HTML
    try:
        # Path to the API reference markdown file
        api_ref_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                   "customers", "kinos", "template", "sources", "api_reference.md")
        
        # Check if the file exists
        if not os.path.exists(api_ref_path):
            logger.warning(f"API reference file not found at {api_ref_path}")
            return jsonify({"error": "API reference documentation not found"}), 404
        
        # Read the markdown content
        with open(api_ref_path, 'r', encoding='utf-8') as f:
            markdown_content = f.read()
        
        # Convert markdown to HTML
        try:
            import markdown
            html_content = markdown.markdown(markdown_content)
        except ImportError:
            # If markdown package is not available, use a simple HTML wrapper
            html_content = f"<pre>{markdown_content}</pre>"
        
        # Wrap in a basic HTML document with some styling
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>KinOS API Reference</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 1000px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                pre {{
                    background-color: #f5f5f5;
                    padding: 10px;
                    border-radius: 5px;
                    overflow-x: auto;
                }}
                code {{
                    background-color: #f5f5f5;
                    padding: 2px 4px;
                    border-radius: 3px;
                }}
                h1, h2, h3 {{
                    margin-top: 1.5em;
                }}
                h1 {{
                    border-bottom: 1px solid #ddd;
                    padding-bottom: 10px;
                }}
                h2 {{
                    border-bottom: 1px solid #eee;
                    padding-bottom: 5px;
                }}
            </style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """
        
        return html, 200, {'Content-Type': 'text/html; charset=utf-8'}
    
    except Exception as e:
        logger.error(f"Error serving API reference: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for Render.
    Note: This endpoint is exempt from API key verification.
    """
    # Include more information in the health check response
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.datetime.now().isoformat(),
        "environment": os.environ.get('ENVIRONMENT', 'development'),
        "website_url": os.environ.get('WEBSITE_URL', 'not set')
    }), 200

@app.route('/<path:undefined_route>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def global_catch_all(undefined_route):
    """Global catch-all route for undefined API endpoints."""
    # Skip if the route starts with 'projects/' as those should be handled by other blueprints
    if undefined_route.startswith('projects/'):
        return jsonify({
            "error": "Not Found",
            "message": f"The project endpoint '/{undefined_route}' does not exist.",
            "documentation_url": "http://api.kinos-engine.ai"
        }), 404
        
    logger.warning(f"Undefined API route accessed: {undefined_route}")
    return jsonify({
        "error": "Not Found",
        "message": f"The requested endpoint '/{undefined_route}' does not exist.",
        "documentation_url": "http://api.kinos-engine.ai"
    }), 404

# Initialize customer templates
initialize_customer_templates()

# Propagate template changes to all projects
logger.info("Propagating template changes to all projects")
try:
    propagate_templates(dry_run=False)
    logger.info("Template propagation completed successfully")
except Exception as e:
    logger.error(f"Error during template propagation: {str(e)}")

# Initialize all customer templates automatically
logger.info("Checking for customer templates to initialize")
project_templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "customers")

if os.path.exists(project_templates_dir):
    # Get list of all customers in the project directory
    available_customers = [d for d in os.listdir(project_templates_dir) 
                          if os.path.isdir(os.path.join(project_templates_dir, d))]
    logger.info(f"Found customers in project directory: {available_customers}")
    
    # Log the current environment for debugging
    logger.info(f"Current environment: {os.environ.get('ENVIRONMENT', 'not set')}")
    logger.info(f"Website URL: {os.environ.get('WEBSITE_URL', 'not set')}")
    
    # Check each customer and initialize if needed
    for customer in available_customers:
        customer_template = os.path.join(CUSTOMERS_DIR, customer, "template")
        if not os.path.exists(customer_template) or not os.listdir(customer_template):
            logger.warning(f"{customer} template not found or empty, attempting to initialize")
            
            # Source template in project
            project_customer_template = os.path.join(project_templates_dir, customer, "template")
            
            if os.path.exists(project_customer_template):
                # Create customer directory if needed
                customer_dir = os.path.join(CUSTOMERS_DIR, customer)
                os.makedirs(customer_dir, exist_ok=True)
                
                # Create projects directory if needed
                customer_projects_dir = os.path.join(customer_dir, "projects")
                os.makedirs(customer_projects_dir, exist_ok=True)
                
                # Copy template
                if os.path.exists(customer_template):
                    shutil.rmtree(customer_template)
                
                logger.info(f"Copying {customer} template from {project_customer_template} to {customer_template}")
                shutil.copytree(project_customer_template, customer_template)
                
                # Verify template was copied
                if os.path.exists(customer_template):
                    template_files = os.listdir(customer_template)
                    logger.info(f"{customer} template files: {template_files}")
            else:
                logger.error(f"{customer} template not found in project directory")
else:
    logger.error(f"Project templates directory not found: {project_templates_dir}")

if __name__ == '__main__':
    # Get port from environment variable (for Render compatibility)
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
