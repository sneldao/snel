"""
SNEL Coral Agent Production Configuration
ENHANCEMENT FIRST: Production-ready configuration for Coral Protocol deployment
"""

import os
from typing import Dict, Any, List
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class CoralAgentConfig:
    """Configuration for SNEL Coral Agent production deployment"""
    
    # Agent Identity
    agent_id: str = "snel-defi-agent-v2"
    agent_name: str = "SNEL DeFi Assistant"
    agent_description: str = "AI-powered cross-chain DeFi assistant specialized in swaps, bridging, portfolio analysis, and protocol research across 17+ blockchain networks"
    agent_version: str = "2.0.0"
    
    # Coral Protocol Configuration
    coral_marketplace_url: str = "https://coral.co/marketplace"
    coral_registry_url: str = "https://api.coral.co/agents"
    coral_pricing_model: str = "usage_based"  # or "time_based", "subscription"
    
    # Pricing Configuration (in Coral Protocol tokens or USD)
    base_price_per_request: float = 0.10  # $0.10 per request
    premium_operations_multiplier: float = 2.0  # 2x for swaps/bridges
    bulk_discount_threshold: int = 100  # Discount after 100 requests
    bulk_discount_rate: float = 0.15  # 15% discount for bulk usage
    
    # Operational Limits
    max_requests_per_hour: int = 1000
    max_concurrent_requests: int = 50
    max_portfolio_analysis_per_day: int = 500
    max_swap_amount_usd: float = 100000.0  # $100k max per swap
    
    # Supported Operations
    supported_chains: List[int] = None
    supported_tokens: List[str] = None
    supported_protocols: List[str] = None
    
    # Performance & Quality
    target_response_time_seconds: float = 3.0
    minimum_success_rate: float = 0.95  # 95% success rate SLA
    uptime_target: float = 0.99  # 99% uptime SLA
    
    # Revenue Sharing (if applicable)
    coral_platform_fee: float = 0.15  # 15% platform fee to Coral
    agent_owner_share: float = 0.85   # 85% to agent owner (you!)
    
    def __post_init__(self):
        """Initialize default values from environment"""
        if self.supported_chains is None:
            self.supported_chains = [1, 8453, 42161, 10, 137, 43114, 56, 324, 11235]  # Major chains + Kaia
            
        if self.supported_tokens is None:
            self.supported_tokens = [
                "ETH", "USDC", "USDT", "DAI", "WETH", "WBTC", 
                "MATIC", "AVAX", "BNB", "OP", "ARB", "KAIA"
            ]
            
        if self.supported_protocols is None:
            self.supported_protocols = [
                "Uniswap", "Sushiswap", "Curve", "Balancer", "1inch",
                "Aave", "Compound", "MakerDAO", "Axelar", "LayerZero"
            ]
    
    def to_coral_manifest(self) -> Dict[str, Any]:
        """Generate Coral Protocol agent manifest"""
        return {
            "id": self.agent_id,
            "name": self.agent_name,
            "description": self.agent_description,
            "version": self.agent_version,
            "category": "DeFi",
            "tags": ["DeFi", "CrossChain", "Swaps", "Portfolio", "AI", "Multi-Agent"],
            "pricing": {
                "model": self.coral_pricing_model,
                "base_price": self.base_price_per_request,
                "premium_multiplier": self.premium_operations_multiplier,
                "bulk_discount": {
                    "threshold": self.bulk_discount_threshold,
                    "rate": self.bulk_discount_rate
                }
            },
            "capabilities": {
                "operations": [
                    {
                        "name": "Token Swap",
                        "description": "Execute token swaps across multiple DEXs",
                        "cost_multiplier": self.premium_operations_multiplier,
                        "supported_chains": self.supported_chains
                    },
                    {
                        "name": "Cross-Chain Bridge", 
                        "description": "Bridge tokens across blockchain networks",
                        "cost_multiplier": self.premium_operations_multiplier,
                        "supported_chains": self.supported_chains
                    },
                    {
                        "name": "Portfolio Analysis",
                        "description": "Comprehensive wallet and portfolio analysis",
                        "cost_multiplier": 1.5,
                        "daily_limit": self.max_portfolio_analysis_per_day
                    },
                    {
                        "name": "Protocol Research",
                        "description": "AI-powered DeFi protocol research and analysis", 
                        "cost_multiplier": 1.0,
                        "supported_protocols": self.supported_protocols
                    },
                    {
                        "name": "General DeFi Assistance",
                        "description": "Natural language DeFi guidance and recommendations",
                        "cost_multiplier": 1.0
                    }
                ],
                "coordination": {
                    "multi_agent_ready": True,
                    "data_sharing": True,
                    "strategy_collaboration": True,
                    "market_coordination": True
                }
            },
            "technical": {
                "supported_chains": self.supported_chains,
                "supported_tokens": self.supported_tokens,
                "supported_protocols": self.supported_protocols,
                "max_concurrent_requests": self.max_concurrent_requests,
                "target_response_time": self.target_response_time_seconds
            },
            "sla": {
                "uptime_target": self.uptime_target,
                "success_rate_target": self.minimum_success_rate,
                "max_response_time": self.target_response_time_seconds * 2
            },
            "contact": {
                "support_email": os.getenv("AGENT_SUPPORT_EMAIL", "support@snel.ai"),
                "documentation_url": "https://docs.snel.ai/coral-agent",
                "github_url": "https://github.com/snel/coral-agent"
            }
        }
    
    def get_revenue_projection(self, estimated_daily_requests: int) -> Dict[str, float]:
        """Calculate revenue projections"""
        # Base revenue calculation
        daily_base_revenue = estimated_daily_requests * self.base_price_per_request
        
        # Apply bulk discounts if applicable
        if estimated_daily_requests > self.bulk_discount_threshold:
            daily_base_revenue *= (1 - self.bulk_discount_rate)
        
        # Assume 30% of requests are premium operations (swaps/bridges)
        premium_requests = estimated_daily_requests * 0.3
        premium_revenue = premium_requests * self.base_price_per_request * (self.premium_operations_multiplier - 1)
        
        daily_gross_revenue = daily_base_revenue + premium_revenue
        coral_platform_fee_amount = daily_gross_revenue * self.coral_platform_fee
        daily_net_revenue = daily_gross_revenue - coral_platform_fee_amount
        
        return {
            "daily_gross_revenue": daily_gross_revenue,
            "daily_net_revenue": daily_net_revenue,
            "monthly_net_revenue": daily_net_revenue * 30,
            "annual_net_revenue": daily_net_revenue * 365,
            "coral_platform_fee": coral_platform_fee_amount,
            "estimated_requests": estimated_daily_requests
        }

