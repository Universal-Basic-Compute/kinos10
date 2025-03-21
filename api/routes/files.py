from flask import Blueprint, request, jsonify
import os
import json
import datetime
import base64
from config import CUSTOMERS_DIR, logger
from services.file_service import get_project_path
from utils.helpers import should_ignore_file, load_gitignore

files_bp = Blueprint('files', __name__)

@files_bp.route('/projects/<path:project_path>/content', methods=['GET'])
def get_project_content(project_path):
    """
    Endpoint to get the content of all files in a project folder as JSON.
    Optional query parameter 'path' to filter by specific file or directory.
    
    Project path can be either:
    - customer/template
    - customer/project_id
    """
    try:
        # Parse the project path
        parts = project_path.split('/')
        if len(parts) != 2:
            return jsonify({"error": "Invalid project path format"}), 400
            
        customer, project_id = parts
        
        # Validate customer
        if not os.path.exists(os.path.join(CUSTOMERS_DIR, customer)):
            return jsonify({"error": f"Customer '{customer}' not found"}), 404
            
        # Get the full project path
        full_project_path = get_project_path(customer, project_id)
        if not os.path.exists(full_project_path):
            return jsonify({"error": f"Project '{project_id}' not found for customer '{customer}'"}), 404
        
        # Get optional path parameter
        path_filter = request.args.get('path', '')
        
        # Normalize the path filter to prevent directory traversal
        path_filter = os.path.normpath(path_filter).lstrip('/')
        
        # Combine project path with path filter
        target_path = os.path.join(full_project_path, path_filter)
        
        # Security check to prevent directory traversal
        if not os.path.abspath(target_path).startswith(os.path.abspath(full_project_path)):
            return jsonify({"error": "Invalid path parameter"}), 403
            
        # Check if the target path exists
        if not os.path.exists(target_path):
            return jsonify({"error": f"Path '{path_filter}' not found in project"}), 404
        
        # Load gitignore patterns
        ignore_patterns = load_gitignore(full_project_path)
        
        # Get the content
        if os.path.isfile(target_path):
            # Single file
            try:
                with open(target_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return jsonify({
                    "path": path_filter,
                    "content": content,
                    "is_directory": False
                })
            except UnicodeDecodeError:
                # Handle binary files
                return jsonify({
                    "path": path_filter,
                    "content": "Binary file not displayed",
                    "is_directory": False,
                    "is_binary": True
                })
        else:
            # Directory - get all files recursively
            result = {"path": path_filter, "is_directory": True, "files": []}
            
            for root, dirs, files in os.walk(target_path):
                # Filter directories to avoid walking into ignored directories
                dirs[:] = [d for d in dirs if not should_ignore_file(os.path.relpath(os.path.join(root, d), full_project_path), ignore_patterns)]
                
                for file in files:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, full_project_path)
                    
                    # Skip ignored files
                    if should_ignore_file(rel_path, ignore_patterns):
                        continue
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            file_content = f.read()
                        
                        result["files"].append({
                            "path": rel_path,
                            "content": file_content,
                            "is_binary": False
                        })
                    except UnicodeDecodeError:
                        # Handle binary files
                        result["files"].append({
                            "path": rel_path,
                            "content": "Binary file not displayed",
                            "is_binary": True
                        })
            
            return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error getting project content: {str(e)}")
        return jsonify({"error": str(e)}), 500

@files_bp.route('/projects/<path:project_path>/files', methods=['GET'])
def get_project_files(project_path):
    """
    Endpoint to get a list of files in a project.
    Project path can be either:
    - customer/template
    - customer/project_id
    """
    try:
        # Parse the project path
        parts = project_path.split('/')
        if len(parts) != 2:
            return jsonify({"error": "Invalid project path format"}), 400
            
        customer, project_id = parts
        
        # Validate customer
        if not os.path.exists(os.path.join(CUSTOMERS_DIR, customer)):
            return jsonify({"error": f"Customer '{customer}' not found"}), 404
            
        # Get the full project path
        full_project_path = get_project_path(customer, project_id)
        if not os.path.exists(full_project_path):
            return jsonify({"error": f"Project '{project_id}' not found for customer '{customer}'"}), 404
        
        # Load gitignore patterns
        ignore_patterns = load_gitignore(full_project_path)
        
        # Get list of files
        files = []
        for root, dirs, filenames in os.walk(full_project_path):
            # Filter directories to avoid walking into ignored directories
            dirs[:] = [d for d in dirs if not should_ignore_file(os.path.relpath(os.path.join(root, d), full_project_path), ignore_patterns)]
            
            for filename in filenames:
                file_path = os.path.join(root, filename)
                rel_path = os.path.relpath(file_path, full_project_path)
                
                # Skip ignored files
                if should_ignore_file(rel_path, ignore_patterns):
                    continue
                    
                files.append({
                    "path": rel_path,
                    "type": "file",
                    "last_modified": datetime.datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
                })
        
        return jsonify({"files": files})
        
    except Exception as e:
        logger.error(f"Error getting project files: {str(e)}")
        return jsonify({"error": str(e)}), 500

@files_bp.route('/projects/<path:project_path>/files/<path:file_path>', methods=['GET'])
def get_file_content(project_path, file_path):
    """
    Endpoint to get the content of a file.
    Project path can be either:
    - customer/template
    - customer/project_id
    """
    try:
        # Parse the project path
        parts = project_path.split('/')
        if len(parts) != 2:
            return jsonify({"error": "Invalid project path format"}), 400
            
        customer, project_id = parts
        
        # Validate customer
        if not os.path.exists(os.path.join(CUSTOMERS_DIR, customer)):
            return jsonify({"error": f"Customer '{customer}' not found"}), 404
            
        # Get the full project path
        full_project_path = get_project_path(customer, project_id)
        if not os.path.exists(full_project_path):
            return jsonify({"error": f"Project '{project_id}' not found for customer '{customer}'"}), 404
        
        # Get file content
        file_full_path = os.path.join(full_project_path, file_path)
        
        # Security check to prevent directory traversal
        if not os.path.abspath(file_full_path).startswith(os.path.abspath(full_project_path)):
            return jsonify({"error": "Invalid file path"}), 403
        
        if not os.path.exists(file_full_path) or not os.path.isfile(file_full_path):
            # For .gitignore specifically, return a 404 but with a proper content type
            # so the client can handle it gracefully
            if file_path == '.gitignore':
                return "", 404, {'Content-Type': 'text/plain; charset=utf-8'}
            return jsonify({"error": f"File '{file_path}' not found"}), 404
        
        # Read file content
        with open(file_full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Determine content type based on file extension
        extension = os.path.splitext(file_path)[1].lower()
        if extension in ['.jpg', '.jpeg', '.png', '.gif']:
            # For images, return base64 encoded data
            with open(file_full_path, 'rb') as f:
                content = base64.b64encode(f.read()).decode('utf-8')
            return jsonify({"content": content, "type": "image"})
        else:
            # For text files, return the content directly
            return content, 200, {'Content-Type': 'text/plain; charset=utf-8'}
        
    except Exception as e:
        logger.error(f"Error getting file content: {str(e)}")
        return jsonify({"error": str(e)}), 500
