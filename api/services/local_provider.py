import os
import requests
import json
from services.llm_service import LLMProvider
from config import logger
import re # For sanitizing response

# Define LOCAL_MODEL_BASE_URL at the module level
LOCAL_MODEL_BASE_URL = "https://trusted-magpie-social.ngrok-free.app"

class LocalProvider(LLMProvider):
    """
    LLM provider that redirects requests to a local or custom (e.g., Ngrok) endpoint.
    Assumes the target endpoint is OpenAI-compatible.
    """
    # Max characters aiming for < 36k tokens, using ~3.5 chars/token as a rough guide
    MAX_CHARS_FOR_PROVIDER = int(36000 * 3.5) # Approx 126,000 characters

    def __init__(self, api_key=None): # api_key might be for the target endpoint
        super().__init__(api_key)
        # If your local endpoint requires a specific API key, you can set it here
        # For example, self.local_api_key = os.getenv("LOCAL_LLM_API_KEY") or api_key
        logger.info(f"LocalProvider initialized, targeting: {LOCAL_MODEL_BASE_URL}")

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
        payload_model = "deepseek/deepseek-r1-0528-qwen3-8b" # Default model name for the local endpoint
        if model:
            if model.startswith("local/"):
                # Extract actual model name, e.g., "local/my-model" -> "my-model"
                payload_model = model.split("/", 1)[1]
            elif model.lower() != "local": 
                # If model is something other than just "local", use it
                payload_model = model

        # Truncate messages if total characters exceed the provider's limit
        truncated_payload_messages = self._truncate_payload_for_token_limit(payload_messages)
        
        # Ensure roles in the (potentially truncated) payload_messages alternate correctly
        cleaned_payload_messages = self._ensure_alternating_roles(truncated_payload_messages)

        payload = {
            "model": payload_model,
            "messages": cleaned_payload_messages, # Use cleaned and role-alternated messages
            "stream": stream,
        }
        if max_tokens is not None and max_tokens > 0: # Check for valid positive integer
            payload["max_tokens"] = max_tokens
            logger.info(f"Using provided max_tokens for Local LLM: {max_tokens}")
        else:
            default_llm_max_tokens = 64000
            payload["max_tokens"] = default_llm_max_tokens
            if max_tokens is not None:
                 logger.info(f"max_tokens was '{max_tokens}', using default max_tokens for Local LLM: {default_llm_max_tokens}")
            else:
                 logger.info(f"max_tokens not provided, using default max_tokens for Local LLM: {default_llm_max_tokens}")
        # You can add other OpenAI-compatible parameters like temperature, top_p here
        # payload["temperature"] = 0.7

        logger.info(f"Sending request to Local LLM (OpenAI-like): {endpoint_url} with model: {payload['model']}")
        logger.debug(f"Local LLM Payload: {json.dumps(payload, indent=2)}")

        try:
            response = requests.post(endpoint_url, headers=headers, json=payload, stream=stream, timeout=600) # Increased timeout to 10 minutes
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

    def _estimate_char_count(self, messages_list):
        """Estimates the total character count of the content in a list of messages."""
        return sum(len(str(msg.get("content", ""))) for msg in messages_list)

    def _truncate_payload_for_token_limit(self, payload_messages):
        """
        Truncates the payload, primarily the system message content (where files are often placed),
        to stay within MAX_CHARS_FOR_PROVIDER.
        It attempts to remove file blocks one by one from the system message.
        """
        current_chars = self._estimate_char_count(payload_messages)

        if current_chars <= self.MAX_CHARS_FOR_PROVIDER:
            return payload_messages

        logger.warning(f"Payload character count ({current_chars}) exceeds limit ({self.MAX_CHARS_FOR_PROVIDER}). Attempting truncation.")
        
        # Separate system message from others
        system_msg_index = -1
        original_system_content = ""
        other_messages = []

        for i, msg in enumerate(payload_messages):
            if msg.get("role") == "system":
                if system_msg_index == -1: # Take the first system message
                    system_msg_index = i
                    original_system_content = str(msg.get("content", ""))
                else: # If multiple system messages, append to others (will be handled by role alternation)
                    other_messages.append(msg)
            else:
                other_messages.append(msg)
        
        chars_from_other_messages = self._estimate_char_count(other_messages)

        if system_msg_index == -1 or not original_system_content:
            logger.warning("Token limit exceeded, but no system message found or system message is empty. Cannot drop files from system prompt. Conversational history might be too long.")
            # Future: Could implement truncation of `other_messages` here if necessary.
            # For now, returning as is, hoping role alternation might simplify it, or the API handles it.
            return payload_messages 

        # Attempt to parse file blocks from system content.
        # Assumes files are appended like: PREAMBLE_TEXT\n# File: file1.txt\nCONTENT1\n# File: file2.txt\nCONTENT2...
        # The split delimiter includes the newline before "# File: " to better isolate blocks.
        parts = original_system_content.split("\n# File: ")
        preamble = parts[0]
        file_blocks_text = []
        if len(parts) > 1:
            for part_content in parts[1:]:
                # Each part_content is "filename.txt\nCONTENT". We need to re-add "# File: "
                file_blocks_text.append("# File: " + part_content)
        
        logger.info(f"Found {len(file_blocks_text)} potential file blocks in system prompt. Preamble length: {len(preamble)} chars.")

        # Iteratively remove file blocks (from the end, assuming less critical or last added)
        # until the total character count is within limits.
        modified_system_content = original_system_content
        
        for i in range(len(file_blocks_text)): # Iterate enough times to potentially remove all
            current_system_parts = [preamble] + file_blocks_text
            current_system_content_str = "\n".join(filter(None, current_system_parts)).strip()
            
            current_total_chars = chars_from_other_messages + len(current_system_content_str)

            if current_total_chars <= self.MAX_CHARS_FOR_PROVIDER:
                logger.info(f"System prompt content reduced by removing {i} file blocks. New total chars: {current_total_chars}")
                payload_messages[system_msg_index]["content"] = current_system_content_str
                return payload_messages
            
            if not file_blocks_text: # No more file blocks to remove
                break
            
            removed_block = file_blocks_text.pop() # Remove the last file block
            logger.debug(f"Removed file block (approx. {len(removed_block)} chars) from system prompt for truncation.")

        # If removing all file blocks is still not enough, truncate the preamble.
        # At this point, file_blocks_text is empty. System content is just the preamble.
        final_system_content = preamble
        current_total_chars = chars_from_other_messages + len(final_system_content)

        if current_total_chars > self.MAX_CHARS_FOR_PROVIDER:
            allowed_preamble_chars = self.MAX_CHARS_FOR_PROVIDER - chars_from_other_messages
            if allowed_preamble_chars < 0: 
                allowed_preamble_chars = 0 # Should not happen if other_messages alone fit
            
            final_system_content = preamble[:allowed_preamble_chars]
            payload_messages[system_msg_index]["content"] = final_system_content
            new_total_chars = chars_from_other_messages + len(final_system_content)
            logger.warning(f"System prompt preamble truncated to {len(final_system_content)} chars. New total chars: {new_total_chars}")
        else:
            payload_messages[system_msg_index]["content"] = final_system_content
            logger.info(f"Removed all file blocks from system prompt. New total chars: {current_total_chars}")
            
        return payload_messages

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
