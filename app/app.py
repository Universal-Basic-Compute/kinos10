from flask import Flask, render_template, jsonify, request, Response, redirect, url_for, send_from_directory
import os
import requests
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.before_request
def log_request_info():
    """Log details about each request."""
    logger.info(f"Website Request: {request.method} {request.path} from {request.remote_addr}")

@app.after_request
def log_response_info(response):
    """Log details about each response."""
    logger.info(f"Website Response: {response.status_code}")
    return response

# Configuration
if os.environ.get('ENVIRONMENT') == 'production':
    API_BASE_URL = "https://kinos-engine.ai"
else:
    API_BASE_URL = "http://localhost:5000"  # Default for local development

@app.route('/')
def index():
    """Render the main debug UI page."""
    # Get list of blueprints
    blueprints_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "blueprints")
    blueprints = [d for d in os.listdir(blueprints_dir) if os.path.isdir(os.path.join(blueprints_dir, d))]
    
    return render_template('index.html', blueprints=blueprints, default_blueprint="kinos", default_kin="template")

@app.route('/api/blueprints/<blueprint>/kins')
def get_kins(blueprint):
    """Get list of kins for a blueprint."""
    try:
        # Try to get kins from the API first
        url = f"{API_BASE_URL}/kins/{blueprint}/kins"
        response = requests.get(url, timeout=10)
        
        if response.ok:
            return response.json()
    except Exception as e:
        print(f"Error fetching kins from API: {str(e)}")
    
    # Fallback to local directory if API fails
    try:
        blueprints_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "blueprints")
        blueprint_dir = os.path.join(blueprints_dir, blueprint)
        
        # Always include template
        kins = ["template"]
        
        # Add other kins if they exist
        kins_dir = os.path.join(blueprint_dir, "kins")
        if os.path.exists(kins_dir):
            kins.extend([d for d in os.listdir(kins_dir) if os.path.isdir(os.path.join(kins_dir, d))])
        
        return jsonify({"kins": kins})
    except Exception as e:
        print(f"Error getting local kins: {str(e)}")
        return jsonify({"kins": ["template"], "error": str(e)})

@app.route('/proxy/<path:endpoint>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def proxy_api(endpoint):
    """Proxy requests to the actual API."""
    url = f"{API_BASE_URL}/{endpoint}"
    
    try:
        # Print debugging information
        print(f"Proxying request to: {url}")
        print(f"Method: {request.method}")
        
        # Forward the request with the appropriate method
        headers = {key: value for key, value in request.headers.items() 
                  if key.lower() not in ['host', 'content-length']}
        
        # Add a custom header to identify the source
        headers['X-Forwarded-From'] = 'kinos-app'
        
        if request.method == 'GET':
            resp = requests.get(
                url, 
                params=request.args,
                headers=headers,
                timeout=30
            )
        elif request.method == 'POST':
            # Check if the request has JSON content
            if request.is_json:
                resp = requests.post(
                    url, 
                    json=request.json,
                    headers=headers,
                    timeout=30
                )
            else:
                # For form data or other content types
                resp = requests.post(
                    url,
                    data=request.get_data(),
                    headers=headers,
                    timeout=30
                )
        else:  # PUT, DELETE, etc.
            resp = requests.request(
                method=request.method,
                url=url,
                headers=headers,
                data=request.get_data(),
                params=request.args,
                timeout=30
            )
        
        # Print response information for debugging
        print(f"Response status: {resp.status_code}")
        
        # Create a Flask response with the same status code and headers
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(name, value) for name, value in resp.headers.items()
                  if name.lower() not in excluded_headers]
        
        response = Response(resp.content, resp.status_code, headers)
        return response
        
    except requests.RequestException as e:
        # Handle request exceptions (connection errors, timeouts, etc.)
        print(f"Request error: {str(e)}")
        return jsonify({"error": f"API request failed: {str(e)}"}), 500

@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors with a custom page."""
    return render_template('404.html'), 404

@app.route('/<path:path>')
def catch_all(path):
    """Catch-all route to handle undefined routes"""
    # First try to serve as a static file
    try:
        return send_from_directory(app.static_folder, path)
    except:
        # If not a static file, return 404
        return page_not_found(None)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)  # Run on port 5001 to avoid conflict with API
