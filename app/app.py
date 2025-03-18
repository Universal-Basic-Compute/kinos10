from flask import Flask, render_template, jsonify, request
import os
import requests
import json

app = Flask(__name__)

# Configuration
API_BASE_URL = "http://localhost:5000/api"  # Assuming the API runs on port 5000

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

@app.route('/api/proxy/<path:endpoint>', methods=['GET', 'POST'])
def proxy_api(endpoint):
    """Proxy requests to the actual API."""
    url = f"{API_BASE_URL}/{endpoint}"
    
    if request.method == 'GET':
        resp = requests.get(url, params=request.args)
    else:  # POST
        resp = requests.post(url, json=request.json)
    
    return jsonify(resp.json()), resp.status_code

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)  # Run on port 5001 to avoid conflict with API
