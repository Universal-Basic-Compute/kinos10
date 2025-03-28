from flask import Blueprint, request, jsonify
import os
import json
import re
import datetime
import requests
from config import CUSTOMERS_DIR, logger
from services.file_service import get_project_path, initialize_project
from services.claude_service import build_context
from services.aider_service import call_aider_with_context

projects_bp = Blueprint('projects', __name__)

@projects_bp.route('/projects', methods=['POST'])
def create_project():
    """
    Endpoint to initialize a new project.
    """
    try:
        data = request.json
        project_name = data.get('project_name', '')
        customer = data.get('customer', '')
        template_override = data.get('template_override')
        
        if not project_name:
            return jsonify({"error": "Project name is required"}), 400
        
        if not customer:
            return jsonify({"error": "Customer is required"}), 400
        
        # Use project_name as project_id if it's a simple name (no spaces or special chars)
        if re.match(r'^[a-zA-Z0-9_-]+$', project_name):
            project_id = project_name
        else:
            project_id = None  # Let the function generate a UUID
        
        project_id = initialize_project(customer, project_name, template_override, project_id)
        
        return jsonify({
            "project_id": project_id,
            "customer": customer,
            "status": "created"
        })
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error creating project: {str(e)}")
        return jsonify({"error": str(e)}), 500

@projects_bp.route('/projects/<customer>/projects', methods=['GET'])
def get_customer_projects(customer):
    """
    Endpoint to get a list of projects for a customer.
    """
    try:
        # Validate customer
        customer_dir = os.path.join(CUSTOMERS_DIR, customer)
        if not os.path.exists(customer_dir):
            return jsonify({"error": f"Customer '{customer}' not found"}), 404
        
        # Get list of projects
        projects = ["template"]  # Always include template
        
        # Add other projects if they exist
        projects_dir = os.path.join(customer_dir, "projects")
        if os.path.exists(projects_dir):
            for project_id in os.listdir(projects_dir):
                project_path = os.path.join(projects_dir, project_id)
                if os.path.isdir(project_path):
                    projects.append(project_id)
        
        return jsonify({"projects": projects})
        
    except Exception as e:
        logger.error(f"Error getting customer projects: {str(e)}")
        return jsonify({"error": str(e)}), 500

@projects_bp.route('/projects/all', methods=['GET'])
def get_all_projects():
    """
    Endpoint to get all customers and their projects.
    """
    try:
        # Get list of all customers
        customers = []
        if os.path.exists(CUSTOMERS_DIR):
            customers = [d for d in os.listdir(CUSTOMERS_DIR) 
                        if os.path.isdir(os.path.join(CUSTOMERS_DIR, d))]
        
        # Get projects for each customer
        all_projects = {}
        for customer in customers:
            projects = ["template"]  # Always include template
            
            # Add other projects if they exist
            projects_dir = os.path.join(CUSTOMERS_DIR, customer, "projects")
            if os.path.exists(projects_dir):
                for project_id in os.listdir(projects_dir):
                    project_path = os.path.join(projects_dir, project_id)
                    if os.path.isdir(project_path):
                        projects.append(project_id)
            
            all_projects[customer] = projects
        
        return jsonify({
            "customers": customers,
            "projects": all_projects
        })
        
    except Exception as e:
        logger.error(f"Error getting all projects: {str(e)}")
        return jsonify({"error": str(e)}), 500

