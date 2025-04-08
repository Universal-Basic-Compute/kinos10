from flask import Blueprint, request, jsonify
import os
import sys
import json
import re
import datetime
import requests
from config import blueprintS_DIR, logger
from services.file_service import get_kin_path, initialize_kin
from services.claude_service import build_context
from services.aider_service import call_aider_with_context

kins_bp = Blueprint('kins', __name__)

@kins_bp.route('/kins', methods=['POST'])
def create_kin():
    """
    Endpoint to initialize a new kin.
    """
    try:
        data = request.json
        kin_name = data.get('kin_name', '')
        blueprint = data.get('blueprint', '')
        template_override = data.get('template_override')
        
        if not kin_name:
            return jsonify({"error": "kin name is required"}), 400
        
        if not blueprint:
            return jsonify({"error": "blueprint is required"}), 400
        
        # Use kin_name as kin_id if it's a simple name (no spaces or special chars)
        if re.match(r'^[a-zA-Z0-9_-]+$', kin_name):
            kin_id = kin_name
        else:
            kin_id = None  # Let the function generate a UUID
        
        kin_id = initialize_kin(blueprint, kin_name, template_override, kin_id)
        
        return jsonify({
            "kin_id": kin_id,
            "blueprint": blueprint,
            "status": "created"
        })
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error creating kin: {str(e)}")
        return jsonify({"error": str(e)}), 500

@kins_bp.route('/kins/<blueprint>/kins', methods=['GET'])
def get_blueprint_kins(blueprint):
    """
    Endpoint to get a list of kins for a blueprint.
    """
    try:
        # Validate blueprint
        blueprint_dir = os.path.join(blueprintS_DIR, blueprint)
        if not os.path.exists(blueprint_dir):
            return jsonify({"error": f"blueprint '{blueprint}' not found"}), 404
        
        # Get list of kins
        kins = ["template"]  # Always include template
        
        # Add other kins if they exist
        kins_dir = os.path.join(blueprint_dir, "kins")
        if os.path.exists(kins_dir):
            for kin_id in os.listdir(kins_dir):
                kin_path = os.path.join(kins_dir, kin_id)
                if os.path.isdir(kin_path):
                    kins.append(kin_id)
        
        return jsonify({"kins": kins})
        
    except Exception as e:
        logger.error(f"Error getting blueprint kins: {str(e)}")
        return jsonify({"error": str(e)}), 500

@kins_bp.route('/blueprints', methods=['GET'])
def get_blueprints():
    """
    Endpoint to get a list of all blueprints.
    """
    try:
        # Get list of all blueprints
        blueprints = []
        if os.path.exists(blueprintS_DIR):
            blueprints = [d for d in os.listdir(blueprintS_DIR) 
                        if os.path.isdir(os.path.join(blueprintS_DIR, d))]
        
        return jsonify({
            "blueprints": blueprints
        })
        
    except Exception as e:
        logger.error(f"Error getting blueprints: {str(e)}")
        return jsonify({"error": str(e)}), 500

@kins_bp.route('/kins/all', methods=['GET'])
def get_all_kins():
    """
    Endpoint to get all blueprints and their kins.
    """
    try:
        # Get list of all blueprints
        blueprints = []
        if os.path.exists(blueprintS_DIR):
            blueprints = [d for d in os.listdir(blueprintS_DIR) 
                        if os.path.isdir(os.path.join(blueprintS_DIR, d))]
        
        # Get kins for each blueprint
        all_kins = {}
        for blueprint in blueprints:
            kins = ["template"]  # Always include template
            
            # Add other kins if they exist
            kins_dir = os.path.join(blueprintS_DIR, blueprint, "kins")
            if os.path.exists(kins_dir):
                for kin_id in os.listdir(kins_dir):
                    kin_path = os.path.join(kins_dir, kin_id)
                    if os.path.isdir(kin_path):
                        kins.append(kin_id)
            
            all_kins[blueprint] = kins
        
        return jsonify({
            "blueprints": blueprints,
            "kins": all_kins
        })
        
    except Exception as e:
        logger.error(f"Error getting all kins: {str(e)}")
        return jsonify({"error": str(e)}), 500

