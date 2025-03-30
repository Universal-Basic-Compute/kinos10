import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Generate a secure API key or load from environment
API_KEY = os.getenv("API_SECRET_KEY")
if not API_KEY:
    logger.warning("API_SECRET_KEY environment variable not set! Using default key (not secure for production)")
    API_KEY = "your-default-secure-key-here"  # Only use this for development
else:
    logger.info("API_SECRET_KEY environment variable found and loaded")

# Define MODEL constant
MODEL = "claude-3-5-haiku-latest"  # Use the latest Claude 3.5 Haiku model

# Get application data directory
def get_app_data_dir():
    """Get the appropriate application data directory based on the platform."""
    # For Windows development environment, use a specific path
    if os.name == 'nt':  # Windows
        app_data = 'C:\\data\\KinOS'  # Use double backslashes for Windows paths
        logger.info(f"Using Windows path: {app_data}")
    # Check if running on Render (with persistent disk)
    elif os.path.exists('/data'):
        app_data = '/data/KinOS'
        logger.info(f"Using Render data directory: {app_data}")
    elif os.name == 'posix':  # Linux/Mac
        app_data = os.path.join(os.path.expanduser('~'), '.kinos')
        logger.info(f"Using Linux/Mac home directory: {app_data}")
    else:  # Fallback
        app_data = os.path.join(os.path.expanduser('~'), '.kinos')
        logger.info(f"Using fallback directory: {app_data}")
    
    # Create directory if it doesn't exist
    try:
        os.makedirs(app_data, exist_ok=True)
        logger.info(f"Verified app data directory exists: {app_data}")
    except Exception as e:
        logger.error(f"Failed to create app data directory {app_data}: {str(e)}")
    
    return app_data

# Constants
CUSTOMERS_DIR = os.path.join(get_app_data_dir(), "customers")
# Ensure customers directory exists
os.makedirs(CUSTOMERS_DIR, exist_ok=True)
