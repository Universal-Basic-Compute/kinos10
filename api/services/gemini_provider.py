import os
import google.generativeai as genai # Use the official package name
# Import types directly from google.ai.generativelanguage
from google.ai.generativelanguage import GenerationConfig
from google.ai.generativelanguage.types import Candidate
from google.ai.generativelanguage.types import SafetyRating
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
            model_name = model.replace("gemini/", "") if model else "gemini-2.5-pro-preview-03-25"
            
            logger.info(f"Calling Gemini API with model: {model_name}")
            logger.info(f"Stream mode: {stream}")
            logger.info(f"Number of messages: {len(messages)}")

            gemini_model_args = {'model_name': model_name}
            if system:
                gemini_model_args['system_instruction'] = system
            
            gemini_model = genai.GenerativeModel(**gemini_model_args)

            generation_config = GenerationConfig() # Use direct import
            if max_tokens:
                generation_config.max_output_tokens = max_tokens
            # Add other generation_config settings as needed, e.g., temperature, top_p

            gemini_formatted_messages = self._convert_messages_to_gemini_format(messages)
            
            # Log the formatted messages for debugging
            # logger.debug(f"Gemini formatted messages: {json.dumps(gemini_formatted_messages, indent=2)}")


            if stream:
                def generate_stream():
                    try:
                        response_stream = gemini_model.generate_content(
                            gemini_formatted_messages,
                            stream=True,
                            generation_config=generation_config
                        )
                        for chunk in response_stream:
                            if chunk.prompt_feedback and chunk.prompt_feedback.block_reason:
                                error_message = f"I apologize, but your request was blocked by Gemini. Reason: {chunk.prompt_feedback.block_reason_message or chunk.prompt_feedback.block_reason}"
                                logger.error(f"Gemini stream error: {error_message}")
                                yield error_message
                                return

                            if not chunk.candidates:
                                if hasattr(chunk, 'text') and chunk.text:
                                     yield chunk.text
                                continue

                            candidate = chunk.candidates[0]
                            if candidate.finish_reason == Candidate.FinishReason.SAFETY: # Use direct import
                                safety_messages = []
                                if candidate.safety_ratings:
                                    for rating in candidate.safety_ratings:
                                        if rating.probability != SafetyRating.HarmProbability.NEGLIGIBLE: # Use direct import
                                            safety_messages.append(f"{rating.category.name.split('_')[-1]} (Prob: {rating.probability.name})")
                                error_message = f"I apologize, but content was blocked by Gemini due to safety concerns: {', '.join(safety_messages)}." if safety_messages else "I apologize, but content was blocked by Gemini due to safety concerns."
                                logger.error(f"Gemini stream error: {error_message}")
                                yield error_message
                                return
                            elif candidate.finish_reason == Candidate.FinishReason.RECITATION: # Use direct import
                                error_message = "I apologize, but content was blocked by Gemini due to recitation policy."
                                logger.error(f"Gemini stream error: {error_message}")
                                yield error_message
                                return
                            
                            text_yielded_from_chunk = False
                            if candidate.content and candidate.content.parts:
                                for part in candidate.content.parts:
                                    if hasattr(part, 'text') and part.text:
                                        yield part.text
                                        text_yielded_from_chunk = True
                            
                            # Fallback for simpler chunk structures if no text from parts
                            if not text_yielded_from_chunk and hasattr(chunk, 'text') and chunk.text:
                                yield chunk.text
                                
                    except Exception as e:
                        logger.error(f"Error during Gemini stream generation: {str(e)}")
                        import traceback
                        logger.error(f"Full traceback: {traceback.format_exc()}")
                        yield f"I apologize, but I encountered an error with Gemini streaming: {str(e)}. Please try again."
                return generate_stream()
            else:
                response = gemini_model.generate_content(
                    gemini_formatted_messages,
                    generation_config=generation_config
                )
                # Log the raw response for debugging
                # logger.debug(f"Gemini API raw response: {response}")

                # Check for prompt-level blocking first
                if response.prompt_feedback and response.prompt_feedback.block_reason:
                    logger.error(f"Gemini prompt feedback: {response.prompt_feedback}")
                    return f"I apologize, but your request was blocked by Gemini. Reason: {response.prompt_feedback.block_reason_message or response.prompt_feedback.block_reason}"

                # Check candidates
                if not response.candidates:
                    logger.error("No candidates found in Gemini response.")
                    return "I apologize, but I received an empty response from Gemini."

                candidate = response.candidates[0]

                # Handle terminal finish reasons
                if candidate.finish_reason == Candidate.FinishReason.SAFETY: # Use direct import
                    safety_messages = []
                    if candidate.safety_ratings:
                        for rating in candidate.safety_ratings:
                            # NEGLIGIBLE = 0, LOW = 1, MEDIUM = 2, HIGH = 3
                            if rating.probability != SafetyRating.HarmProbability.NEGLIGIBLE: # Use direct import
                                safety_messages.append(f"{rating.category.name.split('_')[-1]} (Prob: {rating.probability.name})")
                    if safety_messages:
                        logger.error(f"Content blocked by Gemini due to safety reasons: {', '.join(safety_messages)}")
                        return f"I apologize, but your request was blocked by Gemini due to safety concerns: {', '.join(safety_messages)}."
                    else:
                        logger.error("Content blocked by Gemini due to unspecified safety reasons (FinishReason.SAFETY).")
                        return "I apologize, but your request was blocked by Gemini due to safety concerns."
                elif candidate.finish_reason == Candidate.FinishReason.RECITATION: # Use direct import
                    logger.error("Content blocked by Gemini due to recitation.")
                    return "I apologize, but your request was blocked by Gemini due to recitation policy."
                elif candidate.finish_reason == Candidate.FinishReason.OTHER: # Use direct import
                    logger.error("Gemini response finished due to an 'OTHER' reason.")
                    return "I apologize, but the Gemini response finished due to an unspecified error."

                # If finish_reason is STOP, MAX_TOKENS, or UNSPECIFIED, attempt to get content.
                if candidate.content and candidate.content.parts:
                    # Concatenate text from all parts that have text
                    result_parts = [part.text for part in candidate.content.parts if hasattr(part, 'text') and part.text is not None]
                    result = "".join(result_parts)
                    
                    if not result:
                        logger.warning(f"No text found in Gemini response parts, though parts exist. Finish reason: {candidate.finish_reason.name}")
                        if any(part for part in candidate.content.parts): # Check if there were any parts at all (e.g. image)
                             return "I apologize, but the response from Gemini did not contain any text content."
                        else: # No parts at all
                             return "I apologize, but I received an empty response from Gemini."
                else: 
                    logger.error(f"No content or parts found in Gemini response candidate. Finish reason: {candidate.finish_reason.name}")
                    if candidate.finish_reason == Candidate.FinishReason.MAX_TOKENS: # Use direct import
                        return "I apologize, but the response from Gemini was cut off due to length limits, and no content was provided."
                    # For other finish reasons like STOP or UNSPECIFIED with no content/parts
                    return "I apologize, but I received an empty or malformed response from Gemini."

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
