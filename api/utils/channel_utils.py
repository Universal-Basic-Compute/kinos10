import os
import json
import datetime
import logging
import shutil
from config import logger

def get_channel_messages(kin_path, channel_id, limit=None):
    """
    Get messages for a specific channel.
    
    Args:
        kin_path: Path to the kin directory
        channel_id: Channel ID (if None, returns messages from the main channel)
        limit: Optional limit on the number of messages to return
    
    Returns:
        List of messages
    """
    # Determine which messages file to use
    if channel_id and channel_id != "main":
        # Get channel path
        from services.file_service import get_channel_path
        channel_path = get_channel_path(kin_path, channel_id)
        messages_file = os.path.join(channel_path, "messages.json")
    else:
        # Use main messages file
        messages_file = os.path.join(kin_path, "messages.json")
    
    # Load messages
    if os.path.exists(messages_file):
        try:
            with open(messages_file, 'r', encoding='utf-8') as f:
                messages = json.load(f)
            
            # Apply limit if specified
            if limit and limit > 0:
                messages = messages[-limit:]
                
            return messages
        except json.JSONDecodeError as e:
            logger.error(f"JSON error in messages file: {str(e)}")
            # Try to fix the file
            if fix_channel_messages_json(kin_path, channel_id):
                # Try loading again after fix
                try:
                    with open(messages_file, 'r', encoding='utf-8') as f:
                        messages = json.load(f)
                    
                    # Apply limit if specified
                    if limit and limit > 0:
                        messages = messages[-limit:]
                        
                    return messages
                except Exception as retry_error:
                    logger.error(f"Error reading messages file after fix: {str(retry_error)}")
            return []
        except Exception as e:
            logger.error(f"Error reading messages file: {str(e)}")
    
    # Return empty list if file doesn't exist or there was an error
    return []

def save_channel_messages(kin_path, channel_id, messages):
    """
    Save messages for a specific channel.
    
    Args:
        kin_path: Path to the kin directory
        channel_id: Channel ID (if None, saves to the main channel)
        messages: List of messages to save
    
    Returns:
        Boolean indicating success
    """
    # Determine which messages file to use
    if channel_id and channel_id != "main":
        # Get channel path
        from services.file_service import get_channel_path
        channel_path = get_channel_path(kin_path, channel_id)
        messages_file = os.path.join(channel_path, "messages.json")
    else:
        # Use main messages file
        messages_file = os.path.join(kin_path, "messages.json")
    
    # Save messages
    try:
        with open(messages_file, 'w', encoding='utf-8') as f:
            json.dump(messages, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving messages file: {str(e)}")
        return False

def delete_channel(kin_path, channel_id):
    """
    Delete a channel.
    
    Args:
        kin_path: Path to the kin directory
        channel_id: Channel ID to delete
    
    Returns:
        Boolean indicating success
    """
    # Cannot delete the main channel
    if not channel_id or channel_id == "main":
        logger.error("Cannot delete the main channel")
        return False
    
    # Get channel path
    from services.file_service import get_channel_path
    channel_path = get_channel_path(kin_path, channel_id)
    
    # Check if channel exists
    if not os.path.exists(channel_path):
        logger.error(f"Channel '{channel_id}' not found")
        return False
    
    # Delete the channel directory
    try:
        import shutil
        shutil.rmtree(channel_path)
        logger.info(f"Deleted channel: {channel_id}")
        return True
    except Exception as e:
        logger.error(f"Error deleting channel: {str(e)}")
        return False

def update_channel_info(kin_path, channel_id, updates):
    """
    Update channel information.
    
    Args:
        kin_path: Path to the kin directory
        channel_id: Channel ID to update
        updates: Dictionary of fields to update
    
    Returns:
        Updated channel info dictionary or None if failed
    """
    # Cannot update the main channel
    if not channel_id or channel_id == "main":
        logger.error("Cannot update the main channel info")
        return None
    
    # Get channel path
    from services.file_service import get_channel_path
    channel_path = get_channel_path(kin_path, channel_id)
    
    # Check if channel exists
    if not os.path.exists(channel_path):
        logger.error(f"Channel '{channel_id}' not found")
        return None
    
    # Get channel info
    channel_info_path = os.path.join(channel_path, "channel_info.json")
    if os.path.exists(channel_info_path):
        try:
            with open(channel_info_path, 'r', encoding='utf-8') as f:
                channel_info = json.load(f)
        except Exception as e:
            logger.error(f"Error reading channel info: {str(e)}")
            return None
    else:
        # Create basic channel info if file doesn't exist
        channel_info = {
            "id": channel_id,
            "name": f"Channel {channel_id}",
            "created_at": datetime.datetime.now().isoformat(),
            "type": "unknown"
        }
    
    # Update fields
    for key, value in updates.items():
        if key != "id":  # Don't allow changing the ID
            channel_info[key] = value
    
    # Always update the updated_at timestamp
    channel_info["updated_at"] = datetime.datetime.now().isoformat()
    
    # Save updated info
    try:
        with open(channel_info_path, 'w', encoding='utf-8') as f:
            json.dump(channel_info, f, indent=2)
        return channel_info
    except Exception as e:
        logger.error(f"Error saving channel info: {str(e)}")
        return None

def fix_channel_messages_json(kin_path, channel_id):
    """
    Fix corrupted messages.json file for a channel
    
    Args:
        kin_path: Path to the kin directory
        channel_id: Channel ID with corrupted messages.json
        
    Returns:
        Boolean indicating success
    """
    try:
        # Get channel path
        if channel_id and channel_id != "main":
            # Get channel path
            from services.file_service import get_channel_path
            channel_path = get_channel_path(kin_path, channel_id)
            messages_file = os.path.join(channel_path, "messages.json")
        else:
            # Use main messages file
            messages_file = os.path.join(kin_path, "messages.json")
        
        if not os.path.exists(messages_file):
            logger.warning(f"Messages file not found: {messages_file}")
            return False
        
        # Read the file content
        with open(messages_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Try to parse and fix the JSON
        try:
            # First attempt to parse as is
            messages = json.loads(content)
            logger.info(f"Messages file {messages_file} is valid JSON")
            return True
        except json.JSONDecodeError as e:
            logger.warning(f"JSON error in {messages_file}: {str(e)}")
            
            # Try to fix common issues
            if "Extra data" in str(e):
                # Find the position of the error
                pos = e.pos
                # Truncate the content at the error position
                fixed_content = content[:pos]
                
                # Try to find the last valid JSON structure
                last_bracket = fixed_content.rfind(']')
                if last_bracket > 0:
                    fixed_content = fixed_content[:last_bracket+1]
                    
                    # Validate the fixed content
                    try:
                        messages = json.loads(fixed_content)
                        logger.info(f"Fixed JSON in {messages_file}")
                        
                        # Backup the original file
                        backup_file = f"{messages_file}.bak"
                        shutil.copy2(messages_file, backup_file)
                        logger.info(f"Created backup at {backup_file}")
                        
                        # Write the fixed content
                        with open(messages_file, 'w', encoding='utf-8') as f:
                            json.dump(messages, f, indent=2)
                        
                        logger.info(f"Successfully fixed and saved {messages_file}")
                        return True
                    except json.JSONDecodeError:
                        logger.error(f"Could not fix JSON in {messages_file}")
            
            return False
    except Exception as e:
        logger.error(f"Error fixing messages file: {str(e)}")
        return False
