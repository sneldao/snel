import os
import logging
import httpx
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger(__name__)

class OpenAIProvider:
    """Provider for OpenAI API interactions."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the OpenAI provider with an API key.
        
        Args:
            api_key: OpenAI API key. If None, will try to get from environment.
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning("No OpenAI API key provided")
        
        self.base_url = "https://api.openai.com/v1"
    
    async def process(
        self, 
        prompt: str, 
        model: str = "gpt-4-turbo-preview",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        response_format: Any = None
    ) -> Dict[str, Any]:
        """
        Process a prompt using OpenAI API.
        
        Args:
            prompt: The text prompt to process
            model: OpenAI model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            response_format: Format for structured responses
            
        Returns:
            Dictionary with response content
        """
        headers, data = self._prepare_request(prompt, model, temperature, max_tokens, response_format)

        try:
            response = await self._call_openai_api(headers, data)
            return self._parse_response(response, response_format)
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {str(e)}")
            return {"content": None, "error": f"Failed to call API: {str(e)}"}

    def _prepare_request(self, prompt: str, model: str, temperature: float, max_tokens: int, response_format: Any) -> Tuple[Dict[str, str], Dict[str, Any]]:
        """Prepare the request headers and payload for the OpenAI API call."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        if response_format:
            data["response_format"] = {"type": "json_object"}
            if hasattr(response_format, "model_json_schema"):
                schema = response_format.model_json_schema()
                data["functions"] = [{
                    "name": "parse_response",
                    "description": "Parse the response into a structured format",
                    "parameters": schema
                }]
                data["function_call"] = {"name": "parse_response"}

        return headers, data

    async def _call_openai_api(self, headers: Dict[str, str], data: Dict[str, Any]) -> httpx.Response:
        """Make the API call to OpenAI and return the response."""
        logger.info(f"Calling OpenAI API with model {data['model']}")

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions", 
                headers=headers, 
                json=data
            )

        return response

    def _parse_response(self, response: httpx.Response, response_format: Any) -> Dict[str, Any]:
        """Parse the response from the OpenAI API."""
        if response.status_code != 200:
            error_data = response.json()
            error_message = error_data.get("error", {}).get("message", str(error_data))
            logger.error(f"OpenAI API error ({response.status_code}): {error_message}")
            return {"content": None, "error": f"API error: {error_message}"}

        result = response.json()

        if "choices" in result and result["choices"]:
            choice = result["choices"][0]

            if "function_call" in choice["message"]:
                return self._parse_function_call(choice["message"])
            else:
                return self._parse_regular_response(choice["message"], response_format)

        return {"content": None, "error": "No response from model"}

    def _parse_function_call(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Parse a function call response."""
        try:
            import json
            args_str = message["function_call"]["arguments"]
            args = json.loads(args_str)
            return {"content": args, "error": None}
        except Exception as e:
            logger.error(f"Error parsing function call arguments: {e}")
            return {"content": None, "error": f"Failed to parse structured response: {str(e)}"}

    def _parse_regular_response(self, message: Dict[str, Any], response_format: Any) -> Dict[str, Any]:
        """Parse a regular text response."""
        content = message["content"]

        if response_format and response_format.get("type") == "json_object":
            try:
                import json
                parsed = json.loads(content)
                return {"content": parsed, "error": None}
            except Exception as e:
                logger.error(f"Error parsing JSON response: {e}")
                return {"content": None, "error": f"Failed to parse JSON response: {str(e)}"}

        return {"content": content, "error": None}
    
    async def generate_text(
        self, 
        prompt: str, 
        model: str = "gpt-4-turbo-preview",
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> str:
        """
        Generate text from a prompt.
        
        Args:
            prompt: The text prompt
            model: OpenAI model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text or error message
        """
        response = await self.process(
            prompt=prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        if response.get("error"):
            return f"Error: {response['error']}"
        
        return response.get("content", "No response generated") 