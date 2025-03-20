from typing import Optional, Dict, Any, Type, TypeVar, Union, List
import logging
from pydantic import BaseModel, Field
from openai import AsyncOpenAI
import traceback
import os

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)

class AgentMessage(BaseModel):
    """Base message type for agent responses."""
    content: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = {
        "arbitrary_types_allowed": True
    }

class PointlessAgent(BaseModel):
    """Base class for Pointless agents."""
    prompt: str
    model: str = "gpt-4-turbo-preview"
    temperature: float = 0.7
    client: Optional[AsyncOpenAI] = None
    
    model_config = {
        "arbitrary_types_allowed": True
    }

    def __init__(self, prompt: str, model: str = "gpt-4-turbo-preview", temperature: float = 0.7, provider = None, api_key: Optional[str] = None):
        """
        Initialize the agent with system prompt.
        
        Args:
            prompt: System prompt to use
            model: Model to use (defaults to gpt-4-turbo-preview)
            temperature: Temperature for generation (0.0 to 1.0)
            provider: Provider to use (legacy parameter, not used)
            api_key: OpenAI API key to use (overrides environment variable)
        """
        # Initialize Pydantic model with defaults if needed
        super().__init__(
            prompt=prompt,
            model=model,
            temperature=temperature
        )
        
        # Get OpenAI API key with fallbacks
        openai_api_key = None
        
        # Try to get from provided api_key first
        if api_key:
            openai_api_key = api_key
            
        # Then try provider
        if not openai_api_key and provider and hasattr(provider, 'api_key'):
            openai_api_key = provider.api_key
        
        # Finally try environment variables
        if not openai_api_key:
            openai_api_key = os.environ.get("OPENAI_API_KEY")
            
        if not openai_api_key:
            logger.error("No OpenAI API key found in request headers, provider, or environment")
            raise ValueError("OpenAI API key is required. Please provide it in the request headers or environment variables.")
        
        # Create client options without proxies to avoid HTTPX compatibility issues
        client_options = {
            "api_key": openai_api_key,
        }
        
        # Check if we're in a production environment (Vercel)
        is_production = os.environ.get("VERCEL", "").lower() == "1"
        
        # Only add timeout in production to avoid issues
        if is_production:
            client_options["timeout"] = 60.0
        
        if provider and hasattr(provider, 'client'):
            # Use the provider's client directly
            self.client = provider.client
        else:
            # Create our own client
            self.client = AsyncOpenAI(**client_options)
            
        logger.info("PointlessAgent initialized successfully")

    def _format_messages(self, user_input: str) -> List[Dict[str, str]]:
        """Format the system prompt and user input as chat messages."""
        # Ensure the prompt contains the word 'json' if it doesn't already
        prompt = self.prompt
        if "json" not in prompt.lower():
            prompt += "\nPlease provide your response in JSON format."

        return [
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_input}
        ]

    def _process_response(self, response: Any) -> Dict[str, Any]:
        """Process and validate the response from the model."""
        try:
            if isinstance(response, BaseModel):
                return response.model_dump()
            elif isinstance(response, dict):
                return response
            elif isinstance(response, str):
                return {"content": response}
            else:
                return {"content": str(response)}
        except Exception as e:
            logger.warning(f"Error processing response: {e}")
            return {"content": str(response)}
    
    async def process(self, input_text: str, metadata: Optional[Dict[str, Any]] = None, response_format: Optional[Type[T]] = None) -> Dict[str, Any]:
        """Process input text and return a response."""
        try:
            # Check if we have a client
            if not self.client:
                raise ValueError("OpenAI client not initialized. Please check your API key configuration.")
                
            # Prepare messages
            messages = self._format_messages(input_text)
            
            # Prepare completion kwargs
            completion_kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": self.temperature,
            }
            
            # Add response format if provided
            if response_format:
                # Make sure the word 'json' is in the system message
                if "json" not in messages[0]["content"].lower():
                    messages[0]["content"] += "\nPlease provide your response in JSON format."
                    completion_kwargs["messages"] = messages
                
                completion_kwargs["response_format"] = {"type": "json_object"}
            
            # Call OpenAI
            response = await self.client.chat.completions.create(**completion_kwargs)
            
            # Extract content from response
            content = response.choices[0].message.content
            
            # Parse response if needed
            if response_format and isinstance(content, str):
                import json
                try:
                    content = json.loads(content)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON response: {e}")
                    return AgentMessage(
                        content=None,
                        error=f"Invalid JSON response: {str(e)}",
                        metadata=metadata or {}
                    ).model_dump()
            
            return AgentMessage(
                content=content,
                error=None,
                metadata=metadata or {}
            ).model_dump()
            
        except Exception as e:
            error_msg = f"Error in agent processing: {str(e)}"
            logger.error(error_msg)
            
            # Get full traceback for debugging
            tb = traceback.format_exc()
            logger.debug(f"Traceback: {tb}")
            
            return AgentMessage(
                content=None,
                error=error_msg,
                metadata=metadata or {}
            ).model_dump()