@projects_bp.route('/customers/<customer>/initialize', methods=['POST'])
def initialize_customer(customer):
    """
    Endpoint to manually initialize a customer.
    """
    try:
        # Path to templates in the project
        project_templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "customers")
        customer_template_dir = os.path.join(project_templates_dir, customer, "template")
        
        # Check if customer template exists in project
        if not os.path.exists(customer_template_dir) or not os.path.isdir(customer_template_dir):
            return jsonify({"error": f"Customer template '{customer}' not found in project"}), 404
        
        # Create customer directory if it doesn't exist
        customer_dir = os.path.join(CUSTOMERS_DIR, customer)
        if not os.path.exists(customer_dir):
            logger.info(f"Creating customer directory: {customer_dir}")
            os.makedirs(customer_dir, exist_ok=True)
        
        # Create projects directory if it doesn't exist
        projects_dir = os.path.join(customer_dir, "projects")
        if not os.path.exists(projects_dir):
            logger.info(f"Creating projects directory: {projects_dir}")
            os.makedirs(projects_dir, exist_ok=True)
        
        # Copy template (overwrite if exists)
        dest_template_dir = os.path.join(customer_dir, "template")
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
        
        logger.info(f"Copying template for customer {customer} to app data")
        
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
        custom_copy_tree(customer_template_dir, dest_template_dir)
        
        return jsonify({"status": "success", "message": f"Customer '{customer}' initialized"})
        
    except Exception as e:
        logger.error(f"Error initializing customer: {str(e)}")
        return jsonify({"error": str(e)}), 500

@projects_bp.route('/projects/<customer>/<project_id>/build', methods=['POST'])
def build_project(customer, project_id):
    """
    Endpoint to send a message to Aider for file creation/modification without Claude response.
    Similar to the messages endpoint but only processes with Aider and returns its response.
    """
    try:
        # Parse request data
        data = request.json
        
        # Support both formats: new format with 'message' and original format with 'content'
        message_content = data.get('message', data.get('content', ''))
        
        # Get optional fields
        addSystem = data.get('addSystem', None)  # Optional additional system instructions
        attachments = data.get('attachments', [])
        
        # Validate customer
        if not os.path.exists(os.path.join(CUSTOMERS_DIR, customer)):
            return jsonify({"error": f"Customer '{customer}' not found"}), 404
            
        project_path = get_project_path(customer, project_id)
        
        # Check if project exists
        if not os.path.exists(project_path):
            return jsonify({"error": f"Project '{project_id}' not found for customer '{customer}'"}), 404
        
        # Build context (select relevant files)
        selected_files = build_context(customer, project_id, message_content, attachments, project_path, None, None, addSystem)
        
        # Log the selected files
        logger.info(f"Selected files for build context: {selected_files}")
        
        # Call Aider with the selected context and wait for response
        try:
            # Call Aider synchronously (not in a thread)
            aider_response = call_aider_with_context(project_path, selected_files, message_content, addSystem=addSystem)
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

@projects_bp.route('/projects/<customer>/<project_id>/reset', methods=['POST'])
def reset_project(customer, project_id):
    """
    Endpoint to reset a project to its initial template state.
    """
    try:
        # Validate customer
        if not os.path.exists(os.path.join(CUSTOMERS_DIR, customer)):
            return jsonify({"error": f"Customer '{customer}' not found"}), 404
            
        # Get the project path
        project_path = get_project_path(customer, project_id)
        if not os.path.exists(project_path):
            return jsonify({"error": f"Project '{project_id}' not found for customer '{customer}'"}), 404
        
        # Get the template path
        template_path = os.path.join(CUSTOMERS_DIR, customer, "template")
        if not os.path.exists(template_path):
            return jsonify({"error": f"Template not found for customer '{customer}'"}), 404
        
        # Backup the project name before deleting
        project_name = project_id  # Use project_id as fallback
        project_info_path = os.path.join(project_path, "project_info.json")
        if os.path.exists(project_info_path):
            try:
                with open(project_info_path, 'r') as f:
                    project_info = json.load(f)
                    project_name = project_info.get('name', project_id)
            except:
                logger.warning(f"Could not read project_info.json for {customer}/{project_id}")
        
        # Delete the project directory
        import shutil
        try:
            shutil.rmtree(project_path)
        except PermissionError:
            logger.warning(f"Permission error removing {project_path}, trying to remove files individually")
            # Try to remove files individually
            for root, dirs, files in os.walk(project_path, topdown=False):
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
                os.rmdir(project_path)
            except:
                return jsonify({"error": f"Could not completely remove project directory. Please try again."}), 500
        
        # Reinitialize the project from template
        initialize_project(customer, project_name, project_id=project_id)
        
        return jsonify({
            "status": "success",
            "message": f"Project '{project_id}' has been reset to template state"
        })
        
    except Exception as e:
        logger.error(f"Error resetting project: {str(e)}")
        return jsonify({"error": str(e)}), 500

