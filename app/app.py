from flask import Flask, render_template, jsonify, request, Response
import os
import requests
import json

app = Flask(__name__)

# Configuration
if os.environ.get('ENVIRONMENT') == 'production':
    API_BASE_URL = "https://kinos.onrender.com"
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
    customers_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "customers")
    customer_dir = os.path.join(customers_dir, customer)
    
    # Always include template
    projects = ["template"]
    
    # Add other projects if they exist
    projects_dir = os.path.join(customer_dir, "projects")
    if os.path.exists(projects_dir):
        projects.extend([d for d in os.listdir(projects_dir) if os.path.isdir(os.path.join(projects_dir, d))])
    
    return jsonify({"projects": projects})

@app.route('/api/proxy/<path:endpoint>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def proxy_api(endpoint):
    """Proxy requests to the actual API."""
    url = f"{API_BASE_URL}/api/{endpoint}"
    
    try:
        # Print debugging information
        print(f"Proxying request to: {url}")
        print(f"Method: {request.method}")
        print(f"Headers: {dict(request.headers)}")
        
        # Forward the request with the appropriate method
        if request.method == 'GET':
            resp = requests.get(
                url, 
                params=request.args,
                headers={key: value for key, value in request.headers if key != 'Host'},
                timeout=30
            )
        elif request.method == 'POST':
            # Check if the request has JSON content
            if request.is_json:
                resp = requests.post(
                    url, 
                    json=request.json,
                    headers={key: value for key, value in request.headers if key != 'Host'},
                    timeout=30
                )
            else:
                # For form data or other content types
                resp = requests.post(
                    url,
                    data=request.get_data(),
                    headers={key: value for key, value in request.headers if key != 'Host'},
                    timeout=30
                )
        else:  # PUT, DELETE, etc.
            resp = requests.request(
                method=request.method,
                url=url,
                headers={key: value for key, value in request.headers if key != 'Host'},
                data=request.get_data(),
                params=request.args,
                timeout=30
            )
        
        # Print response information for debugging
        print(f"Response status: {resp.status_code}")
        print(f"Response headers: {dict(resp.headers)}")
        
        # Check if the response is JSON or plain text
        content_type = resp.headers.get('Content-Type', '')
        
        # Create a Flask response with the same status code and headers
        response = Response(
            resp.content,
            resp.status_code,
            {key: value for key, value in resp.headers.items() 
             if key.lower() not in ['content-length', 'transfer-encoding', 'connection']}
        )
        
        return response
    except requests.RequestException as e:
        # Handle request exceptions (connection errors, timeouts, etc.)
        app.logger.error(f"Request error: {str(e)}")
        return jsonify({"error": f"API request failed: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)  # Run on port 5001 to avoid conflict with API