@kins_bp.route('/blueprints/<blueprint>/initialize', methods=['POST'])
def initialize_blueprint(blueprint):
    """
    Endpoint to manually initialize a blueprint.
    """
    try:
        # Path to templates in the kin
        kin_templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "blueprints")
        blueprint_template_dir = os.path.join(kin_templates_dir, blueprint, "template")
        
        # Check if blueprint template exists in kin
        if not os.path.exists(blueprint_template_dir) or not os.path.isdir(blueprint_template_dir):
            return jsonify({"error": f"blueprint template '{blueprint}' not found in kin"}), 404
        
        # Create blueprint directory if it doesn't exist
        blueprint_dir = os.path.join(blueprintS_DIR, blueprint)
        if not os.path.exists(blueprint_dir):
            logger.info(f"Creating blueprint directory: {blueprint_dir}")
            os.makedirs(blueprint_dir, exist_ok=True)
        
        # Create kins directory if it doesn't exist
        kins_dir = os.path.join(blueprint_dir, "kins")
        if not os.path.exists(kins_dir):
            logger.info(f"Creating kins directory: {kins_dir}")
            os.makedirs(kins_dir, exist_ok=True)
        
        # Copy template (overwrite if exists)
        dest_template_dir = os.path.join(blueprint_dir, "template")
        if os.path.exists(dest_template_dir):
            import shutil
            try:
                shutil.rmtree(dest_template_dir)
            except PermissionError:
                logger.warning(f"Permission error removing {dest_template_dir}, trying to remove files individually")
                # Try to remove files individually
                for root, dirs, files in os.walk(dest_template_dir, topdown=False):
                    for name in files:
                        try:
                            os.remove(os.path.join(root, name))
                        except:
                            pass
                    for name in dirs:
                        try:
                            os.rmdir(os.path.join(root, name))
                        except:
                            pass
                try:
                    os.rmdir(dest_template_dir)
                except:
                    pass
        
        logger.info(f"Copying template for blueprint {blueprint} to app data")
        
        # Custom copy function to skip .git directory and handle permission errors
        def custom_copy_tree(src, dst):
            try:
                os.makedirs(dst, exist_ok=True)
                
                # Get list of items to copy (excluding .git)
                items_to_copy = [item for item in os.listdir(src) if item != '.git']
                
                for item in items_to_copy:
                    s = os.path.join(src, item)
                    d = os.path.join(dst, item)
                    
                    try:
                        if os.path.isdir(s):
                            custom_copy_tree(s, d)
                        else:
                            import shutil
                            shutil.copy2(s, d)
                    except PermissionError:
                        logger.warning(f"Permission error copying {s} to {d}, skipping")
                    except Exception as e:
                        logger.warning(f"Error copying {s} to {d}: {str(e)}, skipping")
            except Exception as e:
                logger.warning(f"Error in custom_copy_tree for {src} to {dst}: {str(e)}")
        
        # Use custom copy function instead of shutil.copytree
        custom_copy_tree(blueprint_template_dir, dest_template_dir)
        
        return jsonify({"status": "success", "message": f"blueprint '{blueprint}' initialized"})
        
    except Exception as e:
        logger.error(f"Error initializing blueprint: {str(e)}")
        return jsonify({"error": str(e)}), 500

@kins_bp.route('/kins/<blueprint>/<kin_id>/build', methods=['GET', 'POST'])
def build_kin(blueprint, kin_id):
    """
    Endpoint to send a message to Aider for file creation/modification without Claude response.
    Similar to the messages endpoint but only processes with Aider and returns its response.
    Supports both GET (with query params) and POST (with JSON body).
    """
    try:
        # Parse request data based on method
        if request.method == 'GET':
            # Extract parameters from query string
            message_content = request.args.get('message', '')
            # Remove quotes if present (since query params might include them)
            message_content = message_content.strip('"\'')
            
            # Get optional parameters
            addSystem = request.args.get('addSystem')
            min_files = request.args.get('min_files', 5)
            max_files = request.args.get('max_files', 15)
            attachments = []
            
            # Create a data dict to match POST format
            data = {
                'message': message_content,
                'addSystem': addSystem,
                'min_files': min_files,
                'max_files': max_files,
                'attachments': attachments
            }
        else:  # POST
            # Parse request data
            data = request.json
            
            # Support both formats: new format with 'message' and original format with 'content'
            message_content = data.get('message', data.get('content', ''))
            
            # Get optional fields
            addSystem = data.get('addSystem', None)  # Optional additional system instructions
            attachments = data.get('attachments', [])
            
            # Get optional parameters for context building
            min_files = data.get('min_files', 5)  # Default to 5
            max_files = data.get('max_files', 15)  # Default to 15
        
        # Validate the values
        try:
            min_files = int(min_files)
            max_files = int(max_files)
            if min_files < 1:
                min_files = 1
            if max_files < min_files:
                max_files = min_files
        except (ValueError, TypeError):
            min_files = 5
            max_files = 15

        # Validate blueprint
        if not os.path.exists(os.path.join(blueprintS_DIR, blueprint)):
            return jsonify({"error": f"blueprint '{blueprint}' not found"}), 404
            
        kin_path = get_kin_path(blueprint, kin_id)
        
        # Check if kin exists
        if not os.path.exists(kin_path):
            return jsonify({"error": f"kin '{kin_id}' not found for blueprint '{blueprint}'"}), 404
        
        # Build context (select relevant files)
        selected_files, _ = build_context(
            blueprint, 
            kin_id, 
            message_content, 
            attachments, 
            kin_path, 
            None, 
            None, 
            addSystem, 
            history_length=2,
            min_files=min_files,
            max_files=max_files
        )
        
        # Log the selected files
        logger.info(f"Selected files for build context: {selected_files}")
        
        # Call Aider with the selected context and wait for response
        try:
            # Call Aider synchronously (not in a thread)
            aider_response = call_aider_with_context(kin_path, selected_files, message_content, addSystem=addSystem)
            logger.info("Aider processing completed")
            
            # Return the Aider response
            return jsonify({
                "status": "completed",
                "response": aider_response
            })
            
        except Exception as e:
            logger.error(f"Error in Aider processing: {str(e)}")
            return jsonify({"error": f"Error in Aider processing: {str(e)}"}), 500
        
    except Exception as e:
        logger.error(f"Error processing build request: {str(e)}")
        return jsonify({"error": str(e)}), 500

