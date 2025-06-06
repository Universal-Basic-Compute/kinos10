from flask import Flask, request, jsonify
import os
import shutil
import datetime
import subprocess
import sys
from flask_cors import CORS
from config import logger, blueprintS_DIR, API_KEY
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
from routes.projects import kins_bp
from routes.messages import messages_bp
from routes.files import files_bp
from routes.tts import tts_bp
from routes.stt import stt_bp
from routes.debug import debug_bp
from services.file_service import initialize_blueprint_templates
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
            "https://fictra-portal-cosmos.vercel.app",
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
            "https://fictra-portal-cosmos.vercel.app",
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
    """Verify API key for all requests except health check, root endpoint, and API documentation."""
    # Skip verification for health check, root endpoint, and API documentation
    if request.path == '/health' or request.path == '/' or request.path == '/debug-api/debug' or request.path.startswith('/v2/'):
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

# Register blueprints with appropriate URL prefixes
app.register_blueprint(kins_bp, url_prefix='/api/proxy')
app.register_blueprint(messages_bp, url_prefix='/api/proxy')
app.register_blueprint(files_bp, url_prefix='/api/proxy')
app.register_blueprint(tts_bp, url_prefix='/api/proxy')
app.register_blueprint(stt_bp, url_prefix='/api/proxy')
# Register v2 blueprint for the v2 API
from routes.v2_routes import v2_bp
app.register_blueprint(v2_bp, url_prefix='/v2')
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
            "version": "2.0.0",
            "endpoints": {
                "health": "/health",
                "blueprints": "/v2/blueprints",
                "kins": "/v2/blueprints/{blueprint}/kins",
                "messages": "/v2/blueprints/{blueprint}/kins/{kin_id}/messages",
                "files": "/v2/blueprints/{blueprint}/kins/{kin_id}/files"
            }
        }), 200
    
    # Otherwise, return the API reference documentation as HTML
    try:
        # Path to the API reference markdown file - CHANGED TO V2
        api_ref_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                   "blueprints", "kinos", "template", "sources", "api_reference_v2.md")
        
        # Check if the file exists
        if not os.path.exists(api_ref_path):
            logger.warning(f"API reference file not found at {api_ref_path}")
            return jsonify({"error": "API reference documentation not found"}), 404
        
        # Read the markdown content
        with open(api_ref_path, 'r', encoding='utf-8') as f:
            markdown_content = f.read()
        
        # Convert markdown to HTML with extensions
        try:
            import markdown
            from markdown.extensions.toc import TocExtension
            from markdown.extensions.fenced_code import FencedCodeExtension
            from markdown.extensions.tables import TableExtension
            
            # Convert markdown to HTML with extensions
            html_content = markdown.markdown(
                markdown_content,
                extensions=[
                    'markdown.extensions.fenced_code',
                    'markdown.extensions.tables',
                    'markdown.extensions.toc',
                    'markdown.extensions.codehilite'
                ]
            )
        except ImportError:
            # If markdown package is not available, use a simple HTML wrapper
            html_content = f"<pre>{markdown_content}</pre>"
        
        # Wrap in a basic HTML document with some styling
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>KinOS API Reference</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                :root {{
                    --primary-color: #3498db;
                    --secondary-color: #2c3e50;
                    --background-color: #f9f9f9;
                    --code-background: #f0f0f0;
                    --border-color: #ddd;
                    --text-color: #333;
                    --heading-color: #2c3e50;
                    --link-color: #3498db;
                    --method-get-color: #61affe;
                    --method-post-color: #49cc90;
                    --method-put-color: #fca130;
                    --method-delete-color: #f93e3e;
                }}
                
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
                    line-height: 1.6;
                    color: var(--text-color);
                    margin: 0;
                    padding: 0;
                    background-color: var(--background-color);
                }}
                
                .container {{
                    background-color: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
                    padding: 30px;
                    max-width: 1100px;
                    margin: 0 auto;
                }}
                
                /* Sidebar and layout styles */
                :root {{
                    /* Keep existing variables */
                    --sidebar-width: 250px;
                    --sidebar-background: #f8f9fa;
                    --sidebar-border: #e9ecef;
                }}
                
                .page-container {{
                    display: flex;
                    width: 100%;
                }}
                
                .sidebar {{
                    width: var(--sidebar-width);
                    background-color: var(--sidebar-background);
                    border-right: 1px solid var(--sidebar-border);
                    height: 100vh;
                    position: fixed;
                    top: 0;
                    left: 0;
                    overflow-y: auto;
                    padding: 20px 0;
                    transition: transform 0.3s ease;
                }}
                
                .sidebar-header {{
                    padding: 0 20px 20px;
                    border-bottom: 1px solid var(--sidebar-border);
                    margin-bottom: 20px;
                }}
                
                .sidebar-header h3 {{
                    margin: 0;
                    font-size: 1.2em;
                }}
                
                .sidebar-nav {{
                    list-style-type: none;
                    padding: 0;
                    margin: 0;
                }}
                
                .sidebar-nav li {{
                    padding: 8px 20px;
                }}
                
                .sidebar-nav li:hover {{
                    background-color: rgba(0,0,0,0.05);
                }}
                
                .sidebar-nav a {{
                    color: var(--text-color);
                    text-decoration: none;
                    display: block;
                    font-size: 0.95em;
                }}
                
                .sidebar-nav a:hover {{
                    color: var(--link-color);
                }}
                
                .sidebar-nav .section-title {{
                    font-weight: 600;
                    color: var(--heading-color);
                    padding: 12px 20px 8px;
                    font-size: 0.9em;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }}
                
                .content {{
                    flex: 1;
                    margin-left: var(--sidebar-width);
                    padding: 20px;
                    transition: margin-left 0.3s ease;
                }}
                
                .sidebar-toggle {{
                    display: none;
                    position: fixed;
                    top: 20px;
                    left: 20px;
                    z-index: 1000;
                    background-color: var(--primary-color);
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 12px;
                    cursor: pointer;
                }}
                
                /* Responsive styles */
                @media (max-width: 768px) {{
                    .sidebar {{
                        transform: translateX(-100%);
                        z-index: 999;
                    }}
                    
                    .sidebar.active {{
                        transform: translateX(0);
                    }}
                    
                    .content {{
                        margin-left: 0;
                    }}
                    
                    .sidebar-toggle {{
                        display: block;
                    }}
                    
                    .container {{
                        padding: 15px;
                    }}
                }}
                
                pre {{
                    background-color: var(--code-background);
                    padding: 16px;
                    border-radius: 8px;
                    overflow-x: auto;
                    border: 1px solid var(--border-color);
                    box-shadow: inset 0 1px 3px rgba(0,0,0,0.05);
                    font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
                    font-size: 14px;
                }}
                
                code {{
                    background-color: var(--code-background);
                    padding: 2px 6px;
                    border-radius: 4px;
                    font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
                    font-size: 0.9em;
                }}
                
                h1, h2, h3, h4, h5, h6 {{
                    margin-top: 1.5em;
                    font-weight: 600;
                    color: var(--heading-color);
                }}
                
                h1 {{
                    border-bottom: 2px solid var(--primary-color);
                    padding-bottom: 10px;
                    font-size: 2.2em;
                    margin-top: 0;
                }}
                
                h2 {{
                    border-bottom: 1px solid var(--border-color);
                    padding-bottom: 8px;
                    font-size: 1.8em;
                    margin-top: 2em;
                }}
                
                h3 {{
                    font-size: 1.4em;
                    margin-top: 1.8em;
                }}
                
                a {{
                    color: var(--link-color);
                    text-decoration: none;
                    transition: color 0.2s;
                }}
                
                a:hover {{
                    text-decoration: underline;
                    color: #2980b9;
                }}
                
                p {{
                    margin: 1em 0;
                }}
                
                .endpoint {{
                    background-color: #f8f9fa;
                    border-left: 4px solid var(--primary-color);
                    padding: 15px 20px;
                    margin: 1.5em 0;
                    border-radius: 0 4px 4px 0;
                }}
                
                .method {{
                    display: inline-block;
                    padding: 4px 8px;
                    border-radius: 4px;
                    color: white;
                    font-weight: bold;
                    font-size: 0.8em;
                    margin-right: 8px;
                }}
                
                .method-get {{
                    background-color: var(--method-get-color);
                }}
                
                .method-post {{
                    background-color: var(--method-post-color);
                }}
                
                .method-put {{
                    background-color: var(--method-put-color);
                }}
                
                .method-delete {{
                    background-color: var(--method-delete-color);
                }}
                
                .url {{
                    font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
                    font-weight: 500;
                }}
                
                table {{
                    border-collapse: collapse;
                    width: 100%;
                    margin: 1.5em 0;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                    border-radius: 4px;
                    overflow: hidden;
                }}
                
                th, td {{
                    border: 1px solid var(--border-color);
                    padding: 10px 15px;
                    text-align: left;
                }}
                
                th {{
                    background-color: #f2f2f2;
                    font-weight: 600;
                }}
                
                tr:nth-child(even) {{
                    background-color: #f9f9f9;
                }}
                
                tr:hover {{
                    background-color: #f5f5f5;
                }}
                
                .toc {{
                    background-color: #f8f9fa;
                    border: 1px solid var(--border-color);
                    border-radius: 8px;
                    padding: 20px;
                    margin-bottom: 30px;
                }}
                
                .toc ul {{
                    list-style-type: none;
                    padding-left: 15px;
                }}
                
                .toc li {{
                    margin: 5px 0;
                }}
                
                .toc-h2 {{
                    font-weight: 600;
                }}
                
                .toc-h3 {{
                    padding-left: 15px;
                }}
                
                .toc-h4 {{
                    padding-left: 30px;
                }}
                
                .note {{
                    background-color: #e8f4fc;
                    border-left: 4px solid var(--primary-color);
                    padding: 15px;
                    margin: 1.5em 0;
                    border-radius: 0 4px 4px 0;
                }}
                
                .warning {{
                    background-color: #fff8e6;
                    border-left: 4px solid #f1c40f;
                    padding: 15px;
                    margin: 1.5em 0;
                    border-radius: 0 4px 4px 0;
                }}
                
                .error {{
                    background-color: #fde8e8;
                    border-left: 4px solid #e74c3c;
                    padding: 15px;
                    margin: 1.5em 0;
                    border-radius: 0 4px 4px 0;
                }}
                
                @media (max-width: 768px) {{
                    body {{
                        padding: 15px;
                    }}
                    
                    .container {{
                        padding: 20px;
                    }}
                    
                    pre {{
                        padding: 10px;
                        font-size: 13px;
                    }}
                    
                    h1 {{
                        font-size: 1.8em;
                    }}
                    
                    h2 {{
                        font-size: 1.5em;
                    }}
                    
                    h3 {{
                        font-size: 1.2em;
                    }}
                }}
                
                /* Add syntax highlighting for JSON */
                .json-key {{
                    color: #a626a4;
                }}
                
                .json-string {{
                    color: #50a14f;
                }}
                
                .json-number {{
                    color: #986801;
                }}
                
                .json-boolean {{
                    color: #0184bc;
                }}
                
                .json-null {{
                    color: #0184bc;
                }}
            </style>
            <script>
                /* Add this script to enhance the markdown rendering */
                document.addEventListener('DOMContentLoaded', function() {{
                    /* Sidebar toggle functionality */
                    const sidebarToggle = document.getElementById('sidebarToggle');
                    const sidebar = document.getElementById('sidebar');
                    
                    if (sidebarToggle && sidebar) {{
                        sidebarToggle.addEventListener('click', function() {{
                            sidebar.classList.toggle('active');
                        }});
                    }}
                    
                    // Close sidebar when clicking a link on mobile
                    const sidebarLinks = document.querySelectorAll('.sidebar-nav a');
                    sidebarLinks.forEach(link => {{
                        link.addEventListener('click', function() {{
                            if (window.innerWidth <= 768) {{
                                sidebar.classList.remove('active');
                            }}
                        }});
                    }});
                
                    /* Add method styling to endpoints */
                    document.querySelectorAll('h4').forEach(function(heading) {{
                        const text = heading.textContent;
                        if (text.includes('GET ') || text.includes('POST ') || text.includes('PUT ') || text.includes('DELETE ')) {{
                            const endpoint = document.createElement('div');
                            endpoint.className = 'endpoint';
                            
                            // Extract method and URL
                            const match = text.match(/(GET|POST|PUT|DELETE) (.*)/);
                            if (match) {{
                                const method = match[1];
                                const url = match[2];
                                
                                const methodSpan = document.createElement('span');
                                methodSpan.className = 'method method-' + method.toLowerCase();
                                methodSpan.textContent = method;
                                
                                const urlSpan = document.createElement('span');
                                urlSpan.className = 'url';
                                urlSpan.textContent = url;
                                
                                endpoint.appendChild(methodSpan);
                                endpoint.appendChild(urlSpan);
                                
                                // Replace the heading with our styled endpoint
                                heading.parentNode.insertBefore(endpoint, heading.nextSibling);
                            }}
                        }}
                    }});
                    
                    // Add syntax highlighting to code blocks
                    document.querySelectorAll('pre code').forEach(function(block) {{
                        if (block.textContent.trim().startsWith('{{') || block.textContent.trim().startsWith('[')) {{
                            try {{
                                // Get the raw text content
                                const rawText = block.textContent;
                            
                                // Create a temporary element to work with
                                const tempElement = document.createElement('div');
                            
                                // Function to escape HTML
                                const escapeHtml = (text) => {{
                                    return text
                                        .replace(/&/g, "&amp;")
                                        .replace(/</g, "&lt;")
                                        .replace(/>/g, "&gt;")
                                        .replace(/"/g, "&quot;")
                                        .replace(/'/g, "&#039;");
                                }};
                            
                                // Function to highlight JSON
                                const highlightJSON = (json) => {{
                                    return json
                                        .replace(/("(\\u[a-zA-Z0-9]{{4}}|\\[^u]|[^\\"])*"(\\s*:)?|\b(true|false|null)\b|-?\\d+(?:\\.\\d*)?(?:[eE][+\\-]?\\d+)?)/g, function(match) {{
                                            let cls = 'json-number';
                                            if (/^"/.test(match)) {{
                                                if (/:$/.test(match)) {{
                                                    cls = 'json-key';
                                                    // Remove the colon from the match
                                                    match = match.replace(/:$/, '');
                                                    return '<span class="' + cls + '">' + match + '</span>:';
                                                }} else {{
                                                    cls = 'json-string';
                                                }}
                                            }} else if (/true|false/.test(match)) {{
                                                cls = 'json-boolean';
                                            }} else if (/null/.test(match)) {{
                                                cls = 'json-null';
                                            }}
                                            return '<span class="' + cls + '">' + match + '</span>';
                                        }});
                                }};
                            
                                // Escape the HTML first
                                const escapedText = escapeHtml(rawText);
                            
                                // Apply highlighting
                                const highlighted = highlightJSON(escapedText);
                            
                                // Set the highlighted content
                                block.innerHTML = highlighted;
                            }} catch (e) {{
                                console.error("Error highlighting JSON:", e);
                                // If there's an error, leave the content as is
                            }}
                        }}
                    }});
                }});
            </script>
        </head>
        <body>
            <button class="sidebar-toggle" id="sidebarToggle">☰ Menu</button>
            
            <div class="page-container">
                <div class="sidebar" id="sidebar">
                    <div class="sidebar-header">
                        <h3>API Reference</h3>
                    </div>
                    <ul class="sidebar-nav">
                        <li><a href="#base-url">Base URL</a></li>
                        <li><a href="#authentication">Authentication</a></li>
                        
                        <div class="section-title">API Endpoints</div>
                        <li><a href="#blueprint-management">Blueprint Management</a></li>
                        <li><a href="#kin-management">Kin Management</a></li>
                        <li><a href="#channel-management">Channel Management</a></li>
                        <li><a href="#message-interaction">Message Interaction</a></li>
                        <li><a href="#file-operations">File Operations</a></li>
                        <li><a href="#kin-building">Kin Building</a></li>
                        <li><a href="#modes-and-configuration">Modes & Configuration</a></li>
                        <li><a href="#special-features">Special Features</a></li>
                        <li><a href="#media-processing">Media Processing</a></li>
                        <li><a href="#system-information">System Information</a></li>
                        
                        <div class="section-title">Additional Info</div>
                        <li><a href="#error-handling">Error Handling</a></li>
                        <li><a href="#working-with-images">Working with Images</a></li>
                        <li><a href="#pagination">Pagination</a></li>
                        <li><a href="#versioning">Versioning</a></li>
                        <li><a href="#rate-limiting">Rate Limiting</a></li>
                        <li><a href="#glossary">Glossary</a></li>
                    </ul>
                </div>
                
                <div class="content">
                    <div class="container">
                        <h1>KinOS API Reference</h1>
                        <p>This documentation provides a comprehensive reference for the KinOS API.</p>
                        """ + html_content + """
                    </div>
                </div>
            </div>
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

