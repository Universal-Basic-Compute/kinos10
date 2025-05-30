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
        """Generate a response by calling the local LLM endpoint."""
        
        endpoint_url = f"{self.LOCAL_MODEL_BASE_URL}/v1/chat/completions" # Standard OpenAI path

        headers = {
            "Content-Type": "application/json",
        }
        # If your local endpoint needs an API key:
        # if self.local_api_key:
        #     headers["Authorization"] = f"Bearer {self.local_api_key}"

        payload_messages = []
        if system:
            payload_messages.append({"role": "system", "content": system})
        
        # Ensure messages are in the correct format (list of dicts)
        for msg in messages:
            if isinstance(msg, dict) and "role" in msg and "content" in msg:
                payload_messages.append(msg)
            else:
                logger.warning(f"Skipping malformed message: {msg}")


        # Determine the model name to send in the payload
        payload_model = "local-default" # Default model name for the local endpoint
        if model:
            if model.startswith("local/"):
                # Extract actual model name, e.g., "local/my-model" -> "my-model"
                payload_model = model.split("/", 1)[1]
            elif model.lower() != "local": 
                # If model is something other than just "local", use it
                payload_model = model
        
        payload = {
            "model": payload_model,
            "messages": payload_messages,
            "stream": stream,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
        # You can add other OpenAI-compatible parameters like temperature, top_p here
        # payload["temperature"] = 0.7

        logger.info(f"Sending request to Local LLM: {endpoint_url} with model: {payload['model']}")
        logger.debug(f"Local LLM Payload: {json.dumps(payload, indent=2)}")

        try:
            response = requests.post(endpoint_url, headers=headers, json=payload, stream=stream, timeout=180) # Increased timeout
            response.raise_for_status()

            if stream:
                def generate_stream():
                    try:
                        for line in response.iter_lines():
                            if line:
                                decoded_line = line.decode('utf-8')
                                if decoded_line.startswith("data: "):
                                    json_data_str = decoded_line[len("data: "):].strip()
                                    if json_data_str == "[DONE]":
                                        logger.info("Stream [DONE] received.")
                                        return
                                    try:
                                        data = json.loads(json_data_str)
                                        if data.get("choices") and data["choices"][0].get("delta"):
                                            content_delta = data["choices"][0]["delta"].get("content")
                                            if content_delta:
                                                yield content_delta
                                    except json.JSONDecodeError:
                                        logger.warning(f"Could not decode JSON from stream: {json_data_str}")
                                    except Exception as e_stream_proc:
                                        logger.error(f"Error processing stream data item: {e_stream_proc}")
                                        # Potentially yield an error message or break
                        logger.info("Local LLM stream finished.")
                    except Exception as e_outer_stream:
                        logger.error(f"Error during local LLM streaming: {e_outer_stream}")
                        yield f"Error during streaming: {str(e_outer_stream)}"
                return generate_stream()
            else:
                response_data = response.json()
                logger.debug(f"Local LLM Non-stream Response Data: {json.dumps(response_data, indent=2)}")
                if response_data.get("choices") and response_data["choices"][0].get("message"):
                    full_content = response_data["choices"][0]["message"]["content"]
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
                error_response_text = e.response.text
            return f"Error connecting to local LLM: {str(e)}. Response: {error_response_text}"
        except Exception as e:
            logger.error(f"An unexpected error occurred with local LLM: {str(e)}")
            return f"An unexpected error occurred: {str(e)}"