@kins_bp.route('/kins/<blueprint>/<kin_id>/reset', methods=['POST'])
def reset_kin(blueprint, kin_id):
    """
    Endpoint to reset a kin to its initial template state.
    """
    try:
        # Validate blueprint
        if not os.path.exists(os.path.join(blueprintS_DIR, blueprint)):
            return jsonify({"error": f"blueprint '{blueprint}' not found"}), 404
            
        # Get the kin path
        kin_path = get_kin_path(blueprint, kin_id)
        if not os.path.exists(kin_path):
            return jsonify({"error": f"kin '{kin_id}' not found for blueprint '{blueprint}'"}), 404
        
        # Get the template path
        template_path = os.path.join(blueprintS_DIR, blueprint, "template")
        if not os.path.exists(template_path):
            return jsonify({"error": f"Template not found for blueprint '{blueprint}'"}), 404
        
        # Backup the kin name before deleting
        kin_name = kin_id  # Use kin_id as fallback
        kin_info_path = os.path.join(kin_path, "kin_info.json")
        if os.path.exists(kin_info_path):
            try:
                with open(kin_info_path, 'r') as f:
                    kin_info = json.load(f)
                    kin_name = kin_info.get('name', kin_id)
            except:
                logger.warning(f"Could not read kin_info.json for {blueprint}/{kin_id}")
        
        # Delete the kin directory
        import shutil
        try:
            shutil.rmtree(kin_path)
        except PermissionError:
            logger.warning(f"Permission error removing {kin_path}, trying to remove files individually")
            # Try to remove files individually
            for root, dirs, files in os.walk(kin_path, topdown=False):
                for name in files:
                    try:
                        os.remove(os.path.join(root, name))
                    except:
                        pass
                for name in dirs:
                    try:
                        os.rmdir(os.path.join(root, name))
                    except:
                        pass
            try:
                os.rmdir(kin_path)
            except:
                return jsonify({"error": f"Could not completely remove kin directory. Please try again."}), 500
        
        # Reinitialize the kin from template
        initialize_kin(blueprint, kin_name, kin_id=kin_id)
        
        return jsonify({
            "status": "success",
            "message": f"kin '{kin_id}' has been reset to template state"
        })
        
    except Exception as e:
        logger.error(f"Error resetting kin: {str(e)}")
        return jsonify({"error": str(e)}), 500

