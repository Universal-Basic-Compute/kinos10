import os
import base64
import json # Keep for logging if necessary
from google import generativeai as genai
from google.generativeai import types as genai_types
from google.generativeai.types import HarmCategory, HarmBlockThreshold # For safety settings
from services.llm_service import LLMProvider
from config import logger

class GeminiProvider(LLMProvider):
    """Google Gemini LLM provider implementation using the official Python SDK"""

    def __init__(self, api_key=None):
        super().__init__(api_key)
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            logger.warning("GOOGLE_API_KEY environment variable not set. GeminiProvider may not function.")
            # Depending on SDK behavior, client initialization might fail here or later.
        
        try:
            # The SDK typically uses genai.configure(api_key=...) or passes api_key to client/model.
            # For simplicity with genai.GenerativeModel, ensure API key is configured.
            if self.api_key:
                 genai.configure(api_key=self.api_key)
            logger.info("GeminiProvider (SDK) initialized successfully.")
        except Exception as e:
            logger.error(f"Error configuring Gemini SDK: {str(e)}")
            # This provider instance might be unusable if configuration fails.

    def _convert_messages_to_sdk_format(self, messages):
        sdk_messages = []
        for message in messages:
            role = message.get("role")
            content = message.get("content")

            # SDK expects "user" or "model"
            if role == "assistant":
                role = "model"
            elif role not in ["user", "model"]:
                logger.warning(f"Unsupported role '{role}' for Gemini, defaulting to 'user'.")
                role = "user"
            
            parts = []
            if isinstance(content, list):  # Multimodal content (Anthropic-like format)
                for item in content:
                    item_type = item.get("type")
                    if item_type == "text":
                        parts.append(item.get("text", ""))
                    elif item_type == "image" and item.get("source", {}).get("type") == "base64":
                        try:
                            img_base64_data = item["source"].get("data", "")
                            # Ensure base64 string is clean (remove data URI prefix if present)
                            if ',' in img_base64_data:
                                img_base64_data = img_base64_data.split(',', 1)[1]
                            
                            img_bytes = base64.b64decode(img_base64_data)
                            mime_type = item["source"].get("media_type", "image/jpeg") # Default to JPEG
                            parts.append(genai_types.Part(inline_data=genai_types.Blob(mime_type=mime_type, data=img_bytes)))
                            logger.info(f"Added image part for Gemini SDK: {mime_type}")
                        except Exception as e:
                            logger.error(f"Error processing base64 image for Gemini SDK: {str(e)}")
                            parts.append("[Error processing image]") # Placeholder for error
                    else:
                        logger.warning(f"Unsupported item type '{item_type}' in content list, converting to string.")
                        parts.append(str(item))
            elif isinstance(content, str):
                parts.append(content)
            else:
                logger.warning(f"Unsupported content type '{type(content)}' for Gemini, converting to string.")
                parts.append(str(content))
            
            # Ensure parts are not empty, as SDK might require non-empty parts
            if not parts:
                parts.append("") # Add an empty string if no parts were generated

            sdk_messages.append({"role": role, "parts": parts})
        return sdk_messages

    def _handle_sdk_error(self, e, context_message="Error with Gemini SDK"):
        logger.error(f"{context_message}: {str(e)}")
        # You might want to check for specific SDK exception types here
        # e.g., if isinstance(e, genai.types.BlockedPromptException):
        # return f"Your request was blocked by Gemini: {str(e)}"
        return f"I apologize, but I encountered an error with Gemini (SDK): {str(e)}. Please try again."

    def generate_response(self, messages, system=None, max_tokens=None, model=None, stream=False):
        if not self.api_key:
            return "I apologize, but the Gemini API key is not configured."

        # Model name for SDK, e.g., "gemini-1.5-flash", "gemini-pro"
        # The SDK examples use names like "gemini-2.0-flash", so full names are expected.
        model_name = model if model else "gemini-1.5-flash-latest" 
        
        logger.info(f"Calling Gemini SDK with model: {model_name}, stream: {stream}")

        try:
            gemini_model_instance = genai.GenerativeModel(model_name)
            sdk_formatted_messages = self._convert_messages_to_sdk_format(messages)

            # Prepare GenerationConfig
            config_params = {}
            if max_tokens:
                config_params["max_output_tokens"] = max_tokens
            # Add other parameters like temperature, top_p, top_k as needed
            # config_params["temperature"] = 0.7 

            # System instruction is part of GenerationConfig in newer SDK versions
            # It should be a genai_types.Content object or a simple string.
            # The API reference indicates `system_instruction: content_types.Content | str | None = None`
            if system:
                # Using a simple string as per some examples, but Content object is more robust.
                # config_params["system_instruction"] = system 
                config_params["system_instruction"] = genai_types.Content(parts=[genai_types.Part(text=system)], role="system")


            # Safety settings (example, adjust as needed)
            # safety_settings = {
            #     HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            #     HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            # }
            safety_settings = None # Disable for now unless explicitly configured

            final_generation_config = genai_types.GenerationConfig(**config_params) if config_params else None
            
            if stream:
                def generate_stream():
                    try:
                        response_stream = gemini_model_instance.generate_content(
                            contents=sdk_formatted_messages,
                            generation_config=final_generation_config,
                            safety_settings=safety_settings,
                            stream=True
                        )
                        for chunk in response_stream:
                            # Check for blocking at chunk level (prompt_feedback)
                            if chunk.prompt_feedback and chunk.prompt_feedback.block_reason:
                                reason = chunk.prompt_feedback.block_reason.name
                                reason_msg = getattr(chunk.prompt_feedback, 'block_reason_message', reason) # Safely get message
                                error_message = f"Request blocked by Gemini (SDK). Reason: {reason_msg}"
                                logger.error(error_message)
                                yield error_message
                                return

                            # Check for blocking/finish reason at candidate level
                            if chunk.candidates:
                                candidate = chunk.candidates[0]
                                if candidate.finish_reason.name != "UNSPECIFIED" and candidate.finish_reason.name != "STOP":
                                    if candidate.finish_reason.name == "SAFETY":
                                        safety_ratings_str = ", ".join([f"{r.category.name}({r.probability.name})" for r in candidate.safety_ratings if r.probability.name != "NEGLIGIBLE"])
                                        error_message = f"Content blocked by Gemini (SDK) due to safety: {safety_ratings_str if safety_ratings_str else 'General safety block'}."
                                        logger.error(error_message)
                                        yield error_message
                                        return
                                    elif candidate.finish_reason.name == "MAX_TOKENS":
                                        logger.warning("Gemini stream stopped due to MAX_TOKENS.")
                                        # Continue yielding existing text, then stop.
                                    elif candidate.finish_reason.name != "STOP": # Other reasons like RECITATION, OTHER
                                        error_message = f"Gemini stream stopped. Reason: {candidate.finish_reason.name}."
                                        logger.error(error_message)
                                        yield error_message
                                        return
                                
                                # Yield text from parts
                                if candidate.content and candidate.content.parts:
                                    for part in candidate.content.parts:
                                        if hasattr(part, 'text') and part.text:
                                            yield part.text
                            # If no text and no clear error, it might be an empty chunk, just continue
                    except Exception as e_stream:
                        yield self._handle_sdk_error(e_stream, "Error during Gemini stream")
                        return
                return generate_stream()
            else: # Non-streaming
                response = gemini_model_instance.generate_content(
                    contents=sdk_formatted_messages,
                    generation_config=final_generation_config,
                    safety_settings=safety_settings
                )

                if response.prompt_feedback and response.prompt_feedback.block_reason:
                    reason = response.prompt_feedback.block_reason.name
                    reason_msg = getattr(response.prompt_feedback, 'block_reason_message', reason)
                    logger.error(f"Request blocked by Gemini (SDK). Reason: {reason_msg}")
                    return f"I apologize, but your request was blocked by Gemini (SDK). Reason: {reason_msg}"

                if not response.candidates:
                    logger.error("No candidates found in Gemini SDK response.")
                    return "I apologize, but I received an empty response from Gemini (SDK)."

                candidate = response.candidates[0]
                
                if candidate.finish_reason.name != "STOP" and candidate.finish_reason.name != "UNSPECIFIED":
                    if candidate.finish_reason.name == "SAFETY":
                        safety_ratings_str = ", ".join([f"{r.category.name}({r.probability.name})" for r in candidate.safety_ratings if r.probability.name != "NEGLIGIBLE"])
                        logger.error(f"Content blocked by Gemini (SDK) due to safety: {safety_ratings_str}")
                        return f"I apologize, but content was blocked by Gemini (SDK) due to safety concerns: {safety_ratings_str if safety_ratings_str else 'General safety block'}."
                    elif candidate.finish_reason.name == "MAX_TOKENS":
                        logger.warning("Gemini response stopped due to MAX_TOKENS.")
                        # Fall through to return any partial text
                    else: # RECITATION, OTHER, etc.
                        logger.error(f"Gemini response finished due to: {candidate.finish_reason.name}")
                        return f"I apologize, but the Gemini (SDK) response finished due to: {candidate.finish_reason.name}."

                if candidate.content and candidate.content.parts:
                    result = "".join(part.text for part in candidate.content.parts if hasattr(part, 'text') and part.text)
                    if not result and candidate.finish_reason.name == "MAX_TOKENS":
                        return "I apologize, but the response from Gemini (SDK) was cut off due to length limits, and no content was provided."
                    logger.info(f"Gemini SDK extracted text (first 100 chars): {result[:100]}")
                    return result
                
                logger.warning(f"No text content found in Gemini SDK response. Finish reason: {candidate.finish_reason.name}")
                return "I apologize, but I received an empty or non-text response from Gemini (SDK)."

        except Exception as e:
            # This will catch errors from SDK client instantiation or other unexpected issues.
            if "FinishReason" in str(e) and "google.generativeai.types" in str(e):
                 logger.error("The 'FinishReason' AttributeError occurred with the SDK. This indicates a potential SDK version mismatch or incorrect usage of enums. Check SDK documentation for 'FinishReason'.")
            return self._handle_sdk_error(e)