@app.route('/website/<blueprint>/<kin_id>/<path:path>', methods=['GET'])
def serve_kin_website(blueprint, kin_id, path=''):
    """
    Serve files from a kin's website directory.
    This allows kins to have their own websites at <blueprint>-<kin>.kinos-engine.ai
    """
    try:
        # Get kin path
        from services.file_service import get_kin_path
        kin_path = get_kin_path(blueprint, kin_id)
        
        # Check if kin exists
        if not os.path.exists(kin_path):
            return jsonify({"error": f"Kin '{kin_id}' not found for blueprint '{blueprint}'"}), 404
        
        # Check if website directory exists
        website_dir = os.path.join(kin_path, "website")
        if not os.path.exists(website_dir):
            return jsonify({"error": "This kin doesn't have a website"}), 404
        
        # Handle root path
        if not path:
            path = 'index.html'
        
        # Check if the file exists in the .next/server/pages directory (for SSR)
        next_server_dir = os.path.join(website_dir, ".next", "server", "pages")
        file_path = os.path.join(next_server_dir, path)
        
        # If not found in server/pages, check in the public directory
        if not os.path.exists(file_path):
            file_path = os.path.join(website_dir, "public", path)
        
        # If still not found, check in the .next/static directory
        if not os.path.exists(file_path):
            static_dir = os.path.join(website_dir, ".next", "static")
            for root, dirs, files in os.walk(static_dir):
                potential_path = os.path.join(root, os.path.basename(path))
                if os.path.exists(potential_path):
                    file_path = potential_path
                    break
        
        # If file exists, serve it
        if os.path.exists(file_path):
            # Determine content type based on file extension
            extension = os.path.splitext(file_path)[1].lower()
            content_type = {
                '.html': 'text/html',
                '.js': 'application/javascript',
                '.css': 'text/css',
                '.json': 'application/json',
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.gif': 'image/gif',
                '.svg': 'image/svg+xml',
                '.ico': 'image/x-icon'
            }.get(extension, 'text/plain')
            
            # Read and return the file
            with open(file_path, 'rb') as f:
                return f.read(), 200, {'Content-Type': content_type}
        
        # If file not found, return 404
        return jsonify({"error": f"File '{path}' not found"}), 404
        
    except Exception as e:
        logger.error(f"Error serving kin website: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/', methods=['GET'], subdomain='<subdomain>')
def serve_kin_website_subdomain(subdomain):
    """
    Serve a kin's website based on the subdomain.
    Subdomain format: <blueprint>-<kin>.kinos-engine.ai
    """
    try:
        # Parse the subdomain to extract blueprint and kin
        parts = subdomain.split('-', 1)
        if len(parts) != 2:
            return jsonify({"error": "Invalid subdomain format. Expected: <blueprint>-<kin>"}), 400
            
        blueprint, kin_id = parts
        
        # Redirect to the website route
        return serve_kin_website(blueprint, kin_id, '')
        
    except Exception as e:
        logger.error(f"Error serving kin website from subdomain: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/<path:undefined_route>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def global_catch_all(undefined_route):
    """Global catch-all route for undefined API endpoints."""
    # Skip if the route starts with 'kins/' as those should be handled by other blueprints
    if undefined_route.startswith('kins/'):
        return jsonify({
            "error": "Not Found",
            "message": f"The kin endpoint '/{undefined_route}' does not exist.",
            "documentation_url": "http://api.kinos-engine.ai"
        }), 404
        
    logger.warning(f"Undefined API route accessed: {undefined_route}")
    return jsonify({
        "error": "Not Found",
        "message": f"The requested endpoint '/{undefined_route}' does not exist.",
        "documentation_url": "http://api.kinos-engine.ai"
    }), 404

# Initialize blueprint templates
initialize_blueprint_templates()


# Propagate template changes to all kins
logger.info("Propagating template changes to all kins")
try:
    propagate_templates(dry_run=False)
    logger.info("Template propagation completed successfully")
except Exception as e:
    logger.error(f"Error during template propagation: {str(e)}")

# Function to ensure analysis.txt exists in all blueprint templates
def ensure_analysis_mode_exists():
    """Ensure that the analysis.txt mode file exists in all blueprint templates."""
    logger.info("Ensuring analysis mode exists in all blueprint templates")
    
    # Standard content for analysis.txt
    analysis_content = """# Analysis Mode: Informative Responses Without Memorization

In this mode, you provide information and analysis without memorizing the content of the exchange. This mode is designed for:

1. Answering administrative or debugging questions
2. Providing explanations about your internal functioning
3. Assisting with moderation and supervision
4. Allowing exploratory interactions without impact on your long-term memory

## Specific Guidelines

When operating in this mode:

- Respond with precision and honesty to questions asked
- Explain your reasoning and internal processes if requested
- Provide complete information about your configuration and capabilities
- Do not initiate the creation or modification of memory files
- Do not consider this conversation as something that should influence your future interactions

## Practical Applications

This mode is particularly useful for:
- System administrators checking your configuration
- Moderators evaluating your behavior
- Users wanting to understand your capabilities without modifying your behavior
- Testing and debugging your functioning

Your goal is to provide useful and accurate information while maintaining a clear separation between this interaction and your long-term memory.
"""
    
    # Iterate through all blueprints
    for blueprint in os.listdir(blueprintS_DIR):
        blueprint_dir = os.path.join(blueprintS_DIR, blueprint)
        if not os.path.isdir(blueprint_dir):
            continue
            
        # Check template directory
        template_dir = os.path.join(blueprint_dir, "template")
        if not os.path.exists(template_dir):
            continue
            
        # Ensure modes directory exists
        modes_dir = os.path.join(template_dir, "modes")
        os.makedirs(modes_dir, exist_ok=True)
        
        # Check if analysis.txt exists
        analysis_file = os.path.join(modes_dir, "analysis.txt")
        if not os.path.exists(analysis_file):
            logger.info(f"Creating analysis.txt for blueprint: {blueprint}")
            try:
                with open(analysis_file, 'w', encoding='utf-8') as f:
                    f.write(analysis_content)
            except Exception as e:
                logger.error(f"Error creating analysis.txt for {blueprint}: {str(e)}")

# Initialize all blueprint templates automatically
logger.info("Checking for blueprint templates to initialize")
kin_templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "blueprints")

if os.path.exists(kin_templates_dir):
    # Get list of all blueprints in the kin directory
    available_blueprints = [d for d in os.listdir(kin_templates_dir) 
                          if os.path.isdir(os.path.join(kin_templates_dir, d))]
    logger.info(f"Found blueprints in kin directory: {available_blueprints}")
    
    # Log the current environment for debugging
    logger.info(f"Current environment: {os.environ.get('ENVIRONMENT', 'not set')}")
    logger.info(f"Website URL: {os.environ.get('WEBSITE_URL', 'not set')}")
    
    # Check each blueprint and initialize if needed
    for blueprint in available_blueprints:
        blueprint_template = os.path.join(blueprintS_DIR, blueprint, "template")
        if not os.path.exists(blueprint_template) or not os.listdir(blueprint_template):
            logger.warning(f"{blueprint} template not found or empty, attempting to initialize")
            
            # Source template in kin
            kin_blueprint_template = os.path.join(kin_templates_dir, blueprint, "template")
            
            if os.path.exists(kin_blueprint_template):
                # Create blueprint directory if needed
                blueprint_dir = os.path.join(blueprintS_DIR, blueprint)
                os.makedirs(blueprint_dir, exist_ok=True)
                
                # Create kins directory if needed
                blueprint_kins_dir = os.path.join(blueprint_dir, "kins")
                os.makedirs(blueprint_kins_dir, exist_ok=True)
                
                # Copy template
                if os.path.exists(blueprint_template):
                    shutil.rmtree(blueprint_template)
                
                logger.info(f"Copying {blueprint} template from {kin_blueprint_template} to {blueprint_template}")
                shutil.copytree(kin_blueprint_template, blueprint_template)
                
                # Verify template was copied
                if os.path.exists(blueprint_template):
                    template_files = os.listdir(blueprint_template)
                    logger.info(f"{blueprint} template files: {template_files}")
            else:
                logger.error(f"{blueprint} template not found in kin directory")
else:
    logger.error(f"kin templates directory not found: {kin_templates_dir}")

# Initialize Atlas blueprint specifically
logger.info("Initializing Atlas blueprint specifically")
try:
    from initialize_atlas import initialize_atlas_blueprint
    initialize_atlas_blueprint()
    logger.info("Atlas blueprint initialized successfully")
except Exception as e:
    logger.error(f"Error initializing Atlas blueprint: {str(e)}")

# Ensure analysis mode exists in all templates
ensure_analysis_mode_exists()

# Generate modes.txt for all blueprints
def generate_modes_txt_for_all(force=False):
    """Generate modes.txt files for all blueprint templates."""
    logger.info(f"Generating modes.txt files for all blueprint templates (force={force})")
    try:
        # Import the generate_modes_txt script
        from generate_modes_txt import main as generate_modes_main
        # Run the script with sys.argv set to just the script name (no arguments)
        import sys
        original_argv = sys.argv
        sys.argv = [sys.argv[0]]
        if force:
            sys.argv.append("--force")
        generate_modes_main()
        sys.argv = original_argv
        logger.info("Completed modes.txt generation for all blueprints")
    except Exception as e:
        logger.error(f"Error generating modes.txt files: {str(e)}")

# Function to start the Next.js server for a kin's website
def start_kin_website_server(blueprint, kin_id, port=3000):
    """
    Start the Next.js server for a kin's website.
    
    Args:
        blueprint: Blueprint name
        kin_id: Kin ID
        port: Port to run the server on (default: 3000)
        
    Returns:
        The subprocess object for the server
    """
    try:
        # Get kin path
        from services.file_service import get_kin_path
        kin_path = get_kin_path(blueprint, kin_id)
        
        # Check if kin exists
        if not os.path.exists(kin_path):
            logger.error(f"Kin '{kin_id}' not found for blueprint '{blueprint}'")
            return None
        
        # Check if website directory exists
        website_dir = os.path.join(kin_path, "website")
        if not os.path.exists(website_dir):
            logger.error(f"Website directory not found for {blueprint}/{kin_id}")
            return None
        
        # Start the Next.js server
        logger.info(f"Starting Next.js server for {blueprint}/{kin_id} on port {port}")
        
        # Use npm start to run the production server
        process = subprocess.Popen(
            ["npm", "start", "--", "-p", str(port)],
            cwd=website_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        logger.info(f"Next.js server started with PID {process.pid}")
        return process
        
    except Exception as e:
        logger.error(f"Error starting Next.js server: {str(e)}")
        return None

# Commented out autonomous thinking scheduler
"""
# Set up scheduler for autonomous thinking
def run_autonomous_thinking():
    logger.info("Running scheduled autonomous thinking for therapykindouble/WarmMink92")
    try:
        # Construct the path to the script
        script_path = os.path.join(os.path.dirname(__file__), "autonomous-thinking.py")
        
        # Run the script as a subprocess
        result = subprocess.run(
            [sys.executable, script_path, "therapykindouble", "WarmMink92", "--iterations", "3"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            logger.info("Autonomous thinking completed successfully")
        else:
            logger.error(f"Autonomous thinking failed with exit code {result.returncode}")
            logger.error(f"Error output: {result.stderr}")
            
    except Exception as e:
        logger.error(f"Error running autonomous thinking: {str(e)}")

# Initialize the scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(func=run_autonomous_thinking, trigger="interval", hours=1)
scheduler.start()

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())
"""

# Modes.txt generation is disabled during startup
# To generate modes.txt files, use the generate_modes_txt.py script directly
# or call the API endpoint

if __name__ == '__main__':
    # Get port from environment variable (for Render compatibility)
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