@kins_bp.route('/blueprints/<blueprint>/reset', methods=['POST'])
def reset_blueprint(blueprint):
    """
    Endpoint to reset a blueprint and all its kins to initial template state.
    If the blueprint doesn't exist, it will be created.
    """
    try:
        # Check if blueprint exists
        blueprint_dir = os.path.join(blueprintS_DIR, blueprint)
        if not os.path.exists(blueprint_dir):
            logger.info(f"blueprint '{blueprint}' not found, creating it")
            
            # Create blueprint directory
            os.makedirs(blueprint_dir, exist_ok=True)
            
            # Create kins directory
            kins_dir = os.path.join(blueprint_dir, "kins")
            os.makedirs(kins_dir, exist_ok=True)
        
        # First, reinitialize the blueprint template
        # This will ensure we have the latest template from the kin
        response = initialize_blueprint(blueprint)
        if isinstance(response, tuple) and response[1] != 200:
            # If initialize_blueprint returned an error, pass it through
            return response
        
        # Get list of kins
        kins_dir = os.path.join(blueprint_dir, "kins")
        if not os.path.exists(kins_dir):
            # No kins directory, nothing more to do
            return jsonify({
                "status": "success",
                "message": f"blueprint '{blueprint}' has been reset (no kins found)"
            })
        
        # Get all kins for this blueprint
        kins = []
        for kin_id in os.listdir(kins_dir):
            kin_path = os.path.join(kins_dir, kin_id)
            if os.path.isdir(kin_path):
                kins.append(kin_id)
        
        # Reset each kin
        reset_results = []
        for kin_id in kins:
            try:
                # Get kin name before resetting
                kin_name = kin_id  # Default fallback
                kin_info_path = os.path.join(kins_dir, kin_id, "kin_info.json")
                if os.path.exists(kin_info_path):
                    try:
                        with open(kin_info_path, 'r') as f:
                            kin_info = json.load(f)
                            kin_name = kin_info.get('name', kin_id)
                    except:
                        logger.warning(f"Could not read kin_info.json for {blueprint}/{kin_id}")
                
                # Delete the kin directory
                kin_path = os.path.join(kins_dir, kin_id)
                import shutil
                try:
                    shutil.rmtree(kin_path)
                except PermissionError:
                    logger.warning(f"Permission error removing {kin_path}, trying to remove files individually")
                    # Try to remove files individually
                    for root, dirs, files in os.walk(kin_path, topdown=False):
                        for name in files:
                            try:
                                os.remove(os.path.join(root, name))
                            except:
                                pass
                        for name in dirs:
                            try:
                                os.rmdir(os.path.join(root, name))
                            except:
                                pass
                    try:
                        os.rmdir(kin_path)
                    except:
                        reset_results.append({
                            "kin_id": kin_id,
                            "status": "error",
                            "message": "Could not completely remove kin directory"
                        })
                        continue
                
                # Reinitialize the kin from template
                initialize_kin(blueprint, kin_name, kin_id=kin_id)
                
                reset_results.append({
                    "kin_id": kin_id,
                    "status": "success",
                    "message": f"kin reset to template state"
                })
                
            except Exception as e:
                logger.error(f"Error resetting kin {kin_id}: {str(e)}")
                reset_results.append({
                    "kin_id": kin_id,
                    "status": "error",
                    "message": str(e)
                })
        
        return jsonify({
            "status": "success",
            "message": f"blueprint '{blueprint}' has been reset",
            "kins_reset": len(reset_results),
            "results": reset_results
        })
        
    except Exception as e:
        logger.error(f"Error resetting blueprint: {str(e)}")
        return jsonify({"error": str(e)}), 500

@kins_bp.route('/kins/<blueprint>/<kin_id>/rename', methods=['POST'])
def rename_kin(blueprint, kin_id):
    """
    Endpoint to rename a kin.
    Expects a JSON body with the new name: {"new_name": "New Kin Name"}
    """
    try:
        # Parse request data
        data = request.json
        new_name = data.get('new_name', '')
        
        # Validate new name
        if not new_name:
            return jsonify({"error": "New name is required"}), 400
        
        # Validate blueprint
        if not os.path.exists(os.path.join(blueprintS_DIR, blueprint)):
            return jsonify({"error": f"blueprint '{blueprint}' not found"}), 404
            
        # Get the kin path
        kin_path = get_kin_path(blueprint, kin_id)
        if not os.path.exists(kin_path):
            return jsonify({"error": f"kin '{kin_id}' not found for blueprint '{blueprint}'"}), 404
        
        # Check if this is a template (which shouldn't be renamed)
        if kin_id == "template":
            return jsonify({"error": "Cannot rename the template kin"}), 400
        
        # Update the kin_info.json file or create it if it doesn't exist
        kin_info_path = os.path.join(kin_path, "kin_info.json")
        kin_info = {}
        
        if os.path.exists(kin_info_path):
            try:
                with open(kin_info_path, 'r') as f:
                    kin_info = json.load(f)
            except Exception as e:
                logger.warning(f"Error reading kin_info.json: {str(e)}")
        
        # Update the name
        kin_info['name'] = new_name
        kin_info['updated_at'] = datetime.datetime.now().isoformat()
        
        # Save the updated info
        with open(kin_info_path, 'w') as f:
            json.dump(kin_info, f, indent=2)
        
        logger.info(f"Renamed kin {blueprint}/{kin_id} to '{new_name}'")
        
        return jsonify({
            "status": "success",
            "message": f"kin '{kin_id}' renamed to '{new_name}'",
            "kin_id": kin_id,
            "name": new_name
        })
        
    except Exception as e:
        logger.error(f"Error renaming kin: {str(e)}")
        return jsonify({"error": str(e)}), 500

