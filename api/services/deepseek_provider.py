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
                "stream": stream
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
            
            # Parse the response with more robust error handling
            try:
                # First, try to decode the response as JSON
                response_data = response.json()
            except json.JSONDecodeError as e:
                # If JSON parsing fails, log detailed information
                logger.error(f"Failed to parse JSON response: {str(e)}")
                logger.error(f"Response status code: {response.status_code}")
                logger.error(f"Response content: {response.text[:1000]}")  # Log first 1000 chars
                
                # Try to fix common JSON issues
                try:
                    # Sometimes the response might have invalid escape characters or other issues
                    # Try a more lenient JSON parsing approach
                    import re
                    # Remove control characters
                    cleaned_text = re.sub(r'[\x00-\x1F\x7F]', '', response.text)
                    # Try to parse with a more lenient approach
                    response_data = json.loads(cleaned_text)
                    logger.info("Successfully parsed JSON after cleaning response text")
                except Exception as fix_error:
                    logger.error(f"Failed to fix JSON response: {str(fix_error)}")
                    return f"I apologize, but I received an invalid response from the DeepSeek API. Error details: {str(e)}. Please try again."
            
            # Handle streaming response
            if stream:
                # For streaming, we need to handle the response differently
                # This is a simplified implementation - in a real-world scenario,
                # you would need to handle the SSE stream properly
                logger.warning("Streaming not fully implemented for DeepSeek provider")
                return "Streaming is not fully supported for DeepSeek provider yet."
            else:
                # Extract the response text for non-streaming response
                if response_data.get("choices") and len(response_data["choices"]) > 0:
                    try:
                        return response_data["choices"][0]["message"]["content"]
                    except KeyError as key_error:
                        logger.error(f"Unexpected response structure: {str(key_error)}")
                        logger.error(f"Response data: {json.dumps(response_data)[:1000]}")
                        return "I apologize, but I received an unexpected response structure from the DeepSeek API. Please try again."
                else:
                    logger.error("Empty response from DeepSeek")
                    logger.error(f"Full response: {json.dumps(response_data)[:1000]}")
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
