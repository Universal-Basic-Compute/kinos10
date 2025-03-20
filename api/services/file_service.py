import os
import json
import datetime
import shutil
import logging
from config import CUSTOMERS_DIR, logger

def get_project_path(customer, project_id):
    """Get the full path to a project directory."""
    if project_id == "template":
        return os.path.join(CUSTOMERS_DIR, customer, "template")
    else:
        return os.path.join(CUSTOMERS_DIR, customer, "projects", project_id)

def initialize_project(customer, project_name, template_override=None, project_id=None):
    """
    Initialize a new project for a customer.
    Copies the template directory to create a new project.
    
    Args:
        customer: Customer name
        project_name: Name of the project
        template_override: Optional template to use instead of customer's template
        project_id: Optional specific project ID to use (if None, generates UUID)
    
    Returns:
        Project ID
    """
    # Validate customer exists
    customer_dir = os.path.join(CUSTOMERS_DIR, customer)
    if not os.path.exists(customer_dir):
        logger.error(f"Customer directory not found: {customer_dir}")
        raise ValueError(f"Customer '{customer}' not found")
    
    # Get template path (either default or override)
    template_path = os.path.join(customer_dir, "template")
    if template_override and os.path.exists(os.path.join(CUSTOMERS_DIR, template_override, "template")):
        template_path = os.path.join(CUSTOMERS_DIR, template_override, "template")
    
    if not os.path.exists(template_path):
        logger.error(f"Template directory not found: {template_path}")
        raise ValueError(f"Template not found at {template_path}")
    
    # Create projects directory if it doesn't exist
    projects_dir = os.path.join(customer_dir, "projects")
    try:
        os.makedirs(projects_dir, exist_ok=True)
        logger.info(f"Created or verified projects directory: {projects_dir}")
    except Exception as e:
        logger.error(f"Failed to create projects directory: {str(e)}")
        raise RuntimeError(f"Failed to create projects directory: {str(e)}")
    
    # Generate a unique project ID if not provided
    if project_id is None:
        import uuid
        project_id = str(uuid.uuid4())
    
    logger.info(f"Using project ID: {project_id}")
    
    # Create project directory
    project_dir = os.path.join(projects_dir, project_id)
    try:
        if os.path.exists(project_dir):
            logger.warning(f"Project directory already exists: {project_dir}")
            # We could either return an error or continue and overwrite
            # For now, let's continue and overwrite
        
        # Create the project directory
        os.makedirs(project_dir, exist_ok=True)
        logger.info(f"Created project directory: {project_dir}")
    except Exception as e:
        logger.error(f"Failed to create project directory: {str(e)}")
        raise RuntimeError(f"Failed to create project directory: {str(e)}")
    
    # Copy template to project directory
    try:
        logger.info(f"Copying template from {template_path} to {project_dir}")
        # List template contents for debugging
        template_contents = os.listdir(template_path)
        logger.info(f"Template contents: {template_contents}")
        
        # Use a more robust copy method
        for item in os.listdir(template_path):
            s = os.path.join(template_path, item)
            d = os.path.join(project_dir, item)
            try:
                if os.path.isdir(s):
                    shutil.copytree(s, d)
                else:
                    shutil.copy2(s, d)
                logger.info(f"Copied {s} to {d}")
            except Exception as copy_error:
                logger.error(f"Error copying {s} to {d}: {str(copy_error)}")
                # Continue with other files even if one fails
    except Exception as e:
        logger.error(f"Failed to copy template: {str(e)}")
        raise RuntimeError(f"Failed to copy template: {str(e)}")
    
    # Create messages.json file
    messages_file = os.path.join(project_dir, "messages.json")
    try:
        with open(messages_file, 'w') as f:
            json.dump([], f)
        logger.info(f"Created messages.json file")
    except Exception as e:
        logger.error(f"Failed to create messages.json: {str(e)}")
        # Continue even if this fails
    
    # Create thoughts.txt file
    thoughts_file = os.path.join(project_dir, "thoughts.txt")
    try:
        with open(thoughts_file, 'w') as f:
            f.write(f"# Thoughts for project: {project_name}\nCreated: {datetime.datetime.now().isoformat()}\n\n")
        logger.info(f"Created thoughts.txt file")
    except Exception as e:
        logger.error(f"Failed to create thoughts.txt: {str(e)}")
        # Continue even if this fails
    
    # Update system.txt with project name if needed
    system_file = os.path.join(project_dir, "system.txt")
    if os.path.exists(system_file):
        try:
            with open(system_file, 'r') as f:
                system_content = f.read()
            
            # Replace placeholder if present
            if "{{PROJECT_NAME}}" in system_content:
                system_content = system_content.replace("{{PROJECT_NAME}}", project_name)
                with open(system_file, 'w') as f:
                    f.write(system_content)
                logger.info(f"Updated system.txt with project name")
        except Exception as e:
            logger.error(f"Failed to update system.txt: {str(e)}")
            # Continue even if this fails
    
    # Verify project directory exists and check contents
    if os.path.exists(project_dir):
        dir_contents = os.listdir(project_dir)
        logger.info(f"Project directory contents: {dir_contents}")
    else:
        logger.error(f"Project directory does not exist after creation: {project_dir}")
        raise RuntimeError(f"Project directory does not exist after creation")
    
    return project_id