@kins_bp.route('/kins/<blueprint>/<kin_id>/git_history', methods=['GET'])
def get_git_history(blueprint, kin_id):
    """
    Endpoint to get Git commit history for a kin.
    """
    try:
        # Validate blueprint and kin
        if not os.path.exists(os.path.join(blueprintS_DIR, blueprint)):
            return jsonify({"error": f"blueprint '{blueprint}' not found"}), 404
            
        kin_path = get_kin_path(blueprint, kin_id)
        if not os.path.exists(kin_path):
            return jsonify({"error": f"kin '{kin_id}' not found for blueprint '{blueprint}'"}), 404
        
        # Check if .git directory exists
        git_dir = os.path.join(kin_path, ".git")
        if not os.path.exists(git_dir) or not os.path.isdir(git_dir):
            return jsonify({"error": "No Git repository found for this kin"}), 404
        
        # Get git commit history using git log
        try:
            # Use git log to get commit history (last 20 commits)
            import subprocess
            result = subprocess.run(
                ["git", "log", "--pretty=format:%h|%an|%ad|%s", "--date=short", "-n", "20"],
                cwd=kin_path,
                text=True,
                capture_output=True,
                check=True
            )
            
            # Parse the output
            commits = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split('|', 3)
                    if len(parts) == 4:
                        hash, author, date, message = parts
                        commits.append({
                            "hash": hash,
                            "author": author,
                            "date": date,
                            "message": message
                        })
            
            return jsonify({"commits": commits})
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Git command failed: {e.stderr}")
            return jsonify({"error": f"Git command failed: {e.stderr}"}), 500
        
    except Exception as e:
        logger.error(f"Error getting Git history: {str(e)}")
        return jsonify({"error": str(e)}), 500

@kins_bp.route('/kins/<blueprint>/<kin_id>/autonomous_thinking', methods=['GET', 'POST'])
def trigger_autonomous_thinking(blueprint, kin_id):
    """
    Endpoint to trigger autonomous thinking for a kin.
    Supports both GET (with query params) and POST (with JSON body).
    
    Optional parameters:
    - iterations: Number of thinking iterations (default: 3)
    - wait_time: Wait time between iterations in seconds (default: 600 = 10 minutes)
    """
    try:
        # Parse request data based on method
        if request.method == 'GET':
            # Extract parameters from query string
            iterations = request.args.get('iterations', 3)
            wait_time = request.args.get('wait_time', 600)
            
            # Convert to integers
            try:
                iterations = int(iterations)
                wait_time = int(wait_time)
            except (ValueError, TypeError):
                iterations = 3
                wait_time = 600
                
            # Create a data dict to match POST format
            data = {
                'iterations': iterations,
                'wait_time': wait_time
            }
        else:  # POST
            # Parse request data
            data = request.json or {}
            import subprocess
            import sys
            iterations = data.get('iterations', 3)
            wait_time = data.get('wait_time', 600)
        
        # Validate blueprint and kin
        if not os.path.exists(os.path.join(blueprintS_DIR, blueprint)):
            return jsonify({"error": f"blueprint '{blueprint}' not found"}), 404
            
        kin_path = get_kin_path(blueprint, kin_id)
        if not os.path.exists(kin_path):
            return jsonify({"error": f"kin '{kin_id}' not found for blueprint '{blueprint}'"}), 404
        
        # Construct the path to the script
        script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "autonomous-thinking.py")
        
        # Run the script as a subprocess
        logger.info(f"Triggering autonomous thinking for {blueprint}/{kin_id} with {iterations} iterations")
        
        # Start the process in the background
        import threading
        def run_autonomous_thinking():
            try:
                result = subprocess.run(
                    [sys.executable, script_path, blueprint, kin_id, "--iterations", str(iterations), "--wait-time", str(wait_time)],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    logger.info(f"Autonomous thinking completed successfully for {blueprint}/{kin_id}")
                else:
                    logger.error(f"Autonomous thinking failed with exit code {result.returncode}")
                    logger.error(f"Error output: {result.stderr}")
            except Exception as e:
                logger.error(f"Error running autonomous thinking: {str(e)}")
        
        # Start the thread
        thread = threading.Thread(target=run_autonomous_thinking)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "status": "started",
            "message": f"Autonomous thinking started for {blueprint}/{kin_id}",
            "blueprint": blueprint,
            "kin_id": kin_id,
            "iterations": iterations,
            "wait_time": wait_time
        })
        
    except Exception as e:
        logger.error(f"Error triggering autonomous thinking: {str(e)}")
        return jsonify({"error": str(e)}), 500

