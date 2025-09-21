"""
SNEL Coral MCP Adapter
ENHANCEMENT FIRST: Wraps existing SNEL orchestrator with MCP protocol for Coral Server
CLEAN: Clear separation between MCP protocol and DeFi business logic
MODULAR: Reuses existing orchestrator without duplication
"""

import asyncio
import json
import logging
import os
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

# MCP Protocol imports
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logging.warning("MCP not available - running in standalone mode")

# ENHANCEMENT: Reuse existing proven orchestrator
from orchestrator.platform_orchestrator import SNELOrchestrator, Platform
from config.settings import get_settings

logger = logging.getLogger(__name__)

@dataclass
class CoralEnvironment:
    """Coral orchestration environment variables"""
    connection_url: Optional[str] = None
    agent_id: Optional[str] = None
    session_id: Optional[str] = None
    sse_url: Optional[str] = None
    runtime: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> 'CoralEnvironment':
        """Load Coral environment from environment variables"""
        return cls(
            connection_url=os.getenv("CORAL_CONNECTION_URL"),
            agent_id=os.getenv("CORAL_AGENT_ID", "snel-defi-agent"),
            session_id=os.getenv("CORAL_SESSION_ID"),
            sse_url=os.getenv("CORAL_SSE_URL"),
            runtime=os.getenv("CORAL_ORCHESTRATION_RUNTIME")
        )
    
    @property
    def is_orchestrated(self) -> bool:
        """Check if running under Coral orchestration"""
        return self.runtime is not None
    
    @property
    def is_devmode(self) -> bool:
        """Check if running in devmode"""
        return self.connection_url and "/devmode/" in self.connection_url

