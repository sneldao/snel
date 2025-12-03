"""
Protocol research command processor.
Handles protocol research and analysis operations with built-in knowledge base.
Follows ENHANCEMENT FIRST principle: uses existing contextual processor knowledge as fallback.
"""
import logging
import re
import os
from openai import AsyncOpenAI

from app.models.unified_models import (
    UnifiedCommand, UnifiedResponse, AgentType
)
from app.services.external.firecrawl_service import get_protocol_details, analyze_protocol_with_ai
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
    }
}


class ProtocolProcessor(BaseProcessor):
    """Processes protocol research commands."""
    
    async def process(self, unified_command: UnifiedCommand) -> UnifiedResponse:
        """
        Process protocol research command.
        
        Handles:
        - Protocol information gathering (Firecrawl → built-in knowledge base fallback)
        - AI-powered analysis
        - Intelligent fallback for known protocols
        
        ENHANCEMENT FIRST: Uses built-in knowledge base when Firecrawl fails
        """
        try:
            logger.info(f"Processing protocol research: {unified_command.command}")
            
            # Extract protocol name from command
            protocol_name = self._extract_protocol_name(unified_command)
            
            if not protocol_name:
                return self._create_error_response(
                    "Please specify a protocol to research. E.g., 'research Zcash' or 'tell me about privacy'",
                    AgentType.PROTOCOL_RESEARCH,
                    "No protocol specified"
                )
            
            logger.info(f"Researching protocol: {protocol_name}")
            
            # Check knowledge base first for privacy-related protocols
            knowledge_match = self._find_in_knowledge_base(protocol_name)
            if knowledge_match:
                logger.info(f"Found {protocol_name} in knowledge base")
                return self._create_response_from_knowledge(protocol_name, knowledge_match)
            
            # Try Firecrawl for other protocols
            logger.info(f"Attempting Firecrawl scrape for {protocol_name}")
            scrape_result = await get_protocol_details(
                protocol_name=protocol_name,
                max_content_length=2000,
                timeout=15,
                debug=True
            )
            
            if scrape_result.get("scraping_success", False):
                # Analyze scraped content with AI
                openai_key = unified_command.openai_api_key or os.getenv("OPENAI_API_KEY")
                logger.info(f"Starting AI analysis for {protocol_name}")
                
                ai_result = await analyze_protocol_with_ai(
                    protocol_name=protocol_name,
                    raw_content=scrape_result.get("raw_content", ""),
                    source_url=scrape_result.get("source_url", ""),
                    openai_api_key=openai_key
                )
                
                # Combine results
                result = {
                    **scrape_result,
                    **ai_result,
                    "type": "protocol_research_result"
                }
                
                content = {
                    "message": f"Research complete for {protocol_name}",
                    "type": "protocol_research_result",
                    "protocol_name": protocol_name,
                    "ai_summary": result.get("ai_summary", ""),
                    "protocol_type": result.get("protocol_type", "DeFi Protocol"),
                    "key_features": result.get("key_features", []),
                    "security_info": result.get("security_info", ""),
                    "financial_metrics": result.get("financial_metrics", ""),
                    "analysis_quality": result.get("analysis_quality", "medium"),
                    "source_url": result.get("source_url", ""),
                    "raw_content": result.get("raw_content", ""),
                    "analysis_success": result.get("analysis_success", False),
                    "content_length": result.get("content_length", 0),
                    "requires_transaction": False
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
                            "protocols_scraped": result.get("protocols_scraped", 1),
                            "scraping_success": result.get("scraping_success", False),
                            "source": result.get("source", "firecrawl")
                        }
                    }
                )
            else:
                # Firecrawl failed - try fallback to general knowledge or AI explanation
                logger.warning(f"Firecrawl failed for {protocol_name}, attempting AI fallback")
                return await self._create_ai_fallback_response(
                    protocol_name, 
                    unified_command.openai_api_key
                )
            
        except Exception as e:
            logger.exception("Error processing protocol research")
            return self._create_error_response(
                "Protocol research service is temporarily unavailable",
                AgentType.PROTOCOL_RESEARCH,
                str(e)
            )
    
    def _extract_protocol_name(self, unified_command: UnifiedCommand) -> str:
        """Extract protocol name from command."""
        details = unified_command.details
        
        # Try to extract from details first
        if details and details.token_in and details.token_in.symbol:
            return details.token_in.symbol
        
        if details and hasattr(details, 'protocol_name'):
            return details.protocol_name
        
        # Extract from command text using regex
        command_lower = unified_command.command.lower()
        patterns = [
            r'research\s+(\w+)',
            r'tell me about\s+(\w+)',
            r'what is\s+(\w+)',
            r'about\s+(\w+)',
            r'info on\s+(\w+)',
            r'explain\s+(\w+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, command_lower)
            if match:
                return match.group(1)
        
        return None
    
    def _find_in_knowledge_base(self, protocol_name: str) -> dict | None:
        """Find protocol in knowledge base. Case-insensitive with fuzzy matching."""
        protocol_lower = protocol_name.lower()
        
        # Exact match
        if protocol_lower in PROTOCOL_KNOWLEDGE_BASE:
            return PROTOCOL_KNOWLEDGE_BASE[protocol_lower]
        
        # Fuzzy match on protocol names
        for key, info in PROTOCOL_KNOWLEDGE_BASE.items():
            if protocol_lower == key or protocol_lower in [key] + info.get("aliases", []):
                return info
            # Partial match on official name
            if protocol_lower in info.get("official_name", "").lower():
                return info
        
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
    
    async def _create_ai_fallback_response(self, protocol_name: str, openai_key: str | None) -> UnifiedResponse:
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
                f"I couldn't find information about {protocol_name}. Please try a different protocol or rephrase your question.",
                AgentType.PROTOCOL_RESEARCH,
                str(e)
            )
