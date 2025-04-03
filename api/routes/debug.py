from flask import Blueprint, request, jsonify
import os
import json
import sys
import platform
import socket
import requests
import datetime
from config import get_app_data_dir, blueprintS_DIR, logger

debug_bp = Blueprint('debug', __name__)

@debug_bp.route('/debug', methods=['GET'])
def api_debug():
    """
    Debug endpoint that returns detailed information about the API server.
    Note: This endpoint is exempt from API key verification for diagnostic purposes.
    """
    try:
        # Get basic system information
        # Get network information
        hostname = socket.gethostname()
        try:
            local_ip = socket.gethostbyname(hostname)
        except:
            local_ip = "Unable to determine local IP"
        
        # Get environment variables (filtering out sensitive ones)
        env_vars = {}
        sensitive_keys = ['ANTHROPIC_API_KEY', 'ELEVENLABS_API_KEY', 'SECRET_KEY']
        for key, value in os.environ.items():
            if any(sensitive in key.upper() for sensitive in sensitive_keys):
                env_vars[key] = "***REDACTED***"
            else:
                env_vars[key] = value
        
        # Get directory information
        app_data_dir = get_app_data_dir()
        
        # Check if blueprints directory exists and list contents
        blueprints_info = {}
        if os.path.exists(blueprintS_DIR):
            for blueprint in os.listdir(blueprintS_DIR):
                blueprint_path = os.path.join(blueprintS_DIR, blueprint)
                if os.path.isdir(blueprint_path):
                    # Get template info
                    template_path = os.path.join(blueprint_path, "template")
                    template_exists = os.path.exists(template_path)
                    template_files = os.listdir(template_path) if template_exists else []
                    
                    # Get kins info
                    kins_path = os.path.join(blueprint_path, "kins")
                    kins_exists = os.path.exists(kins_path)
                    kins = os.listdir(kins_path) if kins_exists else []
                    
                    blueprints_info[blueprint] = {
                        "template_exists": template_exists,
                        "template_files": template_files,
                        "kins_exists": kins_exists,
                        "kins": kins
                    }
        
        # Test connection to website
        website_url = os.environ.get('WEBSITE_URL', 'https://kinos10.onrender.com')
        website_status = "Unknown"
        website_message = ""
        try:
            website_response = requests.get(f"{website_url}/health", timeout=5)
            if website_response.ok:
                website_status = "Connected"
                website_message = f"Successfully connected to website, status: {website_response.status_code}"
            else:
                website_status = "Error"
                website_message = f"Website returned status code {website_response.status_code}"
        except requests.RequestException as e:
            website_status = "Error"
            website_message = f"Failed to connect to website: {str(e)}"
        
        # Compile all debug information
        debug_info = {
            "status": "running",
            "timestamp": datetime.datetime.now().isoformat(),
            "system_info": {
                "python_version": sys.version,
                "platform": platform.platform(),
                "hostname": hostname,
                "local_ip": local_ip
            },
            "environment": {
                "app_data_dir": app_data_dir,
                "blueprints_dir": blueprintS_DIR,
                "blueprints_dir_exists": os.path.exists(blueprintS_DIR),
                "env_vars": env_vars
            },
            "blueprints": blueprints_info,
            "website_connection": {
                "url": website_url,
                "status": website_status,
                "message": website_message
            },
            "request_info": {
                "method": request.method,
                "url": request.url,
                "headers": {k: v for k, v in request.headers.items()},
                "remote_addr": request.remote_addr
            }
        }
        
        # Check if the client wants HTML or JSON
        accept_header = request.headers.get('Accept', '')
        
        # If the client specifically wants JSON, return JSON
        if 'application/json' in accept_header and 'text/html' not in accept_header:
            return jsonify(debug_info), 200
        
        # Otherwise, return HTML for better readability in browser
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>KinOS API Debug Information</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
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
                pre {{
                    background-color: #f5f5f5;
                    padding: 10px;
                    border-radius: 5px;
                    overflow-x: auto;
                }}
                .section {{
                    margin-bottom: 30px;
                    padding: 15px;
                    border: 1px solid #ddd;
                    border-radius: 5px;
                }}
                .success {{
                    color: green;
                }}
                .error {{
                    color: red;
                }}
            </style>
        </head>
        <body>
            <h1>KinOS API Debug Information</h1>
            <p>Generated at: {debug_info['timestamp']}</p>
            
            <div class="section">
                <h2>System Information</h2>
                <p><strong>Python Version:</strong> {debug_info['system_info']['python_version']}</p>
                <p><strong>Platform:</strong> {debug_info['system_info']['platform']}</p>
                <p><strong>Hostname:</strong> {debug_info['system_info']['hostname']}</p>
                <p><strong>Local IP:</strong> {debug_info['system_info']['local_ip']}</p>
            </div>
            
            <div class="section">
                <h2>Environment</h2>
                <p><strong>App Data Directory:</strong> {debug_info['environment']['app_data_dir']}</p>
                <p><strong>blueprints Directory:</strong> {debug_info['environment']['blueprints_dir']}</p>
                <p><strong>blueprints Directory Exists:</strong> {debug_info['environment']['blueprints_dir_exists']}</p>
                
                <h3>Environment Variables</h3>
                <pre>{json.dumps(debug_info['environment']['env_vars'], indent=2)}</pre>
            </div>
            
            <div class="section">
                <h2>blueprints</h2>
                <pre>{json.dumps(debug_info['blueprints'], indent=2)}</pre>
            </div>
            
            <div class="section">
                <h2>Website Connection</h2>
                <p><strong>URL:</strong> {debug_info['website_connection']['url']}</p>
                <p><strong>Status:</strong> <span class="{'success' if debug_info['website_connection']['status'] == 'Connected' else 'error'}">{debug_info['website_connection']['status']}</span></p>
                <p><strong>Message:</strong> {debug_info['website_connection']['message']}</p>
            </div>
            
            <div class="section">
                <h2>Request Information</h2>
                <p><strong>Method:</strong> {debug_info['request_info']['method']}</p>
                <p><strong>URL:</strong> {debug_info['request_info']['url']}</p>
                <p><strong>Remote Address:</strong> {debug_info['request_info']['remote_addr']}</p>
                
                <h3>Headers</h3>
                <pre>{json.dumps(dict(debug_info['request_info']['headers']), indent=2)}</pre>
            </div>
        </body>
        </html>
        """
        
        return html, 200, {'Content-Type': 'text/html; charset=utf-8'}
        
    except Exception as e:
        logger.error(f"Error in debug endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Root and health endpoints moved to app.py

@debug_bp.route('/initialize-blueprint/<blueprint>', methods=['GET'])
def initialize_specific_blueprint(blueprint):
    """
    Debug endpoint to manually initialize a specific blueprint.
    """
    try:
        # Path to templates in the kin
        kin_templates_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "blueprints")
        blueprint_template_dir = os.path.join(kin_templates_dir, blueprint, "template")
        
        # Check if blueprint template exists in kin
        if not os.path.exists(blueprint_template_dir) or not os.path.isdir(blueprint_template_dir):
            return jsonify({"error": f"blueprint template '{blueprint}' not found in kin"}), 404
        
        # Create blueprint directory if it doesn't exist
        blueprint_dir = os.path.join(blueprintS_DIR, blueprint)
        if not os.path.exists(blueprint_dir):
            logger.info(f"Creating blueprint directory: {blueprint_dir}")
            os.makedirs(blueprint_dir, exist_ok=True)
        
        # Create kins directory if it doesn't exist
        kins_dir = os.path.join(blueprint_dir, "kins")
        if not os.path.exists(kins_dir):
            logger.info(f"Creating kins directory: {kins_dir}")
            os.makedirs(kins_dir, exist_ok=True)
        
        # Copy template (overwrite if exists)
        dest_template_dir = os.path.join(blueprint_dir, "template")
        if os.path.exists(dest_template_dir):
            import shutil
            shutil.rmtree(dest_template_dir)
        
        logger.info(f"Copying template for blueprint {blueprint} to app data")
        import shutil
        shutil.copytree(blueprint_template_dir, dest_template_dir)
        
        # Verify template was copied
        if os.path.exists(dest_template_dir):
            template_files = os.listdir(dest_template_dir)
            logger.info(f"Template files for {blueprint}: {template_files}")
            return jsonify({
                "status": "success", 
                "message": f"blueprint '{blueprint}' initialized",
                "files": template_files
            })
        else:
            return jsonify({"error": "Failed to copy template"}), 500
        
    except Exception as e:
        logger.error(f"Error initializing blueprint: {str(e)}")
        return jsonify({"error": str(e)}), 500

@debug_bp.route('/<path:undefined_route>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def catch_all_api(undefined_route):
    """Catch-all route for undefined API endpoints within the debug-api prefix."""
    logger.warning(f"Undefined debug API route accessed: {undefined_route}")
    return jsonify({
        "error": "Not Found",
        "message": f"The requested debug endpoint '/{undefined_route}' does not exist.",
        "documentation_url": "https://api.kinos-engine.ai"
    }), 404
