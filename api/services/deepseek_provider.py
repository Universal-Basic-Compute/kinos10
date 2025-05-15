import os
import requests
import json
from services.llm_service import LLMProvider
from config import logger

class DeepSeekProvider(LLMProvider):
    """DeepSeek LLM provider implementation"""
    
    def __init__(self, api_key=None):
        super().__init__(api_key)
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            logger.warning("DEEPSEEK_API_KEY environment variable not set")
        
        # Set API endpoint
        self.api_endpoint = "https://api.deepseek.com/v1/chat/completions"  # Update to v1 endpoint
        logger.info("DeepSeek provider initialized")
    
    def generate_response(self, messages, system=None, max_tokens=4000, model=None, stream=False):
        """Generate a response using DeepSeek API"""
        try:
            # Use provided model or default with proper mapping
            model_to_use = model or "deepseek-chat"
            
            # Map model names to DeepSeek's expected format
            model_mapping = {
                "deepseek-chat": "deepseek-chat",
                "deepseek-coder": "deepseek-coder",
                "deepseek-llm": "deepseek-llm"
            }
            
            # Use the mapped model name if available, otherwise use as-is
            actual_model = model_mapping.get(model_to_use, model_to_use)
            
            logger.info(f"Using DeepSeek model: {actual_model} (mapped from {model_to_use})")
            
            # If system message is provided, add it to the messages array
            formatted_messages = []
            if system:
                formatted_messages.append({"role": "system", "content": system})
            
            # Add the rest of the messages
            formatted_messages.extend(messages)
            
            # Prepare the request payload
            payload = {
                "model": actual_model,
                "messages": formatted_messages,
                "max_tokens": max_tokens,
                "stream": False
            }
            
            # Set up headers with authentication
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            # Log the request (without sensitive data)
            logger.info(f"Sending request to DeepSeek API with model: {actual_model}")
            logger.info(f"Number of messages: {len(formatted_messages)}")
            
            # Make the API call
            response = requests.post(
                self.api_endpoint,
                headers=headers,
                data=json.dumps(payload),
                timeout=60  # 60 second timeout
            )
            
            # Check if the request was successful
            response.raise_for_status()
            
            # Parse the response
            try:
                response_data = response.json()
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {str(e)}")
                logger.error(f"Response content: {response.text[:1000]}")  # Log first 1000 chars
                return f"I apologize, but I received an invalid response from the DeepSeek API. Please try again."
            
            # Extract the response text
            if response_data.get("choices") and len(response_data["choices"]) > 0:
                return response_data["choices"][0]["message"]["content"]
            else:
                logger.error("Empty response from DeepSeek")
                return "I apologize, but I couldn't generate a response."
                
        except requests.exceptions.HTTPError as e:
            # Handle HTTP errors
            logger.error(f"DeepSeek API HTTP error: {str(e)}")
            
            # Try to extract more detailed error information
            error_detail = "Unknown error"
            try:
                error_data = e.response.json()
                if "error" in error_data:
                    error_detail = error_data["error"].get("message", str(error_data["error"]))
            except:
                error_detail = str(e)
                
            return f"I apologize, but there was an API error: {error_detail}. Please try again with a different model or later."
            
        except requests.exceptions.ConnectionError:
            logger.error("Connection error when calling DeepSeek API")
            return "I apologize, but I couldn't connect to the DeepSeek API. Please check your internet connection and try again."
            
        except requests.exceptions.Timeout:
            logger.error("Timeout when calling DeepSeek API")
            return "I apologize, but the request to the DeepSeek API timed out. Please try again later."
            
        except Exception as e:
            logger.error(f"Error calling DeepSeek API: {str(e)}")
            return f"I apologize, but I encountered an error: {str(e)}. Please try again."
