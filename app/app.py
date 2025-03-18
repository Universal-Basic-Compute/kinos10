from flask import Flask, render_template, jsonify, request, Response, redirect, url_for, send_from_directory
import os
import requests
import json

app = Flask(__name__)

# Configuration
if os.environ.get('ENVIRONMENT') == 'production':
    API_BASE_URL = "https://kinos-engine.ai"
else:
    API_BASE_URL = "http://localhost:5000"  # Default for local development

@app.route('/')
def index():
    """Render the main debug UI page."""
    # Get list of customers
    customers_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "customers")
    customers = [d for d in os.listdir(customers_dir) if os.path.isdir(os.path.join(customers_dir, d))]
    
    return render_template('index.html', customers=customers, default_customer="kinos", default_project="template")

@app.route('/api/customers/<customer>/projects')
def get_projects(customer):
    """Get list of projects for a customer."""
    try:
        # Try to get projects from the API first
        url = f"{API_BASE_URL}/api/projects/{customer}/projects"
        response = requests.get(url, timeout=10)
        
        if response.ok:
            return response.json()
    except Exception as e:
        print(f"Error fetching projects from API: {str(e)}")
    
    # Fallback to local directory if API fails
    try:
        customers_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "customers")
        customer_dir = os.path.join(customers_dir, customer)
        
        # Always include template
        projects = ["template"]
        
        # Add other projects if they exist
        projects_dir = os.path.join(customer_dir, "projects")
        if os.path.exists(projects_dir):
            projects.extend([d for d in os.listdir(projects_dir) if os.path.isdir(os.path.join(projects_dir, d))])
        
        return jsonify({"projects": projects})
    except Exception as e:
        print(f"Error getting local projects: {str(e)}")
        return jsonify({"projects": ["template"], "error": str(e)})

@app.route('/api/proxy/<path:endpoint>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def proxy_api(endpoint):
    """Proxy requests to the actual API."""
    url = f"{API_BASE_URL}/api/{endpoint}"
    
    try:
        # Print debugging information
        print(f"Proxying request to: {url}")
        print(f"Method: {request.method}")
        
        # Forward the request with the appropriate method
        headers = {key: value for key, value in request.headers.items() 
                  if key.lower() not in ['host', 'content-length']}
        
        # Add a custom header to identify the source
        headers['X-Forwarded-From'] = 'kinos-website'
        
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

@app.route('/<path:path>')
def catch_all(path):
    """Catch-all route to handle undefined routes"""
    # First try to serve as a static file
    try:
        return send_from_directory(app.static_folder, path)
    except:
        # If not a static file, redirect to home page
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)  # Run on port 5001 to avoid conflict with API
