import os
import requests # Use requests for HTTP calls
from services.llm_service import LLMProvider
from config import logger
import json
import re # Import re for sanitization

# Define constants for finish reasons and harm probabilities
# These are based on typical string values returned by the Gemini REST API
FINISH_REASON_SAFETY = "SAFETY"
FINISH_REASON_RECITATION = "RECITATION"
FINISH_REASON_OTHER = "OTHER"
FINISH_REASON_MAX_TOKENS = "MAX_TOKENS"
FINISH_REASON_STOP = "STOP" # Added for completeness

HARM_PROBABILITY_NEGLIGIBLE = "NEGLIGIBLE"


class GeminiProvider(LLMProvider):
    """Google Gemini LLM provider implementation using direct HTTPS calls"""

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self, api_key=None):
        super().__init__(api_key)
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            logger.warning("GOOGLE_API_KEY environment variable not set")
            # raise ValueError("GOOGLE_API_KEY must be set for GeminiProvider") # Or handle gracefully
        
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        logger.info("GeminiProvider (HTTPS) initialized successfully")

    def _convert_messages_to_gemini_format(self, messages):
        gemini_messages = []
        for message in messages:
            role = message.get("role")
            content = message.get("content")

            # Gemini API expects "user" or "model"
            if role == "assistant":
                role = "model"
            elif role not in ["user", "model"]: # Ensure role is valid
                role = "user" # Default to user if role is something else
            
            if isinstance(content, list): # Handle multimodal content (Anthropic format)
                parts = []
                for item in content:
                    if item.get("type") == "text":
                        parts.append({"text": item.get("text", "")})
                    elif item.get("type") == "image" and item.get("source", {}).get("type") == "base64":
                        # For Gemini REST API, image parts need to be structured correctly
                        # This example assumes base64 encoded images.
                        # The API expects 'inlineData' with 'mimeType' and 'data'.
                        parts.append({
                            "inlineData": {
                                "mimeType": item["source"].get("media_type", "image/jpeg"), # Default to jpeg
                                "data": item["source"].get("data", "")
                            }
                        })
                        logger.info(f"Added image part for Gemini: {item['source'].get('media_type')}")
                    else: # Fallback for unknown content parts
                        parts.append({"text": str(item)}) 
                gemini_messages.append({"role": role, "parts": parts})
            elif isinstance(content, str):
                 gemini_messages.append({"role": role, "parts": [{"text": content}]})
            else:
                logger.warning(f"Unsupported content type in message for Gemini: {type(content)}")
        return gemini_messages

    def _handle_error_response(self, response_data):
        """Helper to parse and log error responses from Gemini API"""
        error_details = response_data.get("error", {})
        message = error_details.get("message", "Unknown error from Gemini API.")
        status = error_details.get("status", "UNKNOWN_STATUS")
        logger.error(f"Gemini API Error: Status {status}, Message: {message}")
        return f"I apologize, but I encountered an error with Gemini: {message}. Please try again."

    def generate_response(self, messages, system=None, max_tokens=None, model=None, stream=False):
        """Generate a response using Gemini API via HTTPS"""
        if not self.api_key:
            return "I apologize, but the Gemini API key is not configured."

        model_name = model.replace("gemini/", "") if model else "gemini-1.5-flash" # Default to a common model
        
        logger.info(f"Calling Gemini API (HTTPS) with model: {model_name}")
        logger.info(f"Stream mode: {stream}")
        logger.info(f"Number of messages: {len(messages)}")

        payload = {
            "contents": self._convert_messages_to_gemini_format(messages)
        }

        if system:
            # For REST API, system_instruction is a top-level key
            payload["system_instruction"] = {"parts": [{"text": system}]}
        
        generation_config = {}
        if max_tokens is not None and max_tokens > 0:
            generation_config["maxOutputTokens"] = max_tokens
            logger.info(f"Using provided max_tokens for Gemini: {max_tokens}")
        else:
            # Default to 64000 if max_tokens is not provided, None, or invalid (e.g., 0)
            default_max_output_tokens = 64000
            generation_config["maxOutputTokens"] = default_max_output_tokens
            if max_tokens is not None: # Log if an invalid value was passed but we're using default
                 logger.info(f"max_tokens was '{max_tokens}', using default maxOutputTokens for Gemini: {default_max_output_tokens}")
            else:
                 logger.info(f"max_tokens not provided, using default maxOutputTokens for Gemini: {default_max_output_tokens}")
        
        # Add other generation_config settings as needed, e.g., temperature, topP
        # generation_config["temperature"] = 0.7 
        payload["generationConfig"] = generation_config # generationConfig will always be set now

        # Safety settings (optional, example to block most harmful content)
        # payload["safetySettings"] = [
        #     {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        #     {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        #     {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        #     {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        # ]

        api_method = "streamGenerateContent?alt=sse" if stream else "generateContent"
        # Ensure model name doesn't have 'gemini/' prefix for URL construction
        url_model_name = model_name.split('/')[-1]
        url = f"{self.BASE_URL}/{url_model_name}:{api_method}?key={self.api_key}"


        try:
            if stream:
                def generate_stream():
                    response = self.session.post(url, json=payload, stream=True, timeout=120) # Added timeout
                    if response.status_code != 200:
                        error_data = {}
                        try:
                            error_data = response.json()
                        except json.JSONDecodeError:
                             error_data = {"error": {"message": f"HTTP Error {response.status_code}. Response: {response.text}"}}
                        yield self._handle_error_response(error_data)
                        return

                    for line in response.iter_lines():
                        if line:
                            decoded_line = line.decode('utf-8')
                            if decoded_line.startswith('data: '):
                                try:
                                    chunk_data = json.loads(decoded_line[6:])
                                    if chunk_data.get("promptFeedback", {}).get("blockReason"):
                                        reason = chunk_data["promptFeedback"]["blockReason"]
                                        reason_msg = chunk_data["promptFeedback"].get("blockReasonMessage", reason)
                                        error_message = f"I apologize, but your request was blocked by Gemini. Reason: {reason_msg}"
                                        logger.error(f"Gemini stream error (prompt feedback): {error_message}")
                                        yield error_message
                                        return

                                    candidates = chunk_data.get("candidates")
                                    if candidates:
                                        candidate = candidates[0]
                                        finish_reason = candidate.get("finishReason")
                                        if finish_reason == FINISH_REASON_SAFETY:
                                            safety_messages = []
                                            for rating in candidate.get("safetyRatings", []):
                                                if rating.get("probability") != HARM_PROBABILITY_NEGLIGIBLE:
                                                    safety_messages.append(f"{rating.get('category', 'UnknownCategory').split('_')[-1]} (Prob: {rating.get('probability')})")
                                            error_message = f"I apologize, but content was blocked by Gemini due to safety concerns: {', '.join(safety_messages)}." if safety_messages else "I apologize, but content was blocked by Gemini due to safety concerns."
                                            logger.error(f"Gemini stream error (safety): {error_message}")
                                            yield error_message
                                            return
                                        elif finish_reason == FINISH_REASON_RECITATION:
                                            error_message = "I apologize, but content was blocked by Gemini due to recitation policy."
                                            logger.error(f"Gemini stream error (recitation): {error_message}")
                                            yield error_message
                                            return
                                        
                                        content = candidate.get("content", {})
                                        parts = content.get("parts", [])
                                        for part_item in parts: # Renamed 'part' to 'part_item' to avoid conflict
                                            if "text" in part_item:
                                                yield part_item["text"]
                                except json.JSONDecodeError:
                                    logger.warning(f"Could not decode JSON line from stream: {decoded_line}")
                                except Exception as e_stream_inner:
                                    logger.error(f"Error processing stream chunk: {str(e_stream_inner)}")
                                    yield f"Error processing stream: {str(e_stream_inner)}" # yield error to client
                                    return # Stop streaming on error
                return generate_stream()
            else: # Non-streaming
                response = self.session.post(url, json=payload, timeout=120) # Added timeout
                if response.status_code != 200:
                    error_data = {}
                    try:
                        error_data = response.json()
                    except json.JSONDecodeError:
                        error_data = {"error": {"message": f"HTTP Error {response.status_code}. Response: {response.text}"}}
                    return self._handle_error_response(error_data)

                response_data = response.json()
                
                # logger.debug(f"Gemini API raw response: {json.dumps(response_data, indent=2)}")

                prompt_feedback = response_data.get("promptFeedback")
                if prompt_feedback and prompt_feedback.get("blockReason"):
                    reason = prompt_feedback["blockReason"]
                    reason_msg = prompt_feedback.get("blockReasonMessage", reason) # Use blockReasonMessage if available
                    logger.error(f"Gemini prompt feedback: {prompt_feedback}")
                    return f"I apologize, but your request was blocked by Gemini. Reason: {reason_msg}"

                candidates = response_data.get("candidates")
                if not candidates:
                    logger.error("No candidates found in Gemini response.")
                    return "I apologize, but I received an empty response from Gemini."

                candidate = candidates[0]
                finish_reason = candidate.get("finishReason")

                if finish_reason == FINISH_REASON_SAFETY:
                    safety_messages = []
                    for rating in candidate.get("safetyRatings", []):
                        if rating.get("probability") != HARM_PROBABILITY_NEGLIGIBLE:
                            safety_messages.append(f"{rating.get('category', 'UnknownCategory').split('_')[-1]} (Prob: {rating.get('probability')})")
                    if safety_messages:
                        logger.error(f"Content blocked by Gemini due to safety reasons: {', '.join(safety_messages)}")
                        return f"I apologize, but your request was blocked by Gemini due to safety concerns: {', '.join(safety_messages)}."
                    else:
                        logger.error("Content blocked by Gemini due to unspecified safety reasons (FinishReason.SAFETY).")
                        return "I apologize, but your request was blocked by Gemini due to safety concerns."
                elif finish_reason == FINISH_REASON_RECITATION:
                    logger.error("Content blocked by Gemini due to recitation.")
                    return "I apologize, but your request was blocked by Gemini due to recitation policy."
                elif finish_reason == FINISH_REASON_OTHER:
                    logger.error("Gemini response finished due to an 'OTHER' reason.")
                    return "I apologize, but the Gemini response finished due to an unspecified error."

                content = candidate.get("content", {})
                parts = content.get("parts", [])
                result_parts = [part_item.get("text", "") for part_item in parts if "text" in part_item] # Renamed 'part' to 'part_item'
                result = "".join(result_parts)
                
                if not result:
                    if finish_reason == FINISH_REASON_MAX_TOKENS:
                         return "I apologize, but the response from Gemini was cut off due to length limits, and no content was provided."
                    logger.warning(f"No text found in Gemini response parts. Finish reason: {finish_reason}")
                    if any(part_item for part_item in parts): # Renamed 'part' to 'part_item'
                         return "I apologize, but the response from Gemini did not contain any text content."
                    return "I apologize, but I received an empty response from Gemini."
                
                result = re.sub(r'[\x00-\x1F\x7F]', '', result) # Sanitize
                logger.info(f"Gemini API (HTTPS) extracted text (first 100 chars): {result[:100]}")
                return result

        except requests.exceptions.RequestException as e_req:
            logger.error(f"Error calling Gemini API (HTTPS) - RequestException: {str(e_req)}")
            return f"I apologize, but I encountered a network error with Gemini: {str(e_req)}. Please try again."
        except json.JSONDecodeError as e_json:
            logger.error(f"Error calling Gemini API (HTTPS) - JSONDecodeError: {str(e_json)}")
            return f"I apologize, but I received an invalid response from Gemini. Please try again."
        except Exception as e:
            logger.error(f"Error calling Gemini API (HTTPS): {str(e)}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return f"I apologize, but I encountered an error with Gemini: {str(e)}. Please try again."
