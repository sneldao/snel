from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Dict, Any, Optional, List, Callable, Awaitable
import logging
import time
import asyncio
from datetime import datetime

# Import services
from app.services.portfolio.portfolio_service import Web3Helper
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
            
        # Keep connection alive by handling messages in a loop
        connected = True
        
        # Add a global timeout for the entire analysis process
        try:
            # Start the analysis process with callback wrapped properly
            result = await asyncio.wait_for(
                perform_portfolio_analysis(wallet_address, chain_id, progress_callback=send_progress),
                timeout=60.0  # 60 second timeout for the entire analysis
            )
            logger.info(f"Portfolio analysis completed for wallet: {wallet_address}")
            # The connection will remain open until client disconnects
        except asyncio.TimeoutError:
            logger.error(f"Portfolio analysis timed out for wallet: {wallet_address}")
            await manager.send_error(wallet_address, "Analysis timed out. Please try again.")
            # Don't disconnect - just return an error
            await manager.send_data(wallet_address, {
                "summary": "Analysis timed out. Please try again with fewer tokens or a single chain.",
                "services_status": {"portfolio": False, "exa": False, "firecrawl": None},
                "error": "Timeout",
                "timestamp": datetime.utcnow().isoformat()
            })
            
        # Keep the connection open and wait for client to disconnect
        try:
            # Wait for client to disconnect
            while connected:
                try:
                    # Ping to keep connection alive and check if client is still there
                    await websocket.receive_text()
                except WebSocketDisconnect:
                    connected = False
                    logger.info(f"WebSocket client disconnected: {wallet_address}")
                    break
        except Exception as e:
            logger.exception(f"Error in WebSocket keep-alive: {str(e)}")
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected during initialization: {wallet_address}")
        manager.disconnect(wallet_address)
    except Exception as e:
        logger.exception(f"Error in portfolio websocket: {str(e)}")
        await manager.send_error(wallet_address, f"Analysis failed: {str(e)}")
        manager.disconnect(wallet_address)

