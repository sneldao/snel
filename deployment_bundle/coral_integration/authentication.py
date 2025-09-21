"""
SNEL Coral Authentication Service
ENHANCEMENT FIRST: Proper agent registration and authentication with Coral Server
RELIABLE: Robust error handling and session management
PERFORMANT: Efficient token handling and caching
"""

import asyncio
import logging
import requests
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class AgentRegistrationData:
    """Data required for agent registration"""
    agent_id: str
    agent_type: str
    name: str
    description: str
    capabilities: list

@dataclass
class AuthenticationResponse:
    """Response from Coral Server authentication"""
    session_token: str
    agent_id: str
    expires_at: int

class CoralAuthenticationService:
    """
    Service for handling Coral Protocol authentication
    ENHANCEMENT: Proper agent registration and session management
    RELIABLE: Robust error handling and retry logic
    """
    
    def __init__(self):
        self.server_urls: Dict[str, str] = {}
        self.auth_tokens: Dict[str, str] = {}
        self.sessions: Dict[str, AuthenticationResponse] = {}
        self.registration_data: Dict[str, AgentRegistrationData] = {}
        
    def configure_server(self, agent_id: str, server_url: str) -> None:
        """
        Configure Coral Server URL for an agent
        """
        self.server_urls[agent_id] = server_url.rstrip('/')
        logger.info(f"[CORAL-AUTH] Configured server URL for agent {agent_id}: {server_url}")
    
    def register_agent_data(self, agent_id: str, registration_data: AgentRegistrationData) -> None:
        """
        Register agent data for future registration
        """
        self.registration_data[agent_id] = registration_data
        logger.info(f"[CORAL-AUTH] Registered agent data for {agent_id}")
    
    def set_auth_token(self, agent_id: str, token: str) -> None:
        """
        Set authentication token for an agent
        """
        self.auth_tokens[agent_id] = token
        logger.info(f"[CORAL-AUTH] Set auth token for agent {agent_id}")
    
    async def register_agent(self, agent_id: str) -> bool:
        """
        Register agent with Coral Server
        """
        try:
            server_url = self.server_urls.get(agent_id)
            if not server_url:
                logger.error(f"[CORAL-AUTH] No server URL configured for agent {agent_id}")
                return False
            
            registration_data = self.registration_data.get(agent_id)
            if not registration_data:
                logger.error(f"[CORAL-AUTH] No registration data for agent {agent_id}")
                return False
            
            logger.info(f"[CORAL-AUTH] Registering agent {agent_id} with Coral Server")
            
            # Prepare registration payload
            payload = {
                "agentId": registration_data.agent_id,
                "type": registration_data.agent_type,
                "name": registration_data.name,
                "description": registration_data.description,
                "capabilities": registration_data.capabilities
            }
            
            # Send registration request
            register_url = f"{server_url}/api/agents"
            response = requests.post(
                register_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                logger.info(f"[CORAL-AUTH] Agent {agent_id} registered successfully")
                return True
            else:
                logger.error(f"[CORAL-AUTH] Failed to register agent {agent_id}: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"[CORAL-AUTH] Exception during agent registration for {agent_id}: {str(e)}")
            return False
    
    async def authenticate_agent(self, agent_id: str) -> Optional[AuthenticationResponse]:
        """
        Authenticate agent with Coral Server and create session
        """
        try:
            server_url = self.server_urls.get(agent_id)
            if not server_url:
                logger.error(f"[CORAL-AUTH] No server URL configured for agent {agent_id}")
                return None
            
            auth_token = self.auth_tokens.get(agent_id)
            if not auth_token:
                logger.error(f"[CORAL-AUTH] No auth token for agent {agent_id}")
                return None
            
            logger.info(f"[CORAL-AUTH] Authenticating agent {agent_id} with Coral Server")
            
            # Prepare authentication payload
            payload = {
                "agentId": agent_id,
                "token": auth_token
            }
            
            # Send authentication request
            auth_url = f"{server_url}/api/agents/authenticate"
            response = requests.post(
                auth_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                auth_response = AuthenticationResponse(
                    session_token=data.get("sessionToken"),
                    agent_id=data.get("agentId"),
                    expires_at=data.get("expiresAt", int(datetime.now().timestamp()) + 3600)
                )
                
                # Store session
                self.sessions[agent_id] = auth_response
                logger.info(f"[CORAL-AUTH] Agent {agent_id} authenticated successfully")
                return auth_response
            else:
                logger.error(f"[CORAL-AUTH] Failed to authenticate agent {agent_id}: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"[CORAL-AUTH] Exception during agent authentication for {agent_id}: {str(e)}")
            return None
    
    def get_session(self, agent_id: str) -> Optional[AuthenticationResponse]:
        """
        Get active session for an agent
        """
        session = self.sessions.get(agent_id)
        if session:
            # Check if session is expired
            if session.expires_at < int(datetime.now().timestamp()):
                logger.info(f"[CORAL-AUTH] Session for agent {agent_id} has expired")
                del self.sessions[agent_id]
                return None
            return session
        return None
    
    def invalidate_session(self, agent_id: str) -> None:
        """
        Invalidate session for an agent
        """
        if agent_id in self.sessions:
            del self.sessions[agent_id]
            logger.info(f"[CORAL-AUTH] Invalidated session for agent {agent_id}")
    
    async def refresh_session(self, agent_id: str) -> Optional[AuthenticationResponse]:
        """
        Refresh session for an agent
        """
        try:
            # Invalidate current session
            self.invalidate_session(agent_id)
            
            # Authenticate again
            return await self.authenticate_agent(agent_id)
            
        except Exception as e:
            logger.error(f"[CORAL-AUTH] Exception during session refresh for {agent_id}: {str(e)}")
            return None