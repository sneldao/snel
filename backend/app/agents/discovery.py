from browser_use import BrowserUse
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.reasoning import ReasoningTools
import asyncio
from decimal import Decimal
import logging
from typing import Dict, Any, Optional, List
import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential
from datetime import datetime

logger = logging.getLogger(__name__)

class ProtocolDiscoverySystem:
    def __init__(self):
        # Initialize Browser Use for automated protocol discovery
        self.browser = BrowserUse()
        
        # Initialize discovery agent with additional tools
        self.discovery_agent = Agent(
            name="Protocol Scout",
            role="Discover and analyze new DeFi protocols",
            model=OpenAIChat(id="gpt-4o-mini"),
            tools=[
                DuckDuckGoTools(),  # For additional protocol research
                ReasoningTools(add_instructions=True),  # For better analysis
            ],
            instructions="""
            1. Protocol Discovery:
               - Monitor DeFiLlama for new protocols
               - Track CoinGecko listings
               - Follow DeFi news sources
               - Analyze social signals
               
            2. Risk Assessment:
               - Verify smart contract audits
               - Check team background
               - Analyze TVL growth
               - Monitor user activity
               
            3. Yield Analysis:
               - Track APY/APR rates
               - Monitor pool stability
               - Analyze token economics
               - Evaluate sustainability
            """,
            add_datetime_to_instructions=True,
        )
        
        # Cache for protocol data
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes
        
        # Rate limiting
        self._request_semaphore = asyncio.Semaphore(5)  # Max 5 concurrent requests
        
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def discover_protocols(self):
        """Discover new DeFi protocols and opportunities with retry logic"""
        try:
            async with self._request_semaphore:
                # Check cache first
                cache_key = "protocols"
                if cache_key in self._cache:
                    return self._cache[cache_key]
                
                # Use Browser Use to navigate DeFi data aggregators
                await self.browser.navigate("https://defillama.com/protocols")
                protocols = await self.browser.extract_data({
                    "name": ".protocol-name",
                    "tvl": ".tvl-value",
                    "change_24h": ".change-24h",
                    "category": ".protocol-category"
                })
                
                # Add Dune Analytics data
                await self._enrich_with_dune_data(protocols)
                
                # Get detailed protocol info
                for protocol in protocols[:10]:
                    try:
                        await self.browser.navigate(f"https://defillama.com/protocol/{protocol['name']}")
                        details = await self.browser.extract_data({
                            "audit_status": ".audit-status",
                            "yield_opportunities": ".yield-list",
                            "risks": ".risk-factors"
                        })
                        protocol.update(details)
                    except Exception as e:
                        logger.error(f"Error fetching details for {protocol['name']}: {e}")
                        continue
                
                # Cache the results
                self._cache[cache_key] = protocols
                return protocols
                
        except Exception as e:
            logger.error(f"Error in discover_protocols: {e}")
            raise
            
    async def _enrich_with_dune_data(self, protocols):
        """Add Dune Analytics data to protocols"""
        try:
            for protocol in protocols:
                query_id = self._get_dune_query_id(protocol['name'])
                if query_id:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            f"https://api.dune.com/api/v1/query/{query_id}/results",
                            headers={"x-dune-api-key": "your_dune_api_key"}
                        ) as response:
                            if response.status == 200:
                                data = await response.json()
                                protocol['dune_metrics'] = data
        except Exception as e:
            logger.error(f"Error enriching with Dune data: {e}")
            
    def _get_dune_query_id(self, protocol_name: str) -> Optional[str]:
        """Map protocol names to Dune query IDs"""
        # Implement mapping logic
        return None
            
    def _normalize_tvl(self, tvl: str) -> float:
        """Normalize TVL to a 0-1 score"""
        try:
            # Convert TVL string to number
            tvl_value = Decimal(tvl.replace('$', '').replace(',', ''))
            
            # TVL thresholds in USD
            thresholds = {
                Decimal('1000000000'): 1.0,  # $1B+ = 1.0
                Decimal('500000000'): 0.9,   # $500M+ = 0.9
                Decimal('100000000'): 0.8,   # $100M+ = 0.8
                Decimal('50000000'): 0.7,    # $50M+ = 0.7
                Decimal('10000000'): 0.6,    # $10M+ = 0.6
                Decimal('5000000'): 0.5,     # $5M+ = 0.5
                Decimal('1000000'): 0.4,     # $1M+ = 0.4
                Decimal('500000'): 0.3,      # $500K+ = 0.3
                Decimal('100000'): 0.2,      # $100K+ = 0.2
                Decimal('0'): 0.1            # Any TVL = 0.1
            }
            
            for threshold, score in thresholds.items():
                if tvl_value >= threshold:
                    return score
            return 0.0
        except Exception as e:
            logger.error(f"Error normalizing TVL: {e}")
            return 0.0
            
    def _audit_score(self, audit_status: Dict[str, Any]) -> float:
        """Convert audit status to a 0-1 score"""
        try:
            base_score = 0.0
            
            # Check for major auditors
            auditors = {
                'certik': 0.3,
                'consensys': 0.3,
                'trail_of_bits': 0.3,
                'quantstamp': 0.25,
                'omniscia': 0.25,
                'hacken': 0.25,
                'peckshield': 0.25
            }
            
            # Add scores for each auditor
            for auditor, score in auditors.items():
                if auditor in audit_status.get('auditors', []):
                    base_score += score
                    
            # Additional audit factors
            factors = {
                'multiple_audits': 0.2,  # Bonus for multiple audits
                'recent_audit': 0.2,     # Audit within last 6 months
                'bug_bounty': 0.1,       # Active bug bounty program
                'open_source': 0.1,      # Open source code
                'formal_verification': 0.2  # Formal verification completed
            }
            
            # Add factor scores
            if len(audit_status.get('auditors', [])) > 1:
                base_score += factors['multiple_audits']
            
            if audit_status.get('last_audit_date'):
                last_audit = datetime.fromisoformat(audit_status['last_audit_date'])
                if (datetime.now() - last_audit).days <= 180:
                    base_score += factors['recent_audit']
                    
            if audit_status.get('bug_bounty_active', False):
                base_score += factors['bug_bounty']
                
            if audit_status.get('open_source', False):
                base_score += factors['open_source']
                
            if audit_status.get('formal_verification', False):
                base_score += factors['formal_verification']
                
            # Cap at 1.0
            return min(base_score, 1.0)
        except Exception as e:
            logger.error(f"Error calculating audit score: {e}")
            return 0.0
            
    def _normalize_market_cap(self, market_cap: str) -> float:
        """Normalize market cap to a 0-1 score"""
        try:
            # Convert market cap string to number
            mc_value = Decimal(market_cap.replace('$', '').replace(',', ''))
            
            # Market cap thresholds
            thresholds = {
                Decimal('10000000000'): 1.0,  # $10B+ = 1.0
                Decimal('5000000000'): 0.9,   # $5B+ = 0.9
                Decimal('1000000000'): 0.8,   # $1B+ = 0.8
                Decimal('500000000'): 0.7,    # $500M+ = 0.7
                Decimal('100000000'): 0.6,    # $100M+ = 0.6
                Decimal('50000000'): 0.5,     # $50M+ = 0.5
                Decimal('10000000'): 0.4,     # $10M+ = 0.4
                Decimal('5000000'): 0.3,      # $5M+ = 0.3
                Decimal('1000000'): 0.2,      # $1M+ = 0.2
                Decimal('0'): 0.1             # Any market cap = 0.1
            }
            
            for threshold, score in thresholds.items():
                if mc_value >= threshold:
                    return score
            return 0.0
        except Exception as e:
            logger.error(f"Error normalizing market cap: {e}")
            return 0.0
            
    def _normalize_volume(self, volume: str) -> float:
        """Normalize volume to a 0-1 score"""
        try:
            # Convert volume string to number
            vol_value = Decimal(volume.replace('$', '').replace(',', ''))
            
            # Volume thresholds
            thresholds = {
                Decimal('100000000'): 1.0,  # $100M+ = 1.0
                Decimal('50000000'): 0.9,   # $50M+ = 0.9
                Decimal('10000000'): 0.8,   # $10M+ = 0.8
                Decimal('5000000'): 0.7,    # $5M+ = 0.7
                Decimal('1000000'): 0.6,    # $1M+ = 0.6
                Decimal('500000'): 0.5,     # $500K+ = 0.5
                Decimal('100000'): 0.4,     # $100K+ = 0.4
                Decimal('50000'): 0.3,      # $50K+ = 0.3
                Decimal('10000'): 0.2,      # $10K+ = 0.2
                Decimal('0'): 0.1           # Any volume = 0.1
            }
            
            # Additional volume factors
            factors = {
                'consistent_volume': 0.2,  # Volume stable over time
                'growing_volume': 0.2,     # Volume growing over time
                'high_liquidity': 0.2      # Good depth on order books
            }
            
            base_score = 0.0
            for threshold, score in thresholds.items():
                if vol_value >= threshold:
                    base_score = score
                    break
                    
            # Add factor scores if data available
            volume_history = self._get_volume_history(vol_value)
            if volume_history:
                if self._is_volume_consistent(volume_history):
                    base_score += factors['consistent_volume']
                if self._is_volume_growing(volume_history):
                    base_score += factors['growing_volume']
                if self._has_good_liquidity(volume_history):
                    base_score += factors['high_liquidity']
                    
            return min(base_score, 1.0)
        except Exception as e:
            logger.error(f"Error normalizing volume: {e}")
            return 0.0
            
    def _normalize_sentiment(self, sentiment: Dict[str, Any]) -> float:
        """Normalize sentiment analysis to a 0-1 score"""
        try:
            # Combine multiple sentiment factors
            factors = {
                'social_score': sentiment.get('social_score', 0) / 100,
                'positive_mentions': sentiment.get('positive_mentions', 0) / sentiment.get('total_mentions', 1),
                'developer_activity': sentiment.get('developer_activity', 0) / 100,
                'community_growth': sentiment.get('community_growth', 0) / 100,
                'github_activity': self._normalize_github_activity(sentiment.get('github_stats', {})),
                'twitter_engagement': self._normalize_twitter_engagement(sentiment.get('twitter_stats', {})),
                'telegram_activity': self._normalize_telegram_activity(sentiment.get('telegram_stats', {}))
            }
            
            # Weight the factors
            weights = {
                'social_score': 0.2,
                'positive_mentions': 0.2,
                'developer_activity': 0.15,
                'community_growth': 0.15,
                'github_activity': 0.1,
                'twitter_engagement': 0.1,
                'telegram_activity': 0.1
            }
            
            # Calculate weighted average
            score = sum(score * weights[factor] for factor, score in factors.items())
            return min(max(score, 0.0), 1.0)
        except Exception as e:
            logger.error(f"Error normalizing sentiment: {e}")
            return 0.0
            
    def _normalize_github_activity(self, github_stats: Dict[str, Any]) -> float:
        """Normalize GitHub activity to a 0-1 score"""
        try:
            metrics = {
                'commits': min(github_stats.get('commits_last_month', 0) / 100, 1.0),
                'contributors': min(github_stats.get('active_contributors', 0) / 20, 1.0),
                'stars': min(github_stats.get('stars', 0) / 1000, 1.0),
                'forks': min(github_stats.get('forks', 0) / 200, 1.0)
            }
            return sum(metrics.values()) / len(metrics)
        except Exception:
            return 0.0
            
    def _normalize_twitter_engagement(self, twitter_stats: Dict[str, Any]) -> float:
        """Normalize Twitter engagement to a 0-1 score"""
        try:
            metrics = {
                'followers': min(twitter_stats.get('followers', 0) / 100000, 1.0),
                'engagement_rate': min(twitter_stats.get('engagement_rate', 0) / 0.05, 1.0),
                'tweet_frequency': min(twitter_stats.get('tweets_per_day', 0) / 10, 1.0)
            }
            return sum(metrics.values()) / len(metrics)
        except Exception:
            return 0.0
            
    def _normalize_telegram_activity(self, telegram_stats: Dict[str, Any]) -> float:
        """Normalize Telegram activity to a 0-1 score"""
        try:
            metrics = {
                'members': min(telegram_stats.get('members', 0) / 50000, 1.0),
                'active_users': min(telegram_stats.get('active_users', 0) / 1000, 1.0),
                'messages_per_day': min(telegram_stats.get('messages_per_day', 0) / 500, 1.0)
            }
            return sum(metrics.values()) / len(metrics)
        except Exception:
            return 0.0
            
    def _get_volume_history(self, current_volume: Decimal) -> Optional[List[Decimal]]:
        """Get historical volume data"""
        # Implementation would fetch historical data
        return None
        
    def _is_volume_consistent(self, volume_history: List[Decimal]) -> bool:
        """Check if volume is consistent over time"""
        if not volume_history or len(volume_history) < 7:
            return False
            
        # Calculate standard deviation
        mean = sum(volume_history) / len(volume_history)
        variance = sum((x - mean) ** 2 for x in volume_history) / len(volume_history)
        std_dev = variance.sqrt()
        
        # Volume is consistent if standard deviation is less than 30% of mean
        return std_dev / mean < Decimal('0.3')
        
    def _is_volume_growing(self, volume_history: List[Decimal]) -> bool:
        """Check if volume is growing over time"""
        if not volume_history or len(volume_history) < 7:
            return False
            
        # Calculate 7-day moving average
        ma_7 = sum(volume_history[-7:]) / 7
        ma_prev = sum(volume_history[-14:-7]) / 7
        
        # Volume is growing if current MA is 10% higher than previous
        return ma_7 > ma_prev * Decimal('1.1')
        
    def _has_good_liquidity(self, volume_history: List[Decimal]) -> bool:
        """Check if protocol has good liquidity"""
        if not volume_history:
            return False
            
        # Good liquidity if average daily volume is above $1M
        avg_volume = sum(volume_history) / len(volume_history)
        return avg_volume > Decimal('1000000')
            
    def _assess_sustainability(self, protocol: Dict[str, Any]) -> float:
        """Assess yield sustainability"""
        try:
            factors = {
                'token_economics': self._analyze_tokenomics(protocol),
                'tvl_stability': self._analyze_tvl_stability(protocol),
                'revenue_model': self._analyze_revenue_model(protocol),
                'competition': self._analyze_competition(protocol)
            }
            
            weights = {
                'token_economics': 0.3,
                'tvl_stability': 0.3,
                'revenue_model': 0.2,
                'competition': 0.2
            }
            
            score = sum(score * weights[factor] for factor, score in factors.items())
            return min(max(score, 0.0), 1.0)
        except Exception as e:
            logger.error(f"Error assessing sustainability: {e}")
            return 0.0
            
    def _analyze_tokenomics(self, protocol: Dict[str, Any]) -> float:
        """Analyze token economics for sustainability"""
        try:
            factors = {
                'emission_schedule': protocol.get('tokenomics', {}).get('emission_rate', 0),
                'vesting_periods': protocol.get('tokenomics', {}).get('vesting_length', 0),
                'token_utility': protocol.get('tokenomics', {}).get('utility_score', 0)
            }
            return sum(factors.values()) / len(factors)
        except Exception:
            return 0.0
            
    def _analyze_tvl_stability(self, protocol: Dict[str, Any]) -> float:
        """Analyze TVL stability over time"""
        try:
            tvl_history = protocol.get('tvl_history', [])
            if not tvl_history:
                return 0.0
                
            # Calculate volatility and trend
            volatility = self._calculate_volatility(tvl_history)
            trend = self._calculate_trend(tvl_history)
            
            return (1 - volatility) * 0.6 + trend * 0.4
        except Exception:
            return 0.0
            
    def _analyze_revenue_model(self, protocol: Dict[str, Any]) -> float:
        """Analyze protocol revenue model"""
        try:
            revenue_data = protocol.get('revenue', {})
            
            factors = {
                'fee_structure': revenue_data.get('fee_score', 0),
                'revenue_growth': revenue_data.get('growth_score', 0),
                'profit_sharing': revenue_data.get('distribution_score', 0)
            }
            
            return sum(factors.values()) / len(factors)
        except Exception:
            return 0.0
            
    def _analyze_competition(self, protocol: Dict[str, Any]) -> float:
        """Analyze competitive landscape"""
        try:
            competition_data = protocol.get('competition', {})
            
            factors = {
                'market_share': competition_data.get('market_share', 0),
                'unique_features': competition_data.get('uniqueness_score', 0),
                'moat_strength': competition_data.get('moat_score', 0)
            }
            
            return sum(factors.values()) / len(factors)
        except Exception:
            return 0.0
            
    def _calculate_volatility(self, history: List[float]) -> float:
        """Calculate TVL volatility"""
        try:
            if len(history) < 2:
                return 1.0
            changes = [abs(b - a) / a for a, b in zip(history[:-1], history[1:])]
            return sum(changes) / len(changes)
        except Exception:
            return 1.0
            
    def _calculate_trend(self, history: List[float]) -> float:
        """Calculate TVL trend"""
        try:
            if len(history) < 2:
                return 0.0
            start, end = history[0], history[-1]
            return max(min((end - start) / start, 1.0), 0.0)
        except Exception:
            return 0.0
        
    async def analyze_opportunities(self, protocols):
        """Analyze discovered protocols for opportunities"""
        opportunities = []
        
        for protocol in protocols:
            # Use Browser Use to check additional sources
            await self.browser.navigate(f"https://www.coingecko.com/en/coins/{protocol['name']}")
            market_data = await self.browser.extract_data({
                "market_cap": ".market-cap",
                "volume": ".volume-24h",
                "social_metrics": ".social-metrics"
            })
            
            # Get community sentiment
            await self.browser.navigate(f"https://twitter.com/search?q={protocol['name']}")
            sentiment = await self.browser.analyze_sentiment()
            
            opportunity = {
                "protocol": protocol,
                "market_data": market_data,
                "sentiment": sentiment,
                "risk_score": self._calculate_risk_score(protocol, market_data, sentiment),
                "yield_potential": self._analyze_yield_potential(protocol)
            }
            
            opportunities.append(opportunity)
            
        return opportunities
        
    def _calculate_risk_score(self, protocol, market_data, sentiment):
        """Calculate risk score based on multiple factors"""
        risk_factors = {
            "tvl": self._normalize_tvl(protocol["tvl"]),
            "audit": self._audit_score(protocol["audit_status"]),
            "market_cap": self._normalize_market_cap(market_data["market_cap"]),
            "volume": self._normalize_volume(market_data["volume"]),
            "sentiment": self._normalize_sentiment(sentiment)
        }
        
        # Weight and combine risk factors
        weights = {"tvl": 0.3, "audit": 0.25, "market_cap": 0.2, 
                  "volume": 0.15, "sentiment": 0.1}
                  
        risk_score = sum(score * weights[factor] for factor, score in risk_factors.items())
        return risk_score
        
    def _analyze_yield_potential(self, protocol):
        """Analyze yield potential and sustainability"""
        yield_data = {
            "base_apy": float(protocol.get("yield_opportunities", {}).get("base_apy", 0)),
            "reward_apy": float(protocol.get("yield_opportunities", {}).get("reward_apy", 0)),
            "sustainability": self._assess_sustainability(protocol)
        }
        
        return {
            "total_apy": yield_data["base_apy"] + yield_data["reward_apy"],
            "sustainable_apy": yield_data["base_apy"] + (yield_data["reward_apy"] * yield_data["sustainability"]),
            "confidence": yield_data["sustainability"]
        } 