from flask import Blueprint, request, jsonify
import os
import json
import re
import datetime
from config import CUSTOMERS_DIR, logger
from services.file_service import get_project_path, initialize_project

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
