from fastapi import APIRouter, HTTPException, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from app.services.agno_agent import PortfolioManagementAgent, get_portfolio_summary
from app.services.external.exa_service import discover_defi_protocols
from app.api.v1.websocket import perform_portfolio_analysis, ConnectionManager
from typing import Optional, Dict, Any
import logging
import json
import asyncio
from datetime import datetime

router = APIRouter()
# Create a connection manager for WebSockets
ws_manager = ConnectionManager()
logger = logging.getLogger(__name__)

class ModelConfig(BaseModel):
    id: str
    config: Dict[str, Any]

class ToolConfig(BaseModel):
    type: str
    config: Dict[str, Any]

class PortfolioAnalysisRequest(BaseModel):
    prompt: str = Field(description="Prompt for portfolio analysis")
    model: Optional[ModelConfig] = None
    tools: Optional[list[ToolConfig]] = None
    instructions: Optional[str] = None
    add_datetime_to_instructions: Optional[bool] = None
    show_tool_calls: Optional[bool] = None
    markdown: Optional[bool] = None
    stream: Optional[bool] = None
    wallet_address: str = Field(description="User's wallet address")
    chain_id: Optional[int] = Field(default=None, description="Current chain ID")

class PortfolioMetric(BaseModel):
    name: str
    value: Any
    trend: Optional[str] = None

class PortfolioAction(BaseModel):
    action: str
    description: str
    priority: str

class PortfolioRisk(BaseModel):
    risk: str
    severity: str
    mitigation: Optional[str] = None

class PortfolioInsight(BaseModel):
    insight: str
    category: str
    importance: str

class PortfolioOpportunity(BaseModel):
    opportunity: str
    potential: str
    timeframe: str

class PortfolioAnalysisResponse(BaseModel):
    analysis: Dict[str, Any] = Field(
        default_factory=lambda: {
            "summary": "",
            "metrics": [],
            "actions": [],
            "riskScore": 0,
            "timestamp": datetime.utcnow().isoformat(),
            "risks": [],
            "keyInsights": [],
            "opportunities": []
        }
    )
    services_status: Dict[str, bool] = Field(
        default_factory=lambda: {
            "portfolio": False,
            "exa": False
        }
    )
    portfolio_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    type: str = "portfolio"

try:
    # Instantiate the agent once (will validate environment variables)
    from app.services.agno_agent import PortfolioManagementAgent
    portfolio_agent = PortfolioManagementAgent()
except Exception as e:
    logger.error(f"Failed to initialize portfolio agent: {str(e)}")
    portfolio_agent = None

def extract_exa_data_from_results(results: Dict) -> Dict[str, Any]:
    """Extract Exa search data from results dictionary."""
    exa_data = {
        "protocols_found": 0,
        "yield_opportunities": 0,
        "best_apy_found": "0.0%",
        "search_success": False,
        "protocols": []
    }

    try:
        if "defi_protocols" in results and results["defi_protocols"]:
            protocols_data = results["defi_protocols"]
            if isinstance(protocols_data, dict):
                exa_data["protocols_found"] = protocols_data.get("protocols_found", 0)
                exa_data["search_success"] = protocols_data.get("success", False)
                protocols = protocols_data.get("protocols", [])
                exa_data["protocols"] = protocols[:5]  # Limit to top 5

                # Extract best APY
                best_apy = 0.0
                for protocol in protocols:
                    yield_info = protocol.get("yield_info", {})
                    max_apy = yield_info.get("max_apy", 0)
                    if max_apy and max_apy > best_apy:
                        best_apy = max_apy

                exa_data["best_apy_found"] = f"{best_apy}%" if best_apy > 0 else "0.0%"
                exa_data["yield_opportunities"] = len([p for p in protocols if p.get("yield_info", {}).get("max_apy", 0) > 0])
    except Exception as e:
        logger.error(f"Error extracting Exa data: {e}")

    return exa_data

