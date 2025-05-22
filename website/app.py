from flask import Flask, render_template, send_from_directory, request, Response, jsonify
import datetime
import os
import requests
import json
import markdown

app = Flask(__name__, static_folder='static', template_folder='templates', static_url_path='')

@app.route('/')
def index():
    """Serve the v2 API reference as the main documentation"""
    try:
        # Path to the v2 API reference markdown file
        api_ref_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                   'blueprints', 'kinos', 'template', 'sources', 
                                   'api_reference_v2.md')
        
        # Check if the file exists
        if not os.path.exists(api_ref_path):
            return render_template('index.html', now=datetime.datetime.now())
        
        # Read the markdown content
        with open(api_ref_path, 'r', encoding='utf-8') as f:
            md_content = f.read()
        
        # Convert markdown to HTML
        html_content = markdown.markdown(md_content, extensions=['fenced_code', 'tables'])
        
        # Render the documentation template with the HTML content
        return render_template('documentation.html', 
                              title="KinOS API Reference v2",
                              content=html_content)
    except Exception as e:
        print(f"Error serving API documentation: {str(e)}")
        # Fall back to the original index page if there's an error
        return render_template('index.html', now=datetime.datetime.now())

@app.route('/v1')
def api_v1_docs():
    """Serve the v1 API reference documentation"""
    try:
        # Path to the v1 API reference markdown file
        api_ref_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                   'blueprints', 'kinos', 'template', 'sources', 
                                   'api_reference.md')
        
        # Check if the file exists
        if not os.path.exists(api_ref_path):
            return render_template('error.html', 
                                  message="API v1 reference documentation not found"), 404
        
        # Read the markdown content
        with open(api_ref_path, 'r', encoding='utf-8') as f:
            md_content = f.read()
        
        # Convert markdown to HTML
        html_content = markdown.markdown(md_content, extensions=['fenced_code', 'tables'])
        
        # Render the documentation template with the HTML content
        return render_template('documentation.html', 
                              title="KinOS API Reference v1 (Legacy)",
                              content=html_content)
    except Exception as e:
        print(f"Error serving API v1 documentation: {str(e)}")
        return render_template('error.html', 
                              message=f"Error loading API v1 documentation: {str(e)}"), 500

@app.route('/kins')
def kins():
    # Fetch real kins from the API
    api_url = os.environ.get('API_URL', 'http://localhost:5000')
    try:
        response = requests.get(f"{api_url}/kins/all")
        if response.ok:
            data = response.json()
            blueprints = data.get('blueprints', [])
            kins = data.get('kins', {})
        else:
            # Fallback to empty data if API call fails
            blueprints = []
            kins = {}
    except requests.RequestException:
        # Fallback to empty data if API call fails
        blueprints = []
        kins = {}
    
    return render_template('kins.html', 
                          blueprints=blueprints, 
                          kins=kins, 
                          now=datetime.datetime.now())

@app.route('/kins/<blueprint>/<kin>')
def kin_detail(blueprint, kin):
    # Fetch real kins from the API
    api_url = os.environ.get('API_URL', 'http://localhost:5000')
    try:
        response = requests.get(f"{api_url}/kins/all")
        if response.ok:
            data = response.json()
            blueprints = data.get('blueprints', [])
            kins = data.get('kins', {})
        else:
            # Fallback to empty data if API call fails
            blueprints = []
            kins = {}
    except requests.RequestException:
        # Fallback to empty data if API call fails
        blueprints = []
        kins = {}
    
    return render_template('kins.html', 
                          blueprints=blueprints, 
                          kins=kins,
                          selected_blueprint=blueprint,
                          selected_kin=kin,
                          now=datetime.datetime.now())

@app.route('/health')
def health():
    return 'OK', 200