async def perform_portfolio_analysis(
    wallet_address: str, 
    chain_id: Optional[int] = None,
    progress_callback: Optional[ProgressCallback] = None,
    force_refresh: bool = False
) -> Dict[str, Any]:
    """Perform full portfolio analysis with real-time progress updates"""
    from functools import partial
    
    service_results = {
        "portfolio_data": None,
        "exa_data": None,

        "services_status": {
            "portfolio": False,  # Using portfolio instead of web3 for consistency
            "exa": False,
            "firecrawl": None  # Set to None to indicate N/A for portfolio analysis
        },
        "timestamp": datetime.utcnow().isoformat(),
        "cached": False
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
            
            # Call get_real_portfolio_data to get data in the format expected by stablecoin analysis
            from app.api.v1.agno import get_real_portfolio_data
            try:
                # First check if we need fresh data or can use cached data
                if progress_callback:
                    await progress_callback("Checking portfolio data cache", 10, "Looking for recent analysis data")

                # Shorter timeout specifically for portfolio data to prevent hanging
                portfolio_data = await asyncio.wait_for(
                    get_real_portfolio_data(wallet_address, chain_id, force_refresh=force_refresh),
                    timeout=30.0  # 30 second timeout for portfolio data
                )

                if "error" in portfolio_data:
                    if progress_callback:
                        await progress_callback("Error retrieving blockchain data", 20, portfolio_data["error"])
                    service_results["services_status"]["portfolio"] = False
                else:
                    service_results["portfolio_data"] = portfolio_data
                    service_results["services_status"]["portfolio"] = True
                    service_results["cached"] = portfolio_data.get("cached", False)
                    
                    # Show slightly different progress message for cached data
                    if portfolio_data.get("cached", False):
                        if progress_callback:
                            await progress_callback("Using cached blockchain data", 30,
                                              f"Found {portfolio_data.get('token_count', 0)} tokens across {portfolio_data.get('active_chains', 0)} chains (cache age: {portfolio_data.get('cache_age', 'unknown')})")
                    else:
                        if progress_callback:
                            await progress_callback("Blockchain data retrieved successfully", 30,
                                              f"Found {portfolio_data.get('token_count', 0)} tokens across {portfolio_data.get('active_chains', 0)} chains")
            except asyncio.TimeoutError:
                logger.warning(f"Portfolio data retrieval timed out for {wallet_address}")
                if progress_callback:
                    await progress_callback("Blockchain data retrieval timed out", 20, "Too many tokens or slow API responses")
                service_results["services_status"]["portfolio"] = False
                service_results["portfolio_data"] = {"error": "Timeout", "wallet_address": wallet_address}
        except Exception as e:
            logger.error(f"Portfolio data retrieval failed: {str(e)}")
            if progress_callback:
                await progress_callback("Blockchain data retrieval failed", 20, str(e))
            service_results["services_status"]["portfolio"] = False
        
        # 2. Get protocol discovery data from Exa
        try:
            if progress_callback:
                await progress_callback("Discovering DeFi protocols", 40, "Querying Exa API for DeFi protocols")
            
            # Build query based on portfolio data
            query = f"DeFi protocols for wallet {wallet_address}"
            if service_results["portfolio_data"] and "error" not in service_results["portfolio_data"]:
                # Extract token symbols for better search from raw_data
                tokens = []
                raw_data = service_results["portfolio_data"].get("raw_data", {})
                for chain_data in raw_data.get("token_balances", {}).values():
                    for token in chain_data.get("tokens", []):
                        if token.get("symbol"):
                            tokens.append(token.get("symbol"))

                if tokens:
                    query += f" with {', '.join(tokens[:5])} tokens"
            
            # Get real Exa data with timeout
            try:
                exa_data = await asyncio.wait_for(
                    discover_defi_protocols(query),
                    timeout=15.0  # 15 second timeout for Exa data
                )
            
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
            except asyncio.TimeoutError:
                logger.warning(f"Exa protocol discovery timed out for {wallet_address}")
                if progress_callback:
                    await progress_callback("Protocol discovery timed out", 45, "Continuing with partial analysis")
                service_results["services_status"]["exa"] = False
                service_results["exa_data"] = {"error": "Timeout", "protocols_found": 0}
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
    if not data["portfolio_data"] or "error" in data["portfolio_data"]:
        error_msg = data["portfolio_data"].get("error", "unknown error") if data["portfolio_data"] else "unknown error"
        if error_msg == "Timeout":
            return "Your portfolio analysis timed out. You may have too many tokens or there might be API rate limiting issues. Try analyzing a specific chain or try again later."
        return f"We couldn't retrieve your portfolio data ({error_msg}). Please check your wallet connection and try again."
    
    # Build summary from actual data using new field names
    portfolio_data = data["portfolio_data"]
    total_value = portfolio_data.get("portfolio_value", 0)
    chain_count = portfolio_data.get("active_chains", 0)
    token_count = portfolio_data.get("token_count", 0)

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
        if status is False:  # Only include services that are False, not None
            unavailable_services.append(service)
    
    if unavailable_services:
        summary += f"Note: {', '.join(unavailable_services)} {'services were' if len(unavailable_services) > 1 else 'service was'} unavailable during analysis."
    
    return summary

def extract_metrics(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract metrics from available data"""
    metrics = []

    if data.get("portfolio_data"):
        portfolio_data = data["portfolio_data"]

        # Use the new data structure field names
        if "portfolio_value" in portfolio_data:
            metrics.append({
                "label": "Total Portfolio Value",
                "value": portfolio_data["portfolio_value"],
                "type": "currency"
            })

        # Extract from raw_data if available
        raw_data = portfolio_data.get("raw_data", {})
        if raw_data:
            if "native_value_usd" in raw_data:
                metrics.append({
                    "label": "Native Token Value",
                    "value": raw_data["native_value_usd"],
                    "type": "currency"
                })

            if "token_value_usd" in raw_data:
                metrics.append({
                    "label": "ERC20 Token Value",
                    "value": raw_data["token_value_usd"],
                    "type": "currency"
                })

        if "active_chains" in portfolio_data:
            metrics.append({
                "label": "Active Chains",
                "value": portfolio_data["active_chains"],
                "type": "number"
            })

        if "token_count" in portfolio_data:
            metrics.append({
                "label": "Total Tokens",
                "value": portfolio_data["token_count"],
                "type": "number"
            })

        if "risk_level" in portfolio_data:
            # Extract numeric risk score from "X/5" format
            risk_level = portfolio_data["risk_level"]
            if "/" in str(risk_level):
                risk_score = float(str(risk_level).split("/")[0])
                metrics.append({
                    "label": "Risk Score",
                    "value": risk_score,
                    "type": "number"
                })

    return metrics

def generate_actions(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate action recommendations based on analysis data"""
    actions = []
    
    # Only generate actions if we have sufficient data
    if not data.get("portfolio_data") or not data["services_status"]["portfolio"]:
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
        if not status and service != "firecrawl":  # Ignore firecrawl service
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
    
    # Add stablecoin-focused recommendations (prioritize over chain diversification)
    if "raw_data" in portfolio_data:
        from app.api.v1.agno import analyze_stablecoin_allocation
        stablecoin_allocation = analyze_stablecoin_allocation(portfolio_data["raw_data"])

        # Debug logging
        logger.info(f"Stablecoin allocation analysis: {stablecoin_allocation}")
        logger.info(f"Portfolio value: {portfolio_data.get('portfolio_value', 0)}")

        # Recommend stablecoin diversification if allocation is low (primary recommendation)
        if stablecoin_allocation["percentage"] < 30 and portfolio_data.get("portfolio_value", 0) > 500:
            logger.info(f"Adding stablecoin diversification recommendation. Current allocation: {stablecoin_allocation['percentage']:.1f}%")
            actions.append({
                "id": "diversify_into_stablecoins",
                "description": "Diversify into stablecoins to reduce risk",
                "type": "rebalance",
                "impact": {
                    "risk": -2.0
                },
                "details": f"Currently {stablecoin_allocation['percentage']:.1f}% stablecoins. Consider swapping some ETH to USDC for stability."
            })

        # Recommend stablecoin yield strategies if they have good allocation
        elif stablecoin_allocation["percentage"] >= 30:
            logger.info("Adding stablecoin yield optimization recommendation")
            actions.append({
                "id": "optimize_stablecoin_yield",
                "description": "Optimize stablecoin yield with DeFi strategies (3-8% APY available)",
                "type": "optimize",
                "impact": {
                    "yield": 1.5
                }
            })
        else:
            logger.info(f"No stablecoin recommendation added. Percentage: {stablecoin_allocation['percentage']:.1f}%, Portfolio value: {portfolio_data.get('portfolio_value', 0)}")

    # Secondary recommendation: chain diversification (only if no stablecoin recommendation)
    if len(actions) == 0 and portfolio_data.get("active_chains", 0) == 1:
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
    """Identify portfolio risks based on analysis data"""
    risks = []
    
    if not data.get("portfolio_data"):
        risks.append("Unable to assess risks without portfolio data")
        return risks
    
    portfolio_data = data["portfolio_data"]

    # Check chain concentration using new field names
    if portfolio_data.get("active_chains", 0) == 1:
        risks.append("Single chain exposure increases vulnerability to chain-specific issues")

    # Check token concentration using new field names
    if portfolio_data.get("token_count", 0) <= 2:
        risks.append("Limited token diversity increases concentration risk")
    
    # Check for missing services
    for service, status in data["services_status"].items():
        if not status:
            if service == "exa":
                risks.append("Protocol discovery unavailable - may miss potential vulnerabilities")
    
    return risks