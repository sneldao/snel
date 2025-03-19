"""
Service for interacting with the Gemini API.
"""
import logging
import os
import json
from typing import Dict, Any, List, Optional, Tuple
import httpx
import asyncio

logger = logging.getLogger(__name__)

# Default model to use (1.5 Flash is more likely to be available on the free tier)
DEFAULT_MODEL = "gemini-1.5-flash"
FALLBACK_MODELS = ["gemini-1.5-flash", "gemini-1.0-pro"]

class GeminiService:
    """
    Service for generating AI-powered responses using Google's Gemini API.
    This service handles natural language processing for crypto and DeFi queries.
    """
    api_key: Optional[str] = None
    http_client: Optional[httpx.AsyncClient] = None
    model_name: str = DEFAULT_MODEL
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Gemini service.
        
        Args:
            api_key: Gemini API key (optional)
        """
        self.api_key = api_key
        self.http_client = self._create_http_client()
        
        if not self.api_key:
            logger.warning("No Gemini API key provided, service will have limited functionality")
    
    def _create_http_client(self) -> httpx.AsyncClient:
        """Create a new HTTP client with proper timeout settings."""
        return httpx.AsyncClient(timeout=30.0)
    
    async def check_model_availability(self) -> Tuple[bool, str]:
        """
        Check if the current model is available.
        
        Returns:
            Tuple of (is_available, model_name)
        """
        if not self.api_key or not self.http_client:
            return False, ""
            
        try:
            # Ensure HTTP client is available
            if self.http_client is None or self.http_client.is_closed:
                self.http_client = self._create_http_client()
                
            # List available models
            models_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={self.api_key}"
            response = await self.http_client.get(models_url)
            
            if response.status_code != 200:
                logger.error(f"Error listing Gemini models: {response.status_code} - {response.text}")
                return False, ""
                
            # Parse response
            data = response.json()
            available_models = [model["name"].split("/")[-1] for model in data.get("models", [])]
            
            # Check if our model is available
            if self.model_name in available_models:
                return True, self.model_name
                
            # Try fallback models
            for model in FALLBACK_MODELS:
                if model in available_models:
                    self.model_name = model
                    logger.info(f"Using fallback Gemini model: {model}")
                    return True, model
                    
            # No suitable model found
            return False, ""
            
        except Exception as e:
            logger.exception(f"Error checking model availability: {e}")
            return False, ""
    
    async def answer_crypto_question(
        self,
        user_query: str,
        wallet_info: Optional[Dict[str, Any]] = None,
        context: Optional[List[Dict[str, str]]] = None,
        max_tokens: int = 500
    ) -> str:
        """
        Generate a response to a user query about crypto or DeFi.
        
        Args:
            user_query: The user's question
            wallet_info: Optional wallet information for context
            context: Optional conversation context (list of role/content pairs)
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated response string
        """
        # Check if we have a valid API key
        if not self.api_key:
            return "I'm sorry, I can't answer general questions right now. Please try using specific commands like */price* or */swap*."

        # If the query is simple enough, just respond directly without API call
        if user_query.lower() in {
            "hi",
            "hello",
            "hey",
            "gm",
            "good morning",
            "good day",
            "good evening",
        }:
            return "🐌 Hello there! I'm Snel, your DeFi assistant. To get started, try commands like */price ETH* or */connect* to set up your wallet."

        try:
            # Ensure HTTP client is available
            if self.http_client is None or self.http_client.is_closed:
                logger.info("HTTP client closed or not initialized, creating new client")
                self.http_client = self._create_http_client()

            # Build system instruction
            system_instruction = """
            You are Snel, a friendly DeFi assistant bot on Telegram that helps users with crypto and blockchain transactions.
            
            IMPORTANT RULES TO FOLLOW:
            1. You are providing information ONLY - you cannot execute any transactions yourself
            2. For actual transactions (swaps, transfers, etc.), always direct users to use specific commands
            3. Be accurate but concise in your answers (50-150 words maximum)
            4. Add a touch of personality with occasional snail emojis 🐌 or slow-themed jokes
            5. Never make up transaction data or wallet balances
            6. If you don't know something, admit it and suggest appropriate commands
            7. When discussing prices or market data, indicate these are estimates
            8. Maintain conversation context and refer back to previous messages naturally
            
            COMMANDS USERS SHOULD USE (not you):
            - /connect - Create or connect wallet
            - /price [token] - Check token prices
            - /swap [amount] [token] for [token] - Swap tokens
            - /balance - Check wallet balance
            - /network [network] - Switch networks
            - /networks - View available networks
            - /help - View all commands
            
            IMPORTANT: When suggesting commands, format them like */command* so they are clickable in Telegram.
            """

            # Build conversation context
            base_context = "The user is interacting with a Telegram bot that provides DeFi services."
            if wallet_info and wallet_info.get("wallet_address"):
                base_context += f" The user has a connected wallet with address {wallet_info['wallet_address']}."

            # Build API request with current model name
            api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent"
            headers = {"Content-Type": "application/json"}

            # Build conversation history
            contents = [
                {
                    "role": "user",
                    "parts": [{"text": system_instruction}]
                },
                {
                    "role": "model",
                    "parts": [{"text": "I understand. I'll follow these guidelines to provide helpful information about DeFi and crypto while directing users to the appropriate commands."}]
                }
            ]

            # Add conversation context if provided
            if context:
                for msg in context:
                    contents.append({
                        "role": msg["role"],
                        "parts": [{"text": msg["content"]}]
                    })

            # Add current query with base context
            contents.append({
                "role": "user",
                "parts": [{"text": f"Context: {base_context}\n\nUser query: {user_query}"}]
            })

            payload = {
                "contents": contents,
                "generationConfig": {
                    "temperature": 0.2,
                    "topK": 40,
                    "topP": 0.95,
                    "maxOutputTokens": max_tokens,
                    "stopSequences": []
                },
                "safetySettings": [
                    {
                        "category": "HARM_CATEGORY_HARASSMENT",
                        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                    },
                    {
                        "category": "HARM_CATEGORY_HATE_SPEECH",
                        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                    },
                    {
                        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                    },
                    {
                        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                    }
                ]
            }

            try:
                # Make API request
                response = await self.http_client.post(
                    f"{api_url}?key={self.api_key}",
                    headers=headers,
                    json=payload
                )

                # Check for successful response
                if response.status_code == 200:
                    data = response.json()

                    # Extract the generated text
                    if "candidates" in data and data["candidates"]:
                        candidate = data["candidates"][0]
                        if "content" in candidate and "parts" in candidate["content"]:
                            parts = candidate["content"]["parts"]
                            if parts and "text" in parts[0]:
                                return parts[0]["text"].strip()

                # If we get a 404, it might be a model issue
                if response.status_code == 404 and "models" in response.text:
                    # Try to check for available models
                    available, model = await self.check_model_availability()
                    if available:
                        # Retry with the new model
                        logger.info(f"Retrying with verified model: {model}")
                        self.model_name = model
                        # Call self recursively to retry
                        return await self.answer_crypto_question(user_query, wallet_info, context, max_tokens)

                # Log error
                logger.error(f"Error from Gemini API: {response.status_code} - {response.text}")
            except (httpx.HTTPError, asyncio.CancelledError, RuntimeError) as http_error:
                # Handle HTTP errors and event loop issues
                if "Event loop is closed" in str(http_error):
                    logger.warning("Event loop closed during Gemini API call, recreating client")
                    # The client needs to be recreated next time
                    try:
                        await self.http_client.aclose()
                    except:
                        pass
                    self.http_client = None
                else:
                    logger.error(f"HTTP error calling Gemini API: {http_error}")

                # Return fallback message
                return "I'm having connection issues right now. Try using specific commands like */help* or */price ETH* instead."

            return "I'm having trouble answering right now. Try using a specific command like */help* to see what I can do."

        except Exception as e:
            logger.exception(f"Error calling Gemini API: {e}")

            # Ensure client is closed if there was an error
            if self.http_client:
                try:
                    await self.http_client.aclose()
                except:
                    pass
                self.http_client = None

            return "Sorry, I'm experiencing some technical difficulties. Please try a specific command like */price ETH* or */help*." 