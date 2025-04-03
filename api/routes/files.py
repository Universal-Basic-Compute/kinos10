from flask import Blueprint, request, jsonify
import os
import json
import datetime
import base64
from config import blueprintS_DIR, logger
from services.file_service import get_kin_path
from utils.helpers import should_ignore_file, load_gitignore

files_bp = Blueprint('files', __name__)

@files_bp.route('/kins/<path:kin_path>/content', methods=['GET'])
def get_kin_content(kin_path):
    """
    Endpoint to get the content of all files in a kin folder as JSON.
    Optional query parameter 'path' to filter by specific file or directory.
    
    kin path can be either:
    - blueprint/template
    - blueprint/kin_id
    """
    try:
        # Parse the kin path
        parts = kin_path.split('/')
        if len(parts) != 2:
            return jsonify({"error": "Invalid kin path format"}), 400
            
        blueprint, kin_id = parts
        
        # Validate blueprint
        if not os.path.exists(os.path.join(blueprintS_DIR, blueprint)):
            return jsonify({"error": f"blueprint '{blueprint}' not found"}), 404
            
        # Get the full kin path
        full_kin_path = get_kin_path(blueprint, kin_id)
        if not os.path.exists(full_kin_path):
            return jsonify({"error": f"kin '{kin_id}' not found for blueprint '{blueprint}'"}), 404
        
        # Get optional path parameter
        path_filter = request.args.get('path', '')
        
        # Normalize the path filter to prevent directory traversal
        path_filter = os.path.normpath(path_filter).lstrip('/')
        
        # Combine kin path with path filter
        target_path = os.path.join(full_kin_path, path_filter)
        
        # Security check to prevent directory traversal
        if not os.path.abspath(target_path).startswith(os.path.abspath(full_kin_path)):
            return jsonify({"error": "Invalid path parameter"}), 403
            
        # Check if the target path exists
        if not os.path.exists(target_path):
            # If it's a directory path that doesn't exist, return empty JSON structure
            # instead of 404 error
            if path_filter and not os.path.splitext(path_filter)[1]:  # No file extension suggests it's a directory
                return jsonify({
                    "path": path_filter,
                    "is_directory": True,
                    "files": []
                })
            else:
                return jsonify({"error": f"Path '{path_filter}' not found in kin"}), 404
        
        # Load gitignore patterns
        ignore_patterns = load_gitignore(full_kin_path)
        
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
                dirs[:] = [d for d in dirs if not should_ignore_file(os.path.relpath(os.path.join(root, d), full_kin_path), ignore_patterns)]
                
                for file in files:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, full_kin_path)
                    
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
        logger.error(f"Error getting kin content: {str(e)}")
        return jsonify({"error": str(e)}), 500

@files_bp.route('/kins/<path:kin_path>/files', methods=['GET'])
def get_kin_files(kin_path):
    """
    Endpoint to get a list of files in a kin.
    kin path can be either:
    - blueprint/template
    - blueprint/kin_id
    """
    try:
        # Parse the kin path
        parts = kin_path.split('/')
        if len(parts) != 2:
            return jsonify({"error": "Invalid kin path format"}), 400
            
        blueprint, kin_id = parts
        
        # Validate blueprint
        if not os.path.exists(os.path.join(blueprintS_DIR, blueprint)):
            return jsonify({"error": f"blueprint '{blueprint}' not found"}), 404
            
        # Get the full kin path
        full_kin_path = get_kin_path(blueprint, kin_id)
        if not os.path.exists(full_kin_path):
            return jsonify({"error": f"kin '{kin_id}' not found for blueprint '{blueprint}'"}), 404
        
        # Load gitignore patterns
        ignore_patterns = load_gitignore(full_kin_path)
        
        # Get list of files
        files = []
        for root, dirs, filenames in os.walk(full_kin_path):
            # Filter directories to avoid walking into ignored directories
            dirs[:] = [d for d in dirs if not should_ignore_file(os.path.relpath(os.path.join(root, d), full_kin_path), ignore_patterns)]
            
            for filename in filenames:
                file_path = os.path.join(root, filename)
                rel_path = os.path.relpath(file_path, full_kin_path)
                
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
        logger.error(f"Error getting kin files: {str(e)}")
        return jsonify({"error": str(e)}), 500

@files_bp.route('/kins/<path:kin_path>/files/<path:file_path>', methods=['GET'])
def get_file_content(kin_path, file_path):
    """
    Endpoint to get the content of a file.
    kin path can be either:
    - blueprint/template
    - blueprint/kin_id
    """
    try:
        # Parse the kin path
        parts = kin_path.split('/')
        if len(parts) != 2:
            return jsonify({"error": "Invalid kin path format"}), 400
            
        blueprint, kin_id = parts
        
        # Validate blueprint
        if not os.path.exists(os.path.join(blueprintS_DIR, blueprint)):
            return jsonify({"error": f"blueprint '{blueprint}' not found"}), 404
            
        # Get the full kin path
        full_kin_path = get_kin_path(blueprint, kin_id)
        if not os.path.exists(full_kin_path):
            return jsonify({"error": f"kin '{kin_id}' not found for blueprint '{blueprint}'"}), 404
        
        # Get file content
        file_full_path = os.path.join(full_kin_path, file_path)
        
        # Security check to prevent directory traversal
        if not os.path.abspath(file_full_path).startswith(os.path.abspath(full_kin_path)):
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
