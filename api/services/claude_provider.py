import os
import json
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
    
    def generate_response(self, messages, system=None, max_tokens=4000, model=None, stream=False):
        """Generate a response using Claude with optional streaming support"""
        try:
            # Use provided model or default
            model_to_use = model or os.getenv("CLAUDE_MODEL", "claude-3-7-sonnet-latest")
            
            # Log the request details
            logger.info(f"Calling Claude API with model: {model_to_use}")
            logger.info(f"Stream mode: {stream}")
            logger.info(f"Number of messages: {len(messages)}")
            
            # Ensure stream parameter is boolean, not string
            if isinstance(stream, str):
                stream = stream.lower() == 'true'
            
            if stream:
                # Return a generator for streaming responses
                return self._generate_streaming_response(model_to_use, max_tokens, system, messages)
            else:
                # Regular non-streaming response
                try:
                    # Log the full request for debugging
                    logger.info(f"Claude API request: model={model_to_use}, max_tokens={max_tokens}")
                    logger.info(f"System prompt length: {len(system) if system else 0}")
                    
                    # Make the API call with explicit error handling
                    try:
                        response = self.client.messages.create(
                            model=model_to_use,
                            max_tokens=max_tokens,
                            system=system,
                            messages=messages
                        )
                        
                        # Log the raw response for debugging
                        logger.info(f"Claude API raw response type: {type(response)}")
                        
                        # Extract the response text
                        if response.content and len(response.content) > 0:
                            result = response.content[0].text
                            # Sanitize the response to remove control characters
                            import re
                            result = re.sub(r'[\x00-\x1F\x7F]', '', result)
                            logger.info(f"Claude API extracted text (first 100 chars): {result[:100]}")
                            return result
                        else:
                            logger.error("Empty response from Claude")
                            return "I apologize, but I couldn't generate a response."
                    except anthropic.APIError as api_err:
                        logger.error(f"Claude API error: {str(api_err)}")
                        return f"I apologize, but there was an API error: {str(api_err)}. Please try again."
                    except anthropic.APIConnectionError as conn_err:
                        logger.error(f"Claude API connection error: {str(conn_err)}")
                        return "I apologize, but I couldn't connect to the Claude API. Please try again later."
                    except anthropic.RateLimitError as rate_err:
                        logger.error(f"Claude API rate limit error: {str(rate_err)}")
                        return "I apologize, but we've hit the rate limit for the Claude API. Please try again in a moment."
                    except Exception as e:
                        logger.error(f"Unexpected error calling Claude API: {str(e)}")
                        return f"I apologize, but I encountered an unexpected error: {str(e)}. Please try again."
                        
                except json.JSONDecodeError as json_err:
                    # Handle JSON parsing errors specifically
                    logger.error(f"JSON parsing error in Claude response: {str(json_err)}")
                    logger.error(f"Error position: line {json_err.lineno}, column {json_err.colno}, char {json_err.pos}")
                    
                    # Try to recover by using a fallback approach
                    try:
                        # Use a more direct approach with the Anthropic API
                        logger.info("Attempting fallback approach with direct API call")
                        
                        # Convert messages to the format expected by the API
                        formatted_messages = []
                        for msg in messages:
                            formatted_messages.append({
                                "role": msg.get("role", "user"),
                                "content": msg.get("content", "")
                            })
                        
                        # Make a direct API call with minimal processing
                        response = self.client.messages.create(
                            model=model_to_use,
                            max_tokens=max_tokens,
                            system=system,
                            messages=formatted_messages
                        )
                        
                        # Extract the response text
                        if response.content and len(response.content) > 0:
                            result = response.content[0].text
                            # Sanitize the response to remove control characters
                            import re
                            result = re.sub(r'[\x00-\x1F\x7F]', '', result)
                            logger.info(f"Fallback approach succeeded, got response (first 100 chars): {result[:100]}")
                            return result
                        else:
                            logger.error("Empty response from Claude in fallback approach")
                            return "I apologize, but I couldn't generate a response."
                            
                    except Exception as fallback_err:
                        logger.error(f"Fallback approach also failed: {str(fallback_err)}")
                        return f"I apologize, but there was an error processing the response. Please try again."
                
        except Exception as e:
            logger.error(f"Error calling Claude API: {str(e)}")
            # Try to provide more context about the error
            error_type = type(e).__name__
            logger.error(f"Error type: {error_type}")
            
            # For debugging, log the full exception traceback
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            
            return f"I apologize, but I encountered an error: {str(e)}. Please try again."
            
    def _generate_streaming_response(self, model, max_tokens, system, messages):
        """Generate a streaming response using Claude"""
        try:
            # Create a streaming response
            with self.client.messages.stream(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=messages
            ) as stream:
                # Yield each text chunk as it arrives
                for text in stream.text_stream:
                    # Sanitize the text chunk to remove control characters
                    import re
                    sanitized_text = re.sub(r'[\x00-\x1F\x7F]', '', text)
                    yield sanitized_text
        except Exception as e:
            logger.error(f"Error in Claude streaming API: {str(e)}")
            yield f"I apologize, but I encountered an error: {str(e)}. Please try again."
