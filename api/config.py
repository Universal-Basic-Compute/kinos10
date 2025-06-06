import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

# API base URL
BASE_URL = os.getenv("BASE_URL", "http://localhost:5000/api/proxy")  # Default value if not defined

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Generate a secure API key or load from environment
API_KEY = os.getenv("API_SECRET_KEY")
if not API_KEY:
    logger.error("API_SECRET_KEY environment variable not set! API will not function correctly.")
    # Set a default key for development environments
    if os.environ.get('ENVIRONMENT') == 'development':
        API_KEY = "dev_api_key_for_testing"
        logger.warning(f"Using default development API key: {API_KEY}")
    # Don't set a default key in production - this will cause the API to reject all requests if no key is configured
else:
    logger.info(f"API_SECRET_KEY environment variable found and loaded: '{API_KEY[:3]}...{API_KEY[-3:]}'")

# Define MODEL constant
MODEL = "gemini/gemini-2.5-flash-preview-05-20"  # Default model when none is specified

# LLM Provider Configuration
DEFAULT_LLM_PROVIDER = os.getenv("DEFAULT_LLM_PROVIDER", "gemini") # Default provider
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-3-opus-20240229") # Default Claude model if Claude is chosen
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o") # Default OpenAI model if OpenAI is chosen

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

# Get blueprints directory with v2 compatibility
def get_blueprints_dir():
    """Get the blueprints directory with v2 compatibility."""
    app_data_dir = get_app_data_dir()
    
    # Check both possible locations (with and without v2 prefix)
    v2_blueprints_dir = os.path.join(app_data_dir, "v2", "blueprints")
    direct_blueprints_dir = os.path.join(app_data_dir, "blueprints")
    
    # Prefer v2 path if it exists and has content
    if os.path.exists(v2_blueprints_dir) and os.listdir(v2_blueprints_dir):
        logger.info(f"Using v2 blueprints directory: {v2_blueprints_dir}")
        return v2_blueprints_dir
    
    # Fall back to direct path
    logger.info(f"Using direct blueprints directory: {direct_blueprints_dir}")
    return direct_blueprints_dir

# Constants
blueprintS_DIR = get_blueprints_dir()
# Ensure blueprints directory exists
os.makedirs(blueprintS_DIR, exist_ok=True)
