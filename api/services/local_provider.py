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
        """Generate a response by calling the local LLM endpoint (OpenAI-compatible)."""
        
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
        payload_model = "google/gemma-3-27b" # Default model name for the local endpoint
        if model:
            if model.startswith("local/"):
                # Extract actual model name, e.g., "local/my-model" -> "my-model"
                payload_model = model.split("/", 1)[1]
            elif model.lower() != "local": 
                # If model is something other than just "local", use it
                payload_model = model
        
        # Ensure roles in payload_messages alternate correctly
        cleaned_payload_messages = self._ensure_alternating_roles(payload_messages)

        payload = {
            "model": payload_model,
            "messages": cleaned_payload_messages, # Use cleaned messages
            "stream": stream,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
        # You can add other OpenAI-compatible parameters like temperature, top_p here
        # payload["temperature"] = 0.7

        logger.info(f"Sending request to Local LLM (OpenAI-like): {endpoint_url} with model: {payload['model']}")
        logger.debug(f"Local LLM Payload: {json.dumps(payload, indent=2)}")

        try:
            response = requests.post(endpoint_url, headers=headers, json=payload, stream=stream, timeout=180) 
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
                try:
                    error_response_text = e.response.json().get("error", e.response.text)
                except json.JSONDecodeError:
                    error_response_text = e.response.text
            return f"Error connecting to local LLM: {str(e)}. Response: {error_response_text}"
        except Exception as e:
            logger.error(f"An unexpected error occurred with local LLM: {str(e)}")
            return f"An unexpected error occurred: {str(e)}"

    def _ensure_alternating_roles(self, original_payload_messages):
        """
        Ensures that messages alternate between 'user' and 'assistant' roles,
        after an optional initial 'system' message. Merges consecutive messages
        of the same role.
        """
        if not original_payload_messages:
            return []

        cleaned_messages = []
        
        # 1. Handle initial system message(s)
        #    Multiple system messages will be merged into one.
        system_content_parts = []
        messages_after_system = []
        system_message_processed = False

        for i, msg_dict in enumerate(original_payload_messages):
            if msg_dict.get("role") == "system":
                system_content_parts.append(str(msg_dict.get("content", "")))
                system_message_processed = True
            else:
                # Once a non-system message is found, the rest are conversational
                messages_after_system = original_payload_messages[i:]
                break
        
        if not system_message_processed: # No system messages at the start
            messages_after_system = original_payload_messages

        if system_content_parts:
            cleaned_messages.append({"role": "system", "content": "\n".join(filter(None, system_content_parts))})

        if not messages_after_system:
            return cleaned_messages # Only system message(s), or empty input

        # 2. Process conversational messages (user/assistant)
        #    Ensures the first is 'user' and then alternates, merging same-role messages.
        
        # Temporary list to hold user/assistant messages before adding to cleaned_messages
        temp_conversational_messages = []

        for msg_idx, current_msg_dict in enumerate(messages_after_system):
            current_role = current_msg_dict.get("role")
            current_content = str(current_msg_dict.get("content", ""))

            if current_role not in ["user", "assistant"]:
                logger.warning(f"Skipping message with invalid role '{current_role}': {current_msg_dict}")
                continue

            if not temp_conversational_messages: # This is the first message in the user/assistant sequence
                if current_role == "assistant":
                    logger.warning("First conversational message is 'assistant'. Prepending a generic user message.")
                    temp_conversational_messages.append({"role": "user", "content": "(System note: Ensuring conversation starts with user role)"})
                # Add the current message (it's either 'user', or 'assistant' now following the generic 'user')
                temp_conversational_messages.append({"role": current_role, "content": current_content})
            else: # Not the first conversational message
                last_added_role_in_temp = temp_conversational_messages[-1].get("role")
                if current_role == last_added_role_in_temp:
                    logger.warning(f"Consecutive '{current_role}' roles. Merging content.")
                    temp_conversational_messages[-1]["content"] += "\n" + current_content
                else: # Roles alternate, good to add
                    temp_conversational_messages.append({"role": current_role, "content": current_content})
        
        cleaned_messages.extend(temp_conversational_messages)
                
        return cleaned_messages
