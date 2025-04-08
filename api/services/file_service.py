import os
import json
import datetime
import shutil
import logging
from config import blueprintS_DIR, logger

def get_kin_path(blueprint, kin_id):
    """Get the full path to a kin directory."""
    if kin_id == "template":
        return os.path.join(blueprintS_DIR, blueprint, "template")
    else:
        return os.path.join(blueprintS_DIR, blueprint, "kins", kin_id)

def get_channel_path(kin_path, channel_id=None):
    """
    Get the path to a channel directory within a kin.
    
    Args:
        kin_path: Path to the kin directory
        channel_id: Channel ID (if None, returns the main channel)
    
    Returns:
        Path to the channel directory
    """
    if not channel_id:
        # Return the main channel (root of kin directory)
        return kin_path
    
    # Create channels directory if it doesn't exist
    channels_dir = os.path.join(kin_path, "channels")
    os.makedirs(channels_dir, exist_ok=True)
    
    # Return the specific channel directory
    channel_path = os.path.join(channels_dir, channel_id)
    os.makedirs(channel_path, exist_ok=True)
    
    return channel_path

def initialize_kin(blueprint, kin_name, template_override=None, kin_id=None):
    """
    Initialize a new kin for a blueprint.
    Copies the template directory to create a new kin.
    
    Args:
        blueprint: blueprint name
        kin_name: Name of the kin
        template_override: Optional template to use instead of blueprint's template
        kin_id: Optional specific kin ID to use (if None, generates UUID)
    
    Returns:
        kin ID
    """
    # Validate blueprint exists
    blueprint_dir = os.path.join(blueprintS_DIR, blueprint)
    if not os.path.exists(blueprint_dir):
        logger.error(f"blueprint directory not found: {blueprint_dir}")
        raise ValueError(f"blueprint '{blueprint}' not found")
    
    # Get template path (either default or override)
    template_path = os.path.join(blueprint_dir, "template")
    if template_override and os.path.exists(os.path.join(blueprintS_DIR, template_override, "template")):
        template_path = os.path.join(blueprintS_DIR, template_override, "template")
    
    if not os.path.exists(template_path):
        logger.error(f"Template directory not found: {template_path}")
        raise ValueError(f"Template not found at {template_path}")
    
    # Create kins directory if it doesn't exist
    kins_dir = os.path.join(blueprint_dir, "kins")
    try:
        os.makedirs(kins_dir, exist_ok=True)
        logger.info(f"Created or verified kins directory: {kins_dir}")
    except Exception as e:
        logger.error(f"Failed to create kins directory: {str(e)}")
        raise RuntimeError(f"Failed to create kins directory: {str(e)}")
    
    # Generate a unique kin ID if not provided
    if kin_id is None:
        import uuid
        kin_id = str(uuid.uuid4())
    
    logger.info(f"Using kin ID: {kin_id}")
    
    # Create kin directory
    kin_dir = os.path.join(kins_dir, kin_id)
    try:
        if os.path.exists(kin_dir):
            logger.warning(f"kin directory already exists: {kin_dir}")
            # We could either return an error or continue and overwrite
            # For now, let's continue and overwrite
        
        # Create the kin directory
        os.makedirs(kin_dir, exist_ok=True)
        logger.info(f"Created kin directory: {kin_dir}")
    except Exception as e:
        logger.error(f"Failed to create kin directory: {str(e)}")
        raise RuntimeError(f"Failed to create kin directory: {str(e)}")
    
    # Copy template to kin directory
    try:
        logger.info(f"Copying template from {template_path} to {kin_dir}")
        # List template contents for debugging
        template_contents = os.listdir(template_path)
        logger.info(f"Template contents: {template_contents}")
        
        # Use a more robust copy method
        for item in os.listdir(template_path):
            s = os.path.join(template_path, item)
            d = os.path.join(kin_dir, item)
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
    messages_file = os.path.join(kin_dir, "messages.json")
    try:
        with open(messages_file, 'w') as f:
            json.dump([], f)
        logger.info(f"Created messages.json file")
    except Exception as e:
        logger.error(f"Failed to create messages.json: {str(e)}")
        # Continue even if this fails
    
    # Create thoughts.txt file
    thoughts_file = os.path.join(kin_dir, "thoughts.txt")
    try:
        with open(thoughts_file, 'w') as f:
            f.write(f"# Thoughts for kin: {kin_name}\nCreated: {datetime.datetime.now().isoformat()}\n\n")
        logger.info(f"Created thoughts.txt file")
    except Exception as e:
        logger.error(f"Failed to create thoughts.txt: {str(e)}")
        # Continue even if this fails
    
    # Update system.txt with kin name if needed
    system_file = os.path.join(kin_dir, "system.txt")
    if os.path.exists(system_file):
        try:
            with open(system_file, 'r') as f:
                system_content = f.read()
            
            # Replace placeholder if present
            if "{{kin_NAME}}" in system_content:
                system_content = system_content.replace("{{kin_NAME}}", kin_name)
                with open(system_file, 'w') as f:
                    f.write(system_content)
                logger.info(f"Updated system.txt with kin name")
        except Exception as e:
            logger.error(f"Failed to update system.txt: {str(e)}")
            # Continue even if this fails
    
    # Verify kin directory exists and check contents
    if os.path.exists(kin_dir):
        dir_contents = os.listdir(kin_dir)
        logger.info(f"kin directory contents: {dir_contents}")
    else:
        logger.error(f"kin directory does not exist after creation: {kin_dir}")
        raise RuntimeError(f"kin directory does not exist after creation")
    
    return kin_id