@kins_bp.route('/kins/<blueprint>/<kin_id>/modes', methods=['GET'])
def get_kin_modes(blueprint, kin_id):
    """
    Endpoint to get available modes for a kin.
    """
    try:
        # Validate blueprint and kin
        if not os.path.exists(os.path.join(blueprintS_DIR, blueprint)):
            return jsonify({"error": f"blueprint '{blueprint}' not found"}), 404
            
        kin_path = get_kin_path(blueprint, kin_id)
        if not os.path.exists(kin_path):
            return jsonify({"error": f"kin '{kin_id}' not found for blueprint '{blueprint}'"}), 404
        
        # Check for modes directory
        modes_dir = os.path.join(kin_path, "modes")
        if not os.path.exists(modes_dir):
            return jsonify({"modes": []})
        
        # Get list of mode files
        modes = []
        for filename in os.listdir(modes_dir):
            if filename.endswith('.txt'):
                mode_name = os.path.splitext(filename)[0]
                mode_path = os.path.join(modes_dir, filename)
                
                # Read the first line of the file to get the title
                title = mode_name.capitalize()  # Default title
                try:
                    with open(mode_path, 'r', encoding='utf-8') as f:
                        first_line = f.readline().strip()
                        if first_line.startswith('# '):
                            title = first_line[2:].strip()
                except Exception as e:
                    logger.warning(f"Error reading mode file {mode_path}: {str(e)}")
                
                modes.append({
                    "id": mode_name,
                    "title": title
                })
        
        return jsonify({"modes": modes})
        
    except Exception as e:
        logger.error(f"Error getting kin modes: {str(e)}")
        return jsonify({"error": str(e)}), 500

@kins_bp.route('/blueprints/codeguardian/create', methods=['POST'])
def create_code_guardian_api():
    """
    Endpoint to create a CodeGuardian kin for a GitHub repository.
    
    Expected JSON body:
    {
        "github_url": "https://github.com/username/repo",
        "kin_name": "Optional custom name"  // Optional
    }
    """
    try:
        # Parse request data
        data = request.json
        github_url = data.get('github_url')
        kin_name = data.get('kin_name')
        
        # Validate required parameters
        if not github_url:
            return jsonify({"error": "GitHub URL is required"}), 400
        
        # Import the create_code_guardian function
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "blueprints", "codeguardian"))
        from create_code_guardian import create_code_guardian, extract_repo_info
        
        # Extract repository information for validation
        try:
            repo_info = extract_repo_info(github_url)
            logger.info(f"Repository information: {repo_info}")
        except ValueError as e:
            return jsonify({"error": f"Invalid GitHub URL: {str(e)}"}), 400
        
        # Create the CodeGuardian
        try:
            result = create_code_guardian(github_url, kin_name)
            if not result:
                return jsonify({"error": "Failed to create CodeGuardian"}), 500
            
            # If kin_name wasn't provided, it was generated based on the repo
            if not kin_name:
                kin_name = f"{repo_info['repo']}Guardian"
            
            return jsonify({
                "status": "success",
                "message": f"CodeGuardian '{kin_name}' created successfully for {repo_info['full_name']}",
                "blueprint": "codeguardian",
                "kin_id": kin_name,
                "repository": {
                    "owner": repo_info['owner'],
                    "repo": repo_info['repo'],
                    "url": github_url
                }
            })
            
        except Exception as e:
            logger.error(f"Error creating CodeGuardian: {str(e)}")
            return jsonify({"error": f"Error creating CodeGuardian: {str(e)}"}), 500
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return jsonify({"error": str(e)}), 500

