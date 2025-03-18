from flask import Flask, render_template, send_from_directory, request, Response, jsonify
import datetime
import os
import requests
import json

app = Flask(__name__, static_folder='static', template_folder='templates', static_url_path='')

@app.route('/')
def index():
    return render_template('index.html', now=datetime.datetime.now())

@app.route('/projects')
def projects():
    # Fetch real projects from the API
    api_url = os.environ.get('API_URL', 'http://localhost:5000')
    try:
        response = requests.get(f"{api_url}/api/projects/all")
        if response.ok:
            data = response.json()
            customers = data.get('customers', [])
            projects = data.get('projects', {})
        else:
            # Fallback to empty data if API call fails
            customers = []
            projects = {}
    except requests.RequestException:
        # Fallback to empty data if API call fails
        customers = []
        projects = {}
    
    return render_template('projects.html', 
                          customers=customers, 
                          projects=projects, 
                          now=datetime.datetime.now())

@app.route('/projects/<customer>/<project>')
def project_detail(customer, project):
    # Fetch real projects from the API
    api_url = os.environ.get('API_URL', 'http://localhost:5000')
    try:
        response = requests.get(f"{api_url}/api/projects/all")
        if response.ok:
            data = response.json()
            customers = data.get('customers', [])
            projects = data.get('projects', {})
        else:
            # Fallback to empty data if API call fails
            customers = []
            projects = {}
    except requests.RequestException:
        # Fallback to empty data if API call fails
        customers = []
        projects = {}
    
    return render_template('projects.html', 
                          customers=customers, 
                          projects=projects,
                          selected_customer=customer,
                          selected_project=project,
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
        sensitive_keys = ['SECRET_KEY', 'API_KEY']
        for key, value in os.environ.items():
            if any(sensitive in key.upper() for sensitive in sensitive_keys):
                env_vars[key] = "***REDACTED***"
            else:
                env_vars[key] = value
        
        # Test connection to API
        api_url = os.environ.get('API_URL', 'http://localhost:5000')
        api_status = "Unknown"
        api_message = ""
        try:
            api_response = requests.get(f"{api_url}/api/health", timeout=5)
            if api_response.ok:
                api_status = "Connected"
                api_message = f"Successfully connected to API, status: {api_response.status_code}"
            else:
                api_status = "Error"
                api_message = f"API returned status code {api_response.status_code}"
        except requests.RequestException as e:
            api_status = "Error"
            api_message = f"Failed to connect to API: {str(e)}"
        
        # Test API projects endpoint
        projects_status = "Unknown"
        projects_message = ""
        try:
            projects_response = requests.get(f"{api_url}/api/projects/all", timeout=5)
            if projects_response.ok:
                projects_status = "Connected"
                projects_message = f"Successfully connected to projects endpoint"
                projects_data = projects_response.json()
            else:
                projects_status = "Error"
                projects_message = f"Projects endpoint returned status code {projects_response.status_code}"
                projects_data = {}
        except requests.RequestException as e:
            projects_status = "Error"
            projects_message = f"Failed to connect to projects endpoint: {str(e)}"
            projects_data = {}
        
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
            "projects_endpoint": {
                "url": f"{api_url}/api/projects/all",
                "status": projects_status,
                "message": projects_message,
                "data": projects_data
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
                <h2>Projects Endpoint</h2>
                <p><strong>URL:</strong> {debug_info['projects_endpoint']['url']}</p>
                <p><strong>Status:</strong> <span class="{'success' if debug_info['projects_endpoint']['status'] == 'Connected' else 'error'}">{debug_info['projects_endpoint']['status']}</span></p>
                <p><strong>Message:</strong> {debug_info['projects_endpoint']['message']}</p>
                
                <h3>Data</h3>
                <pre>{json.dumps(debug_info['projects_endpoint']['data'], indent=2)}</pre>
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

@app.route('/api/projects/<path:project_path>/files/<path:file_path>')
def get_project_file(project_path, file_path):
    """Proxy API requests for specific project files"""
    # API server URL (adjust as needed)
    api_url = os.environ.get('API_URL', 'http://localhost:5000')
    
    # Forward the request to the API server
    url = f"{api_url}/api/projects/{project_path}/files/{file_path}"
    
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

@app.route('/api/proxy/projects/<path:project_path>/files/<path:file_path>')
def proxy_project_file(project_path, file_path):
    """Proxy API requests for specific project files"""
    # API server URL (adjust as needed)
    api_url = os.environ.get('API_URL', 'http://localhost:5000')
    
    # Forward the request to the API server
    url = f"{api_url}/api/projects/{project_path}/files/{file_path}"
    
    try:
        # Forward the request
        resp = requests.request(
            method=request.method,
            url=url,
            headers={key: value for (key, value) in request.headers if key != 'Host'},
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False,
            params=request.args
        )
        
        # Create a Flask response object
        response = Response(
            resp.content,
            resp.status_code,
            {key: value for (key, value) in resp.headers.items() if key != 'Content-Length'}
        )
        
        return response
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api', methods=['GET'])
def api_test():
    """Test endpoint to verify API routes are working"""
    # Get the API URL from environment or use default
    api_url = os.environ.get('API_URL', 'http://localhost:5000')
    
    # Test if we can connect to the API server
    api_status = "Unknown"
    api_message = ""
    try:
        response = requests.get(f"{api_url}/api/health", timeout=5)
        if response.ok:
            api_status = "Connected"
            api_message = "Successfully connected to API server"
        else:
            api_status = "Error"
            api_message = f"API server returned status code {response.status_code}"
    except requests.RequestException as e:
        api_status = "Error"
        api_message = f"Failed to connect to API server: {str(e)}"
    
    # Check if the projects endpoint is working
    projects_status = "Unknown"
    projects_message = ""
    try:
        response = requests.get(f"{api_url}/api/projects/all", timeout=5)
        if response.ok:
            projects_status = "Working"
            projects_message = "Projects endpoint is working"
            projects_data = response.json()
        else:
            projects_status = "Error"
            projects_message = f"Projects endpoint returned status code {response.status_code}"
            projects_data = {}
    except requests.RequestException as e:
        projects_status = "Error"
        projects_message = f"Failed to connect to projects endpoint: {str(e)}"
        projects_data = {}
    
    return jsonify({
        "status": "OK",
        "message": "API routes diagnostic information",
        "api_server": {
            "url": api_url,
            "status": api_status,
            "message": api_message
        },
        "endpoints": {
            "/api/projects/all": {
                "status": projects_status,
                "message": projects_message,
                "data": projects_data if projects_status == "Working" else None
            },
            "/api/projects/<customer>/<project>/files": "Get files for a specific project",
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

@app.route('/api/projects/all')
def get_all_projects():
    """API endpoint to get all customers and their projects"""
    # API server URL (adjust as needed)
    api_url = os.environ.get('API_URL', 'http://localhost:5000')
    
    try:
        # Forward the request to the API server
        response = requests.get(f"{api_url}/api/projects/all")
        
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
            "customers": [],
            "projects": {}
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))  # Change default from 5000 to 5001
    app.run(debug=False, host='0.0.0.0', port=port)
