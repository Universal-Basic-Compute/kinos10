import os
import re
import openai
from services.llm_service import LLMProvider
from config import logger

class OpenAIProvider(LLMProvider):
    """OpenAI (ChatGPT) LLM provider implementation"""
    
    def __init__(self, api_key=None):
        super().__init__(api_key)
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning("OPENAI_API_KEY environment variable not set")
        
        # Initialize client
        try:
            self.client = openai.OpenAI(api_key=self.api_key)
            logger.info("OpenAI client initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing OpenAI client: {str(e)}")
            raise RuntimeError(f"Could not initialize OpenAI client: {str(e)}")
    
    def generate_response(self, messages, system=None, max_tokens=4000, model=None):
        """Generate a response using OpenAI"""
        try:
            # Use provided model or default
            model_to_use = model or os.getenv("OPENAI_MODEL", "gpt-4o")
            
            # Validate model name to prevent common errors
            model_to_use = self._validate_model_name(model_to_use)
            
            # If system message is provided, add it to the messages array
            if system:
                # OpenAI uses a different format for system messages
                formatted_messages = [{"role": "system", "content": system}]
                formatted_messages.extend(messages)
            else:
                formatted_messages = messages
            
            response = self.client.chat.completions.create(
                model=model_to_use,
                messages=formatted_messages,
                max_tokens=max_tokens
            )
            
            # Extract the response text
            if response.choices and len(response.choices) > 0:
                return response.choices[0].message.content
            else:
                logger.error("Empty response from OpenAI")
                return "I apologize, but I couldn't generate a response."
                
        except openai.NotFoundError as e:
            # Handle model not found errors specifically
            logger.error(f"Model not found error: {str(e)}")
            return f"I apologize, but the specified model '{model_to_use}' was not found. Please try with a valid model like 'gpt-4o' or 'gpt-4'."
        except openai.APIError as e:
            # Handle API errors
            logger.error(f"OpenAI API error: {str(e)}")
            return f"I apologize, but there was an API error: {str(e)}. Please try again with a different model or later."
        except openai.RateLimitError as e:
            # Handle rate limit errors
            logger.error(f"OpenAI rate limit error: {str(e)}")
            return "I apologize, but we've hit the rate limit for the OpenAI API. Please try again in a moment."
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {str(e)}")
            return f"I apologize, but I encountered an error: {str(e)}. Please try again."
    def _validate_model_name(self, model_name):
        """
        Validate and correct common model name errors
        """
        # List of valid OpenAI model prefixes
        valid_prefixes = ["gpt-4", "gpt-3.5"]
        
        # Special case for o4-mini-2025-04-16 which seems to have issues
        if model_name == "o4-mini-2025-04-16":
            logger.info(f"Mapping model 'o4-mini-2025-04-16' to 'o4-mini'")
            return "o4-mini"
        
        # Add specific date-based models that are known to exist
        # These should be kept as-is, not remapped
        known_date_models = [
            "gpt-4.1-2025-04-14"
            # Removed o4-mini-2025-04-16 since it's being handled separately
        ]
        
        # Known valid models that should be kept as-is
        known_valid_models = [
            "o4-mini",  # Add o4-mini as a known valid model
            "o3-mini"   # Add o3-mini as a known valid model
        ]
        
        # Check if this is a known valid model that should be kept as-is
        if model_name in known_valid_models:
            logger.info(f"Using known valid model: {model_name}")
            return model_name
        
        # Check if this is a known date-based model that should be kept as-is
        if model_name in known_date_models:
            logger.info(f"Using known date-based model: {model_name}")
            return model_name
        
        # Common model name corrections
        corrections = {
            # Correct common typos and variations
            "gpt4": "gpt-4",
            "gpt-4o-mini": "gpt-4o-mini",
            "gpt4o": "gpt-4o",
            "gpt-4-o": "gpt-4o",
            "gpt4-o": "gpt-4o",
            "o4": "gpt-4o",
            "gpt-35": "gpt-3.5-turbo",
            "gpt-3.5": "gpt-3.5-turbo",
            "gpt35": "gpt-3.5-turbo",
            "gpt-4-turbo": "gpt-4-turbo",
            "gpt-4-vision": "gpt-4-vision-preview",
            "gpt-4-vision-preview": "gpt-4-vision-preview"
        }
        
        # Check for exact match in corrections
        if model_name in corrections:
            logger.info(f"Corrected model name from '{model_name}' to '{corrections[model_name]}'")
            return corrections[model_name]
        
        # Check for date-based versions that don't exist
        date_pattern = r'(gpt-|o[34])(-[a-z]+)?-\d{4}-\d{2}-\d{2}'
        if re.match(date_pattern, model_name) and model_name not in known_date_models:
            logger.warning(f"Detected date-based model name that may not exist: {model_name}")
            # Fall back to a safe default
            logger.info(f"Falling back to default model 'gpt-4o'")
            return "gpt-4o"
        
        # If it starts with a valid prefix, assume it's valid
        for prefix in valid_prefixes:
            if model_name.startswith(prefix):
                return model_name
        
        # If it starts with o3- or o4-, assume it's valid
        if model_name.startswith("o4-") or model_name.startswith("o3-"):
            return model_name
            
        # If it's not recognized at all, use the default
        if not model_name.startswith("gpt-") and not model_name.startswith("o4-") and not model_name.startswith("o3-"):
            logger.warning(f"Unrecognized model name: {model_name}, falling back to default")
            return os.getenv("OPENAI_MODEL", "gpt-4o")
        
        # Otherwise, return as is
        return model_name
