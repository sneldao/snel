import os
from typing import Optional

import httpx


async def get_user_id(username: str) -> Optional[int]:
    """Convert a Twitter/X username to a user ID.

    Args:
        username: Twitter/X username (without @ symbol)

    Returns:
        User ID as integer if found, None if not found
    """
    # Remove @ if present
    username = username.lstrip("@")

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
            return int(data["data"]["id"])
        except (httpx.HTTPError, KeyError, ValueError):
            return None