@kins_bp.route('/blueprints/create_analysis_mode', methods=['POST'])
def create_analysis_mode():
    """
    Endpoint to create or replace the analysis mode file for each blueprint.
    This ensures that each blueprint template has a proper modes/analysis.txt file.
    """
    try:
        # Get list of blueprints from request or use all available blueprints
        data = request.json or {}
        blueprints = data.get('blueprints', None)
        
        # If no blueprints specified, get all available blueprints
        if not blueprints:
            if os.path.exists(blueprintS_DIR):
                blueprints = [d for d in os.listdir(blueprintS_DIR) 
                            if os.path.isdir(os.path.join(blueprintS_DIR, d))]
                logger.info(f"Processing all blueprints: {blueprints}")
            else:
                logger.error(f"blueprints directory not found: {blueprintS_DIR}")
                return jsonify({"error": "blueprints directory not found"}), 500
        
        # Standard content for the analysis.txt file
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
        
        # Process each blueprint
        results = []
        for blueprint in blueprints:
            result = {"blueprint": blueprint}
            
            # Path to the blueprint template directory
            template_dir = os.path.join(blueprintS_DIR, blueprint, "template")
            logger.info(f"Processing blueprint {blueprint}, template dir: {template_dir}")
            
            # Check if template directory exists
            if not os.path.exists(template_dir):
                logger.warning(f"Template directory not found for blueprint {blueprint}: {template_dir}")
                result["status"] = "error"
                result["message"] = f"Template directory not found: {template_dir}"
                results.append(result)
                continue
            
            # Path to the modes directory
            modes_dir = os.path.join(template_dir, "modes")
            logger.info(f"Modes directory path: {modes_dir}")
            
            # Create modes directory if it doesn't exist
            if not os.path.exists(modes_dir):
                try:
                    logger.info(f"Creating modes directory: {modes_dir}")
                    os.makedirs(modes_dir, exist_ok=True)
                except Exception as e:
                    logger.error(f"Error creating modes directory for {blueprint}: {str(e)}")
                    result["status"] = "error"
                    result["message"] = f"Error creating modes directory: {str(e)}"
                    results.append(result)
                    continue
            
            # Path to the analysis.txt file
            analysis_file = os.path.join(modes_dir, "analysis.txt")
            logger.info(f"Analysis file path: {analysis_file}")
            
            # Create or replace the analysis.txt file
            try:
                logger.info(f"Writing analysis.txt file for {blueprint}")
                with open(analysis_file, 'w', encoding='utf-8') as f:
                    f.write(analysis_content)
                result["status"] = "success"
                result["message"] = "Analysis mode file created/updated"
                
                # Verify the file was actually created
                if os.path.exists(analysis_file):
                    file_size = os.path.getsize(analysis_file)
                    logger.info(f"Successfully created analysis.txt for {blueprint}, size: {file_size} bytes")
                else:
                    logger.warning(f"File not found after creation attempt: {analysis_file}")
                    result["status"] = "error"
                    result["message"] = "File not found after creation attempt"
            except Exception as e:
                logger.error(f"Error creating analysis.txt for {blueprint}: {str(e)}")
                result["status"] = "error"
                result["message"] = f"Error creating analysis.txt: {str(e)}"
            
            results.append(result)
        
        return jsonify({
            "status": "completed",
            "results": results
        })
        
    except Exception as e:
        logger.error(f"Error creating analysis mode files: {str(e)}")
        return jsonify({"error": str(e)}), 500

@kins_bp.route('/kins/<blueprint>/<kin_id>/analysis', methods=['POST'])
def analyze_kin(blueprint, kin_id):
    """
    Endpoint to analyze a kin with Claude without modifying files.
    Similar to the messages endpoint but specifically for analysis purposes.
    """
    try:
        # Parse request data
        data = request.json
        message_content = data.get('message', '')
        model = data.get('model', 'claude-3-7-sonnet-latest')
        
        # Validate required parameters
        if not message_content:
            return jsonify({"error": "Message is required"}), 400
        
        # Validate blueprint and kin
        if not os.path.exists(os.path.join(blueprintS_DIR, blueprint)):
            return jsonify({"error": f"blueprint '{blueprint}' not found"}), 404
            
        kin_path = get_kin_path(blueprint, kin_id)
        if not os.path.exists(kin_path):
            return jsonify({"error": f"kin '{kin_id}' not found for blueprint '{blueprint}'"}), 404
        
        # Build context (select relevant files)
        selected_files, selected_mode = build_context(blueprint, kin_id, message_content, kin_path=kin_path, history_length=2)
        
        # Log the selected files and mode
        logger.info(f"Selected files for analysis: {selected_files}")
        logger.info(f"Analysis request with message: {message_content[:100]}...")
        if selected_mode:
            logger.info(f"Selected mode: {selected_mode}")
        
        # Use Claude to analyze the kin
        from services.claude_service import call_claude_with_context
        
        # Add specific system instructions for analysis mode
        analysis_system_instructions = """
        You are in analysis mode. Your task is to analyze the kin and provide insights without modifying any files.
        Focus on explaining the code, architecture, and design patterns.
        Provide detailed explanations and suggestions for improvement if asked.
        Do not generate code modifications or file changes unless explicitly requested.
        """
        
        # Call Claude to analyze the kin
        claude_response = call_claude_with_context(
            selected_files, 
            kin_path, 
            message_content,  # Ensure this is the actual user message
            model=model,
            is_new_message=False,
            addSystem=analysis_system_instructions,
            mode=selected_mode  # Pass the selected mode
        )
        
        response_data = {
            "status": "success",
            "response": claude_response
        }
        
        # Add selected_mode if one was determined
        if selected_mode:
            response_data["mode"] = selected_mode
            
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error analyzing kin: {str(e)}")
        return jsonify({"error": str(e)}), 500