def create_channel(kin_path, channel_name, user_id=None, channel_type="direct", metadata=None, channel_id=None):
    """
    Create a new channel in a kin.
    
    Args:
        kin_path: Path to the kin directory
        channel_name: Name of the channel
        user_id: Optional user ID for user-specific channels
        channel_type: Type of channel (default: "direct")
        metadata: Optional metadata for the channel
        channel_id: Optional specific channel ID (if None, generates UUID)
    
    Returns:
        Channel ID
    """
    # Create channels directory if it doesn't exist
    channels_dir = os.path.join(kin_path, "channels")
    os.makedirs(channels_dir, exist_ok=True)
    
    # Generate a unique channel ID if not provided
    if channel_id is None:
        import uuid
        channel_id = f"channel_{str(uuid.uuid4())}"
    
    # Create channel directory
    channel_path = os.path.join(channels_dir, channel_id)
    os.makedirs(channel_path, exist_ok=True)
    
    # Create channel metadata file
    channel_info = {
        "id": channel_id,
        "name": channel_name,
        "created_at": datetime.datetime.now().isoformat(),
        "updated_at": datetime.datetime.now().isoformat(),
        "type": channel_type,
        "metadata": metadata or {}
    }
    
    if user_id:
        channel_info["user_id"] = user_id
    
    # Save channel info
    channel_info_path = os.path.join(channel_path, "channel_info.json")
    with open(channel_info_path, 'w', encoding='utf-8') as f:
        json.dump(channel_info, f, indent=2)
    
    # Create empty messages.json file
    messages_file = os.path.join(channel_path, "messages.json")
    with open(messages_file, 'w', encoding='utf-8') as f:
        json.dump([], f)
    
    return channel_id

def get_channels(kin_path):
    """
    Get a list of all channels in a kin.
    
    Args:
        kin_path: Path to the kin directory
    
    Returns:
        List of channel info dictionaries
    """
    channels = []
    
    # Add main channel
    main_channel = {
        "id": "main",
        "name": "Main Channel",
        "created_at": datetime.datetime.fromtimestamp(os.path.getctime(kin_path)).isoformat(),
        "updated_at": datetime.datetime.fromtimestamp(os.path.getmtime(kin_path)).isoformat(),
        "type": "main",
        "is_main": True
    }
    channels.append(main_channel)
    
    # Check if channels directory exists
    channels_dir = os.path.join(kin_path, "channels")
    if not os.path.exists(channels_dir):
        return channels
    
    # Get all channel directories
    for channel_id in os.listdir(channels_dir):
        channel_path = os.path.join(channels_dir, channel_id)
        if os.path.isdir(channel_path):
            # Try to load channel info
            channel_info_path = os.path.join(channel_path, "channel_info.json")
            if os.path.exists(channel_info_path):
                try:
                    with open(channel_info_path, 'r', encoding='utf-8') as f:
                        channel_info = json.load(f)
                    channels.append(channel_info)
                except Exception as e:
                    logger.error(f"Error loading channel info for {channel_id}: {str(e)}")
            else:
                # Create basic channel info if file doesn't exist
                channel_info = {
                    "id": channel_id,
                    "name": f"Channel {channel_id}",
                    "created_at": datetime.datetime.fromtimestamp(os.path.getctime(channel_path)).isoformat(),
                    "updated_at": datetime.datetime.fromtimestamp(os.path.getmtime(channel_path)).isoformat(),
                    "type": "unknown"
                }
                channels.append(channel_info)
    
    return channels

