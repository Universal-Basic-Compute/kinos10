import os
import google.generativeai as genai
from services.llm_service import LLMProvider
from config import logger
import json

class GeminiProvider(LLMProvider):
    """Google Gemini LLM provider implementation"""

    def __init__(self, api_key=None):
        super().__init__(api_key)
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            logger.warning("GOOGLE_API_KEY environment variable not set")
        
        try:
            genai.configure(api_key=self.api_key)
            logger.info("Google Gemini client configured successfully")
        except Exception as e:
            logger.error(f"Error configuring Gemini client: {str(e)}")
            raise RuntimeError(f"Could not configure Gemini client: {str(e)}")

    def _convert_messages_to_gemini_format(self, messages):
        gemini_messages = []
        for message in messages:
            role = message.get("role")
            content = message.get("content")

            if role == "assistant":
                role = "model"
            
            if isinstance(content, list): # Handle multimodal content
                parts = []
                for item in content:
                    if item.get("type") == "text":
                        parts.append({"text": item.get("text", "")})
                    elif item.get("type") == "image" and item.get("source", {}).get("type") == "base64":
                        # Gemini expects image data directly, not a complex structure
                        # This part might need adjustment based on how image data is actually passed
                        # For now, assuming we handle base64 images if passed in a specific way
                        # This is a placeholder and might need actual image bytes.
                        # For simplicity, we'll assume text parts for now.
                        # Actual image handling would require converting base64 to image bytes
                        # and using appropriate Part types.
                        # parts.append({"inline_data": {"mime_type": item["source"]["media_type"], "data": item["source"]["data"]}})
                        logger.warning("Image part in Gemini message detected, but full handling is complex. Treating as text for now.")
                        parts.append({"text": "[Image content not directly translatable to simple text]"})
                    else:
                        parts.append({"text": str(item)}) # Fallback for unknown content parts
                gemini_messages.append({"role": role, "parts": parts})
            elif isinstance(content, str):
                 gemini_messages.append({"role": role, "parts": [{"text": content}]})
            else:
                logger.warning(f"Unsupported content type in message for Gemini: {type(content)}")
        return gemini_messages

    def generate_response(self, messages, system=None, max_tokens=None, model=None, stream=False):
        """Generate a response using Gemini API"""
        try:
            # Remove "gemini/" prefix if present for the API call
            model_name = model.replace("gemini/", "") if model else "gemini-1.5-pro-latest"
            
            logger.info(f"Calling Gemini API with model: {model_name}")
            logger.info(f"Stream mode: {stream}")
            logger.info(f"Number of messages: {len(messages)}")

            gemini_model_args = {'model_name': model_name}
            if system:
                gemini_model_args['system_instruction'] = system
            
            gemini_model = genai.GenerativeModel(**gemini_model_args)

            generation_config = genai.types.GenerationConfig()
            if max_tokens:
                generation_config.max_output_tokens = max_tokens
            # Add other generation_config settings as needed, e.g., temperature, top_p

            gemini_formatted_messages = self._convert_messages_to_gemini_format(messages)
            
            # Log the formatted messages for debugging
            # logger.debug(f"Gemini formatted messages: {json.dumps(gemini_formatted_messages, indent=2)}")


            if stream:
                def generate_stream():
                    response_stream = gemini_model.generate_content(
                        gemini_formatted_messages,
                        stream=True,
                        generation_config=generation_config
                    )
                    for chunk in response_stream:
                        if chunk.parts:
                            yield chunk.parts[0].text
                        elif chunk.text: # Some simpler chunks might just have text
                            yield chunk.text
                return generate_stream()
            else:
                response = gemini_model.generate_content(
                    gemini_formatted_messages,
                    generation_config=generation_config
                )
                # Log the raw response for debugging
                # logger.debug(f"Gemini API raw response: {response}")
                if response.parts:
                    result = response.parts[0].text
                elif response.text: # Fallback for simpler response structures
                    result = response.text
                else:
                    logger.error("Empty or unexpected response from Gemini")
                    # Check for prompt feedback or finish reason
                    if response.prompt_feedback:
                        logger.error(f"Gemini prompt feedback: {response.prompt_feedback}")
                        if response.prompt_feedback.block_reason:
                             return f"I apologize, but your request was blocked by Gemini. Reason: {response.prompt_feedback.block_reason_message or response.prompt_feedback.block_reason}"
                    return "I apologize, but I couldn't generate a response from Gemini."

                import re
                result = re.sub(r'[\x00-\x1F\x7F]', '', result) # Sanitize
                logger.info(f"Gemini API extracted text (first 100 chars): {result[:100]}")
                return result

        except Exception as e:
            logger.error(f"Error calling Gemini API: {str(e)}")
            # Log traceback for more details
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return f"I apologize, but I encountered an error with Gemini: {str(e)}. Please try again."
