"""
Dependencies forwarding module for backward compatibility.

This module forwards all public imports from app.api.dependencies to maintain
backward compatibility with code that imports from app.dependencies.
"""

from app.api.dependencies import (
    get_redis_service,
    get_token_service,
    get_wallet_service,
    get_wallet_bridge_service,
    get_gemini_service,
    get_openai_key,
    get_swap_agent,
    get_price_agent,
    get_base_agent,
    get_swap_service,
    get_telegram_agent
) 