def load_file_content(kin_path, file_path):
    """Load the content of a file from the kin."""
    full_path = os.path.join(kin_path, file_path)
    if not os.path.exists(full_path) or not os.path.isfile(full_path):
        logger.warning(f"File not found: {full_path}")
        return None
    
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading file {full_path}: {str(e)}")
        return None

def initialize_blueprint_templates():
    """
    Initialize blueprint templates by copying them from the kin directory
    to the app data location if they don't exist yet.
    """
    # Path to templates in the kin
    kin_templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "blueprints")
    
    # Check if kin templates directory exists
    if not os.path.exists(kin_templates_dir):
        logger.warning(f"kin templates directory not found: {kin_templates_dir}")
        return
    
    # Log the available blueprints in the kin directory
    if os.path.exists(kin_templates_dir):
        available_blueprints = [d for d in os.listdir(kin_templates_dir) 
                              if os.path.isdir(os.path.join(kin_templates_dir, d))]
        logger.info(f"Available blueprints in kin directory: {available_blueprints}")
    else:
        logger.warning(f"kin templates directory not found: {kin_templates_dir}")
    
    logger.info(f"Initializing blueprint templates from: {kin_templates_dir}")
    logger.info(f"Available blueprints in kin: {os.listdir(kin_templates_dir)}")
    
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
    
    # Get list of blueprints from kin templates
    for blueprint in os.listdir(kin_templates_dir):
        blueprint_path = os.path.join(kin_templates_dir, blueprint)
        # Skip if not a directory
        if not os.path.isdir(blueprint_path):
            continue
            
        logger.info(f"Processing blueprint: {blueprint}")
        blueprint_dir = os.path.join(blueprintS_DIR, blueprint)
        
        # Create blueprint directory if it doesn't exist
        if not os.path.exists(blueprint_dir):
            logger.info(f"Creating blueprint directory: {blueprint_dir}")
            os.makedirs(blueprint_dir, exist_ok=True)
        
        # Create kins directory if it doesn't exist
        kins_dir = os.path.join(blueprint_dir, "kins")
        if not os.path.exists(kins_dir):
            logger.info(f"Creating kins directory: {kins_dir}")
            os.makedirs(kins_dir, exist_ok=True)
        
        # Copy template if it doesn't exist
        blueprint_template_dir = os.path.join(kin_templates_dir, blueprint, "template")
        if os.path.exists(blueprint_template_dir) and os.path.isdir(blueprint_template_dir):
            # Destination in app data
            dest_template_dir = os.path.join(blueprint_dir, "template")
            
            # Check if template exists but is empty
            if os.path.exists(dest_template_dir) and not os.listdir(dest_template_dir):
                logger.info(f"Template directory exists but is empty for {blueprint}, copying template")
                custom_copy_tree(blueprint_template_dir, dest_template_dir)
            # Only copy if destination doesn't exist
            elif not os.path.exists(dest_template_dir):
                logger.info(f"Copying template for blueprint {blueprint} to app data")
                # Use custom copy function instead of shutil.copytree
                custom_copy_tree(blueprint_template_dir, dest_template_dir)
            else:
                logger.info(f"Template already exists for blueprint {blueprint}")
                
            # Verify template was copied correctly
            if os.path.exists(dest_template_dir):
                template_files = os.listdir(dest_template_dir)
                logger.info(f"Template files for {blueprint}: {template_files}")
            else:
                logger.warning(f"Template directory not created for {blueprint}")
