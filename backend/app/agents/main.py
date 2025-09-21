#!/usr/bin/env python3
"""
SNEL Coral Agent Main Entry Point
ENHANCEMENT FIRST: Proper Coral Server integration using existing orchestrator
CLEAN: Clear separation between MCP protocol and business logic
MODULAR: Reuses proven SNEL architecture
"""

import asyncio
import logging
import os
import signal
import sys
from typing import Optional

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from coral_mcp_adapter import SNELCoralMCPAdapter, CoralEnvironment

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class SNELCoralAgent:
    """
    Main SNEL Coral Agent
    ENHANCEMENT FIRST: Wraps existing orchestrator with proper Coral integration
    """
    
    def __init__(self):
        self.adapter: Optional[SNELCoralMCPAdapter] = None
        self.running = False
        
    async def start(self):
        """Start the Coral agent"""
        logger.info("[SNEL] Starting SNEL Coral Agent...")
        
        # Check environment
        coral_env = CoralEnvironment.from_env()
        
        # CLEAN: Don't load .env files if running under orchestration
        if not coral_env.is_orchestrated:
            logger.info("[SNEL] Running in standalone mode - loading .env")
            try:
                from dotenv import load_dotenv
                load_dotenv()
            except ImportError:
                logger.warning("[SNEL] python-dotenv not available")
        else:
            logger.info(f"[SNEL] Running under Coral orchestration: {coral_env.runtime}")
        
        # Initialize MCP adapter
        self.adapter = SNELCoralMCPAdapter()
        await self.adapter.initialize()
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.running = True
        logger.info("[SNEL] SNEL Coral Agent started successfully")
        
        # Main event loop
        await self._run_main_loop()
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"[SNEL] Received signal {signum}, shutting down...")
        self.running = False
    
    async def _run_main_loop(self):
        """Main agent event loop"""
        try:
            while self.running:
                # Health check
                if self.adapter:
                    health = await self.adapter.health_check()
                    if health.get('status') != 'healthy':
                        logger.warning(f"[SNEL] Health check warning: {health}")
                
                # Wait before next iteration
                await asyncio.sleep(10)
                
        except Exception as e:
            logger.error(f"[SNEL] Main loop error: {e}")
        finally:
            await self._shutdown()
    
    async def _shutdown(self):
        """Graceful shutdown"""
        logger.info("[SNEL] Shutting down SNEL Coral Agent...")
        
        if self.adapter:
            await self.adapter.shutdown()
        
        logger.info("[SNEL] Shutdown complete")

async def main():
    """Main entry point"""
    coral_env = CoralEnvironment.from_env()
    
    logger.info("🚀 SNEL Coral Agent v1.0")
    logger.info("=" * 50)
    logger.info(f"Agent ID: {coral_env.agent_id}")
    logger.info(f"Session ID: {coral_env.session_id}")
    logger.info(f"Runtime: {coral_env.runtime or 'standalone'}")
    logger.info(f"Connection URL: {coral_env.connection_url or 'none'}")
    
    # Validate required environment for orchestration
    if coral_env.is_orchestrated and not coral_env.connection_url:
        logger.error("[SNEL] CORAL_CONNECTION_URL required when running under orchestration")
        sys.exit(1)
    
    # Start the agent
    agent = SNELCoralAgent()
    try:
        await agent.start()
    except KeyboardInterrupt:
        logger.info("[SNEL] Interrupted by user")
    except Exception as e:
        logger.error(f"[SNEL] Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())