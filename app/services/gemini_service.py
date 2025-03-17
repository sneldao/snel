"""
Service for interacting with the Gemini API.
"""
import logging
import os
import json
from typing import Dict, Any, List, Optional
import httpx

logger = logging.getLogger(__name__)

class GeminiService:
    """
    Service for generating AI-powered responses using Google's Gemini API.
    This service handles natural language processing for crypto and DeFi queries.
    """
    api_key: Optional[str] = None
    http_client: httpx.AsyncClient
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Gemini service.
        
        Args:
            api_key: Gemini API key (optional)
        """
        self.api_key = api_key
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
        if not self.api_key:
            logger.warning("No Gemini API key provided, service will have limited functionality")
    
    async def answer_crypto_question(
        self,
        user_query: str,
        wallet_info: Optional[Dict[str, Any]] = None,
        max_tokens: int = 500
    ) -> str:
        """
        Generate a response to a user query about crypto or DeFi.
        
        Args:
            user_query: The user's question
            wallet_info: Optional wallet information for context
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated response string
        """
        if not self.api_key:
            return "I'm sorry, I can't answer general questions right now. Please try using specific commands like /price or /swap."
            
        try:
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
            
            COMMANDS USERS SHOULD USE (not you):
            - /connect - Create or connect wallet
            - /price [token] - Check token prices
            - /swap [amount] [token] for [token] - Swap tokens
            - /balance - Check wallet balance
            - /network [network] - Switch networks
            - /networks - View available networks
            - /keys - Explain key management
            - /help - View all commands
            
            IMPORTANT: When suggesting commands, format them like */command* so they are clickable in Telegram.
            """
            
            # Build conversation context
            context = "The user is interacting with a Telegram bot that provides DeFi services."
            if wallet_info and wallet_info.get("connected"):
                context += f" The user has a connected wallet with address {wallet_info['address']}."
            
            # Build API request with specific model version
            api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-001:generateContent"
            headers = {"Content-Type": "application/json"}
            
            payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": system_instruction}]
                    },
                    {
                        "role": "model",
                        "parts": [{"text": "I understand. I'll follow these guidelines to provide helpful information about DeFi and crypto while directing users to the appropriate commands for transactions."}]
                    },
                    {
                        "role": "user",
                        "parts": [{"text": f"Context: {context}\n\nUser query: {user_query}"}]
                    }
                ],
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
            
            # Log error
            logger.error(f"Error from Gemini API: {response.status_code} - {response.text}")
            return "I'm having trouble answering right now. Try using a specific command like */help* to see what I can do."
            
        except Exception as e:
            logger.exception(f"Error calling Gemini API: {e}")
            return "Sorry, I'm experiencing some technical difficulties. Please try a specific command like */price ETH* or */help*." 