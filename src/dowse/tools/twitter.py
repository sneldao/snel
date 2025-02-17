import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger("dowse")

USER_ID_CACHE: dict[str, int] = {}


async def get_user_id(username: str) -> Optional[int]:
    """Convert a Twitter/X username to a user ID.

    Args:
        username: Twitter/X username (without @ symbol)

    Returns:
        User ID as integer if found, None if not found
    """
    # Remove @ if present
    username = username.lstrip("@")

    if username in USER_ID_CACHE:
        return USER_ID_CACHE[username]

    # Twitter API v2 endpoint
    url = f"https://api.twitter.com/2/users/by/username/{username}"

    # Get bearer token from environment
    bearer_token = os.environ.get("TWITTER_BEARER_TOKEN")
    if not bearer_token:
        raise ValueError("TWITTER_BEARER_TOKEN environment variable not set")

    headers = {"Authorization": f"Bearer {bearer_token}"}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            user_id = int(data["data"]["id"])
            USER_ID_CACHE[username] = user_id
            return user_id
        except (httpx.HTTPError, KeyError, ValueError) as e:
            logger.error(str(e))
            return None