@projects_bp.route('/customers/<customer>/reset', methods=['POST'])
def reset_customer(customer):
    """
    Endpoint to reset a customer and all its projects to initial template state.
    If the customer doesn't exist, it will be created.
    """
    try:
        # Check if customer exists
        customer_dir = os.path.join(CUSTOMERS_DIR, customer)
        if not os.path.exists(customer_dir):
            logger.info(f"Customer '{customer}' not found, creating it")
            
            # Create customer directory
            os.makedirs(customer_dir, exist_ok=True)
            
            # Create projects directory
            projects_dir = os.path.join(customer_dir, "projects")
            os.makedirs(projects_dir, exist_ok=True)
        
        # First, reinitialize the customer template
        # This will ensure we have the latest template from the project
        response = initialize_customer(customer)
        if isinstance(response, tuple) and response[1] != 200:
            # If initialize_customer returned an error, pass it through
            return response
        
        # Get list of projects
        projects_dir = os.path.join(customer_dir, "projects")
        if not os.path.exists(projects_dir):
            # No projects directory, nothing more to do
            return jsonify({
                "status": "success",
                "message": f"Customer '{customer}' has been reset (no projects found)"
            })
        
        # Get all projects for this customer
        projects = []
        for project_id in os.listdir(projects_dir):
            project_path = os.path.join(projects_dir, project_id)
            if os.path.isdir(project_path):
                projects.append(project_id)
        
        # Reset each project
        reset_results = []
        for project_id in projects:
            try:
                # Get project name before resetting
                project_name = project_id  # Default fallback
                project_info_path = os.path.join(projects_dir, project_id, "project_info.json")
                if os.path.exists(project_info_path):
                    try:
                        with open(project_info_path, 'r') as f:
                            project_info = json.load(f)
                            project_name = project_info.get('name', project_id)
                    except:
                        logger.warning(f"Could not read project_info.json for {customer}/{project_id}")
                
                # Delete the project directory
                project_path = os.path.join(projects_dir, project_id)
                import shutil
                try:
                    shutil.rmtree(project_path)
                except PermissionError:
                    logger.warning(f"Permission error removing {project_path}, trying to remove files individually")
                    # Try to remove files individually
                    for root, dirs, files in os.walk(project_path, topdown=False):
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
                        os.rmdir(project_path)
                    except:
                        reset_results.append({
                            "project_id": project_id,
                            "status": "error",
                            "message": "Could not completely remove project directory"
                        })
                        continue
                
                # Reinitialize the project from template
                initialize_project(customer, project_name, project_id=project_id)
                
                reset_results.append({
                    "project_id": project_id,
                    "status": "success",
                    "message": f"Project reset to template state"
                })
                
            except Exception as e:
                logger.error(f"Error resetting project {project_id}: {str(e)}")
                reset_results.append({
                    "project_id": project_id,
                    "status": "error",
                    "message": str(e)
                })
        
        return jsonify({
            "status": "success",
            "message": f"Customer '{customer}' has been reset",
            "projects_reset": len(reset_results),
            "results": reset_results
        })
        
    except Exception as e:
        logger.error(f"Error resetting customer: {str(e)}")
        return jsonify({"error": str(e)}), 500

