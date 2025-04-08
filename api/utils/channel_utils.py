import os
import json
import datetime
import logging
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