@kins_bp.route('/kins/<blueprint>/<kin_id>/image', methods=['POST'])
def generate_kin_image(blueprint, kin_id):
    """
    Endpoint to generate an image based on a message using Ideogram API.
    Uses a direct HTTP call to Claude to create a detailed prompt based on the message and context.
    """
    try:
        # Parse request data
        data = request.json
        message_content = data.get('message', '')
        
        # If message is empty, check for 'content' for backward compatibility
        if not message_content and 'content' in data:
            message_content = data.get('content', '')
            
        # Optional parameters
        aspect_ratio = data.get('aspect_ratio', 'ASPECT_1_1')
        model = data.get('model', 'V_2')
        magic_prompt_option = data.get('magic_prompt_option', 'AUTO')
        
        # Validate required parameters
        if not message_content:
            return jsonify({"error": "Message is required"}), 400
        
        # Validate blueprint and kin
        if not os.path.exists(os.path.join(blueprintS_DIR, blueprint)):
            return jsonify({"error": f"blueprint '{blueprint}' not found"}), 404
            
        kin_path = get_kin_path(blueprint, kin_id)
        if not os.path.exists(kin_path):
            return jsonify({"error": f"kin '{kin_id}' not found for blueprint '{blueprint}'"}), 404
        
        # Build context (select relevant files)
        selected_files, _ = build_context(blueprint, kin_id, message_content, kin_path=kin_path)
        
        # Log the selected files
        logger.info(f"Selected files for image generation context: {selected_files}")
        
        # Load content of selected files for context
        file_contents = []
        for file in selected_files:
            file_path = os.path.join(kin_path, file)
            if os.path.exists(file_path) and os.path.isfile(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    file_contents.append(f"# File: {file}\n{content}")
                except Exception as e:
                    logger.error(f"Error reading file {file_path}: {str(e)}")
        
        # Combine file contents into a single context string
        context = "\n\n".join(file_contents)
        
        # Add specific system instructions for prompt creation
        prompt_system_instructions = """
        Your task is to create a concise, effective prompt for the Ideogram image generation API based on the user's message.
        Format your response as a single, focused prompt without explanations or commentary.

        The prompt should:
        - Be 1-3 sentences long
        - Describe the main subject and visual elements clearly
        - Include specific style keywords that Ideogram responds well to
        - Avoid overly complex instructions or multiple concepts
        """
        
        # Get API key from environment variable
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            logger.error("ANTHROPIC_API_KEY environment variable not set")
            return jsonify({"error": "Anthropic API key not configured"}), 500
        
        # Make a direct HTTP request to Claude API
        import requests
        
        # Prepare the request
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        # Prepare the payload
        payload = {
            "model": "claude-3-7-sonnet-latest",
            "max_tokens": 1024,
            "system": context + "\n\n" + prompt_system_instructions,
            "messages": [
                {
                    "role": "user", 
                    "content": f"Create a detailed image generation prompt based on this request: {message_content}"
                }
            ]
        }
        
        logger.info("Making direct HTTP request to Claude API for image prompt generation")
        
        # Make the request
        response = requests.post(url, headers=headers, json=payload)
        
        # Check if the request was successful
        if response.status_code != 200:
            logger.error(f"Claude API error: {response.status_code} - {response.text}")
            return jsonify({"error": f"Claude API error: {response.status_code}"}), 500
        
        # Parse the response
        claude_data = response.json()
        logger.info(f"Claude API response: {claude_data}")
        
        # Extract the text from the response
        if "content" in claude_data and len(claude_data["content"]) > 0:
            for content_item in claude_data["content"]:
                if content_item.get("type") == "text":
                    image_prompt = content_item.get("text", "").strip()
                    break
            else:
                # If no text content was found
                logger.error("No text content found in Claude response")
                image_prompt = message_content  # Fall back to original message
        else:
            logger.error("Empty content array in Claude response")
            image_prompt = message_content  # Fall back to original message
        
        logger.info(f"Generated image prompt: {image_prompt}")
        
        # Import the Ideogram service
        from services.ideogram_service import generate_image
        
        # Generate the image
        result = generate_image(image_prompt, aspect_ratio, model, magic_prompt_option)
        
        # Check for errors
        if "error" in result:
            logger.error(f"Ideogram API error: {result['error']}")
            return jsonify(result), 500
            
        # Verify we have data in the result
        if "data" not in result or not result["data"]:
            logger.error("Ideogram API returned no data")
            return jsonify({"error": "No image data returned from Ideogram API"}), 500
        
        # Get the image URL from the response
        image_url = None
        if "data" in result and len(result["data"]) > 0:
            if "url" in result["data"][0]:
                image_url = result["data"][0]["url"]
                logger.info(f"Got image URL from Ideogram: {image_url}")
            else:
                logger.error("No URL found in Ideogram response data")
                return jsonify({"error": "No image URL in response", "result": result}), 500
        
        if not image_url:
            logger.error("Failed to extract image URL from Ideogram response")
            return jsonify({"error": "Failed to extract image URL", "result": result}), 500
        
        # Return the result
        return jsonify({
            "status": "success",
            "prompt": image_prompt,
            "result": result
        })
        
    except Exception as e:
        logger.error(f"Error generating image: {str(e)}")
        return jsonify({"error": str(e)}), 500
