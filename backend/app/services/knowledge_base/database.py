"""Knowledge base database with static entries and dynamic metrics."""
import logging
from typing import Dict, Optional, Tuple
from datetime import datetime
from difflib import SequenceMatcher

from .models import ProtocolEntry, ProtocolMetrics

logger = logging.getLogger(__name__)


class ProtocolKnowledgeBase:
    """Single source of truth for protocol information (static + dynamic)."""
    
    def __init__(self):
        """Initialize KB with static protocol data."""
        self.static_entries: Dict[str, ProtocolEntry] = self._init_static_protocols()
        self.metrics: Dict[str, ProtocolMetrics] = {}  # Dynamic, updated via Firecrawl
        self.query_analytics: Dict[str, int] = {}  # Track KB misses
    
    def get(self, protocol_name: str) -> Optional[Tuple[str, ProtocolEntry]]:
        """
        Get protocol entry with exact, alias, and fuzzy matching.
        
        Returns:
            Tuple of (canonical_key, entry) or None.
            canonical_key is used in responses (corrects misspellings).
        """
        protocol_lower = protocol_name.lower().strip()
        
        # 1. Exact match on key (fastest)
        if protocol_lower in self.static_entries:
            return (protocol_lower, self.static_entries[protocol_lower])
        
        # 2. Check aliases
        for key, entry in self.static_entries.items():
            if protocol_lower in [alias.lower() for alias in entry.aliases]:
                logger.info(f"Alias match: '{protocol_name}' -> '{key}'")
                return (key, entry)
        
        # 3. Exact match on official_name
        for key, entry in self.static_entries.items():
            if protocol_lower in entry.official_name.lower():
                return (key, entry)
        
        # 4. Fuzzy match on keys (>80% similarity)
        best_match = None
        best_score = 0.80
        
        for key in self.static_entries.keys():
            similarity = SequenceMatcher(None, protocol_lower, key).ratio()
            if similarity > best_score:
                best_score = similarity
                best_match = key
                logger.info(f"Fuzzy match: '{protocol_name}' -> '{key}' ({best_score:.1%} confidence)")
        
        if best_match:
            return (best_match, self.static_entries[best_match])
        
        # Track miss for analytics
        self.query_analytics[protocol_lower] = self.query_analytics.get(protocol_lower, 0) + 1
        return None
    
    def get_metrics(self, protocol_name: str) -> Optional[ProtocolMetrics]:
        """Get dynamic metrics for protocol (e.g., TVL, volume from Firecrawl cache)."""
        key = self._normalize_key(protocol_name)
        return self.metrics.get(key)
    
    def update_metrics(self, protocol_name: str, metrics: ProtocolMetrics) -> None:
        """Cache metrics from Firecrawl or external sources (enrichment)."""
        key = self._normalize_key(protocol_name)
        metrics.last_updated = datetime.utcnow()
        self.metrics[key] = metrics
        logger.info(f"Updated metrics for '{protocol_name}': {metrics.source}")
    
    def get_top_misses(self, limit: int = 20) -> list:
        """Get most frequently searched but not-found protocols (for KB gap analysis)."""
        return sorted(
            self.query_analytics.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]
    
    @staticmethod
    def _normalize_key(name: str) -> str:
        """Normalize protocol name to KB key."""
        return name.lower().strip()
    
    def _init_static_protocols(self) -> Dict[str, ProtocolEntry]:
        """Initialize static protocol knowledge base."""
        return {
            "zcash": ProtocolEntry(
                official_name="Zcash",
                type="Privacy-Preserving Cryptocurrency",
                aliases=["zec", "zcash protocol", "zec token"],
                summary="Zcash is a cryptocurrency built on the Bitcoin blockchain that enables private and transparent transactions. It uses zero-knowledge proofs to allow users to hide transaction details while still verifying transactions on the blockchain.",
                key_features=[
                    "Shielded transactions - hide sender, receiver, and amount",
                    "Zero-knowledge proofs for transaction verification",
                    "Unified Addresses (UA) - work across all address types",
                    "Encrypted transaction memos - send private messages",
                    "Optional transparency - users choose to disclose transactions when needed"
                ],
                privacy_explanation="Zcash uses zk-SNARKs (zero-knowledge Succinct Non-interactive ARguments of Knowledge) to prove transaction validity without revealing sender, receiver, or amount. Transaction history is encrypted and only visible to the transaction participants.",
                technical_explanation="Zcash implements zk-SNARKs circuits (Sprout, Sapling, Orchard) that allow zero-knowledge proofs of transaction validity. Shielded transactions use elliptic curve cryptography and commitment schemes to hide amounts while preserving blockchain verification.",
                how_it_works="When you send a shielded transaction in Zcash, the transaction is encrypted. The sender proves they have the funds without revealing their address, and the recipient can decrypt the transaction with their private viewing key. All of this happens while maintaining blockchain verification.",
                use_cases=[
                    "Private financial transactions",
                    "Confidential business payments",
                    "Personal financial privacy",
                    "Protection from transaction surveillance"
                ],
                recommended_wallets=[
                    {"name": "Zashi", "type": "Mobile", "url": "https://zashi.app/", "note": "Official Zcash mobile wallet, shielded by default"},
                    {"name": "Nighthawk", "type": "Desktop", "url": "https://nighthawkwallet.com/", "note": "Full desktop support, shielded by default"}
                ],
                names={"en": "Zcash", "es": "Zcash", "zh": "Zcash"},
                audits=[
                    {"firm": "Trail of Bits", "date": "2023-Q3", "status": "passed"},
                    {"firm": "Least Authority", "date": "2023-Q2", "status": "passed"},
                ],
                governance_token=None,
                integrations_with=["bitcoin", "ethereum"],
                bridges_to=["ethereum", "polygon"],
                last_verified=datetime(2024, 1, 6),
            ),
            "privacy": ProtocolEntry(
                official_name="Privacy Features",
                type="Concept",
                aliases=["privacy concept", "transaction privacy", "anonymity"],
                summary="Privacy features enable users to transact on blockchain without revealing sensitive information.",
                key_features=[
                    "Transaction privacy - amounts and participants are hidden",
                    "Anonymity - transactions blend with others in privacy pools",
                    "Selective disclosure - optionally prove transaction history when needed",
                    "Zero-knowledge proofs - mathematical verification without revealing data"
                ],
                how_it_works="Privacy transactions use cryptographic techniques (zero-knowledge proofs) to prove transactions are valid without revealing the transaction details. This means the blockchain network can verify transactions without knowing who sent what to whom.",
                privacy_explanation="Privacy in blockchain means your transaction details (who sent to whom, how much) are not publicly visible. Instead of storing plain information on the blockchain, cryptographic proofs ensure transactions are valid while keeping details private.",
                use_cases=[
                    "Protecting financial data from public view",
                    "Confidential corporate transactions",
                    "Personal security",
                ],
                recommended_wallets=[
                    {"name": "Zashi", "type": "Mobile", "url": "https://zashi.app/", "note": "Zcash mobile wallet with shielded by default"},
                    {"name": "Nighthawk", "type": "Desktop", "url": "https://nighthawkwallet.com/", "note": "Desktop privacy wallet for Zcash"}
                ],
                names={"en": "Privacy Features", "es": "Características de Privacidad", "zh": "隐私功能"},
                last_verified=datetime(2024, 1, 6),
            ),
            "shielded transactions": ProtocolEntry(
                official_name="Shielded Transactions",
                type="Zcash Feature",
                aliases=["shielded", "zec shielded", "private transactions"],
                summary="Transactions that encrypt the sender, receiver, and amount using zero-knowledge proofs.",
                key_features=[
                    "Sender privacy - your address is hidden",
                    "Receiver privacy - recipient address is hidden",
                    "Amount privacy - transaction amount is encrypted",
                    "Memo privacy - encrypted messages between sender and receiver"
                ],
                technical_explanation="Shielded transactions use the Sprout and Sapling circuits (or Orchard in newer versions) to prove transaction validity. The sender proves they have the funds and the receiver can decrypt the transaction, all without revealing information to the blockchain.",
                privacy_explanation="Shielded transactions hide all sensitive information while proving the transaction is valid. Unlike transparent transactions, shielded transactions encrypt sender, receiver, and amount - making them completely private on the blockchain.",
                how_it_works="To send a shielded transaction: 1) You initiate the transaction with encrypted details, 2) Zero-knowledge proofs verify you have the funds without revealing your address, 3) The recipient receives the encrypted data and decrypts it with their private key. The blockchain records only that a valid transaction occurred, not the details.",
                recommended_wallets=[
                    {"name": "Zashi", "type": "Mobile", "url": "https://zashi.app/", "note": "Official mobile wallet, shielded by default"},
                    {"name": "Nighthawk", "type": "Desktop", "url": "https://nighthawkwallet.com/", "note": "Full-featured desktop wallet with shielding"}
                ],
                names={"en": "Shielded Transactions", "es": "Transacciones Protegidas", "zh": "屏蔽交易"},
                last_verified=datetime(2024, 1, 6),
            ),
            "bridging": ProtocolEntry(
                official_name="Cross-Chain Bridging",
                type="DeFi Operation",
                aliases=["bridge", "cross-chain", "atomic swap"],
                summary="Moving assets from one blockchain to another securely using bridge protocols.",
                key_features=[
                    "Cross-chain transfers - send assets between different blockchains",
                    "Wrapped tokens - represent assets on non-native blockchains",
                    "Multi-step transactions - approval followed by actual bridge",
                    "Security checks - verification that assets arrive safely"
                ],
                how_it_works="Bridges lock assets on the source chain and mint equivalent wrapped tokens on the destination chain. When you return the wrapped tokens, the original assets are unlocked.",
                use_cases=[
                    "Move liquidity between chains",
                    "Access different DeFi protocols on other chains",
                    "Optimize fees by finding cheaper chains",
                ],
                custom_fields={"privacy_bridge_explanation": "Privacy bridging allows you to move assets from public chains (Ethereum, Polygon, Base, etc.) to privacy chains (Zcash) so your transaction becomes private on the destination chain."},
                bridges_to=["ethereum", "polygon", "base", "arbitrum", "optimism"],
                names={"en": "Cross-Chain Bridging", "es": "Puentes Entre Cadenas", "zh": "跨链桥接"},
                last_verified=datetime(2024, 1, 6),
            ),
            "axelar": ProtocolEntry(
                official_name="Axelar",
                type="Cross-Chain Infrastructure",
                aliases=["axl", "axelar network"],
                summary="Axelar is a network that enables secure cross-chain communication and asset transfers using General Message Passing (GMP).",
                key_features=[
                    "General Message Passing (GMP) - send messages between blockchains",
                    "Secure verification - validator network ensures message integrity",
                    "Multi-chain support - connects 16+ blockchain networks",
                    "Standardized protocols - consistent interface across chains"
                ],
                governance_token="AXL",
                audits=[
                    {"firm": "Halborn", "date": "2023-Q1", "status": "passed"},
                ],
                integrations_with=["ethereum", "polygon", "arbitrum", "optimism", "moonbeam"],
                bridges_to=["ethereum", "polygon", "arbitrum", "optimism"],
                names={"en": "Axelar", "es": "Axelar", "zh": "Axelar"},
                last_verified=datetime(2024, 1, 6),
            ),
            "mnee": ProtocolEntry(
                official_name="MNEE Stablecoin",
                type="Stablecoin for Commerce & Payments",
                aliases=["mnee token", "mnee stablecoin", "mnee coin"],
                summary="MNEE is a programmable stablecoin designed for efficient commerce and payment transactions on the blockchain. It provides stable value pegged to fiat currency while enabling instant, low-cost transactions across multiple blockchains.",
                key_features=[
                    "Stable value pegged to USD - maintains price stability for transactions",
                    "Programmable payments - conditional execution of transactions",
                    "Optimized for commerce - built specifically for e-commerce and payment flows",
                    "Low transaction fees - efficient for frequent microtransactions",
                    "Multi-chain compatibility - works across multiple blockchain networks",
                    "DeFi protocol integration - compatible with existing DeFi ecosystems",
                    "Instant settlement - fast transaction finality for payment confirmations"
                ],
                how_it_works="MNEE enables merchants and users to conduct transactions on blockchain while maintaining price stability. Each MNEE token represents $1 USD, making it ideal for price prediction and budgeting. Transactions are verified across the blockchain network and settle instantly.",
                use_cases=[
                    "E-commerce payments - online shopping and digital goods",
                    "Point-of-sale transactions - in-store payments with blockchain settlement",
                    "Subscription payments - recurring payment automation",
                    "Cross-border payments - send value internationally with minimal fees",
                    "Payment channels - micropayment support for digital content",
                    "DeFi yield farming - earn passive income on holdings",
                    "Stable store of value - hold funds without volatility risk",
                ],
                governance_token=None,
                integrations_with=["uniswap", "aave", "curve"],
                bridges_to=["ethereum", "polygon", "base", "arbitrum"],
                competes_with=["usdc", "usdt", "dai"],
                names={"en": "MNEE Stablecoin", "es": "Moneda Estable MNEE", "zh": "MNEE稳定币"},
                last_verified=datetime(2024, 1, 6),
            ),
        }


# Singleton instance
_kb_instance: Optional[ProtocolKnowledgeBase] = None


def get_protocol_kb() -> ProtocolKnowledgeBase:
    """Get or create singleton KB instance."""
    global _kb_instance
    if _kb_instance is None:
        _kb_instance = ProtocolKnowledgeBase()
    return _kb_instance
