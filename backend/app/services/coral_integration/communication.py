"""
SNEL Coral Communication Service
ENHANCEMENT FIRST: Proper MCP thread-based communication with Coral Server
RELIABLE: Persistent connections with reconnection logic
PERFORMANT: Efficient message handling and queuing
"""

import asyncio
import logging
import json
import websockets
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class Message:
    """Represents a message in MCP thread communication"""
    thread_id: str
    message_id: str
    sender: str
    recipient: str
    content: Dict[str, Any]
    timestamp: float
    metadata: Dict[str, Any]

class CoralCommunicationService:
    """
    Service for handling Coral Protocol communication
    ENHANCEMENT: Proper MCP thread-based communication
    RELIABLE: Persistent connections with reconnection logic
    """
    
    def __init__(self, auth_service):
        self.auth_service = auth_service
        self.connections: Dict[str, websockets.WebSocketClientProtocol] = {}
        self.message_handlers: Dict[str, Callable] = {}
        self.message_queues: Dict[str, asyncio.Queue] = {}
        self.reconnect_tasks: Dict[str, asyncio.Task] = {}
        
    async def establish_connection(self, agent_id: str, server_url: str) -> bool:
        """
        Establish WebSocket connection for persistent communication
        """
        try:
            # Get active session
            session = self.auth_service.get_session(agent_id)
            if not session:
                logger.error(f"[CORAL-COMM] No active session for agent {agent_id}")
                return False
            
            # Close existing connection if present
            if agent_id in self.connections:
                await self.connections[agent_id].close()
                del self.connections[agent_id]
            
            # Construct WebSocket URI with session token
            ws_uri = f"ws://{server_url.split('://')[1]}/api/agents/connect?token={session.session_token}"
            
            logger.info(f"[CORAL-COMM] Connecting to WebSocket: {ws_uri}")
            
            # Establish WebSocket connection
            websocket = await websockets.connect(ws_uri)
            self.connections[agent_id] = websocket
            
            # Start message receiver task
            asyncio.create_task(self._receive_messages(agent_id))
            
            logger.info(f"[CORAL-COMM] Established WebSocket connection for agent {agent_id}")
            return True
            
        except Exception as e:
            logger.error(f"[CORAL-COMM] Failed to establish WebSocket connection for agent {agent_id}: {str(e)}")
            return False
    
    async def _receive_messages(self, agent_id: str) -> None:
        """
        Receive messages from WebSocket connection
        """
        try:
            websocket = self.connections.get(agent_id)
            if not websocket:
                logger.error(f"[CORAL-COMM] No WebSocket connection for agent {agent_id}")
                return
            
            async for message_str in websocket:
                try:
                    # Parse message
                    message_data = json.loads(message_str)
                    
                    # Create message object
                    message = Message(
                        thread_id=message_data.get("threadId", ""),
                        message_id=message_data.get("messageId", ""),
                        sender=message_data.get("sender", ""),
                        recipient=message_data.get("recipient", ""),
                        content=message_data.get("content", {}),
                        timestamp=message_data.get("timestamp", datetime.now().timestamp()),
                        metadata=message_data.get("metadata", {})
                    )
                    
                    # Handle message
                    await self._handle_message(agent_id, message)
                    
                except json.JSONDecodeError:
                    logger.warning(f"[CORAL-COMM] Failed to parse message: {message_str}")
                except Exception as e:
                    logger.error(f"[CORAL-COMM] Exception during message handling: {str(e)}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"[CORAL-COMM] WebSocket connection closed for agent {agent_id}")
            await self._reconnect(agent_id)
        except Exception as e:
            logger.error(f"[CORAL-COMM] Exception during message receiving for agent {agent_id}: {str(e)}")
            await self._reconnect(agent_id)
    
    async def _handle_message(self, agent_id: str, message: Message) -> None:
        """
        Handle received message
        """
        try:
            # Check if there's a specific handler for this agent
            handler = self.message_handlers.get(agent_id)
            if handler:
                await handler(message)
            else:
                # Queue message for later processing
                if agent_id not in self.message_queues:
                    self.message_queues[agent_id] = asyncio.Queue()
                
                await self.message_queues[agent_id].put(message)
                logger.info(f"[CORAL-COMM] Queued message for agent {agent_id}")
                
        except Exception as e:
            logger.error(f"[CORAL-COMM] Exception during message handling for agent {agent_id}: {str(e)}")
    
    async def send_message(self, agent_id: str, message: Message) -> bool:
        """
        Send message through WebSocket connection
        """
        try:
            websocket = self.connections.get(agent_id)
            if not websocket or websocket.closed:
                logger.error(f"[CORAL-COMM] No active WebSocket connection for agent {agent_id}")
                return False
            
            # Prepare message data
            message_data = {
                "threadId": message.thread_id,
                "messageId": message.message_id,
                "sender": message.sender,
                "recipient": message.recipient,
                "content": message.content,
                "timestamp": message.timestamp,
                "metadata": message.metadata
            }
            
            # Send message
            await websocket.send(json.dumps(message_data))
            logger.info(f"[CORAL-COMM] Sent message to agent {agent_id}")
            return True
            
        except Exception as e:
            logger.error(f"[CORAL-COMM] Failed to send message to agent {agent_id}: {str(e)}")
            return False
    
    async def _reconnect(self, agent_id: str) -> None:
        """
        Reconnect WebSocket connection
        """
        try:
            logger.info(f"[CORAL-COMM] Attempting to reconnect agent {agent_id}")
            
            # Cancel existing reconnect task if present
            if agent_id in self.reconnect_tasks:
                self.reconnect_tasks[agent_id].cancel()
            
            # Schedule reconnect task
            self.reconnect_tasks[agent_id] = asyncio.create_task(self._reconnect_task(agent_id))
            
        except Exception as e:
            logger.error(f"[CORAL-COMM] Exception during reconnect scheduling for agent {agent_id}: {str(e)}")
    
    async def _reconnect_task(self, agent_id: str) -> None:
        """
        Reconnect task with exponential backoff
        """
        try:
            server_url = self.auth_service.server_urls.get(agent_id)
            if not server_url:
                logger.error(f"[CORAL-COMM] No server URL for agent {agent_id}")
                return
            
            # Exponential backoff
            backoff = 1
            max_backoff = 60
            
            while True:
                try:
                    # Refresh session
                    session = await self.auth_service.refresh_session(agent_id)
                    if session:
                        # Re-establish connection
                        connected = await self.establish_connection(agent_id, server_url)
                        if connected:
                            logger.info(f"[CORAL-COMM] Successfully reconnected agent {agent_id}")
                            break
                        else:
                            logger.error(f"[CORAL-COMM] Failed to reconnect agent {agent_id}")
                    else:
                        logger.error(f"[CORAL-COMM] Failed to refresh session for agent {agent_id}")
                        
                except Exception as e:
                    logger.error(f"[CORAL-COMM] Exception during reconnect attempt for agent {agent_id}: {str(e)}")
                
                # Wait before next attempt
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, max_backoff)
                
        except Exception as e:
            logger.error(f"[CORAL-COMM] Exception in reconnect task for agent {agent_id}: {str(e)}")
    
    def set_message_handler(self, agent_id: str, handler: Callable) -> None:
        """
        Set message handler for an agent
        """
        self.message_handlers[agent_id] = handler
        logger.info(f"[CORAL-COMM] Set message handler for agent {agent_id}")
    
    async def get_queued_messages(self, agent_id: str) -> asyncio.Queue:
        """
        Get message queue for an agent
        """
        if agent_id not in self.message_queues:
            self.message_queues[agent_id] = asyncio.Queue()
        return self.message_queues[agent_id]
    
    async def close_connection(self, agent_id: str) -> None:
        """
        Close WebSocket connection for an agent
        """
        try:
            if agent_id in self.connections:
                await self.connections[agent_id].close()
                del self.connections[agent_id]
                logger.info(f"[CORAL-COMM] Closed connection for agent {agent_id}")
            
            # Cancel reconnect task if present
            if agent_id in self.reconnect_tasks:
                self.reconnect_tasks[agent_id].cancel()
                del self.reconnect_tasks[agent_id]
                
        except Exception as e:
            logger.error(f"[CORAL-COMM] Exception during connection closing for agent {agent_id}: {str(e)}")