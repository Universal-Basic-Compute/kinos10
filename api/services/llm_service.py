import os
import logging
import json
from config import logger

class LLMProvider:
    """Base class for LLM providers"""
    
    def __init__(self, api_key=None):
        self.api_key = api_key
        
    def generate_response(self, messages, system=None, max_tokens=None, model=None, stream=False):
        """Generate a response from the LLM with optional streaming support"""
        raise NotImplementedError("Subclasses must implement this method")
        
    @classmethod
    def get_provider(cls, provider_name=None, model=None):
        """Factory method to get the appropriate provider based on provider name or model prefix"""
        # If provider is explicitly specified, use that
        if provider_name:
            provider_name = provider_name.lower()
            
            if provider_name == "claude" or provider_name.startswith("claude-") or provider_name == "anthropic":
                from services.claude_provider import ClaudeProvider
                return ClaudeProvider()
            elif provider_name == "openai" or provider_name == "chatgpt":
                from services.openai_provider import OpenAIProvider
                return OpenAIProvider()
            elif provider_name == "deepseek":
                from services.deepseek_provider import DeepSeekProvider
                return DeepSeekProvider()
            elif provider_name == "gemini":
                from services.gemini_provider import GeminiProvider
                return GeminiProvider()
        
        # If model is specified but provider isn't, infer provider from model name
        if model:
            if model.startswith("gpt-") or model.startswith("o"):
                from services.openai_provider import OpenAIProvider
                return OpenAIProvider()
            elif model.startswith("claude-"):
                from services.claude_provider import ClaudeProvider
                return ClaudeProvider()
            elif model.startswith("deepseek"):
                from services.deepseek_provider import DeepSeekProvider
                return DeepSeekProvider()
            elif model.startswith("gemini"):
                from services.gemini_provider import GeminiProvider
                return GeminiProvider()
        
        # Default to Claude if no provider or model specified
        logger.warning(f"No provider specified and couldn't determine from model, falling back to Claude")
        from services.claude_provider import ClaudeProvider
        return ClaudeProvider()
