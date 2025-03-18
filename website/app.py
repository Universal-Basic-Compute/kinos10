from flask import Flask, render_template, send_from_directory, request, Response
import datetime
import os
import requests

app = Flask(__name__, static_folder='static', template_folder='templates', static_url_path='')

@app.route('/')
def index():
    return render_template('index.html', now=datetime.datetime.now())

@app.route('/projects')
def projects():
    # Mock data - in a real app, you would fetch this from your API
    customers = ['deskmate', 'duogaming', 'kinkong', 'kinos']
    projects = {
        'deskmate': ['template', 'math_project', 'science_project'],
        'duogaming': ['template', 'minecraft', 'fortnite'],
        'kinkong': ['template', 'trading_bot', 'portfolio_analysis'],
        'kinos': ['template', 'api_development', 'documentation']
    }
    
    return render_template('projects.html', 
                          customers=customers, 
                          projects=projects, 
                          now=datetime.datetime.now())

@app.route('/projects/<customer>/<project>')
def project_detail(customer, project):
    # This is a placeholder - in a real app, you would fetch project details
    # For now, we'll just render the same template with the project info
    customers = ['deskmate', 'duogaming', 'kinkong', 'kinos']
    projects = {
        'deskmate': ['template', 'math_project', 'science_project'],
        'duogaming': ['template', 'minecraft', 'fortnite'],
        'kinkong': ['template', 'trading_bot', 'portfolio_analysis'],
        'kinos': ['template', 'api_development', 'documentation']
    }
    
    return render_template('projects.html', 
                          customers=customers, 
                          projects=projects,
                          selected_customer=customer,
                          selected_project=project,
                          now=datetime.datetime.now())

@app.route('/health')
def health():
    return 'OK', 200

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

@app.route('/api/projects/all')
def get_all_projects():
    """API endpoint to get all customers and their projects"""
    # In a real app, you would fetch this from your database or API
    # For now, we'll return mock data
    customers = ['deskmate', 'duogaming', 'kinkong', 'kinos']
    projects = {
        'deskmate': ['template', 'math_project', 'science_project'],
        'duogaming': ['template', 'minecraft', 'fortnite'],
        'kinkong': ['template', 'trading_bot', 'portfolio_analysis'],
        'kinos': ['template', 'api_development', 'documentation']
    }
    
    return jsonify({
        'customers': customers,
        'projects': projects
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))  # Change default from 5000 to 5001
    app.run(debug=False, host='0.0.0.0', port=port)
