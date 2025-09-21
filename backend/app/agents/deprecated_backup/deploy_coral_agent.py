#!/usr/bin/env python3
"""
SNEL Coral Agent Deployment Script
ENHANCEMENT FIRST: Automated deployment to Coral Protocol marketplace
"""

import os
import json
import sys
import asyncio
import aiohttp
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import asdict
from coral_agent_config import default_config

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CoralDeploymentManager:
    """Manages deployment of SNEL agent to Coral Protocol"""
    
    def __init__(self, config_override: Optional[Dict] = None):
        self.config = default_config
        if config_override:
            for key, value in config_override.items():
                setattr(self.config, key, value)
        
        # Coral Protocol API credentials
        self.api_key = os.getenv("CORAL_API_KEY")
        self.agent_secret = os.getenv("CORAL_AGENT_SECRET") 
        self.deployment_env = os.getenv("CORAL_DEPLOYMENT_ENV", "production")  # or "staging"
        
        if not self.api_key:
            logger.warning("⚠️  CORAL_API_KEY not found - deployment will be simulated")
        
    async def validate_agent_health(self) -> bool:
        """Validate that the agent is healthy before deployment"""
        logger.info("🔍 Validating agent health...")
        
        try:
            # Import and test the agent
            sys.path.append(str(Path(__file__).parent))
            from coral_agent_v2 import SNELCoralAgentV2 as SNELCoralAgent
            
            # Initialize agent
            agent = SNELCoralAgent()
            
            # Test basic functionality - simplified health check
            test_queries = [
                "Hello",  # Simple response test
                "What is your name?",  # Basic agent identity test
            ]
            
            for query in test_queries:
                try:
                    response = await asyncio.wait_for(
                        agent.process_request(query),
                        timeout=15.0  # Increased timeout for complex agent operations
                    )
                    if not response or len(response) < 10:
                        logger.error(f"❌ Invalid response to test query: {query}")
                        return False
                        
                except asyncio.TimeoutError:
                    logger.error(f"❌ Timeout on test query: {query}")
                    return False
                except Exception as e:
                    logger.error(f"❌ Error on test query '{query}': {str(e)}")
                    return False
            
            logger.info("✅ Agent health validation passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Agent health validation failed: {str(e)}")
            return False
    
    async def generate_deployment_package(self) -> Dict[str, Any]:
        """Generate complete deployment package for Coral Protocol"""
        logger.info("📦 Generating deployment package...")
        
        # Generate base manifest
        manifest = self.config.to_coral_manifest()
        
        # Add deployment-specific metadata
        deployment_package = {
            "manifest": manifest,
            "deployment": {
                "environment": self.deployment_env,
                "runtime": "python3.11",
                "dependencies": self._get_dependencies(),
                "environment_variables": self._get_required_env_vars(),
                "health_check": {
                    "endpoint": "/health",
                    "timeout_seconds": 5,
                    "interval_seconds": 30
                },
                "scaling": {
                    "min_instances": 1,
                    "max_instances": 10,
                    "cpu_threshold": 70,
                    "memory_threshold": 80
                },
                "monitoring": {
                    "metrics_enabled": True,
                    "logging_level": "INFO",
                    "performance_tracking": True
                }
            },
            "metadata": {
                "created_at": "2024-01-20T00:00:00Z",
                "created_by": "SNEL Development Team",
                "deployment_version": "1.0.0",
                "coral_sdk_version": "2.1.0"
            }
        }
        
        return deployment_package
    
    def _get_dependencies(self) -> Dict[str, str]:
        """Get required Python dependencies"""
        return {
            "langchain": ">=0.1.0",
            "langchain-openai": ">=0.0.5",
            "openai": ">=1.0.0",
            "aiohttp": ">=3.9.0",
            "python-dotenv": ">=1.0.0",
            "pydantic": ">=2.0.0",
            "requests": ">=2.31.0"
        }
    
    def _get_required_env_vars(self) -> Dict[str, str]:
        """Get required environment variables (without values)"""
        return {
            "OPENAI_API_KEY": "OpenAI API key for LLM operations",
            "BRIAN_API_KEY": "Brian API key for DeFi operations (optional)",
            "AXELAR_API_KEY": "Axelar API key for bridging (optional)",
            "AGENT_SUPPORT_EMAIL": "Support email for the agent",
            "CORAL_AGENT_SECRET": "Agent secret for Coral Protocol authentication"
        }
    
    async def deploy_to_coral(self, deployment_package: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy agent package to Coral Protocol"""
        if not self.api_key:
            logger.info("🎭 SIMULATION MODE: Would deploy to Coral Protocol")
            return self._simulate_deployment(deployment_package)
        
        logger.info("🚀 Deploying to Coral Protocol...")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Agent-Secret": self.agent_secret or "",
            "X-Deployment-Env": self.deployment_env
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                # First, register the agent
                registration_url = f"{self.config.coral_registry_url}/register"
                async with session.post(registration_url, 
                                      headers=headers, 
                                      json=deployment_package) as response:
                    
                    if response.status == 201:
                        result = await response.json()
                        logger.info(f"✅ Agent registered successfully!")
                        logger.info(f"🆔 Agent ID: {result.get('agent_id')}")
                        logger.info(f"🔗 Marketplace URL: {result.get('marketplace_url')}")
                        
                        return {
                            "status": "success",
                            "agent_id": result.get("agent_id"),
                            "marketplace_url": result.get("marketplace_url"),
                            "deployment_id": result.get("deployment_id"),
                            "estimated_approval_time": "24-48 hours"
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Deployment failed: {response.status} - {error_text}")
                        return {
                            "status": "error",
                            "error": error_text,
                            "status_code": response.status
                        }
        
        except Exception as e:
            logger.error(f"❌ Deployment error: {str(e)}")
            return {
                "status": "error", 
                "error": str(e)
            }
    
    def _simulate_deployment(self, deployment_package: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate deployment for testing purposes"""
        import uuid
        
        # Save deployment package locally
        package_file = Path("coral_deployment_package.json")
        with open(package_file, 'w') as f:
            json.dump(deployment_package, f, indent=2)
        
        logger.info(f"💾 Deployment package saved to: {package_file}")
        
        # Simulate successful deployment
        mock_agent_id = f"snel-agent-{uuid.uuid4().hex[:8]}"
        mock_marketplace_url = f"https://coral.co/marketplace/agents/{mock_agent_id}"
        
        return {
            "status": "simulated_success",
            "agent_id": mock_agent_id,
            "marketplace_url": mock_marketplace_url,
            "deployment_id": f"deploy-{uuid.uuid4().hex[:12]}",
            "estimated_approval_time": "24-48 hours",
            "note": "This is a simulated deployment. Set CORAL_API_KEY for real deployment."
        }
    
    async def setup_monitoring(self, agent_id: str) -> bool:
        """Setup monitoring and analytics for deployed agent"""
        logger.info("📊 Setting up monitoring and analytics...")
        
        # Create monitoring dashboard configuration
        monitoring_config = {
            "agent_id": agent_id,
            "metrics": [
                "request_count",
                "response_time", 
                "success_rate",
                "error_rate",
                "revenue_generated",
                "user_satisfaction"
            ],
            "alerts": [
                {
                    "name": "High Error Rate",
                    "condition": "error_rate > 0.05",  # 5% error rate
                    "notification": "email"
                },
                {
                    "name": "Slow Response Time",
                    "condition": "avg_response_time > 5.0",  # 5 seconds
                    "notification": "slack"
                },
                {
                    "name": "Low Success Rate",
                    "condition": "success_rate < 0.95",  # 95% success rate
                    "notification": "email"
                }
            ],
            "dashboards": [
                {
                    "name": "Performance Overview",
                    "widgets": ["request_volume", "response_times", "success_rates"]
                },
                {
                    "name": "Revenue Analytics", 
                    "widgets": ["daily_revenue", "user_growth", "pricing_optimization"]
                }
            ]
        }
        
        # Save monitoring config
        monitoring_file = Path(f"monitoring_config_{agent_id}.json")
        with open(monitoring_file, 'w') as f:
            json.dump(monitoring_config, f, indent=2)
        
        logger.info(f"📈 Monitoring configuration saved to: {monitoring_file}")
        return True

async def main():
    """Main deployment function"""
    logger.info("🚀 SNEL Coral Agent Deployment Starting...")
    
    # Initialize deployment manager
    deployer = CoralDeploymentManager()
    
    # Step 1: Validate agent health
    if not await deployer.validate_agent_health():
        logger.error("❌ Agent health check failed. Aborting deployment.")
        sys.exit(1)
    
    # Step 2: Generate deployment package
    deployment_package = await deployer.generate_deployment_package()
    
    # Step 3: Deploy to Coral Protocol
    deployment_result = await deployer.deploy_to_coral(deployment_package)
    
    # Step 4: Setup monitoring (if deployment successful)
    if deployment_result.get("status") in ["success", "simulated_success"]:
        agent_id = deployment_result.get("agent_id")
        await deployer.setup_monitoring(agent_id)
        
        # Print success summary
        print("\n" + "="*60)
        print("🎉 SNEL Coral Agent Deployment Complete!")
        print("="*60)
        print(f"🤖 Agent ID: {agent_id}")
        print(f"🔗 Marketplace: {deployment_result.get('marketplace_url')}")
        print(f"⏱️  Approval Time: {deployment_result.get('estimated_approval_time')}")
        print(f"💰 Revenue Potential: See coral_agent_config.py projections")
        print("\n🎯 Next Steps:")
        print("  1. Monitor approval status on Coral marketplace")
        print("  2. Set up payment processing")
        print("  3. Create user documentation") 
        print("  4. Begin Phase 3: Multi-agent coordination")
        print("="*60)
    else:
        logger.error("❌ Deployment failed. Check logs for details.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
