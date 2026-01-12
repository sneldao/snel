"""
SNEL Multi-Platform Orchestrator
ENHANCEMENT FIRST: Unified service layer across web app + Coral ecosystem
RELIABLE: Shared resource pooling, graceful fallbacks, performance monitoring
PERFORMANT: Connection pooling, request deduplication, intelligent caching
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum
import json
from concurrent.futures import ThreadPoolExecutor
import weakref

# ENHANCEMENT: Import existing SNEL services
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.portfolio.portfolio_service import Web3Helper
from config.settings import Settings
from openai import AsyncOpenAI
# Payment imports
from app.domains.payment_actions.models import CreatePaymentActionRequest, PaymentActionType
from app.domains.payment_actions.service import get_payment_action_service
from app.domains.payment_actions.executor import get_payment_executor, ExecutionStatus

logger = logging.getLogger(__name__)

class Platform(Enum):
    """Platform types for multi-channel operation"""
    WEB_APP = "web_app"
    CORAL_AGENT = "coral_agent" 
    LINE_MINI_DAPP = "line_mini_dapp"
    API = "api"

@dataclass
class RequestMetrics:
    """Request performance and reliability metrics"""
    platform: Platform
    operation: str
    start_time: float
    duration: float
    success: bool
    user_id: Optional[str] = None
    error: Optional[str] = None

@dataclass
class ServiceHealth:
    """Service health monitoring"""
    service_name: str
    is_healthy: bool
    last_check: float
    response_time: float
    error_rate: float
    request_count: int

class SNELOrchestrator:
    """
    Multi-Platform Service Orchestrator for SNEL
    ENHANCEMENT: Unified backend serving web app, Coral agents, LINE mini-dApp
    RELIABLE: Health monitoring, circuit breakers, graceful degradation  
    PERFORMANT: Connection pooling, caching, request deduplication
    """
    
    def __init__(self):
        logger.info("[ORCHESTRATOR] Initializing SNEL Multi-Platform Orchestrator...")
        
        # PERFORMANCE: Shared service instances with connection pooling
        # Initialize settings and existing SNEL services
        self._settings = Settings()
        
        # ENHANCEMENT: Initialize services with graceful error handling
        self._service_pool = {}
        
        # Initialize OpenAI if API key available
        if os.getenv("OPENAI_API_KEY"):
            self._service_pool['openai'] = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        else:
            logger.warning("OpenAI API key not found - AI features will be limited")
            self._service_pool['openai'] = None
        
        # Initialize Web3Helper (doesn't require API key)
        self._service_pool['web3_helper'] = Web3Helper(self._settings.chains.supported_chains)
        
        # Initialize Axelar service
        try:
            from services.axelar_service import AxelarService
            self._service_pool['axelar'] = AxelarService()
        except Exception as e:
            logger.warning(f"Axelar service initialization failed: {e}")
            self._service_pool['axelar'] = None
        
        # Initialize command processor if brian client is available
        self._service_pool['command_processor'] = None
        if self._service_pool.get('brian'):
            try:
                from services.command_processor import CommandProcessor
                command_processor = CommandProcessor(
                    brian_client=self._service_pool['brian'],
                    settings=self._settings
                )
                self._service_pool['command_processor'] = command_processor
            except Exception as e:
                logger.warning(f"Command processor initialization failed: {e}")

        # Initialize Payment Services (Async init handling in methods)
        self._service_pool['payment_service'] = None
        self._service_pool['payment_executor'] = None
        
        # RELIABLE: Health monitoring and circuit breakers
        self._service_health: Dict[str, ServiceHealth] = {}
        self._circuit_breakers: Dict[str, bool] = {}
        
        # PERFORMANT: Request deduplication and caching
        self._active_requests: Dict[str, asyncio.Task] = {}
        self._response_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = 60  # 1 minute default
        
        # USER DELIGHT: Platform-specific optimizations
        self._platform_configs = {
            Platform.WEB_APP: {
                'timeout': 30,
                'detailed_responses': True,
                'include_charts': True,
                'cache_portfolio': True
            },
            Platform.CORAL_AGENT: {
                'timeout': 45,
                'detailed_responses': True,
                'include_collaboration_data': True,
                'cache_analysis': True
            },
            Platform.LINE_MINI_DAPP: {
                'timeout': 15,
                'detailed_responses': False,
                'mobile_optimized': True,
                'cache_quotes': True
            },
            Platform.API: {
                'timeout': 20,
                'detailed_responses': True,
                'include_metadata': True,
                'cache_all': False
            }
        }
        
        # PERFORMANCE: Metrics collection
        self._metrics: List[RequestMetrics] = []
        self._executor = ThreadPoolExecutor(max_workers=10)
        
        # Initialize health monitoring
        asyncio.create_task(self._health_monitor())
        
        logger.info("[ORCHESTRATOR] SNEL Multi-Platform Orchestrator initialized successfully")
    
    def _get_chain_id_from_name(self, chain_name: str) -> int:
        """Convert chain name to chain ID"""
        name_to_id = {
            'ethereum': 1, 'eth': 1,
            'base': 8453,
            'arbitrum': 42161, 'arb': 42161,
            'optimism': 10, 'opt': 10,
            'polygon': 137, 'matic': 137,
            'avalanche': 43114, 'avax': 43114,
            'bsc': 56, 'binance': 56,
            'scroll': 534352,
            'linea': 59144,
            'mantle': 5000,
            'blast': 81457,
            'zksync': 324,
            'mode': 34443,
            'gnosis': 100,
            'taiko': 167000
        }
        return name_to_id.get(chain_name.lower(), 1)  # Default to Ethereum
    
    async def _health_monitor(self):
        """RELIABLE: Continuous health monitoring of all services"""
        while True:
            try:
                for service_name, service in self._service_pool.items():
                    start_time = time.time()
                    
                    try:
                        # Simple health check (adapt per service)
                        if hasattr(service, 'health_check'):
                            await service.health_check()
                        
                        response_time = time.time() - start_time
                        
                        # Update health status
                        if service_name not in self._service_health:
                            self._service_health[service_name] = ServiceHealth(
                                service_name=service_name,
                                is_healthy=True,
                                last_check=time.time(),
                                response_time=response_time,
                                error_rate=0.0,
                                request_count=0
                            )
                        else:
                            health = self._service_health[service_name]
                            health.is_healthy = True
                            health.last_check = time.time()
                            health.response_time = response_time
                            
                        # Reset circuit breaker if healthy
                        self._circuit_breakers[service_name] = False
                        
                    except Exception as e:
                        logger.warning(f"[ORCHESTRATOR] Health check failed for {service_name}: {e}")
                        
                        if service_name in self._service_health:
                            self._service_health[service_name].is_healthy = False
                            self._service_health[service_name].last_check = time.time()
                        
                        # Trigger circuit breaker if multiple failures
                        self._circuit_breakers[service_name] = True
                
                await asyncio.sleep(30)  # Health check every 30 seconds
                
            except Exception as e:
                logger.error(f"[ORCHESTRATOR] Health monitor error: {e}")
                await asyncio.sleep(60)
    
    def _get_cache_key(self, operation: str, params: Dict[str, Any], platform: Platform) -> str:
        """Generate cache key for request deduplication"""
        cache_data = {
            'operation': operation,
            'params': params,
            'platform': platform.value
        }
        return hash(json.dumps(cache_data, sort_keys=True))
    
    def _is_cached(self, cache_key: str) -> bool:
        """PERFORMANCE: Check if response is cached and fresh"""
        if cache_key not in self._response_cache:
            return False
            
        cached_data = self._response_cache[cache_key]
        if time.time() - cached_data['timestamp'] > self._cache_ttl:
            del self._response_cache[cache_key]
            return False
            
        return True
    
    def _get_cached_response(self, cache_key: str) -> Any:
        """PERFORMANCE: Retrieve cached response"""
        return self._response_cache[cache_key]['data']
    
    def _cache_response(self, cache_key: str, data: Any):
        """PERFORMANCE: Cache successful response"""
        self._response_cache[cache_key] = {
            'data': data,
            'timestamp': time.time()
        }
    
    async def _deduplicate_request(self, cache_key: str, coro) -> Any:
        """PERFORMANCE: Request deduplication to prevent duplicate API calls"""
        if cache_key in self._active_requests:
            logger.info(f"[ORCHESTRATOR] Deduplicating request: {cache_key}")
            return await self._active_requests[cache_key]
        
        # Create and store the task
        task = asyncio.create_task(coro)
        self._active_requests[cache_key] = task
        
        try:
            result = await task
            return result
        finally:
            # Clean up completed task
            if cache_key in self._active_requests:
                del self._active_requests[cache_key]
    
    async def execute_defi_operation(
        self, 
        operation: str, 
        parameters: Dict[str, Any], 
        platform: Platform,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        ENHANCED: Execute DeFi operation with platform-specific optimizations
        USER DELIGHT: Tailored responses per platform for optimal experience
        RELIABLE: Circuit breakers, fallbacks, comprehensive error handling
        PERFORMANT: Caching, deduplication, timeout management
        """
        start_time = time.time()
        platform_config = self._platform_configs[platform]
        
        logger.info(f"[ORCHESTRATOR] Executing {operation} for {platform.value}")
        
        try:
            # PERFORMANCE: Check cache first
            cache_key = self._get_cache_key(operation, parameters, platform)
            
            if self._is_cached(cache_key) and platform_config.get('cache_all', True):
                logger.info(f"[ORCHESTRATOR] Cache hit for {operation}")
                cached_response = self._get_cached_response(cache_key)
                
                # Record metrics
                self._record_metrics(RequestMetrics(
                    platform=platform,
                    operation=operation,
                    start_time=start_time,
                    duration=time.time() - start_time,
                    success=True,
                    user_id=user_id
                ))
                
                return self._format_response(cached_response, platform, from_cache=True)
            
            # Route to appropriate operation with deduplication
            if operation.lower() in ['swap', 'trade', 'exchange']:
                result = await self._deduplicate_request(
                    cache_key, 
                    self._execute_swap(parameters, platform, platform_config)
                )
            elif operation.lower() in ['pay', 'send', 'payment', 'transfer']:
                 # Payments are critical, deduplicate but prioritize
                result = await self._deduplicate_request(
                    cache_key,
                    self._execute_payment(parameters, platform, platform_config)
                )
            elif operation.lower() in ['bridge']:
                result = await self._deduplicate_request(
                    cache_key,
                    self._execute_bridge(parameters, platform, platform_config)
                )
            elif operation.lower() in ['analyze', 'portfolio', 'balance']:
                result = await self._deduplicate_request(
                    cache_key,
                    self._analyze_portfolio(parameters, platform, platform_config)
                )
            elif operation.lower() in ['research', 'protocol']:
                result = await self._deduplicate_request(
                    cache_key,
                    self._research_protocol(parameters, platform, platform_config)
                )
            else:
                result = await self._process_natural_language(operation, parameters, platform, platform_config)
            
            # PERFORMANCE: Cache successful results
            if platform_config.get('cache_quotes') or platform_config.get('cache_analysis'):
                self._cache_response(cache_key, result)
            
            # Record successful metrics
            self._record_metrics(RequestMetrics(
                platform=platform,
                operation=operation,
                start_time=start_time,
                duration=time.time() - start_time,
                success=True,
                user_id=user_id
            ))
            
            return self._format_response(result, platform)
            
        except Exception as e:
            error_msg = f"DeFi operation failed: {str(e)}"
            logger.error(f"[ORCHESTRATOR] {error_msg}")
            
            # Record failure metrics
            self._record_metrics(RequestMetrics(
                platform=platform,
                operation=operation,
                start_time=start_time,
                duration=time.time() - start_time,
                success=False,
                user_id=user_id,
                error=str(e)
            ))
            
            return self._format_error_response(error_msg, platform)
    
    async def _execute_payment(self, params: Dict[str, Any], platform: Platform, config: Dict[str, Any]) -> Dict[str, Any]:
        """ENHANCED: Platform-optimized payment execution with MNEE integration"""
        try:
            # Lazy load services
            payment_service = await get_payment_action_service()
            payment_executor = await get_payment_executor()
            
            # Extract parameters
            recipient = params.get('recipient', params.get('to_address', params.get('to')))
            amount = params.get('amount')
            token = params.get('token', 'MNEE')  # Default to MNEE
            chain_id = int(params.get('chain_id', 1))
            wallet_address = params.get('wallet_address', params.get('from_address'))
            schedule = params.get('schedule')
            name = params.get('name', f"Payment to {recipient[:6]}...")
            
            if not all([recipient, amount, wallet_address]):
                raise ValueError("Missing required parameters: recipient, amount, wallet_address")
                
            # Create payment action
            action_request = CreatePaymentActionRequest(
                name=name,
                action_type=PaymentActionType.RECURRING if schedule else PaymentActionType.SINGLE,
                recipient_address=recipient,
                amount=str(amount),
                token=token,
                chain_id=chain_id,
                schedule=schedule,
                metadata={"platform": platform.value}
            )
            
            # 1. Store action (Persistent)
            action = await payment_service.create_action(wallet_address, action_request)
            
            # 2. Execute (Build Tx) - Pauses at AWAITING_SIGNATURE
            execution_result = await payment_executor.execute_action(
                action=action,
                from_wallet=wallet_address,
                signing_function=None  # No signer = return raw tx for user
            )
            
            if execution_result.status == ExecutionStatus.FAILED:
                raise Exception(execution_result.error_message)
                
            # 3. Format Response for User Signing
            base_result = {
                'operation': 'payment',
                'action_id': action.id,
                'status': 'awaiting_signature',
                'payment_details': {
                    'recipient': recipient,
                    'amount': amount,
                    'token': token,
                    'chain_id': chain_id,
                    'fee_mnee': execution_result.metadata.get('quote', {}).get('estimated_fee_mnee', 'Unknown')
                },
                'transaction_data': execution_result.metadata.get('transaction'),
                'next_steps': 'Sign the transaction data to complete payment.'
            }
            
            if config.get('detailed_responses'):
                base_result['mnee_quote'] = execution_result.metadata.get('quote')
                
            if platform == Platform.LINE_MINI_DAPP:
                base_result['mobile_deeplink'] = f"snel://sign?action_id={action.id}"
                
            return base_result

        except Exception as e:
            logger.error(f"Payment execution failed: {e}")
            raise e

    async def _execute_swap(self, params: Dict[str, Any], platform: Platform, config: Dict[str, Any]) -> Dict[str, Any]:
        """ENHANCED: Platform-optimized swap execution using existing SNEL services"""
        
        # Check if Brian service is available
        if not self._service_pool.get('brian'):
            raise Exception("Brian service not available - API key may be missing")
        
        # RELIABLE: Circuit breaker check
        if self._circuit_breakers.get('brian', False):
            raise Exception("Brian service temporarily unavailable")
        
        try:
            from_token = params.get('from_token', params.get('token_in'))
            to_token = params.get('to_token', params.get('token_out'))
            amount = params.get('amount')
            chain_id = params.get('chain_id', 1)
            wallet_address = params.get('wallet_address', params.get('address'))
            
            if not all([from_token, to_token, amount]):
                raise ValueError("Missing required parameters: from_token, to_token, amount")
            
            if not wallet_address:
                raise ValueError("Wallet address is required for swap quotes")
            
            # Use existing SNEL Brian service
            brian_client = self._service_pool['brian']
            
            # Execute with timeout
            quote_result = await asyncio.wait_for(
                brian_client.get_swap_transaction(
                    from_token=from_token,
                    to_token=to_token,
                    amount=float(amount),
                    chain_id=chain_id,
                    wallet_address=wallet_address
                ),
                timeout=config['timeout']
            )
            
            # Check if Brian returned an error
            if quote_result.get('error'):
                raise Exception(quote_result.get('message', 'Swap quote failed'))
            
            # USER DELIGHT: Platform-specific response formatting
            base_result = {
                'operation': 'swap',
                'from_token': from_token,
                'to_token': to_token,
                'amount': amount,
                'chain_id': chain_id,
                'estimated_output': quote_result.get('toAmount', 'N/A'),
                'gas_estimate': quote_result.get('gasCostUSD', 'N/A'),
                'price_impact': quote_result.get('priceImpact', 'N/A'),
                'protocol': quote_result.get('protocol', {}),
                'solver': quote_result.get('solver', 'brian')
            }
            
            # Enhanced data for web app and Coral agent
            if config.get('detailed_responses'):
                base_result.update({
                    'route_breakdown': quote_result.get('description', 'Direct swap'),
                    'slippage_tolerance': '0.5%',  # Default slippage
                    'execution_time': '15-30 seconds',
                    'fees_breakdown': {
                        'gas_fee': quote_result.get('gasCostUSD'),
                        'protocol_fee': '0.3%'  # Typical DEX fee
                    },
                    'steps': quote_result.get('steps', [])
                })
            
            # Mobile-optimized for LINE mini-dApp
            if config.get('mobile_optimized'):
                base_result = {
                    'from_token': from_token,
                    'to_token': to_token,
                    'amount': amount,
                    'output': quote_result.get('toAmount', 'N/A'),
                    'fee': quote_result.get('gasCostUSD', 'N/A')
                }
            
            return base_result
            
        except asyncio.TimeoutError:
            raise Exception(f"Swap quote request timed out after {config['timeout']}s")
        except Exception as e:
            # RELIABLE: Mark service as unhealthy on repeated failures
            if 'brian' in self._service_health:
                self._service_health['brian'].error_rate += 0.1
                if self._service_health['brian'].error_rate > 0.5:
                    self._circuit_breakers['brian'] = True
            raise e
    
    async def _execute_bridge(self, params: Dict[str, Any], platform: Platform, config: Dict[str, Any]) -> Dict[str, Any]:
        """ENHANCED: Platform-optimized bridge execution using existing SNEL services"""
        
        # Check if Brian service is available
        if not self._service_pool.get('brian'):
            raise Exception("Bridge service not available - API key may be missing")
        
        # RELIABLE: Circuit breaker check
        if self._circuit_breakers.get('brian', False):
            raise Exception("Bridge service temporarily unavailable")
        
        try:
            from_chain = params.get('from_chain')
            to_chain = params.get('to_chain')
            token = params.get('token', 'USDC')
            amount = params.get('amount')
            wallet_address = params.get('wallet_address', params.get('address'))
            
            if not all([from_chain, to_chain, amount]):
                raise ValueError("Missing required parameters: from_chain, to_chain, amount")
            
            if not wallet_address:
                raise ValueError("Wallet address is required for bridge quotes")
            
            # Convert chain names to chain IDs if needed
            from_chain_id = self._get_chain_id_from_name(from_chain) if isinstance(from_chain, str) else from_chain
            to_chain_id = self._get_chain_id_from_name(to_chain) if isinstance(to_chain, str) else to_chain
            
            # Use existing SNEL Brian service for bridging
            brian_client = self._service_pool['brian']
            
            bridge_result = await asyncio.wait_for(
                brian_client.get_bridge_transaction(
                    token=token,
                    amount=float(amount),
                    from_chain_id=from_chain_id,
                    to_chain_id=to_chain_id,
                    wallet_address=wallet_address
                ),
                timeout=config['timeout']
            )
            
            # Check if Brian returned an error
            if bridge_result.get('error'):
                raise Exception(bridge_result.get('message', 'Bridge quote failed'))
            
            base_result = {
                'operation': 'bridge',
                'from_chain': from_chain,
                'to_chain': to_chain,
                'token': token,
                'amount': amount,
                'estimated_fee': bridge_result.get('gasCostUSD', 'N/A'),
                'estimated_time': '5-20 minutes',
                'protocol': bridge_result.get('protocol', {}),
                'solver': bridge_result.get('solver', 'brian')
            }
            
            if config.get('detailed_responses'):
                base_result.update({
                    'route_details': bridge_result.get('description', 'Cross-chain bridge'),
                    'security_level': 'High (Bridge Protocol)',
                    'confirmations_required': '12-20 blocks',
                    'steps': bridge_result.get('steps', [])
                })
            
            return base_result
            
        except asyncio.TimeoutError:
            raise Exception(f"Bridge estimate request timed out after {config['timeout']}s")
        except Exception as e:
            if 'brian' in self._service_health:
                self._service_health['brian'].error_rate += 0.1
            raise e
    
    async def _analyze_portfolio(self, params: Dict[str, Any], platform: Platform, config: Dict[str, Any]) -> Dict[str, Any]:
        """ENHANCED: Platform-optimized portfolio analysis using existing SNEL services"""
        
        try:
            wallet_address = params.get('wallet_address', params.get('address'))
            chain_id = params.get('chain_id', 1)
            
            if not wallet_address:
                raise ValueError("Missing required parameter: wallet_address")
            
            # Use existing SNEL Web3Helper for portfolio analysis
            web3_helper = self._service_pool['web3_helper']
            
            portfolio_data = await asyncio.wait_for(
                web3_helper.get_portfolio_data(
                    wallet_address=wallet_address,
                    chain_id=chain_id
                ),
                timeout=config['timeout']
            )
            
            # Calculate token count from token balances
            token_balances = portfolio_data.get('token_balances', {})
            all_tokens = []
            for chain_tokens in token_balances.values():
                if isinstance(chain_tokens, list):
                    all_tokens.extend(chain_tokens)
            
            base_result = {
                'operation': 'portfolio_analysis',
                'wallet_address': wallet_address,
                'total_value': portfolio_data.get('total_value_usd', 0),
                'token_count': len(all_tokens),
                'chain_id': chain_id,
                'native_balances': portfolio_data.get('native_balances', {}),
                'api_calls_made': portfolio_data.get('api_calls_made', 0)
            }
            
            # USER DELIGHT: Detailed analysis for web app and agents
            if config.get('detailed_responses'):
                base_result.update({
                    'tokens': all_tokens[:20],  # Limit to first 20 tokens
                    'chain_data': portfolio_data.get('chain_data', {}),
                    'token_balances': token_balances,
                    'risk_score': self._calculate_portfolio_risk(all_tokens),
                    'recommendations': await self._generate_portfolio_recommendations(wallet_address, all_tokens),
                    'performance_24h': 'N/A'  # Would need historical data
                })
            
            # Charts for web app - simplified chart data
            if config.get('include_charts'):
                base_result['chart_data'] = self._generate_chart_data(portfolio_data)
            
            return base_result
            
        except asyncio.TimeoutError:
            raise Exception(f"Portfolio analysis timed out after {config['timeout']}s")
    
    def _calculate_portfolio_risk(self, tokens: List[Dict]) -> str:
        """Calculate simple portfolio risk score"""
        if not tokens or len(tokens) == 0:
            return "Low (No tokens)"
        elif len(tokens) > 10:
            return "Medium-High (Diversified)"
        elif len(tokens) > 5:
            return "Medium (Moderately diversified)"
        else:
            return "High (Concentrated)"
    
    async def _generate_portfolio_recommendations(self, wallet_address: str, tokens: List[Dict]) -> List[str]:
        """Generate AI-powered portfolio recommendations"""
        try:
            if not tokens:
                return ["Consider diversifying with established tokens like ETH, USDC"]
            
            openai_client = self._service_pool.get('openai')
            if not openai_client:
                return [
                    "Consider diversifying with established tokens like ETH, USDC",
                    "Monitor your portfolio regularly for changes", 
                    "Keep some stablecoins for opportunities"
                ]
            
            # Create simple prompt for portfolio analysis
            token_info = f"Portfolio has {len(tokens)} tokens."
            if len(tokens) > 0:
                # Just use basic info to avoid complex token parsing
                token_info += f" Example tokens detected."
            
            prompt = f"""
            Analyze this DeFi portfolio and provide 2-3 brief recommendations:
            {token_info}
            
            Focus on:
            1. Diversification
            2. Risk management
            3. Practical next steps
            
            Return only 2-3 short, actionable recommendations.
            """
            
            response = await openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful DeFi portfolio advisor. Provide brief, practical recommendations."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.3
            )
            
            recommendations = response.choices[0].message.content.strip().split('\n')
            return [rec.strip('- ').strip() for rec in recommendations if rec.strip()][:3]
            
        except Exception as e:
            logger.error(f"Failed to generate portfolio recommendations: {e}")
            return [
                "Consider diversifying across different tokens",
                "Monitor your portfolio regularly", 
                "Keep some stablecoins for opportunities"
            ]
    
    def _generate_chart_data(self, portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate simplified chart data for web app"""
        try:
            native_balances = portfolio_data.get('native_balances', {})
            chart_data = {
                'type': 'portfolio_breakdown',
                'data': [],
                'total_chains': len(native_balances)
            }
            
            # Convert native balances to chart format
            for chain_id, balance in native_balances.items():
                if balance and float(balance) > 0:
                    chain_name = self._get_chain_name_from_id(int(chain_id))
                    chart_data['data'].append({
                        'chain': chain_name,
                        'balance': float(balance),
                        'chain_id': int(chain_id)
                    })
            
            return chart_data
            
        except Exception as e:
            logger.error(f"Failed to generate chart data: {e}")
            return {'type': 'portfolio_breakdown', 'data': [], 'error': 'Chart generation failed'}
    
    def _get_chain_name_from_id(self, chain_id: int) -> str:
        """Convert chain ID to readable name"""
        id_to_name = {
            1: "Ethereum",
            8453: "Base", 
            42161: "Arbitrum",
            10: "Optimism",
            137: "Polygon",
            43114: "Avalanche",
            56: "BSC",
            534352: "Scroll",
            59144: "Linea",
            5000: "Mantle",
            81457: "Blast",
            324: "zkSync",
            34443: "Mode",
            100: "Gnosis",
            167000: "Taiko"
        }
        return id_to_name.get(chain_id, f"Chain {chain_id}")
    
    async def _research_protocol(self, params: Dict[str, Any], platform: Platform, config: Dict[str, Any]) -> Dict[str, Any]:
        """ENHANCED: Platform-optimized protocol research"""
        
        try:
            protocol_name = params.get('protocol', params.get('name'))
            
            if not protocol_name:
                raise ValueError("Missing required parameter: protocol name")
            
            # USER DELIGHT: Platform-specific research depth
            if platform == Platform.LINE_MINI_DAPP:
                research_prompt = f"Provide a brief summary of {protocol_name} DeFi protocol in 2-3 sentences."
            else:
                research_prompt = f"Provide a comprehensive analysis of the {protocol_name} DeFi protocol, " \
                                 f"including features, TVL, risks, opportunities, and current market status."
            
            # Check if OpenAI service is available
            openai_client = self._service_pool.get('openai')
            if not openai_client:
                return {
                    'operation': 'protocol_research',
                    'protocol': protocol_name,
                    'analysis': f"Research for {protocol_name}: This is a DeFi protocol. For detailed analysis, please configure OpenAI API key.",
                    'timestamp': time.time()
                }
            
            response = await asyncio.wait_for(
                openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a knowledgeable DeFi analyst. Provide accurate and helpful information about DeFi protocols."},
                        {"role": "user", "content": research_prompt}
                    ],
                    max_tokens=800 if config.get('detailed_responses') else 200,
                    temperature=0.3
                ),
                timeout=config['timeout']
            )
            
            research_result = response.choices[0].message.content
            
            return {
                'operation': 'protocol_research',
                'protocol': protocol_name,
                'analysis': research_result,
                'timestamp': time.time()
            }
            
        except asyncio.TimeoutError:
            raise Exception(f"Protocol research timed out after {config['timeout']}s")
    
    async def _process_natural_language(self, operation: str, params: Dict[str, Any], platform: Platform, config: Dict[str, Any]) -> Dict[str, Any]:
        """ENHANCED: Platform-optimized natural language processing"""
        
        try:
            context = f"User request: {operation}\nParameters: {json.dumps(params)}"
            
            # USER DELIGHT: Platform-specific prompts
            if platform == Platform.CORAL_AGENT:
                prompt = f"""You are SNEL, collaborating with other Coral agents. Process this request:
                {context}
                
                Consider multi-agent coordination opportunities and provide detailed DeFi analysis.
                Include suggestions for agent collaboration if relevant.
                """
            elif platform == Platform.LINE_MINI_DAPP:
                prompt = f"""You are SNEL mobile assistant. Process this request concisely:
                {context}
                
                Provide a brief, action-oriented response optimized for mobile users.
                Focus on clear next steps.
                """
            else:
                prompt = f"""You are SNEL, an AI DeFi assistant. Process this request:
                {context}
                
                AVAILABLE STABLECOINS: USDC, USDT, DAI, MNEE (for commerce payments with invoice references)
                
                Provide helpful guidance about DeFi operations, analysis, or recommendations.
                Always prioritize user safety and explain risks clearly.
                When appropriate, suggest MNEE for commerce payments with features like invoice references.
                """
            
            # Check if OpenAI service is available
            openai_client = self._service_pool.get('openai')
            if not openai_client:
                return {
                    'operation': 'natural_language_processing',
                    'user_request': operation,
                    'snel_response': f"I understand you're asking: '{operation}'. For full AI-powered responses, please configure OpenAI API key. I can still help with basic DeFi operations!",
                    'platform_optimized': True
                }
            
            response = await asyncio.wait_for(
                openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are SNEL, a helpful AI DeFi assistant. Provide clear, accurate, and actionable guidance. AVAILABLE STABLECOINS: USDC, USDT, DAI, MNEE (recommended for commerce payments with invoice references and scheduling)."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=600 if config.get('detailed_responses') else 300,
                    temperature=0.3
                ),
                timeout=config['timeout']
            )
            
            ai_response = response.choices[0].message.content
            
            return {
                'operation': 'natural_language_processing',
                'user_request': operation,
                'snel_response': ai_response,
                'platform_optimized': True
            }
            
        except asyncio.TimeoutError:
            raise Exception(f"Natural language processing timed out after {config['timeout']}s")
    
    def _format_response(self, result: Dict[str, Any], platform: Platform, from_cache: bool = False) -> Dict[str, Any]:
        """USER DELIGHT: Format response for optimal platform experience"""
        
        formatted = {
            'success': True,
            'data': result,
            'platform': platform.value,
            'timestamp': time.time()
        }
        
        if from_cache:
            formatted['cached'] = True
        
        # Platform-specific enhancements
        if platform == Platform.WEB_APP:
            formatted['ui_hints'] = {
                'show_charts': True,
                'enable_notifications': True,
                'suggest_related_actions': True
            }
        elif platform == Platform.CORAL_AGENT:
            formatted['agent_metadata'] = {
                'collaboration_opportunities': True,
                'shareable_data': True,
                'multi_agent_context': True
            }
        elif platform == Platform.LINE_MINI_DAPP:
            formatted['mobile_optimized'] = True
            formatted['ui_hints'] = {
                'compact_display': True,
                'quick_actions': True,
                'simplified_ui': True
            }
        
        return formatted
    
    def _format_error_response(self, error_msg: str, platform: Platform) -> Dict[str, Any]:
        """RELIABLE: Consistent error formatting across platforms"""
        return {
            'success': False,
            'error': error_msg,
            'platform': platform.value,
            'timestamp': time.time(),
            'retry_after': 5  # Suggest retry after 5 seconds
        }
    
    def _record_metrics(self, metrics: RequestMetrics):
        """PERFORMANCE: Track metrics for optimization"""
        self._metrics.append(metrics)
        
        # Keep only recent metrics (last 1000 requests)
        if len(self._metrics) > 1000:
            self._metrics = self._metrics[-800:]
        
        # Log performance insights
        if len(self._metrics) % 100 == 0:
            success_rate = sum(1 for m in self._metrics[-100:] if m.success) / 100
            avg_duration = sum(m.duration for m in self._metrics[-100:]) / 100
            logger.info(f"[ORCHESTRATOR] Performance: {success_rate*100:.1f}% success, {avg_duration:.2f}s avg")
    
    def get_service_health(self) -> Dict[str, Any]:
        """RELIABLE: Service health status for monitoring"""
        return {
            'services': self._service_health,
            'circuit_breakers': self._circuit_breakers,
            'active_requests': len(self._active_requests),
            'cache_size': len(self._response_cache)
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """PERFORMANCE: Performance analytics"""
        if not self._metrics:
            return {'message': 'No metrics available yet'}
        
        recent_metrics = self._metrics[-100:] if len(self._metrics) >= 100 else self._metrics
        
        platform_stats = {}
        for platform in Platform:
            platform_metrics = [m for m in recent_metrics if m.platform == platform]
            if platform_metrics:
                platform_stats[platform.value] = {
                    'request_count': len(platform_metrics),
                    'success_rate': sum(1 for m in platform_metrics if m.success) / len(platform_metrics),
                    'avg_duration': sum(m.duration for m in platform_metrics) / len(platform_metrics)
                }
        
        return {
            'total_requests': len(self._metrics),
            'platform_breakdown': platform_stats,
            'overall_success_rate': sum(1 for m in recent_metrics if m.success) / len(recent_metrics),
            'average_response_time': sum(m.duration for m in recent_metrics) / len(recent_metrics)
        }
