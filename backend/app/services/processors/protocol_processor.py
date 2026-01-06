"""
Protocol research command processor.
Handles protocol research and analysis operations with built-in knowledge base.
Follows ENHANCEMENT FIRST principle: uses existing contextual processor knowledge as fallback.
"""
import logging
import re
import os
from typing import Union
from difflib import SequenceMatcher
from openai import AsyncOpenAI

from app.models.unified_models import (
    UnifiedCommand, UnifiedResponse, AgentType, CommandType
)
from app.services.error_guidance_service import ErrorContext
from app.services.external.firecrawl_service import (
    get_protocol_details,
    analyze_protocol_with_ai,
    answer_protocol_question,
)
from app.services.external.firecrawl_client import FirecrawlClient, FirecrawlError
from app.services.research.router import ResearchRouter, Intent
from .base_processor import BaseProcessor

logger = logging.getLogger(__name__)

# Built-in knowledge base for privacy protocols and core concepts
# Single source of truth for protocol information - DRY principle
PROTOCOL_KNOWLEDGE_BASE = {
    "zcash": {
        "official_name": "Zcash",
        "type": "Privacy-Preserving Cryptocurrency",
        "summary": "Zcash is a cryptocurrency built on the Bitcoin blockchain that enables private and transparent transactions. It uses zero-knowledge proofs to allow users to hide transaction details while still verifying transactions on the blockchain.",
        "key_features": [
            "Shielded transactions - hide sender, receiver, and amount",
            "Zero-knowledge proofs for transaction verification",
            "Unified Addresses (UA) - work across all address types",
            "Encrypted transaction memos - send private messages",
            "Optional transparency - users choose to disclose transactions when needed"
        ],
        "privacy_explanation": "Zcash uses zk-SNARKs (zero-knowledge Succinct Non-interactive ARguments of Knowledge) to prove transaction validity without revealing sender, receiver, or amount. Transaction history is encrypted and only visible to the transaction participants.",
        "how_it_works": "When you send a shielded transaction in Zcash, the transaction is encrypted. The sender proves they have the funds without revealing their address, and the recipient can decrypt the transaction with their private viewing key. All of this happens while maintaining blockchain verification.",
        "shielded_addresses": "Addresses starting with 'u' are Unified Addresses that work in both shielded and transparent pools. Shielded addresses provide full privacy.",
        "recommended_wallets": [
            {"name": "Zashi", "type": "Mobile", "url": "https://zashi.app/", "note": "Official Zcash mobile wallet, shielded by default"},
            {"name": "Nighthawk", "type": "Desktop", "url": "https://nighthawkwallet.com/", "note": "Full desktop support, shielded by default"}
        ],
        "use_cases": [
            "Private financial transactions",
            "Confidential business payments",
            "Personal financial privacy",
            "Protection from transaction surveillance"
        ]
    },
    "privacy": {
        "official_name": "Privacy Features",
        "type": "Concept",
        "summary": "Privacy features enable users to transact on blockchain without revealing sensitive information.",
        "key_features": [
            "Transaction privacy - amounts and participants are hidden",
            "Anonymity - transactions blend with others in privacy pools",
            "Selective disclosure - optionally prove transaction history when needed",
            "Zero-knowledge proofs - mathematical verification without revealing data"
        ],
        "how_it_works": "Privacy transactions use cryptographic techniques (zero-knowledge proofs) to prove transactions are valid without revealing the transaction details. This means the blockchain network can verify transactions without knowing who sent what to whom.",
        "privacy_explanation": "Privacy in blockchain means your transaction details (who sent to whom, how much) are not publicly visible. Instead of storing plain information on the blockchain, cryptographic proofs ensure transactions are valid while keeping details private.",
        "recommended_wallets": [
            {"name": "Zashi", "type": "Mobile", "url": "https://zashi.app/", "note": "Zcash mobile wallet with shielded by default"},
            {"name": "Nighthawk", "type": "Desktop", "url": "https://nighthawkwallet.com/", "note": "Desktop privacy wallet for Zcash"}
        ],
        "privacy_pools": "Larger privacy pools provide better anonymity. When your transaction is mixed with others, it's harder to trace which transaction is yours."
    },
    "shielded transactions": {
        "official_name": "Shielded Transactions",
        "type": "Zcash Feature",
        "summary": "Transactions that encrypt the sender, receiver, and amount using zero-knowledge proofs.",
        "key_features": [
            "Sender privacy - your address is hidden",
            "Receiver privacy - recipient address is hidden",
            "Amount privacy - transaction amount is encrypted",
            "Memo privacy - encrypted messages between sender and receiver"
        ],
        "technical_explanation": "Shielded transactions use the Sprout and Sapling circuits (or Orchard in newer versions) to prove transaction validity. The sender proves they have the funds and the receiver can decrypt the transaction, all without revealing information to the blockchain.",
        "privacy_explanation": "Shielded transactions hide all sensitive information while proving the transaction is valid. Unlike transparent transactions, shielded transactions encrypt sender, receiver, and amount - making them completely private on the blockchain.",
        "how_it_works": "To send a shielded transaction: 1) You initiate the transaction with encrypted details, 2) Zero-knowledge proofs verify you have the funds without revealing your address, 3) The recipient receives the encrypted data and decrypts it with their private key. The blockchain records only that a valid transaction occurred, not the details.",
        "recommended_wallets": [
            {"name": "Zashi", "type": "Mobile", "url": "https://zashi.app/", "note": "Official mobile wallet, shielded by default"},
            {"name": "Nighthawk", "type": "Desktop", "url": "https://nighthawkwallet.com/", "note": "Full-featured desktop wallet with shielding"}
        ]
    },
    "bridging": {
        "official_name": "Cross-Chain Bridging",
        "type": "DeFi Operation",
        "summary": "Moving assets from one blockchain to another securely using bridge protocols.",
        "key_features": [
            "Cross-chain transfers - send assets between different blockchains",
            "Wrapped tokens - represent assets on non-native blockchains",
            "Multi-step transactions - approval followed by actual bridge",
            "Security checks - verification that assets arrive safely"
        ],
        "privacy_bridge_explanation": "Privacy bridging allows you to move assets from public chains (Ethereum, Polygon, Base, etc.) to privacy chains (Zcash) so your transaction becomes private on the destination chain."
    },
    "axelar": {
        "official_name": "Axelar",
        "type": "Cross-Chain Infrastructure",
        "summary": "Axelar is a network that enables secure cross-chain communication and asset transfers using General Message Passing (GMP).",
        "key_features": [
            "General Message Passing (GMP) - send messages between blockchains",
            "Secure verification - validator network ensures message integrity",
            "Multi-chain support - connects 16+ blockchain networks",
            "Standardized protocols - consistent interface across chains"
        ]
    },
    "mnee": {
        "official_name": "MNEE Stablecoin",
        "type": "Stablecoin for Commerce & Payments",
        "summary": "MNEE is a programmable stablecoin designed for efficient commerce and payment transactions on the blockchain. It provides stable value pegged to fiat currency while enabling instant, low-cost transactions across multiple blockchains.",
        "key_features": [
            "Stable value pegged to USD - maintains price stability for transactions",
            "Programmable payments - conditional execution of transactions",
            "Optimized for commerce - built specifically for e-commerce and payment flows",
            "Low transaction fees - efficient for frequent microtransactions",
            "Multi-chain compatibility - works across multiple blockchain networks",
            "DeFi protocol integration - compatible with existing DeFi ecosystems",
            "Instant settlement - fast transaction finality for payment confirmations"
        ],
        "how_it_works": "MNEE enables merchants and users to conduct transactions on blockchain while maintaining price stability. Each MNEE token represents $1 USD, making it ideal for price prediction and budgeting. Transactions are verified across the blockchain network and settle instantly.",
        "commerce_use_cases": [
            "E-commerce payments - accept payments for online goods and services",
            "Point-of-sale transactions - in-store payments with blockchain settlement",
            "Subscription payments - recurring payment automation",
            "Cross-border payments - send value internationally with minimal fees",
            "Payment channels - micropayment support for digital content"
        ],
        "defi_integration": [
            "Liquidity pools - provide trading pairs on DEXs",
            "Yield farming - earn returns on idle MNEE holdings",
            "Lending protocols - use MNEE as collateral or lending asset",
            "Cross-chain bridges - transfer value between blockchains"
        ],
        "advantages": [
            "Price stability eliminates volatility risk for merchants",
            "Fast transactions enable real-time payment confirmation",
            "Low fees reduce cost of commerce compared to traditional payment",
            "Programmable - enable conditional payments and smart contracts",
            "Transparent - all transactions visible on blockchain",
            "Censorship-resistant - no middleman control over funds"
        ],
        "use_cases": [
            "E-commerce payments - online shopping and digital goods",
            "Cross-chain transfers - move value between different blockchains",
            "DeFi yield farming - earn passive income on holdings",
            "Stable store of value - hold funds without volatility risk",
            "Payment aggregation - consolidate multiple payment methods",
            "Merchant settlements - receive payments with instant finality"
        ]
    }
}


