from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Dict, Any, Optional, List, Callable, Awaitable
import logging
from datetime import datetime

# Import services
from app.services.agno_agent import Web3Helper
from app.services.external.exa_service import discover_defi_protocols

# Set up logging
logger = logging.getLogger(__name__)
router = APIRouter()

# Active connections manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, wallet_address: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[wallet_address] = websocket
        logger.info(f"WebSocket connected for wallet: {wallet_address}")
    
    def disconnect(self, wallet_address: str):
        if wallet_address in self.active_connections:
            del self.active_connections[wallet_address]
            logger.info(f"WebSocket disconnected for wallet: {wallet_address}")
    
    async def send_progress(self, wallet_address: str, stage: str, completion: int, details: str = "", type: str = "progress"):
        """Send progress update to specific client"""
        if wallet_address in self.active_connections:
            try:
                await self.active_connections[wallet_address].send_json({
                    "type": type,
                    "data": {
                        "stage": stage,
                        "completion": completion,
                        "details": details,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                })
            except Exception as e:
                logger.error(f"Error sending progress update: {str(e)}")
    
    async def send_data(self, wallet_address: str, data: Dict[str, Any], data_type: str = "result"):
        """Send data payload to specific client"""
        if wallet_address in self.active_connections:
            try:
                await self.active_connections[wallet_address].send_json({
                    "type": data_type,
                    "data": data
                })
            except Exception as e:
                logger.error(f"Error sending data: {str(e)}")
    
    async def send_error(self, wallet_address: str, error_message: str, error_code: str = "ERROR"):
        """Send error message to specific client"""
        if wallet_address in self.active_connections:
            try:
                await self.active_connections[wallet_address].send_json({
                    "type": "error",
                    "data": {
                        "message": error_message,
                        "code": error_code,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                })
            except Exception as e:
                logger.error(f"Error sending error message: {str(e)}")

# Create manager instance
manager = ConnectionManager()

# Progress callback type
ProgressCallback = Callable[[str, int, str], Awaitable[None]]

@router.websocket("/portfolio/{wallet_address}")
async def portfolio_websocket(
    websocket: WebSocket, 
    wallet_address: str,
    chain_id: Optional[int] = Query(None)
):
    """WebSocket endpoint for real-time portfolio analysis"""
    try:
        await manager.connect(wallet_address, websocket)
        
        # Create a progress callback for this specific connection
        async def send_progress(stage: str, completion: int, details: str = ""):
            await manager.send_progress(wallet_address, stage, completion, details)
        
        # Start the analysis process with callback wrapped properly
        result = await perform_portfolio_analysis(wallet_address, chain_id, progress_callback=send_progress)
        logger.info(f"Portfolio analysis completed for wallet: {wallet_address}")
        
    except WebSocketDisconnect:
        manager.disconnect(wallet_address)
    except Exception as e:
        logger.exception(f"Error in portfolio websocket: {str(e)}")
        await manager.send_error(wallet_address, f"Analysis failed: {str(e)}")
        manager.disconnect(wallet_address)

async def perform_portfolio_analysis(
    wallet_address: str, 
    chain_id: Optional[int] = None,
    progress_callback: Optional[ProgressCallback] = None
) -> Dict[str, Any]:
    """Perform full portfolio analysis with real-time progress updates"""
    service_results = {
        "portfolio_data": None,
        "exa_data": None,
        "services_status": {
            "web3": False,
            "exa": False
        },
        "timestamp": datetime.utcnow().isoformat()
    }
    
    try:
        # Initialize supported chains
        supported_chains = {
            1: "Ethereum",
            8453: "Base",
            42161: "Arbitrum",
            10: "Optimism",
            137: "Polygon"
        }
        
        # 1. Get portfolio data from blockchain
        if progress_callback:
            await progress_callback("Connecting to blockchain networks", 10, "Initializing RPC connections")
        
        try:
            # Get actual portfolio data - no mocks
            if progress_callback:
                await progress_callback("Fetching on-chain portfolio data", 20, "Reading wallet balances and tokens")
            
            # Call get_portfolio_summary function directly
            from app.services.agno_agent import get_portfolio_summary
            portfolio_data = await get_portfolio_summary(wallet_address, chain_id)
            
            if "error" in portfolio_data:
                if progress_callback:
                    await progress_callback("Error retrieving blockchain data", 20, portfolio_data["error"])
                service_results["services_status"]["web3"] = False
            else:
                service_results["portfolio_data"] = portfolio_data
                service_results["services_status"]["web3"] = True
                if progress_callback:
                    await progress_callback("Blockchain data retrieved successfully", 30, 
                                          f"Found {portfolio_data.get('total_tokens', 0)} tokens across {portfolio_data.get('chains_active', 0)} chains")
        except Exception as e:
            logger.error(f"Portfolio data retrieval failed: {str(e)}")
            if progress_callback:
                await progress_callback("Blockchain data retrieval failed", 20, str(e))
            service_results["services_status"]["web3"] = False
        
        # 2. Get protocol discovery data from Exa
        try:
            if progress_callback:
                await progress_callback("Discovering DeFi protocols", 40, "Querying Exa API for DeFi protocols")
            
            # Build query based on portfolio data
            query = f"DeFi protocols for wallet {wallet_address}"
            if service_results["portfolio_data"]:
                # Extract token symbols for better search
                tokens = []
                for chain_data in service_results["portfolio_data"].get("token_balances", {}).values():
                    for token in chain_data.get("tokens", []):
                        if token.get("symbol"):
                            tokens.append(token.get("symbol"))
                
                if tokens:
                    query += f" with {', '.join(tokens[:5])} tokens"
            
            # Get real Exa data
            exa_data = await discover_defi_protocols(query)
            
            if "error" in exa_data:
                if progress_callback:
                    await progress_callback("Protocol discovery limited", 45, exa_data["error"])
                service_results["services_status"]["exa"] = False
            else:
                service_results["exa_data"] = exa_data
                service_results["services_status"]["exa"] = True
                if progress_callback:
                    await progress_callback("Protocol discovery completed", 50, 
                                          f"Found {exa_data.get('protocols_found', 0)} relevant protocols")
        except Exception as e:
            logger.error(f"Exa protocol discovery failed: {str(e)}")
            if progress_callback:
                await progress_callback("Protocol discovery failed", 45, str(e))
            service_results["services_status"]["exa"] = False
        
        # 3. Generate analysis based on available data
        if progress_callback:
            await progress_callback("Generating portfolio analysis", 80, "Analyzing collected data")
        
        # Build response with whatever data we have - no mocks
        response = {
            "summary": generate_portfolio_summary(service_results),
            "portfolio_data": service_results["portfolio_data"] or {},
            "exa_data": service_results["exa_data"] or {},
            "services_status": service_results["services_status"],
            "metrics": extract_metrics(service_results),
            "actions": generate_actions(service_results),
            "risks": identify_risks(service_results),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if progress_callback:
            await progress_callback("Analysis complete", 100, "Portfolio analysis finished")
        
        # Send final result
        await manager.send_data(wallet_address, response)
        
    except Exception as e:
        logger.exception(f"Portfolio analysis failed: {str(e)}")
        if progress_callback:
            await progress_callback("Analysis failed", 0, str(e))
        await manager.send_error(wallet_address, f"Portfolio analysis failed: {str(e)}")
    
    return service_results

def generate_portfolio_summary(data: Dict[str, Any]) -> str:
    """Generate text summary based on available data - no fake data"""
    if not data["portfolio_data"]:
        return "We couldn't retrieve your portfolio data. Please check your wallet connection and try again."
    
    # Build summary from actual data
    portfolio_data = data["portfolio_data"]
    total_value = portfolio_data.get("total_portfolio_value_usd", 0)
    chain_count = portfolio_data.get("chains_active", 0)
    token_count = portfolio_data.get("total_tokens", 0)
    
    summary = f"Portfolio Analysis: "
    
    if total_value > 0:
        summary += f"Your portfolio is worth ${total_value:,.2f} across {chain_count} chains with {token_count} different tokens. "
    else:
        summary += f"We found {token_count} tokens across {chain_count} chains, but couldn't determine their value. "
    
    # Add protocol info if available
    if data["services_status"]["exa"] and data["exa_data"]:
        protocols_found = data["exa_data"].get("protocols_found", 0)
        if protocols_found > 0:
            summary += f"We discovered {protocols_found} relevant DeFi protocols for your portfolio. "
    
    # Add service status info
    unavailable_services = []
    for service, status in data["services_status"].items():
        if not status:
            unavailable_services.append(service)
    
    if unavailable_services:
        summary += f"Note: {', '.join(unavailable_services)} {'services were' if len(unavailable_services) > 1 else 'service was'} unavailable during analysis."
    
    return summary

def extract_metrics(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract metrics from available data - no fake metrics"""
    metrics = []
    
    if data["portfolio_data"]:
        portfolio_data = data["portfolio_data"]
        
        # Only add metrics we actually have
        if "total_portfolio_value_usd" in portfolio_data:
            metrics.append({
                "label": "Total Portfolio Value",
                "value": portfolio_data["total_portfolio_value_usd"],
                "type": "currency"
            })
        
        if "native_value_usd" in portfolio_data:
            metrics.append({
                "label": "Native Token Value",
                "value": portfolio_data["native_value_usd"],
                "type": "currency"
            })
        
        if "token_value_usd" in portfolio_data:
            metrics.append({
                "label": "ERC20 Token Value",
                "value": portfolio_data["token_value_usd"],
                "type": "currency"
            })
        
        if "chains_active" in portfolio_data:
            metrics.append({
                "label": "Active Chains",
                "value": portfolio_data["chains_active"],
                "type": "number"
            })
        
        if "total_tokens" in portfolio_data:
            metrics.append({
                "label": "Total Tokens",
                "value": portfolio_data["total_tokens"],
                "type": "number"
            })
        
        if "risk_score" in portfolio_data:
            metrics.append({
                "label": "Risk Score",
                "value": portfolio_data["risk_score"],
                "type": "number"
            })
    
    return metrics

def generate_actions(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate action recommendations based on real data"""
    actions = []
    
    # Only generate actions if we have sufficient data
    if not data["portfolio_data"] or not data["services_status"]["web3"]:
        # Add an action to connect wallet if we couldn't get portfolio data
        actions.append({
            "id": "connect_wallet",
            "description": "Connect your wallet to see personalized recommendations",
            "type": "connect",
            "impact": {}
        })
        return actions
    
    # If we have portfolio data but missing services, add action to retry
    missing_services = []
    for service, status in data["services_status"].items():
        if not status and service != "web3":  # We already have web3 data
            missing_services.append(service)
    
    if missing_services:
        actions.append({
            "id": "retry_services",
            "description": f"Retry analysis to include {', '.join(missing_services)} data",
            "type": "retry",
            "impact": {}
        })
    
    # Add real portfolio actions based on what we have
    portfolio_data = data["portfolio_data"]
    
    # Check if portfolio is concentrated on one chain
    if portfolio_data.get("chains_active", 0) == 1:
        actions.append({
            "id": "diversify_chains",
            "description": "Diversify across multiple chains to reduce risk",
            "type": "rebalance",
            "impact": {
                "risk": -1.5
            }
        })
    
    # Check if we have Exa protocol data for yield opportunities
    if data["services_status"]["exa"] and data["exa_data"]:
        exa_data = data["exa_data"]
        
        if exa_data.get("yield_opportunities", 0) > 0:
            actions.append({
                "id": "explore_yield",
                "description": f"Explore {exa_data.get('yield_opportunities', 'new')} yield opportunities",
                "type": "enter",
                "impact": {
                    "yield": 1.2
                }
            })
    
    return actions

def identify_risks(data: Dict[str, Any]) -> List[str]:
    """Identify real portfolio risks based on actual data"""
    risks = []
    
    if not data["portfolio_data"]:
        risks.append("Unable to assess risks without portfolio data")
        return risks
    
    portfolio_data = data["portfolio_data"]
    
    # Check chain concentration
    if portfolio_data.get("chains_active", 0) == 1:
        risks.append("Single chain exposure increases vulnerability to chain-specific issues")
    
    # Check token concentration
    if portfolio_data.get("total_tokens", 0) <= 2:
        risks.append("Limited token diversity increases concentration risk")
    
    # Check for missing services
    for service, status in data["services_status"].items():
        if not status:
            if service == "exa":
                risks.append("Protocol discovery unavailable - may miss potential vulnerabilities")
    
    return risks