def extract_firecrawl_data_from_results(results: Dict) -> Dict[str, Any]:
    """Extract Firecrawl scraping data from results dictionary."""
    firecrawl_data = {
        "tvl_analyzed": "N/A",
        "security_audits": "Unverified",
        "live_rates": "No rates",
        "scraping_success": False,
        "protocols_scraped": 0
    }

    try:
        if "defi_positions" in results and results["defi_positions"]:
            defi_data = results["defi_positions"]
            if "yield_opportunities" in defi_data:
                opportunities = defi_data["yield_opportunities"]
                firecrawl_data["protocols_scraped"] = len(opportunities)
                firecrawl_data["scraping_success"] = firecrawl_data["protocols_scraped"] > 0
        
        # If there's protocol details data available, use it
        if "protocol_details" in results and results["protocol_details"]:
            protocol_data = results["protocol_details"]
            if isinstance(protocol_data, dict) and protocol_data.get("success", False):
                firecrawl_data["tvl_analyzed"] = protocol_data.get("tvl_analyzed", "N/A")
                firecrawl_data["security_audits"] = protocol_data.get("security_audits", "Unverified")
                firecrawl_data["live_rates"] = protocol_data.get("live_rates", "No rates")
    except Exception as e:
        logger.error(f"Error extracting Firecrawl data: {e}")

    return firecrawl_data

async def get_real_portfolio_data(wallet_address: str, chain_id: Optional[int] = None) -> Dict[str, Any]:
    """Get real portfolio data directly from blockchain."""
    try:
        # Call the actual portfolio service - no mocks
        portfolio_data = await get_portfolio_summary(wallet_address, chain_id)
        
        if "error" in portfolio_data:
            logger.error(f"Error getting portfolio data: {portfolio_data['error']}")
            return {
                "api_calls_made": 0,
                "portfolio_value": 0,
                "active_chains": 0,
                "token_count": 0,
                "risk_level": "Unknown",
                "error": portfolio_data['error']
            }
        
        # Format response consistently
        return {
            "api_calls_made": portfolio_data.get("api_calls_made", 1),
            "portfolio_value": portfolio_data.get("total_portfolio_value_usd", 0),
            "active_chains": portfolio_data.get("chains_active", 0),
            "token_count": portfolio_data.get("total_tokens", 0),
            "risk_level": f"{portfolio_data.get('risk_score', 0)}/5",
            "raw_data": portfolio_data  # Include full data for detailed analysis
        }
    except Exception as e:
        logger.error(f"Error getting portfolio data: {str(e)}")
        return {
            "api_calls_made": 0,
            "portfolio_value": 0,
            "active_chains": 0,
            "token_count": 0,
            "risk_level": "Error",
            "error": str(e)
        }

def parse_analysis_text(text: str) -> Dict[str, Any]:
    """Parse analysis text to extract structured data"""
    try:
        result = {
            "summary": "",
            "metrics": [],
            "actions": [],
            "risks": [],
            "keyInsights": [],
            "opportunities": [],
            "riskScore": 0
        }

        # Extract summary (first paragraph or executive summary section)
        lines = text.split('\n')
        summary_lines = []
        for line in lines[:10]:  # First 10 lines for summary
            if line.strip() and not line.startswith('#'):
                summary_lines.append(line.strip())
        result["summary"] = ' '.join(summary_lines)[:300] + "..." if len(' '.join(summary_lines)) > 300 else ' '.join(summary_lines)

        # Extract risks (look for risk-related keywords)
        risk_keywords = ['risk', 'danger', 'warning', 'caution', 'volatile']
        for line in lines:
            if any(keyword in line.lower() for keyword in risk_keywords) and line.strip():
                result["risks"].append(line.strip())

        # Extract insights (look for insight-related keywords)
        insight_keywords = ['insight', 'analysis', 'finding', 'observation']
        for line in lines:
            if any(keyword in line.lower() for keyword in insight_keywords) and line.strip():
                result["keyInsights"].append(line.strip())

        # Extract opportunities (look for opportunity-related keywords)
        opportunity_keywords = ['opportunity', 'potential', 'recommend', 'suggest']
        for line in lines:
            if any(keyword in line.lower() for keyword in opportunity_keywords) and line.strip():
                result["opportunities"].append(line.strip())

        return result
    except Exception as e:
        logger.error(f"Error parsing analysis text: {str(e)}")
        return {
            "summary": text[:300] + "..." if len(text) > 300 else text,
            "metrics": [],
            "actions": [],
            "risks": [],
            "keyInsights": [],
            "opportunities": [],
            "riskScore": 0
        }