class ProtocolProcessor(BaseProcessor):
    """Processes protocol research commands with intelligent routing."""
    
    def __init__(self, **kwargs):
        """Initialize protocol processor with router."""
        super().__init__(**kwargs)
        self.router = ResearchRouter()
    
    async def process(self, unified_command: UnifiedCommand) -> UnifiedResponse:
        """
        Process protocol research command with intelligent routing.
        
        Routes to appropriate tool based on intent:
        - concept: Built-in knowledge base
        - depth: Firecrawl deep research
        - discovery: Exa opportunity finding
        
        ENHANCEMENT FIRST: Uses built-in knowledge base when available
        """
        try:
            logger.info(f"Processing protocol research: {unified_command.command}")
            
            # Classify intent and get routing decision
            routing_decision = self.router.classify_intent(unified_command.command)
            self.router.log_routing_decision(routing_decision)
            
            # Route based on intent
            if routing_decision.intent == "concept":
                return await self._handle_concept_query(routing_decision, unified_command)
            elif routing_decision.intent == "depth":
                return await self._handle_depth_query(routing_decision, unified_command)
            elif routing_decision.intent == "discovery":
                return await self._handle_discovery_query(routing_decision, unified_command)
            else:
                # Fallback
                return self._create_error_response(
                    "Unable to understand your research request",
                    AgentType.PROTOCOL_RESEARCH,
                    f"Unexpected intent: {routing_decision.intent}"
                )
            
        except Exception as e:
            logger.exception("Error processing protocol research")
            return self._create_error_response(
                "Protocol research service is temporarily unavailable",
                AgentType.PROTOCOL_RESEARCH,
                str(e)
            )
    
    async def _handle_concept_query(
        self,
        routing_decision,
        unified_command: UnifiedCommand
    ) -> UnifiedResponse:
        """Handle concept/educational queries (knowledge base first)."""
        try:
            concept_name = self.router.transform_query_for_tool(routing_decision)
            logger.info(f"Handling concept query: {concept_name}")
            
            # Check knowledge base
            kb_result = self._find_in_knowledge_base(concept_name)
            if kb_result:
                matched_key, knowledge_match = kb_result
                logger.info(f"Found '{concept_name}' in knowledge base as '{matched_key}'")
                return self._create_response_from_knowledge(matched_key, knowledge_match)
            
            # Fallback to AI for unknown concepts
            logger.info(f"Concept '{concept_name}' not in KB, using AI fallback")
            return await self._create_ai_fallback_response(
                concept_name,
                unified_command.openai_api_key
            )
            
        except Exception as e:
            logger.error(f"Error handling concept query: {e}")
            return self._create_error_response(
                "Unable to answer that question",
                AgentType.PROTOCOL_RESEARCH,
                str(e)
            )
    
    async def _handle_depth_query(
        self,
        routing_decision,
        unified_command: UnifiedCommand
    ) -> UnifiedResponse:
        """Handle depth queries (specific protocol research)."""
        try:
            # Use extracted entity name for KB lookup, not transformed query
            protocol_name = routing_decision.extracted_entity or self.router.transform_query_for_tool(routing_decision)
            logger.info(f"Handling depth query: {protocol_name} (extracted: {routing_decision.extracted_entity})")
            
            # Try knowledge base first with the extracted entity name
            kb_result = self._find_in_knowledge_base(protocol_name)
            if kb_result:
                # kb_result is (matched_key, knowledge_dict) tuple
                matched_key, knowledge_match = kb_result
                logger.info(f"Found '{protocol_name}' in knowledge base as '{matched_key}'")
                return self._create_response_from_knowledge(matched_key, knowledge_match)
            
            # Use Firecrawl for detailed research
            logger.info(f"Attempting Firecrawl for {protocol_name}")
            from app.core.dependencies import get_service_container
            from app.config.settings import get_settings
            
            container = get_service_container(get_settings())
            firecrawl_client = container.get_firecrawl_client()
            
            scrape_result = await get_protocol_details(
                firecrawl_client,
                protocol_name,
                use_llm_extraction=True,
            )
            
            if scrape_result.get("scraping_success", False):
                # Analyze with AI
                openai_key = unified_command.openai_api_key or os.getenv("OPENAI_API_KEY")
                logger.info(f"Starting AI analysis for {protocol_name}")
                
                ai_result = await analyze_protocol_with_ai(
                    protocol_name=protocol_name,
                    raw_content=scrape_result.get("raw_content", ""),
                    source_url=scrape_result.get("source_url", ""),
                    openai_api_key=openai_key,
                )
                
                result = {**scrape_result, **ai_result}
                
                content = {
                    "message": f"Research complete for {protocol_name}",
                    "type": "protocol_research_result",
                    "protocol_name": protocol_name,
                    "ai_summary": result.get("ai_summary", ""),
                    "source_url": result.get("source_url", ""),
                    "raw_content": result.get("raw_content", ""),
                    "analysis_success": result.get("analysis_success", False),
                    "requires_transaction": False,
                }
                
                return self._create_success_response(
                    content=content,
                    agent_type=AgentType.PROTOCOL_RESEARCH,
                    metadata={
                        "parsed_command": {
                            "protocol": protocol_name,
                            "command_type": "protocol_research"
                        },
                        "research_details": {
                            "scraping_success": True,
                            "source": "firecrawl",
                        }
                    }
                )
            else:
                logger.warning(f"Firecrawl scraping failed for {protocol_name}")
                raise FirecrawlError(scrape_result.get("error", "Unknown error"))
                
        except (FirecrawlError, Exception) as e:
            logger.warning(f"Depth research failed: {e}, falling back to AI")
            protocol_name = routing_decision.original_query
            return await self._create_ai_fallback_response(
                protocol_name,
                unified_command.openai_api_key
            )
    
    async def _handle_discovery_query(
        self,
        routing_decision,
        unified_command: UnifiedCommand
    ) -> UnifiedResponse:
        """Handle discovery queries (opportunity finding with Exa)."""
        try:
            query = self.router.transform_query_for_tool(routing_decision)
            logger.info(f"Handling discovery query: {query}")
            
            # Get Exa client with optional caching
            from app.core.dependencies import get_service_container
            from app.config.settings import get_settings
            
            container = get_service_container(get_settings())
            exa_client = container.get_exa_client()
            
            # Use Exa for opportunity discovery
            exa_result = await exa_client.search_opportunities(
                query=query,
                max_results=5,
                cache=True,
            )
            
            if exa_result.get("search_success", False) and exa_result.get("protocols"):
                protocols = exa_result.get("protocols", [])
                
                content = {
                    "message": f"Found {len(protocols)} DeFi opportunity/opportunities",
                    "type": "discovery_result",
                    "opportunities": protocols,
                    "summary": {
                        "count": exa_result.get("protocols_found", 0),
                        "yield_opportunities": exa_result.get("yield_opportunities", 0),
                        "best_apy": exa_result.get("best_apy_found", "Unknown"),
                    },
                    "requires_transaction": False,
                }
                
                return self._create_success_response(
                    content=content,
                    agent_type=AgentType.PROTOCOL_RESEARCH,
                    metadata={
                        "parsed_command": {
                            "query": routing_decision.original_query,
                            "command_type": "opportunity_discovery"
                        },
                        "research_details": {
                            "tool": "exa",
                            "protocols_found": exa_result.get("protocols_found", 0),
                            "yield_opportunities": exa_result.get("yield_opportunities", 0),
                        }
                    }
                )
            else:
                error_msg = exa_result.get("error", "No protocols found")
                logger.warning(f"Exa discovery failed: {error_msg}")
                return self._create_error_response(
                    f"Unable to find opportunities: {error_msg}",
                    AgentType.PROTOCOL_RESEARCH,
                    error_msg
                )
            
        except Exception as e:
            logger.error(f"Error handling discovery query: {e}")
            return self._create_error_response(
                "Unable to search for opportunities",
                AgentType.PROTOCOL_RESEARCH,
                str(e)
            )
    
    def _find_in_knowledge_base(self, protocol_name: str) -> Union[tuple, None]:
        """
        Find protocol in knowledge base. Case-insensitive with fuzzy matching (>80% similarity).
        
        Returns:
            Tuple of (matched_key, knowledge_dict) or None if not found.
            The matched_key is the canonical name to use in responses (corrects misspellings).
        """
        protocol_lower = protocol_name.lower().strip()
        
        # Exact match (fastest path)
        if protocol_lower in PROTOCOL_KNOWLEDGE_BASE:
            return (protocol_lower, PROTOCOL_KNOWLEDGE_BASE[protocol_lower])
        
        # Check for exact match on official names
        for key, info in PROTOCOL_KNOWLEDGE_BASE.items():
            if protocol_lower in info.get("official_name", "").lower():
                return (key, info)
        
        # Fuzzy match: find best similarity across KB keys
        best_match = None
        best_score = 0.8  # Threshold: >80% similarity required
        
        for key in PROTOCOL_KNOWLEDGE_BASE.keys():
            similarity = SequenceMatcher(None, protocol_lower, key).ratio()
            if similarity > best_score:
                best_score = similarity
                best_match = key
                logger.info(f"Fuzzy match: '{protocol_name}' matched '{key}' with {best_score:.1%} confidence")
        
        if best_match:
            return (best_match, PROTOCOL_KNOWLEDGE_BASE[best_match])
        
        return None
    
    def _create_response_from_knowledge(self, protocol_name: str, knowledge: dict) -> UnifiedResponse:
        """Create response from built-in knowledge base."""
        content = {
            "message": f"Here's what I know about {knowledge.get('official_name', protocol_name)}:",
            "type": "protocol_research_result",
            "protocol_name": protocol_name,
            "official_name": knowledge.get("official_name", protocol_name),
            "ai_summary": knowledge.get("summary", ""),
            "protocol_type": knowledge.get("type", "Protocol"),
            "key_features": knowledge.get("key_features", []),
            "analysis_quality": "high",
            "source_url": "",
            "raw_content": "",
            "analysis_success": True,
            "content_length": 0,
            "requires_transaction": False,
            # Additional privacy-specific fields
            "privacy_explanation": knowledge.get("privacy_explanation", ""),
            "technical_explanation": knowledge.get("technical_explanation", ""),
            "how_it_works": knowledge.get("how_it_works", ""),
            "recommended_wallets": knowledge.get("recommended_wallets", []),
            "use_cases": knowledge.get("use_cases", []),
            "from_knowledge_base": True
        }
        
        return self._create_success_response(
            content=content,
            agent_type=AgentType.PROTOCOL_RESEARCH,
            metadata={
                "source": "knowledge_base",
                "protocol": protocol_name,
                "knowledge_base_match": True,
                "research_details": {
                    "source": "snel_built_in_knowledge_base",
                    "guaranteed_accuracy": True,
                    "last_updated": "2024"
                }
            }
        )
    
    async def _create_ai_fallback_response(self, protocol_name: str, openai_key: Union[str, None]) -> UnifiedResponse:
        """Create response using AI when Firecrawl fails and knowledge base is empty."""
        try:
            openai_key = openai_key or os.getenv("OPENAI_API_KEY")
            if not openai_key:
                return self._create_error_response(
                    f"I couldn't find information about {protocol_name} and the research service is unavailable. Please try a different protocol or check the spelling.",
                    AgentType.PROTOCOL_RESEARCH,
                    "No OpenAI key available"
                )
            
            client = AsyncOpenAI(api_key=openai_key)
            
            # Use AI to provide general knowledge about the protocol
            prompt = f"""
You are SNEL, a DeFi expert. The user asked about {protocol_name}.
Your web research failed, but you can still provide useful general knowledge about this protocol if you know about it.

Provide a helpful response about {protocol_name} in this format:
- Brief explanation (1-2 sentences)
- Key features (as a list)
- Type of protocol
- How it relates to DeFi or privacy if applicable

Keep it concise and accurate. If you don't have reliable information, say so clearly.
"""
            
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are SNEL, a knowledgeable DeFi assistant. Provide accurate information about blockchain protocols."
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.3  # Lower temperature for factual accuracy
            )
            
            ai_response = response.choices[0].message.content
            
            content = {
                "message": ai_response,
                "type": "protocol_research_result",
                "protocol_name": protocol_name,
                "ai_summary": ai_response,
                "analysis_quality": "medium",
                "analysis_success": True,
                "from_ai_fallback": True
            }
            
            return self._create_success_response(
                content=content,
                agent_type=AgentType.PROTOCOL_RESEARCH,
                metadata={
                    "source": "ai_fallback",
                    "protocol": protocol_name,
                    "note": "Web research unavailable, using AI general knowledge"
                }
            )
            
        except Exception as e:
            logger.exception(f"AI fallback failed for {protocol_name}")
            return self._create_error_response(
                f"AI fallback failed: {str(e)}",
                AgentType.PROTOCOL_RESEARCH,
                str(e)
            )