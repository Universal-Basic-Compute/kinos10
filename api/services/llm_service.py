import os
import logging
import json
from config import logger

class LLMProvider:
    """Base class for LLM providers"""
    
    def __init__(self, api_key=None):
        self.api_key = api_key
        
    def generate_response(self, messages, system=None, max_tokens=None):
        """Generate a response from the LLM"""
        raise NotImplementedError("Subclasses must implement this method")
        
    @classmethod
    def get_provider(cls, provider_name=None):
        """Factory method to get the appropriate provider"""
        if not provider_name:
            # Get default provider from environment or config
            provider_name = os.getenv("DEFAULT_LLM_PROVIDER", "claude")
            
        provider_name = provider_name.lower()
        
        if provider_name == "claude" or provider_name.startswith("claude-"):
            from services.claude_provider import ClaudeProvider
            return ClaudeProvider()
        elif provider_name == "openai" or provider_name == "chatgpt" or provider_name.startswith("gpt-"):
            from services.openai_provider import OpenAIProvider
            return OpenAIProvider()
        else:
            logger.warning(f"Unknown provider: {provider_name}, falling back to Claude")
            from services.claude_provider import ClaudeProvider
            return ClaudeProvider()
