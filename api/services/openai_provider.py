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
        Don't validate or change model names, just return as-is
        """
        # Log the model name for debugging
        logger.info(f"Using model name as-is: {model_name}")
        return model_name