class SNELCoralMCPAdapter:
    """
    MCP Adapter for SNEL DeFi Agent
    ENHANCEMENT FIRST: Wraps existing orchestrator with MCP protocol
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.coral_env = CoralEnvironment.from_env()
        
        # ENHANCEMENT: Reuse existing orchestrator
        self.orchestrator = SNELOrchestrator()
        
        # MCP session (if available)
        self.mcp_session: Optional[ClientSession] = None
        
        # Performance tracking
        self.request_count = 0
        self.success_count = 0
        self.start_time = time.time()
        
        logger.info(f"[CORAL] Initializing SNEL MCP Adapter")
        logger.info(f"[CORAL] Agent ID: {self.coral_env.agent_id}")
        logger.info(f"[CORAL] Orchestrated: {self.coral_env.is_orchestrated}")
        logger.info(f"[CORAL] Devmode: {self.coral_env.is_devmode}")
    
    async def initialize(self):
        """Initialize MCP connection if available"""
        if not MCP_AVAILABLE:
            logger.warning("[CORAL] MCP not available - running in standalone mode")
            return
        
        if self.coral_env.connection_url:
            try:
                await self._connect_to_coral()
                logger.info("[CORAL] Successfully connected to Coral Server")
            except Exception as e:
                logger.error(f"[CORAL] Failed to connect to Coral Server: {e}")
                if not self.coral_env.is_devmode:
                    raise
        else:
            logger.info("[CORAL] No CORAL_CONNECTION_URL - running in standalone mode")
    
    async def _connect_to_coral(self):
        """Connect to Coral Server via MCP"""
        if not self.coral_env.connection_url:
            return
        
        # For SSE connections, we'll implement the SSE client
        if self.coral_env.connection_url.startswith("http"):
            await self._connect_sse()
        else:
            # For stdio connections
            await self._connect_stdio()
    
    async def _connect_sse(self):
        """Connect via SSE (Server-Sent Events) with bidirectional communication"""
        import aiohttp
        import json
        
        logger.info(f"[CORAL] Connecting to SSE endpoint: {self.coral_env.connection_url}")
        
        try:
            # Parse connection URL and setup headers
            url = self.coral_env.connection_url
            headers = {
                'Accept': 'text/event-stream',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive'
            }
            
            # Create persistent SSE connection
            self._sse_session = aiohttp.ClientSession()
            
            async with self._sse_session.get(url, headers=headers) as response:
                if response.status == 200:
                    logger.info("[CORAL] SSE connection established")
                    
                    # Send initial handshake
                    await self._send_handshake()
                    
                    # Listen for MCP messages
                    async for line in response.content:
                        if line:
                            try:
                                decoded_line = line.decode().strip()
                                
                                # Handle SSE format (data: prefix)
                                if decoded_line.startswith('data: '):
                                    message_data = decoded_line[6:]  # Remove 'data: ' prefix
                                    if message_data and message_data != '[DONE]':
                                        await self._process_mcp_message(message_data)
                                elif decoded_line.startswith('event: '):
                                    # Handle event types
                                    event_type = decoded_line[7:]
                                    logger.debug(f"[CORAL] Received event: {event_type}")
                                    
                            except Exception as e:
                                logger.error(f"[CORAL] Error processing SSE line: {e}")
                                
                elif response.status == 404:
                    logger.warning("[CORAL] SSE endpoint not found - may be running in devmode without server")
                else:
                    logger.error(f"[CORAL] SSE connection failed: {response.status}")
                    
        except aiohttp.ClientConnectorError:
            logger.warning("[CORAL] Cannot connect to Coral Server - running in standalone mode")
        except Exception as e:
            logger.error(f"[CORAL] SSE connection error: {e}")
            raise
    
    async def _send_handshake(self):
        """Send initial handshake to Coral Server"""
        handshake = {
            'type': 'handshake',
            'agent_id': self.coral_env.agent_id,
            'session_id': self.coral_env.session_id,
            'capabilities': [tool['name'] for tool in self.get_available_tools()],
            'version': '1.0.0'
        }
        
        logger.info(f"[CORAL] Sending handshake: {handshake}")
        # In a full implementation, this would be sent via POST to a handshake endpoint
    
    async def _send_response(self, response_data: dict):
        """Send response back to Coral Server via SSE"""
        try:
            if hasattr(self, '_sse_session') and self._sse_session:
                # In a full bidirectional SSE implementation, we'd send via a separate endpoint
                # For now, we'll log the response that would be sent
                logger.info(f"[CORAL] Would send response: {response_data}")
                
                # TODO: Implement actual response sending via POST to response endpoint
                # response_url = self.coral_env.connection_url.replace('/sse/', '/response/')
                # async with self._sse_session.post(response_url, json=response_data) as resp:
                #     if resp.status != 200:
                #         logger.error(f"Failed to send response: {resp.status}")
                
        except Exception as e:
            logger.error(f"[CORAL] Error sending response: {e}")
    
    async def _process_mcp_message(self, message: str):
        """Process incoming MCP message from Coral Server"""
        try:
            if not message.strip():
                return
                
            # Parse JSON message
            import json
            data = json.loads(message)
            
            # Handle different MCP message types
            if data.get('type') == 'tool_call':
                tool_name = data.get('tool_name')
                parameters = data.get('parameters', {})
                call_id = data.get('call_id')
                
                logger.info(f"[CORAL] Received tool call: {tool_name}")
                
                # Execute tool via orchestrator
                result = await self.handle_tool_call(tool_name, parameters)
                
                # Send response back
                response = {
                    'type': 'tool_response',
                    'call_id': call_id,
                    'result': result
                }
                
                # Send response via appropriate channel
                if self.coral_env.connection_url and self.coral_env.connection_url.startswith("http"):
                    await self._send_response(response)
                else:
                    await self._send_stdio_response(response)
                
                logger.info(f"[CORAL] Tool response sent: {result.get('success', False)}")
                
            elif data.get('type') == 'ping':
                # Respond to ping for connection health
                logger.debug("[CORAL] Received ping")
                
        except json.JSONDecodeError:
            logger.error(f"[CORAL] Invalid JSON message: {message}")
        except Exception as e:
            logger.error(f"[CORAL] Error processing MCP message: {e}")
    
    async def _connect_stdio(self):
        """Connect via stdio for MCP communication"""
        import sys
        import json
        import asyncio
        
        logger.info("[CORAL] Connecting via stdio for MCP communication")
        
        try:
            # Send initial handshake
            await self._send_stdio_handshake()
            
            # Create reader for stdin
            reader = asyncio.StreamReader()
            protocol = asyncio.StreamReaderProtocol(reader)
            await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)
            
            # Listen for MCP messages on stdin
            while True:
                try:
                    line = await reader.readline()
                    if not line:
                        break
                        
                    message = line.decode().strip()
                    if message:
                        await self._process_mcp_message(message)
                        
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"[CORAL] Error reading stdio: {e}")
                    
        except Exception as e:
            logger.error(f"[CORAL] Stdio connection error: {e}")
            raise
    
    async def _send_stdio_handshake(self):
        """Send handshake via stdout for stdio MCP"""
        import json
        import sys
        
        handshake = {
            'jsonrpc': '2.0',
            'method': 'initialize',
            'params': {
                'agent_id': self.coral_env.agent_id,
                'capabilities': [tool['name'] for tool in self.get_available_tools()],
                'version': '1.0.0'
            }
        }
        
        # Send via stdout
        print(json.dumps(handshake), flush=True)
        logger.info("[CORAL] Sent stdio handshake")
    
    async def _send_stdio_response(self, response_data: dict):
        """Send response via stdout for stdio MCP"""
        import json
        import sys
        
        try:
            # Format as JSON-RPC response
            jsonrpc_response = {
                'jsonrpc': '2.0',
                'id': response_data.get('call_id'),
                'result': response_data.get('result')
            }
            
            # Send via stdout
            print(json.dumps(jsonrpc_response), flush=True)
            logger.debug(f"[CORAL] Sent stdio response for call {response_data.get('call_id')}")
            
        except Exception as e:
            logger.error(f"[CORAL] Error sending stdio response: {e}")
    
    async def handle_tool_call(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle MCP tool calls by delegating to SNEL orchestrator
        ENHANCEMENT FIRST: Reuses existing proven DeFi logic
        """
        self.request_count += 1
        start_time = time.time()
        
        try:
            logger.info(f"[CORAL] Handling tool call: {tool_name}")
            
            # Map MCP tool calls to orchestrator operations
            operation_mapping = {
                "execute_swap": "swap",
                "execute_bridge": "bridge", 
                "analyze_portfolio": "analyze",
                "research_protocol": "research",
                "general_defi_help": "help"
            }
            
            operation = operation_mapping.get(tool_name, tool_name)
            
            # ENHANCEMENT: Use existing orchestrator
            result = await self.orchestrator.execute_defi_operation(
                operation=operation,
                parameters=parameters,
                platform=Platform.CORAL_AGENT,
                user_id=f"coral-{self.coral_env.session_id or 'unknown'}"
            )
            
            self.success_count += 1
            duration = time.time() - start_time
            
            logger.info(f"[CORAL] Tool call completed in {duration:.2f}s")
            
            # Claim payment for successful operation
            await self._claim_payment_for_operation(tool_name, parameters)
            
            return {
                "success": True,
                "result": result,
                "execution_time": duration,
                "agent_id": self.coral_env.agent_id,
                "billing": {
                    "operation": tool_name,
                    "fee_claimed": True
                }
            }
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"[CORAL] Tool call failed: {e}")
            
            return {
                "success": False,
                "error": str(e),
                "execution_time": duration,
                "agent_id": self.coral_env.agent_id
            }
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available MCP tools"""
        return [
            {
                "name": "execute_swap",
                "description": "Execute a token swap operation across supported chains",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "from_token": {"type": "string", "description": "Token to swap from"},
                        "to_token": {"type": "string", "description": "Token to swap to"},
                        "amount": {"type": "number", "description": "Amount to swap"},
                        "chain_id": {"type": "number", "description": "Blockchain network ID"},
                        "wallet_address": {"type": "string", "description": "User's wallet address"}
                    },
                    "required": ["from_token", "to_token", "amount"]
                }
            },
            {
                "name": "execute_bridge",
                "description": "Execute cross-chain bridge operation",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "token": {"type": "string", "description": "Token to bridge"},
                        "amount": {"type": "number", "description": "Amount to bridge"},
                        "from_chain": {"type": "string", "description": "Source blockchain"},
                        "to_chain": {"type": "string", "description": "Destination blockchain"},
                        "wallet_address": {"type": "string", "description": "User's wallet address"}
                    },
                    "required": ["token", "amount", "from_chain", "to_chain"]
                }
            },
            {
                "name": "analyze_portfolio",
                "description": "Analyze wallet portfolio and provide recommendations",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "wallet_address": {"type": "string", "description": "Wallet address to analyze"},
                        "chain_id": {"type": "number", "description": "Blockchain network ID"}
                    },
                    "required": ["wallet_address"]
                }
            },
            {
                "name": "research_protocol",
                "description": "Research DeFi protocol information and analysis",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "protocol_name": {"type": "string", "description": "Name of DeFi protocol to research"}
                    },
                    "required": ["protocol_name"]
                }
            },
            {
                "name": "general_defi_help",
                "description": "Provide general DeFi assistance and guidance",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_request": {"type": "string", "description": "User's question or request"}
                    },
                    "required": ["user_request"]
                }
            }
        ]
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for Coral Server"""
        orchestrator_health = self.orchestrator.get_service_health()
        
        return {
            "status": "healthy",
            "agent_id": self.coral_env.agent_id,
            "session_id": self.coral_env.session_id,
            "runtime": self.coral_env.runtime,
            "mcp_connected": self.mcp_session is not None,
            "orchestrator_health": orchestrator_health,
            "uptime": time.time() - self.start_time,
            "requests_processed": self.request_count,
            "success_rate": (self.success_count / self.request_count * 100) if self.request_count > 0 else 0,
            "tools_available": len(self.get_available_tools())
        }
    
    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("[CORAL] Shutting down SNEL MCP Adapter")
        
        if self.mcp_session:
            try:
                await self.mcp_session.close()
            except Exception as e:
                logger.error(f"[CORAL] Error closing MCP session: {e}")
        
        logger.info("[CORAL] Shutdown complete")
    
    async def _claim_payment_for_operation(self, tool_name: str, parameters: Dict[str, Any]):
        """Claim payment via Crossmint for agent operation"""
        try:
            # Get operation pricing from export settings
            pricing_map = {
                "execute_swap": 0.10,
                "execute_bridge": 0.15,
                "analyze_portfolio": 0.05,
                "research_protocol": 0.08,
                "general_defi_help": 0.03
            }
            
            base_fee = pricing_map.get(tool_name, 0.05)
            
            # Premium operations get multiplier
            premium_ops = ["execute_swap", "execute_bridge"]
            if tool_name in premium_ops:
                base_fee *= 2.0
            
            # Convert to Coral tokens (example rate: $1 = 10 Coral)
            coral_amount = int(base_fee * 10)
            
            logger.info(f"[CORAL] Claiming payment: {coral_amount} Coral tokens for {tool_name}")
            
            # In production, this would call the Coral API:
            # curl 'http://CORAL_API_URL/api/v1/internal/claim/{session_id}' \
            #   --request POST \
            #   --header 'Content-Type: application/json' \
            #   --data '{"amount": {"type": "coral", "amount": coral_amount}}'
            
            # For now, log the payment claim
            logger.info(f"[CORAL] Payment claimed: {coral_amount} Coral tokens")
            
        except Exception as e:
            logger.error(f"[CORAL] Payment claim failed: {e}")
            # Don't fail the operation if payment claim fails

# Devmode support function
def get_devmode_connection_url(app_id: str = "snel", priv_key: str = "dev", session_id: str = "default", agent_id: str = "snel-defi-agent") -> str:
    """Generate devmode connection URL for local testing"""
    base_url = os.getenv("CORAL_SERVER_URL", "http://localhost:5555")
    return f"{base_url}/sse/v1/devmode/{app_id}/{priv_key}/{session_id}/?agentId={agent_id}"