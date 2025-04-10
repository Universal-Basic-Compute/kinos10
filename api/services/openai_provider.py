import os
import openai
from services.llm_service import LLMProvider
from config import logger

class OpenAIProvider(LLMProvider):
    """OpenAI (ChatGPT) LLM provider implementation"""
    
    def __init__(self, api_key=None):
        super().__init__(api_key)
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning("OPENAI_API_KEY environment variable not set")
        
        # Initialize client
        try:
            self.client = openai.OpenAI(api_key=self.api_key)
            logger.info("OpenAI client initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing OpenAI client: {str(e)}")
            raise RuntimeError(f"Could not initialize OpenAI client: {str(e)}")
    
    def generate_response(self, messages, system=None, max_tokens=4000, model=None):
        """Generate a response using OpenAI"""
        try:
            # Use provided model or default
            model_to_use = model or os.getenv("OPENAI_MODEL", "gpt-4o")
            
            # If system message is provided, add it to the messages array
            if system:
                # OpenAI uses a different format for system messages
                formatted_messages = [{"role": "system", "content": system}]
                formatted_messages.extend(messages)
            else:
                formatted_messages = messages
            
            response = self.client.chat.completions.create(
                model=model_to_use,
                messages=formatted_messages,
                max_tokens=max_tokens
            )
            
            # Extract the response text
            if response.choices and len(response.choices) > 0:
                return response.choices[0].message.content
            else:
                logger.error("Empty response from OpenAI")
                return "I apologize, but I couldn't generate a response."
                
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {str(e)}")
            return f"I apologize, but I encountered an error: {str(e)}. Please try again."
