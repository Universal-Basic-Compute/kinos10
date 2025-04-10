import os
import anthropic
from services.llm_service import LLMProvider
from config import logger

class ClaudeProvider(LLMProvider):
    """Claude (Anthropic) LLM provider implementation"""
    
    def __init__(self, api_key=None):
        super().__init__(api_key)
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            logger.warning("ANTHROPIC_API_KEY environment variable not set")
        
        # Initialize client
        try:
            self.client = anthropic.Anthropic(api_key=self.api_key)
            logger.info("Claude client initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing Claude client: {str(e)}")
            raise RuntimeError(f"Could not initialize Claude client: {str(e)}")
    
    def generate_response(self, messages, system=None, max_tokens=4000, model=None):
        """Generate a response using Claude"""
        try:
            # Use provided model or default
            model_to_use = model or os.getenv("CLAUDE_MODEL", "claude-3-7-sonnet-latest")
            
            response = self.client.messages.create(
                model=model_to_use,
                max_tokens=max_tokens,
                system=system,
                messages=messages
            )
            
            # Extract the response text
            if response.content and len(response.content) > 0:
                return response.content[0].text
            else:
                logger.error("Empty response from Claude")
                return "I apologize, but I couldn't generate a response."
                
        except Exception as e:
            logger.error(f"Error calling Claude API: {str(e)}")
            return f"I apologize, but I encountered an error: {str(e)}. Please try again."
