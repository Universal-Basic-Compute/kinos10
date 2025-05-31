import os
import requests
import json
from services.llm_service import LLMProvider
from config import logger
import re # For sanitizing response

class LocalProvider(LLMProvider):
    """
    LLM provider that redirects requests to a local or custom (e.g., Ngrok) endpoint.
    Assumes the target endpoint is OpenAI-compatible.
    """
    LOCAL_MODEL_BASE_URL = "https://trusted-magpie-social.ngrok-free.app" 

    def __init__(self, api_key=None): # api_key might be for the target endpoint
        super().__init__(api_key)
        # If your local endpoint requires a specific API key, you can set it here
        # For example, self.local_api_key = os.getenv("LOCAL_LLM_API_KEY") or api_key
        logger.info(f"LocalProvider initialized, targeting: {self.LOCAL_MODEL_BASE_URL}")

    def generate_response(self, messages, system=None, max_tokens=None, model=None, stream=False):
        """Generate a response by calling the local LLM endpoint (Ollama-compatible)."""
        
        endpoint_url = f"{self.LOCAL_MODEL_BASE_URL}/api/chat" # Ollama /api/chat endpoint

        headers = {
            "Content-Type": "application/json",
        }
        # If your local endpoint needs an API key (though Ollama typically doesn't for /api/chat)
        # if self.local_api_key:
        #     headers["Authorization"] = f"Bearer {self.local_api_key}"

        payload_messages = []
        if system:
            payload_messages.append({"role": "system", "content": system})
        
        # Ensure messages are in the correct format (list of dicts)
        for msg in messages:
            if isinstance(msg, dict) and "role" in msg and "content" in msg:
                # Convert "assistant" role to "model" if needed by the endpoint,
                # but Ollama uses "assistant" for responses and expects "user" or "system" for inputs.
                # For requests, "assistant" messages are valid to show conversation history.
                payload_messages.append(msg)
            else:
                logger.warning(f"Skipping malformed message: {msg}")

        # Determine the model name to send in the payload
        # For Ollama, this is the model tag, e.g., "llama2" or "gemma3:12b"
        payload_model = "gemma3:27b" # Default model if not specified or only "local" is given
        if model:
            if model.startswith("local/"):
                # Extract actual model name, e.g., "local/gemma3:12b" -> "gemma3:12b"
                payload_model = model.split("/", 1)[1]
            elif model.lower() != "local": 
                # If model is something other than just "local", use it (e.g. "gemma3:12b")
                payload_model = model
        
        payload = {
            "model": payload_model,
            "messages": payload_messages,
            "stream": stream,
        }
        
        # Ollama uses "options" for parameters like max_tokens (num_predict), temperature etc.
        options = {}
        if max_tokens:
            options["num_predict"] = max_tokens # Ollama's equivalent for max_tokens
        # if temperature: options["temperature"] = temperature
        if options:
            payload["options"] = options


        logger.info(f"Sending request to Local LLM (Ollama-like): {endpoint_url} with model: {payload['model']}")
        logger.debug(f"Local LLM Payload: {json.dumps(payload, indent=2)}")

        try:
            response = requests.post(endpoint_url, headers=headers, json=payload, stream=stream, timeout=180) 
            response.raise_for_status()

            if stream:
                def generate_stream():
                    try:
                        for line in response.iter_lines():
                            if line:
                                decoded_line = line.decode('utf-8').strip()
                                if not decoded_line:
                                    continue
                                try:
                                    data = json.loads(decoded_line)
                                    if data.get("error"):
                                        logger.error(f"Error from local LLM stream: {data['error']}")
                                        yield f"Error: {data['error']}"
                                        return
                                    
                                    content_chunk = data.get("message", {}).get("content")
                                    if content_chunk:
                                        yield content_chunk
                                    
                                    if data.get("done"):
                                        logger.info("Local LLM stream finished (done: true).")
                                        return
                                except json.JSONDecodeError:
                                    logger.warning(f"Could not decode JSON from stream line: {decoded_line}")
                                except Exception as e_stream_proc:
                                    logger.error(f"Error processing stream data item: {e_stream_proc}")
                                    yield f"Error processing stream: {str(e_stream_proc)}"
                                    return
                        logger.info("Local LLM stream iteration complete.")
                    except Exception as e_outer_stream:
                        logger.error(f"Error during local LLM streaming: {e_outer_stream}")
                        yield f"Error during streaming: {str(e_outer_stream)}"
                return generate_stream()
            else: # Non-streaming
                response_data = response.json()
                logger.debug(f"Local LLM Non-stream Response Data: {json.dumps(response_data, indent=2)}")
                
                if response_data.get("error"):
                    logger.error(f"Error from local LLM: {response_data['error']}")
                    return f"Error: {response_data['error']}"

                if response_data.get("message") and "content" in response_data["message"]:
                    full_content = response_data["message"]["content"]
                    # Sanitize the response to remove control characters
                    sanitized_content = re.sub(r'[\x00-\x1F\x7F]', '', full_content)
                    return sanitized_content
                else:
                    logger.error(f"Unexpected response structure from local LLM: {response_data}")
                    return "Error: Unexpected response structure from local LLM."

        except requests.exceptions.Timeout:
            logger.error(f"Timeout calling local LLM endpoint: {endpoint_url}")
            return "Error: Timeout connecting to local LLM."
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error calling local LLM endpoint: {endpoint_url}")
            return "Error: Could not connect to local LLM. Ensure it's running and accessible."
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling local LLM endpoint: {str(e)}")
            error_response_text = ""
            if e.response is not None:
                try:
                    error_response_text = e.response.json().get("error", e.response.text)
                except json.JSONDecodeError:
                    error_response_text = e.response.text
            return f"Error connecting to local LLM: {str(e)}. Response: {error_response_text}"
        except Exception as e:
            logger.error(f"An unexpected error occurred with local LLM: {str(e)}")
            return f"An unexpected error occurred: {str(e)}"