def format_streaming_response(generator):
    """Format streaming response for frontend consumption"""
    try:
        accumulated_text = ""
        for chunk in generator:
            accumulated_text += str(chunk)

            # Create a structured response
            response = PortfolioAnalysisResponse(
                analysis={
                    "summary": accumulated_text,
                    "metrics": [],  # You could parse metrics from the text
                    "actions": [],  # Parse actions from text
                    "riskScore": 0,  # Calculate based on content
                    "timestamp": datetime.utcnow().isoformat(),
                    "risks": [],  # Parse risks from text
                    "keyInsights": [],  # Parse insights from text
                    "opportunities": []  # Parse opportunities from text
                },
                type="portfolio"
            )

            yield f"data: {json.dumps(response.dict())}\n\n"
    except Exception as e:
        logger.error(f"Error in streaming response: {str(e)}")
        yield f"data: {json.dumps({'error': str(e), 'type': 'error'})}\n\n"

@router.post("/portfolio-analysis")
async def analyze_portfolio(request: PortfolioAnalysisRequest):
    try:
        # Validate request
        if not request.wallet_address:
            raise HTTPException(
                status_code=400,
                detail="Wallet address is required for portfolio analysis"
            )

        # Create response dict for analysis results
        response_data = {
            "analysis": {
                "summary": "Analyzing portfolio...",
                "metrics": [],
                "actions": [],
                "riskScore": 0,
                "timestamp": datetime.utcnow().isoformat(),
                "risks": [],
                "keyInsights": [],
                "opportunities": []
            },
            "services_status": {
                "portfolio": False,
                "exa": False
            },
            "type": "portfolio",
            "progress": "Starting analysis..."
        }
        
        # Step 1: Get portfolio data first (most important)
        logger.info(f"Starting fast analysis for wallet: {request.wallet_address}, chain: {request.chain_id}")

        response_data["progress"] = "Fetching portfolio data..."
        portfolio_data = await get_real_portfolio_data(request.wallet_address, request.chain_id)

        if "error" in portfolio_data:
            response_data["analysis"]["summary"] = f"Error retrieving portfolio data: {portfolio_data['error']}"
            response_data["services_status"]["portfolio"] = False
        else:
            response_data["services_status"]["portfolio"] = True
            response_data["portfolio_data"] = portfolio_data
            response_data["progress"] = "Portfolio data retrieved, analyzing..."

            # Update response with real portfolio data
            if portfolio_data["portfolio_value"] > 0:
                response_data["analysis"]["summary"] = f"Portfolio value: ${portfolio_data['portfolio_value']:,.2f} across {portfolio_data['active_chains']} chains with {portfolio_data['token_count']} tokens."
                response_data["analysis"]["riskScore"] = float(portfolio_data["risk_level"].split("/")[0])

                # Add metrics based on real data
                if "raw_data" in portfolio_data:
                    raw_data = portfolio_data["raw_data"]

                    # Add metrics
                    response_data["analysis"]["metrics"] = [
                        {"name": "Total Value", "value": f"${raw_data.get('total_portfolio_value_usd', 0):,.2f}", "trend": None},
                        {"name": "Native Value", "value": f"${raw_data.get('native_value_usd', 0):,.2f}", "trend": None},
                        {"name": "Token Value", "value": f"${raw_data.get('token_value_usd', 0):,.2f}", "trend": None},
                        {"name": "Active Chains", "value": raw_data.get('chains_active', 0), "trend": None},
                        {"name": "Token Count", "value": raw_data.get('total_tokens', 0), "trend": None}
                    ]

                    # Add risks based on real data
                    if raw_data.get('chains_active', 0) < 2:
                        response_data["analysis"]["risks"].append("Low chain diversification")

                    if raw_data.get('total_tokens', 0) < 3:
                        response_data["analysis"]["risks"].append("Limited token diversification")

        # Step 2: Get relevant DeFi protocols based on actual portfolio holdings (no Firecrawl)
        response_data["progress"] = "Finding relevant DeFi opportunities..."

        # Note: Firecrawl removed from portfolio analysis as it's not suitable for this use case

        # Try Exa API for protocol discovery based on user's holdings
        try:
            if portfolio_data["portfolio_value"] > 0 and "raw_data" in portfolio_data:
                raw_data = portfolio_data["raw_data"]

                # Build a targeted query based on what the user actually holds
                query_parts = []

                # Check if they have stablecoins or significant token value
                if raw_data.get('token_value_usd', 0) > 100:
                    query_parts.append("stablecoin yield farming")

                # Check if they're on multiple chains
                if raw_data.get('chains_active', 0) > 1:
                    query_parts.append("cross-chain defi")

                # Default to general DeFi if no specific holdings
                if not query_parts:
                    query_parts.append("defi lending borrowing")

                query = " ".join(query_parts)
                logger.info(f"Searching for DeFi protocols with query: {query}")

                # Get relevant protocols with timeout
                from app.services.external.exa_service import discover_defi_protocols

                exa_data = await asyncio.wait_for(
                    discover_defi_protocols(query, max_results=3, timeout=15),
                    timeout=20.0
                )

                # Check if we got valid data
                if isinstance(exa_data, dict) and exa_data.get("search_success"):
                    response_data["services_status"]["exa"] = True
                    # Add top protocols found
                    protocols = exa_data.get("protocols", [])[:2]
                    for protocol in protocols:
                        if protocol.get("apy") != "Unknown":
                            response_data["analysis"]["opportunities"].append({
                                "opportunity": f"Consider {protocol['name']}",
                                "potential": f"APY: {protocol['apy']}",
                                "timeframe": "Current"
                            })
                else:
                    response_data["services_status"]["exa"] = False

        except asyncio.TimeoutError:
            logger.warning("Exa API timed out, using basic analysis only")
            response_data["services_status"]["exa"] = False
        except Exception as e:
            logger.error(f"Error getting Exa data: {e}")
            response_data["services_status"]["exa"] = False

        # Add basic opportunities based on portfolio data (always available)
        if response_data["services_status"]["portfolio"] and portfolio_data["portfolio_value"] > 0:
            if "raw_data" in portfolio_data:
                raw_data = portfolio_data["raw_data"]

                # Suggest stablecoin yield if they have significant token value
                if raw_data.get('token_value_usd', 0) > 100:
                    response_data["analysis"]["opportunities"].append({
                        "opportunity": "Consider stablecoin yield strategies",
                        "potential": "3-8% APY typically available",
                        "timeframe": "Current"
                    })

                # Suggest diversification if low chain count
                if raw_data.get('chains_active', 0) < 2:
                    response_data["analysis"]["opportunities"].append({
                        "opportunity": "Multi-chain diversification",
                        "potential": "Risk reduction",
                        "timeframe": "Medium-term"
                    })

                # Add insights based on portfolio composition
                if portfolio_data["portfolio_value"] > 1000:
                    response_data["analysis"]["keyInsights"].append("Portfolio size suitable for DeFi strategies")
                    if raw_data.get('chains_active', 0) >= 2:
                        response_data["analysis"]["keyInsights"].append("Good multi-chain diversification")
                else:
                    response_data["analysis"]["keyInsights"].append("Consider accumulating more assets before complex DeFi strategies")

        if request.stream:
            return StreamingResponse(
                format_streaming_response(response_data["analysis"]["summary"]),
                media_type="text/event-stream"
            )

        # Finalize the response
        response_data["progress"] = "Analysis complete"

        # Create final summary combining all data
        unavailable_services = []
        for service, status in response_data["services_status"].items():
            if not status:
                unavailable_services.append(service)

        if unavailable_services:
            service_warning = f"\n\nNote: Limited data from: {', '.join(unavailable_services)}."
            if response_data["analysis"]["summary"]:
                response_data["analysis"]["summary"] += service_warning
            else:
                response_data["analysis"]["summary"] = f"Basic portfolio analysis completed. Limited data from: {', '.join(unavailable_services)}."
        
        # Add API call count to be transparent about real usage
        api_calls = 0
        if response_data["services_status"]["portfolio"]:
            api_calls += response_data.get("portfolio_data", {}).get("api_calls_made", 1)
        if response_data["services_status"]["exa"]:
            api_calls += 1  # One call to Exa API
        if response_data["services_status"]["firecrawl"]:
            api_calls += 1  # One call to Firecrawl API
            
        response_data["api_calls"] = api_calls
        
        # Create final response object
        response = PortfolioAnalysisResponse(**response_data)
        
        return response

    except HTTPException:
        raise
    except ValueError as e:
        # Handle configuration errors
        raise HTTPException(
            status_code=500,
            detail=f"Configuration error: {str(e)}"
        )
    except Exception as e:
        logger.exception("Error in portfolio analysis")
        # Return an error response with service status information
        error_response = PortfolioAnalysisResponse(
            analysis={
                "summary": f"Portfolio analysis failed: {str(e)}",
                "metrics": [],
                "actions": [],
                "riskScore": 0,
                "timestamp": datetime.utcnow().isoformat(),
                "risks": ["Analysis failed due to technical error"],
                "keyInsights": [],
                "opportunities": []
            },
            services_status={
                "portfolio": False,
                "exa": False
            },
            error=str(e)
        )
        return error_response