@app.route('/website-debug', methods=['GET'])
def website_debug():
    """Debug endpoint that returns detailed information about the website server."""
    try:
        # Get basic system information
        import sys
        import platform
        import socket
        
        # Get network information
        hostname = socket.gethostname()
        try:
            local_ip = socket.gethostbyname(hostname)
        except:
            local_ip = "Unable to determine local IP"
        
        # Get environment variables (filtering out sensitive ones)
        env_vars = {}
        # More comprehensive list of sensitive key patterns
        sensitive_patterns = ['KEY', 'SECRET', 'TOKEN', 'PASSWORD', 'PASS', 'AUTH', 'CREDENTIAL']
        for key, value in os.environ.items():
            if any(pattern in key.upper() for pattern in sensitive_patterns):
                env_vars[key] = "***REDACTED***"
            else:
                env_vars[key] = value
        
        # Test connection to API
        api_url = os.environ.get('API_URL', 'http://localhost:5000')
        api_status = "Unknown"
        api_message = ""
        try:
            api_response = requests.get(f"{api_url}/health", timeout=5)
            if api_response.ok:
                api_status = "Connected"
                api_message = f"Successfully connected to API, status: {api_response.status_code}"
            else:
                api_status = "Error"
                api_message = f"API returned status code {api_response.status_code}"
        except requests.RequestException as e:
            api_status = "Error"
            api_message = f"Failed to connect to API: {str(e)}"
        
        # Test API kins endpoint
        kins_status = "Unknown"
        kins_message = ""
        try:
            kins_response = requests.get(f"{api_url}/kins/all", timeout=5)
            if kins_response.ok:
                kins_status = "Connected"
                kins_message = f"Successfully connected to kins endpoint"
                kins_data = kins_response.json()
            else:
                kins_status = "Error"
                kins_message = f"kins endpoint returned status code {kins_response.status_code}"
                kins_data = {}
        except requests.RequestException as e:
            kins_status = "Error"
            kins_message = f"Failed to connect to kins endpoint: {str(e)}"
            kins_data = {}
        
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
                "env_vars": env_vars,
                "static_folder": app.static_folder,
                "template_folder": app.template_folder,
                "static_files": os.listdir(app.static_folder) if os.path.exists(app.static_folder) else [],
                "template_files": os.listdir(app.template_folder) if os.path.exists(app.template_folder) else [],
                "css_files": os.listdir(os.path.join(app.static_folder, 'css')) if os.path.exists(os.path.join(app.static_folder, 'css')) else []
            },
            "api_connection": {
                "url": api_url,
                "status": api_status,
                "message": api_message
            },
            "kins_endpoint": {
                "url": f"{api_url}/kins/all",
                "status": kins_status,
                "message": kins_message,
                "data": kins_data
            },
            "request_info": {
                "method": request.method,
                "url": request.url,
                "headers": {k: v for k, v in request.headers.items()},
                "remote_addr": request.remote_addr
            }
        }
        
        # Return HTML for better readability in browser
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>KinOS Website Debug Information</title>
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
            <h1>KinOS Website Debug Information</h1>
            <p style="color: red; font-weight: bold;">WARNING: This debug endpoint exposes system information and should NOT be enabled in production environments!</p>
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
                <p><strong>Static Folder:</strong> {debug_info['environment']['static_folder']}</p>
                <p><strong>Template Folder:</strong> {debug_info['environment']['template_folder']}</p>
                
                <h3>Static Files</h3>
                <pre>{json.dumps(debug_info['environment']['static_files'], indent=2)}</pre>
                
                <h3>Template Files</h3>
                <pre>{json.dumps(debug_info['environment']['template_files'], indent=2)}</pre>
                
                <h3>CSS Files</h3>
                <pre>{json.dumps(debug_info['environment']['css_files'], indent=2)}</pre>
                
                <h3>Environment Variables</h3>
                <pre>{json.dumps(debug_info['environment']['env_vars'], indent=2)}</pre>
            </div>
            
            <div class="section">
                <h2>API Connection</h2>
                <p><strong>URL:</strong> {debug_info['api_connection']['url']}</p>
                <p><strong>Status:</strong> <span class="{'success' if debug_info['api_connection']['status'] == 'Connected' else 'error'}">{debug_info['api_connection']['status']}</span></p>
                <p><strong>Message:</strong> {debug_info['api_connection']['message']}</p>
            </div>
            
            <div class="section">
                <h2>kins Endpoint</h2>
                <p><strong>URL:</strong> {debug_info['kins_endpoint']['url']}</p>
                <p><strong>Status:</strong> <span class="{'success' if debug_info['kins_endpoint']['status'] == 'Connected' else 'error'}">{debug_info['kins_endpoint']['status']}</span></p>
                <p><strong>Message:</strong> {debug_info['kins_endpoint']['message']}</p>
                
                <h3>Data</h3>
                <pre>{json.dumps(debug_info['kins_endpoint']['data'], indent=2)}</pre>
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
        print(f"Error in debug endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/debug')
def debug():
    """Debug endpoint to check if the app is running"""
    static_files = os.listdir(os.path.join(app.static_folder))
    template_files = os.listdir(os.path.join(app.template_folder))
    
    # Check if CSS file exists
    css_path = os.path.join(app.static_folder, 'css', 'styles.css')
    css_exists = os.path.exists(css_path)
    
    return {
        'status': 'running',
        'static_files': static_files,
        'template_files': template_files,
        'static_folder': app.static_folder,
        'template_folder': app.template_folder,
        'css_file_exists': css_exists,
        'css_path': css_path
    }

@app.route('/debug-info')
def debug_info():
    """Debug endpoint to show detailed environment information"""
    import sys
    import platform
    
    debug_info = {
        'python_version': sys.version,
        'platform': platform.platform(),
        'environment': dict(os.environ),
        'working_directory': os.getcwd(),
        'static_folder': app.static_folder,
        'template_folder': app.template_folder,
        'static_files': os.listdir(app.static_folder) if os.path.exists(app.static_folder) else [],
        'template_files': os.listdir(app.template_folder) if os.path.exists(app.template_folder) else [],
        'css_files': os.listdir(os.path.join(app.static_folder, 'css')) if os.path.exists(os.path.join(app.static_folder, 'css')) else []
    }
    
    # Return as formatted HTML
    html = "<h1>Debug Information</h1>"
    html += "<p style='color: red; font-weight: bold;'>WARNING: This debug endpoint exposes system information and should NOT be enabled in production environments!</p>"
    for key, value in debug_info.items():
        if key == 'environment':
            html += f"<h2>{key}</h2><ul>"
            for env_key, env_value in value.items():
                html += f"<li><strong>{env_key}</strong>: {env_value}</li>"
            html += "</ul>"
        elif isinstance(value, list):
            html += f"<h2>{key}</h2><ul>"
            for item in value:
                html += f"<li>{item}</li>"
            html += "</ul>"
        else:
            html += f"<h2>{key}</h2><p>{value}</p>"
    
    return html

@app.route('/test')
def test():
    """Simple test endpoint to verify the app is running"""
    return "Website is running!", 200

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Explicitly serve static files"""
    return send_from_directory(app.static_folder, filename)

@app.route('/css-test')
def css_test():
    """Test endpoint to directly serve the CSS file"""
    return send_from_directory(os.path.join(app.static_folder, 'css'), 'styles.css')

@app.route('/api/kins/<path:kin_path>/files/<path:file_path>')
def get_kin_file(kin_path, file_path):
    """Proxy API requests for specific kin files"""
    # API server URL (adjust as needed)
    api_url = os.environ.get('API_URL', 'http://localhost:5000')
    
    # Forward the request to the API server
    url = f"{api_url}/kins/{kin_path}/files/{file_path}"
    
    try:
        # Forward the request
        resp = requests.request(
            method=request.method,
            url=url,
            headers={key: value for key, value in request.headers if key != 'Host'},
            cookies=request.cookies,
            allow_redirects=False,
            params=request.args
        )
        
        # Create a Flask response object
        response = Response(
            resp.content,
            resp.status_code,
            {key: value for key, value in resp.headers.items() if key != 'Content-Length'}
        )
        
        return response
    except requests.RequestException as e:
        # Log the error and return a friendly error response
        print(f"API proxy error: {str(e)}")
        return jsonify({"error": "Failed to connect to API server"}), 500

# Route removed to eliminate proxy calls

@app.route('/api', methods=['GET'])
def api_test():
    """Test endpoint to verify API routes are working"""
    # Get the API URL from environment or use default
    api_url = os.environ.get('API_URL', 'https://kinos.onrender.com')
    
    # Test if we can connect to the API server
    api_status = "Unknown"
    api_message = ""
    try:
        response = requests.get(f"{api_url}/health", timeout=5)
        if response.ok:
            api_status = "Connected"
            api_message = "Successfully connected to API server"
        else:
            api_status = "Error"
            api_message = f"API server returned status code {response.status_code}"
    except requests.RequestException as e:
        api_status = "Error"
        api_message = f"Failed to connect to API server: {str(e)}"
    
    # Check if the kins endpoint is working
    kins_status = "Unknown"
    kins_message = ""
    try:
        response = requests.get(f"{api_url}/kins/all", timeout=5)
        if response.ok:
            kins_status = "Working"
            kins_message = "kins endpoint is working"
            kins_data = response.json()
        else:
            kins_status = "Error"
            kins_message = f"kins endpoint returned status code {response.status_code}"
            kins_data = {}
    except requests.RequestException as e:
        kins_status = "Error"
        kins_message = f"Failed to connect to kins endpoint: {str(e)}"
        kins_data = {}
    
    return jsonify({
        "status": "OK",
        "message": "API routes diagnostic information",
        "api_server": {
            "url": api_url,
            "status": api_status,
            "message": api_message
        },
        "endpoints": {
            "/api/kins/all": {
                "status": kins_status,
                "message": kins_message,
                "data": kins_data if kins_status == "Working" else None
            },
            "/api/kins/<blueprint>/<kin>/files": "Get files for a specific kin",
            "/api/health": "Health check endpoint"
        },
        "environment": {
            "API_URL": os.environ.get('API_URL', 'http://localhost:5000'),
            "FLASK_ENV": os.environ.get('FLASK_ENV', 'development'),
            "PORT": os.environ.get('PORT', '5001')
        },
        "request_info": {
            "host": request.host,
            "path": request.path,
            "url": request.url,
            "headers": dict(request.headers)
        }
    })

@app.route('/check-templates')
def check_templates():
    """Check if the templates directory exists and what templates are available"""
    template_dir = app.template_folder
    templates = []
    
    if os.path.exists(template_dir):
        templates = os.listdir(template_dir)
    
    return jsonify({
        "template_dir": template_dir,
        "exists": os.path.exists(template_dir),
        "templates": templates
    })

@app.route('/check-api-docs')
def check_api_docs():
    """Check if the API reference files exist"""
    base_dir = os.path.dirname(os.path.dirname(__file__))
    v1_path = os.path.join(base_dir, 'blueprints', 'kinos', 'template', 'sources', 'api_reference.md')
    v2_path = os.path.join(base_dir, 'blueprints', 'kinos', 'template', 'sources', 'api_reference_v2.md')
    
    return jsonify({
        "base_dir": base_dir,
        "v1_path": v1_path,
        "v1_exists": os.path.exists(v1_path),
        "v2_path": v2_path,
        "v2_exists": os.path.exists(v2_path)
    })

@app.route('/api/chat', methods=['POST'])
def chat():
    """API endpoint for the chat widget that uses KinOS API v2"""
    try:
        data = request.json
        user_message = data.get('message', '')
        blueprint = data.get('blueprint', 'kinos')  # Default to 'kinos'
        kin_id = data.get('kin_id', 'builder')      # Default to 'builder'
        
        # KinOS API v2 endpoint
        kinos_api_url = "https://api.kinos-engine.ai/v2"
        
        # Prepare the request to KinOS API v2
        kinos_request = {
            "content": user_message,
            "model": "claude-sonnet-4-20250514",  # Or your preferred model
            "mode": "helpful",  # Or another appropriate mode
            "addSystem": "You are the KinOS website assistant. Provide helpful, concise information about KinOS features, capabilities, and use cases. Be friendly and professional."
        }
        
        # Call the KinOS API
        try:
            response = requests.post(
                f"{kinos_api_url}/blueprints/{blueprint}/kins/{kin_id}/messages",
                json=kinos_request,
                headers={
                    "Authorization": f"Bearer {os.environ.get('KINOS_API_KEY', '')}"
                }
            )
            
            if response.ok:
                ai_response = response.json().get("response", "")
                return jsonify({"response": ai_response})
            else:
                # Fallback to simple responses if API call fails
                print(f"KinOS API error: {response.status_code} - {response.text}")
                return jsonify({"response": get_fallback_response(user_message)})
                
        except requests.RequestException as e:
            print(f"Error calling KinOS API: {str(e)}")
            return jsonify({"response": get_fallback_response(user_message)})
        
    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        return jsonify({"response": "I'm sorry, I encountered an error processing your request."}), 500

def get_fallback_response(message):
    """Provide fallback responses when the API is unavailable"""
    message = message.lower()
    
    if 'hello' in message or 'hi' in message:
        return "Hello! How can I assist you with KinOS today?"
    elif 'feature' in message or 'capabilities' in message:
        return "KinOS offers persistent context management, adaptive mode switching, file system integration, long-term memory, and multi-modal support. Which feature would you like to know more about?"
    elif 'pricing' in message or 'cost' in message:
        return "For pricing information, please contact our sales team through the contact form. We offer customized pricing based on your specific needs and scale."
    elif 'documentation' in message or 'docs' in message:
        return "You can find our documentation by clicking on the 'Documentation' link in the footer. It includes API references, integration guides, and examples."
    elif 'contact' in message or 'support' in message:
        return "You can reach our support team through the contact form on this page. Just scroll down to the 'Contact Us' section."
    else:
        return "Thank you for your message. To provide you with the most accurate information, could you please specify what aspect of KinOS you're interested in learning more about?"

@app.route('/api/kins/all')
def get_all_kins():
    """API endpoint to get all blueprints and their kins"""
    # API server URL (adjust as needed)
    api_url = os.environ.get('API_URL', 'https://kinos.onrender.com')
    
    try:
        # Forward the request to the API server
        response = requests.get(f"{api_url}/kins/all")
        
        if response.ok:
            return response.json()
        else:
            return jsonify({
                "error": f"API server returned status code {response.status_code}",
                "message": response.text
            }), response.status_code
    except requests.RequestException as e:
        # Log the error and return a friendly error response
        print(f"API proxy error: {str(e)}")
        return jsonify({
            "error": "Failed to connect to API server",
            "blueprints": [],
            "kins": {}
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))  # Change default from 5000 to 5001
    app.run(debug=False, host='0.0.0.0', port=port)