# Create default configuration instance
default_config = CoralAgentConfig()

# Revenue projections for different scenarios
def show_revenue_projections():
    """Display revenue projections for different usage scenarios"""
    scenarios = [
        ("Conservative", 50),    # 50 requests/day
        ("Moderate", 200),       # 200 requests/day  
        ("Popular", 500),        # 500 requests/day
        ("Viral", 1000),         # 1000 requests/day
    ]
    
    print("🚀 SNEL Coral Agent Revenue Projections")
    print("=" * 60)
    
    for scenario_name, daily_requests in scenarios:
        projection = default_config.get_revenue_projection(daily_requests)
        print(f"\n📊 {scenario_name} Scenario ({daily_requests} requests/day):")
        print(f"   💰 Daily Net Revenue: ${projection['daily_net_revenue']:.2f}")
        print(f"   📅 Monthly Net Revenue: ${projection['monthly_net_revenue']:.2f}")
        print(f"   🎯 Annual Net Revenue: ${projection['annual_net_revenue']:.2f}")
        print(f"   🏦 Platform Fee (15%): ${projection['coral_platform_fee']:.2f}/day")

if __name__ == "__main__":
    # Display configuration
    print("🤖 SNEL Coral Agent Production Configuration")
    print("=" * 50)
    print(f"Agent ID: {default_config.agent_id}")
    print(f"Pricing: ${default_config.base_price_per_request}/request")
    print(f"Supported Chains: {len(default_config.supported_chains)}")
    print(f"Supported Tokens: {len(default_config.supported_tokens)}")
    
    # Show revenue projections
    show_revenue_projections()
    
    # Generate manifest
    print(f"\n📄 Coral Manifest Preview:")
    manifest = default_config.to_coral_manifest()
    import json
    print(json.dumps(manifest, indent=2)[:500] + "...")
