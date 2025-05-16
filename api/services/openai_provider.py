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
    
    def generate_response(self, messages, system=None, max_tokens=4000, model=None, stream=False):
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
            
            # Create parameters dict - some models use max_tokens, others use max_completion_tokens
            params = {
                "model": model_to_use,
                "messages": formatted_messages,
                "stream": stream
            }
            
            # Determine which token parameter to use based on model
            try:
                # Try with max_completion_tokens first (newer parameter)
                params["max_completion_tokens"] = max_tokens
                response = self.client.chat.completions.create(**params)
            except openai.BadRequestError as e:
                # If we get an error about unsupported parameter, try with max_tokens instead
                if "max_completion_tokens" in str(e) and "not supported" in str(e):
                    logger.info(f"Switching to max_tokens parameter for model {model_to_use}")
                    del params["max_completion_tokens"]
                    params["max_tokens"] = max_tokens
                    response = self.client.chat.completions.create(**params)
                else:
                    # Re-raise if it's a different error
                    raise
            
            # Handle streaming response
            if stream:
                # Return a generator for streaming responses
                def generate_stream():
                    for chunk in response:
                        if chunk.choices and len(chunk.choices) > 0:
                            content = chunk.choices[0].delta.content
                            if content:
                                yield content
                
                return generate_stream()
            else:
                # Extract the response text for non-streaming response
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
        # Special case for gpt-4-1 which should be gpt-4.1
        if model_name == "gpt-4-1":
            logger.info(f"Mapping 'gpt-4-1' to 'gpt-4.1'")
            return "gpt-4.1"
        
        # Special case for gpt-4o-mini which should be gpt-4o-mini
        if model_name == "gpt-4o-mini":
            logger.info(f"Using model name as-is: {model_name}")
            return "gpt-4o-mini"
            
        # Log the model name for debugging
        logger.info(f"Using model name as-is: {model_name}")
        return model_name