@projects_bp.route('/projects/<customer>/<project_id>/git_history', methods=['GET'])
def get_git_history(customer, project_id):
    """
    Endpoint to get Git commit history for a project.
    """
    try:
        # Validate customer and project
        if not os.path.exists(os.path.join(CUSTOMERS_DIR, customer)):
            return jsonify({"error": f"Customer '{customer}' not found"}), 404
            
        project_path = get_project_path(customer, project_id)
        if not os.path.exists(project_path):
            return jsonify({"error": f"Project '{project_id}' not found for customer '{customer}'"}), 404
        
        # Check if .git directory exists
        git_dir = os.path.join(project_path, ".git")
        if not os.path.exists(git_dir) or not os.path.isdir(git_dir):
            return jsonify({"error": "No Git repository found for this project"}), 404
        
        # Get git commit history using git log
        try:
            # Use git log to get commit history (last 20 commits)
            import subprocess
            result = subprocess.run(
                ["git", "log", "--pretty=format:%h|%an|%ad|%s", "--date=short", "-n", "20"],
                cwd=project_path,
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

@projects_bp.route('/projects/<customer>/<project_id>/image', methods=['POST'])
def generate_project_image(customer, project_id):
    """
    Endpoint to generate an image based on a message using Ideogram API.
    Uses Claude to create a detailed prompt based on the message and context.
    """
    try:
        # Parse request data
        data = request.json
        message_content = data.get('message', '')
        
        # Optional parameters
        aspect_ratio = data.get('aspect_ratio', 'ASPECT_1_1')
        model = data.get('model', 'V_2')
        magic_prompt_option = data.get('magic_prompt_option', 'AUTO')
        
        # Validate required parameters
        if not message_content:
            return jsonify({"error": "Message is required"}), 400
        
        # Validate customer and project
        if not os.path.exists(os.path.join(CUSTOMERS_DIR, customer)):
            return jsonify({"error": f"Customer '{customer}' not found"}), 404
            
        project_path = get_project_path(customer, project_id)
        if not os.path.exists(project_path):
            return jsonify({"error": f"Project '{project_id}' not found for customer '{customer}'"}), 404
        
        # Build context (select relevant files)
        selected_files = build_context(customer, project_id, message_content, project_path=project_path)
        
        # Log the selected files
        logger.info(f"Selected files for image generation context: {selected_files}")
        
        # Use Claude to create a detailed prompt based on the message and context
        from services.claude_service import call_claude_with_context
        
        # Add specific system instructions for prompt creation
        prompt_system_instructions = """
        Your task is to create a detailed, vivid image generation prompt based on the user's message.
        The prompt should be descriptive and specific, focusing on visual elements.
        Do not include any explanations or commentary - just output the prompt text that will be sent to an image generation API.
        The prompt should be 1-3 paragraphs long and include details about:
        - Main subject and composition
        - Style, mood, and atmosphere
        - Colors, lighting, and visual effects
        - Background and environment
        - Any specific artistic influences if relevant
        """
        
        # Call Claude to create the prompt
        claude_response = call_claude_with_context(
            selected_files, 
            project_path, 
            f"Create a detailed image generation prompt based on this request: {message_content}",
            model="claude-3-5-haiku-latest",
            is_new_message=False,
            addSystem=prompt_system_instructions
        )
        
        # Clean up the prompt (remove any markdown formatting, etc.)
        image_prompt = claude_response.strip()
        logger.info(f"Generated image prompt: {image_prompt}")
        
        # Import the Ideogram service
        from services.ideogram_service import generate_image
        
        # Generate the image
        result = generate_image(image_prompt, aspect_ratio, model, magic_prompt_option)
        
        # Check for errors
        if "error" in result:
            return jsonify(result), 500
        
        # Save the image to the project's images directory
        images_dir = os.path.join(project_path, "images")
        os.makedirs(images_dir, exist_ok=True)
        
        # Get the image URL from the response
        if "data" in result and len(result["data"]) > 0 and "url" in result["data"][0]:
            image_url = result["data"][0]["url"]
            
            # Download the image
            image_response = requests.get(image_url)
            if image_response.status_code == 200:
                # Generate a filename with timestamp
                timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                image_filename = f"ideogram_{timestamp}.jpg"
                image_path = os.path.join(images_dir, image_filename)
                
                # Save the image
                with open(image_path, 'wb') as f:
                    f.write(image_response.content)
                
                # Add the local path to the result
                result["local_path"] = os.path.join("images", image_filename)
                logger.info(f"Saved image to {image_path}")
            else:
                logger.error(f"Failed to download image from {image_url}: {image_response.status_code}")
                return jsonify({
                    "error": "Failed to download image",
                    "status_code": image_response.status_code
                }), 500
        
        # Return the result
        return jsonify({
            "status": "success",
            "prompt": image_prompt,
            "result": result
        })
        
    except Exception as e:
        logger.error(f"Error generating image: {str(e)}")
        return jsonify({"error": str(e)}), 500
