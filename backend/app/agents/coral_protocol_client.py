"""
Minimal Coral Protocol Client for SNEL Agent Integration
ENHANCEMENT FIRST: Enhances existing SNEL agent with proper Coral Protocol integration
DRY: Reuses existing SNEL services and orchestrator
CLEAN: Clear separation of concerns
MODULAR: Composable and testable
"""

"""
LEGACY: This file is kept for reference only
Use main.py and coral_mcp_adapter.py for new Coral Server integration
ENHANCEMENT FIRST: Replaced with proper MCP protocol implementation
"""



import asyncio
import json
import logging
import uuid
from typing import Dict, Any, Optional
from dataclasses import dataclass

import requests
import websockets
from websockets.exceptions import ConnectionClosed

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class AgentRegistration:
    """Agent registration data"""
    agent_id: str
    agent_type: str
    name: str
    description: str
    capabilities: list

@dataclass
class AuthenticationResponse:
    """Authentication response from Coral Server"""
    session_token: str
    agent_id: str
    expires_at: int

class CoralProtocolClient:
    """
    Minimal Coral Protocol Client
    Implements proper authentication and communication flow
    """
    
    def __init__(self, server_url: str, agent_id: str):
        self.server_url = server_url.rstrip('/')
        self.agent_id = agent_id
        self.session_token: Optional[str] = None
        self.websocket_uri: Optional[str] = None
        
    def register_agent(self, registration_data: AgentRegistration) -> bool:
        """
        Register agent with Coral Server
        ENHANCEMENT: Uses existing SNEL agent metadata
        """
        try:
            logger.info(f"[CORAL] Registering agent {self.agent_id}")
            
            # Use the correct endpoint for agent registration
            register_url = f"{self.server_url}/api/agents"
            
            payload = {
                "agentId": self.agent_id,
                "type": registration_data.agent_type,
                "name": registration_data.name,
                "description": registration_data.description,
                "capabilities": registration_data.capabilities
            }
            
            response = requests.post(
                register_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                logger.info(f"[CORAL] Agent {self.agent_id} registered successfully")
                return True
            else:
                logger.error(f"[CORAL] Failed to register agent: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"[CORAL] Exception during agent registration: {str(e)}")
            return False
    
    def register_with_autonome(self, autonom_api_key: str) -> bool:
        """
        Register the agent with Autonome (DeFAI) platform for verifiable agent actions.
        PL Genesis Hackathon Requirement.
        """
        try:
            logger.info(f"[AUTONOME] Registering agent {self.agent_id} with Autonome")
            autonome_url = os.getenv("AUTONOME_RPC_URL", "https://rpc.autonome.ai/v1/agents/register")
            
            payload = {
                "agentId": self.agent_id,
                "metadata": {
                    "name": "SNEL Sovereign DeFAI Agent",
                    "version": "1.0.0",
                    "capabilities": ["multi-chain-swap", "cross-chain-bridge", "private-zk-swap"],
                    "privacy_layer": "Starknet"
                }
            }
            
            response = requests.post(
                autonome_url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {autonome_api_key}",
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"[AUTONOME] Agent {self.agent_id} registered successfully with Autonome")
                return True
            else:
                logger.error(f"[AUTONOME] Autonome registration failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"[AUTONOME] Exception during Autonome registration: {str(e)}")
            return False

    def submit_verifiable_action(self, action_type: str, details: Dict[str, Any], proof: str) -> bool:
        """
        Submit a verifiable action to Autonome.
        Ensures agent actions are auditable and verifiable (Proof-of-Action).
        """
        try:
            autonome_url = os.getenv("AUTONOME_RPC_URL", "https://rpc.autonome.ai/v1/actions")
            api_key = os.getenv("AUTONOME_API_KEY")
            
            if not api_key:
                return False

            payload = {
                "agentId": self.agent_id,
                "action": action_type,
                "details": details,
                "proof": proof, # e.g., IPFS CID or Starknet Tx Hash
                "timestamp": int(time.time())
            }
            
            requests.post(
                autonome_url,
                json=payload,
                headers={"Authorization": f"Bearer {api_key}"}
            )
            return True
        except Exception as e:
            logger.error(f"[AUTONOME] Verifiable action submission failed: {e}")
            return False

    def authenticate_agent(self, auth_token: str) -> Optional[AuthenticationResponse]:
        """
        Authenticate agent with Coral Server
        Returns session token for persistent communication
        """
        try:
            logger.info(f"[CORAL] Authenticating agent {self.agent_id}")
            
            # Use the correct authentication endpoint
            auth_url = f"{self.server_url}/api/agents/authenticate"
            
            payload = {
                "agentId": self.agent_id,
                "token": auth_token
            }
            
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
                    expires_at=data.get("expiresAt", 0)
                )
                
                self.session_token = auth_response.session_token
                logger.info(f"[CORAL] Agent {self.agent_id} authenticated successfully")
                return auth_response
            else:
                logger.error(f"[CORAL] Failed to authenticate agent: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"[CORAL] Exception during agent authentication: {str(e)}")
            return None
    
    async def connect_to_websocket(self) -> bool:
        """
        Establish persistent WebSocket connection for MCP thread communication
        """
        try:
            if not self.session_token:
                logger.error("[CORAL] No session token available for WebSocket connection")
                return False
            
            # Construct WebSocket URI with session token
            ws_uri = f"ws://{self.server_url.split('://')[1]}/api/agents/connect?token={self.session_token}"
            self.websocket_uri = ws_uri
            
            logger.info(f"[CORAL] Connecting to WebSocket: {ws_uri}")
            
            # Establish WebSocket connection
            self.websocket = await websockets.connect(ws_uri)
            logger.info("[CORAL] WebSocket connection established successfully")
            return True
            
        except Exception as e:
            logger.error(f"[CORAL] Exception during WebSocket connection: {str(e)}")
            return False
    
    async def send_message(self, message: Dict[str, Any]) -> bool:
        """
        Send message through MCP thread communication
        """
        try:
            if not hasattr(self, 'websocket') or not self.websocket.open:
                logger.error("[CORAL] WebSocket connection not available")
                return False
            
            # Add session token to message headers
            message_with_auth = {
                "headers": {
                    "Authorization": f"Bearer {self.session_token}",
                    "Content-Type": "application/json"
                },
                "body": message
            }
            
            await self.websocket.send(json.dumps(message_with_auth))
            logger.info("[CORAL] Message sent successfully")
            return True
            
        except Exception as e:
            logger.error(f"[CORAL] Exception during message sending: {str(e)}")
            return False
    
    async def receive_messages(self, message_handler):
        """
        Receive messages through MCP thread communication
        """
        try:
            async for message in self.websocket:
                try:
                    parsed_message = json.loads(message)
                    await message_handler(parsed_message)
                except json.JSONDecodeError:
                    logger.warning(f"[CORAL] Failed to parse message: {message}")
                    
        except ConnectionClosed:
            logger.info("[CORAL] WebSocket connection closed")
        except Exception as e:
            logger.error(f"[CORAL] Exception during message receiving: {str(e)}")
    
    def disconnect(self):
        """
        Disconnect from Coral Server
        """
        try:
            if hasattr(self, 'websocket') and self.websocket.open:
                asyncio.create_task(self.websocket.close())
                logger.info("[CORAL] Disconnected from Coral Server")
        except Exception as e:
            logger.error(f"[CORAL] Exception during disconnection: {str(e)}")

# Example usage
async def example_usage():
    """
    Example usage of the Coral Protocol Client
    """
    # Initialize client
    client = CoralProtocolClient("http://localhost:5555", "snel-defi-agent")
    
    # Register agent
    registration = AgentRegistration(
        agent_id="snel-defi-agent",
        agent_type="local",
        name="SNEL DeFi Agent",
        description="AI-powered cross-chain DeFi assistant for swaps, bridging, and portfolio analysis",
        capabilities=[
            {"type": "tool", "name": "execute-swap", "description": "Execute token swaps"},
            {"type": "tool", "name": "bridge-assets", "description": "Bridge assets between chains"},
            {"type": "tool", "name": "analyze-portfolio", "description": "Analyze DeFi portfolio"}
        ]
    )
    
    # Register (this would typically be done once)
    # registered = client.register_agent(registration)
    
    # Authenticate (this would be done each session)
    # auth_response = client.authenticate_agent("your-auth-token-here")
    
    # if auth_response:
    #     # Connect to WebSocket for persistent communication
    #     connected = await client.connect_to_websocket()
        
    #     if connected:
    #         # Start receiving messages
    #         await client.receive_messages(handle_message)
    
    print("Coral Protocol Client initialized")

async def handle_message(message):
    """
    Handle incoming messages from Coral Server
    """
    print(f"Received message: {message}")

if __name__ == "__main__":
    asyncio.run(example_usage())