def load_file_content(project_path, file_path):
    """Load the content of a file from the project."""
    full_path = os.path.join(project_path, file_path)
    if not os.path.exists(full_path) or not os.path.isfile(full_path):
        logger.warning(f"File not found: {full_path}")
        return None
    
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading file {full_path}: {str(e)}")
        return None

def initialize_customer_templates():
    """
    Initialize customer templates by copying them from the project directory
    to the app data location if they don't exist yet.
    """
    # Path to templates in the project
    project_templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "customers")
    
    # Check if project templates directory exists
    if not os.path.exists(project_templates_dir):
        logger.warning(f"Project templates directory not found: {project_templates_dir}")
        return
    
    logger.info(f"Initializing customer templates from: {project_templates_dir}")
    logger.info(f"Available customers in project: {os.listdir(project_templates_dir)}")
    
    # Custom copy function to skip .git directory and handle permission errors
    def custom_copy_tree(src, dst):
        try:
            os.makedirs(dst, exist_ok=True)
            
            # Get list of items to copy (excluding .git)
            items_to_copy = [item for item in os.listdir(src) if item != '.git']
            logger.info(f"Items to copy from {src}: {items_to_copy}")
            
            for item in items_to_copy:
                s = os.path.join(src, item)
                d = os.path.join(dst, item)
                
                try:
                    if os.path.isdir(s):
                        custom_copy_tree(s, d)
                    else:
                        shutil.copy2(s, d)
                        logger.info(f"Copied file: {s} -> {d}")
                except PermissionError:
                    logger.warning(f"Permission error copying {s} to {d}, skipping")
                except Exception as e:
                    logger.warning(f"Error copying {s} to {d}: {str(e)}, skipping")
        except Exception as e:
            logger.warning(f"Error in custom_copy_tree for {src} to {dst}: {str(e)}")
    
    # Get list of customers from project templates
    for customer in os.listdir(project_templates_dir):
        customer_path = os.path.join(project_templates_dir, customer)
        # Skip if not a directory
        if not os.path.isdir(customer_path):
            continue
            
        logger.info(f"Processing customer: {customer}")
        customer_dir = os.path.join(CUSTOMERS_DIR, customer)
        
        # Create customer directory if it doesn't exist
        if not os.path.exists(customer_dir):
            logger.info(f"Creating customer directory: {customer_dir}")
            os.makedirs(customer_dir, exist_ok=True)
        
        # Create projects directory if it doesn't exist
        projects_dir = os.path.join(customer_dir, "projects")
        if not os.path.exists(projects_dir):
            logger.info(f"Creating projects directory: {projects_dir}")
            os.makedirs(projects_dir, exist_ok=True)
        
        # Copy template if it doesn't exist
        customer_template_dir = os.path.join(project_templates_dir, customer, "template")
        if os.path.exists(customer_template_dir) and os.path.isdir(customer_template_dir):
            # Destination in app data
            dest_template_dir = os.path.join(customer_dir, "template")
            
            # Check if template exists but is empty
            if os.path.exists(dest_template_dir) and not os.listdir(dest_template_dir):
                logger.info(f"Template directory exists but is empty for {customer}, copying template")
                custom_copy_tree(customer_template_dir, dest_template_dir)
            # Only copy if destination doesn't exist
            elif not os.path.exists(dest_template_dir):
                logger.info(f"Copying template for customer {customer} to app data")
                # Use custom copy function instead of shutil.copytree
                custom_copy_tree(customer_template_dir, dest_template_dir)
            else:
                logger.info(f"Template already exists for customer {customer}")
                
            # Verify template was copied correctly
            if os.path.exists(dest_template_dir):
                template_files = os.listdir(dest_template_dir)
                logger.info(f"Template files for {customer}: {template_files}")
            else:
                logger.warning(f"Template directory not created for {customer}")
