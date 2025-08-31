"""
Permit2 Handler for 0x Protocol v2 EIP-712 Integration.

This module provides comprehensive support for Permit2 signature handling,
EIP-712 message formatting, and transaction data concatenation as required
by 0x Protocol v2.

Key Features:
- EIP-712 message formatting for Permit2 signatures
- Transaction data concatenation with signature
- Permit2 contract validation
- Signature length calculation and encoding
- Domain separator validation

Standards Compliance:
- EIP-712: Typed structured data hashing and signing
- EIP-2612: Permit extension for ERC-20
- Permit2: Universal token approval contract
"""

import logging
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Permit2Data:
    """Structured Permit2 data from 0x API response."""
    permit_type: str
    hash: str
    eip712: Dict[str, Any]
    signature_deadline: int
    nonce: str


class Permit2Handler:
    """
    Handles Permit2 EIP-712 signature operations for 0x Protocol v2.

    The Permit2 system eliminates the need for token-specific approvals by using
    a universal approval contract and EIP-712 signatures for each transaction.
    """

    # Permit2 contract address (same across all chains)
    PERMIT2_ADDRESS = "0x000000000022d473030f116ddee9f6b43ac78ba3"

    # Standard EIP-712 domain for Permit2
    PERMIT2_DOMAIN_NAME = "Permit2"

    def __init__(self):
        self.name = "Permit2Handler"

    def extract_permit2_data(self, api_response: Dict[str, Any]) -> Optional[Permit2Data]:
        """
        Extract and validate Permit2 data from 0x API response.

        Args:
            api_response: Raw response from 0x /swap/permit2/quote endpoint

        Returns:
            Permit2Data object if permit2 data exists, None otherwise
        """
        permit2_raw = api_response.get("permit2")
        if not permit2_raw:
            logger.debug("No permit2 data in API response")
            return None

        try:
            eip712_data = permit2_raw.get("eip712", {})
            if not eip712_data:
                logger.warning("permit2 data exists but missing eip712 field")
                return None

            # Validate required EIP-712 fields
            required_fields = ["types", "domain", "message", "primaryType"]
            for field in required_fields:
                if field not in eip712_data:
                    logger.error(f"Missing required EIP-712 field: {field}")
                    return None

            # Extract deadline from message
            message = eip712_data.get("message", {})
            deadline = message.get("deadline", 0)

            return Permit2Data(
                permit_type=permit2_raw.get("type", "Permit2"),
                hash=permit2_raw.get("hash", ""),
                eip712=eip712_data,
                signature_deadline=int(deadline),
                nonce=message.get("nonce", "0")
            )

        except Exception as e:
            logger.error(f"Failed to extract permit2 data: {e}")
            return None

    def validate_permit2_contract(self, chain_id: int, contract_address: str) -> bool:
        """
        Validate that the provided contract address matches the expected Permit2 contract.

        Args:
            chain_id: Chain ID for the transaction
            contract_address: Contract address to validate

        Returns:
            True if address matches expected Permit2 contract
        """
        expected = self.PERMIT2_ADDRESS.lower()
        actual = contract_address.lower() if contract_address else ""

        is_valid = actual == expected

        if not is_valid:
            logger.warning(
                f"Permit2 contract address mismatch on chain {chain_id}. "
                f"Expected: {expected}, Got: {actual}"
            )

        return is_valid

    def format_eip712_message(self, permit2_data: Permit2Data, chain_id: int) -> Dict[str, Any]:
        """
        Format EIP-712 message for signing.

        Args:
            permit2_data: Permit2 data from 0x API
            chain_id: Chain ID for domain validation

        Returns:
            Formatted EIP-712 message ready for signing
        """
        eip712 = permit2_data.eip712

        # Validate domain
        domain = eip712.get("domain", {})
        if domain.get("chainId") != chain_id:
            logger.warning(f"Chain ID mismatch in EIP-712 domain: expected {chain_id}, got {domain.get('chainId')}")

        if domain.get("verifyingContract", "").lower() != self.PERMIT2_ADDRESS.lower():
            logger.warning(f"Verifying contract mismatch: expected {self.PERMIT2_ADDRESS}, got {domain.get('verifyingContract')}")

        # Return formatted message for wallet signing
        return {
            "types": eip712["types"],
            "domain": domain,
            "message": eip712["message"],
            "primaryType": eip712["primaryType"]
        }

    def validate_signature_deadline(self, permit2_data: Permit2Data, buffer_seconds: int = 300) -> bool:
        """
        Validate that the permit2 signature deadline hasn't expired.

        Args:
            permit2_data: Permit2 data with deadline
            buffer_seconds: Safety buffer before deadline (default 5 minutes)

        Returns:
            True if deadline is valid (not expired with buffer)
        """
        if permit2_data.signature_deadline == 0:
            logger.warning("Permit2 deadline is 0 (unlimited) - this may not be secure")
            return True

        current_timestamp = int(datetime.utcnow().timestamp())
        deadline_with_buffer = permit2_data.signature_deadline - buffer_seconds

        is_valid = current_timestamp < deadline_with_buffer

        if not is_valid:
            logger.error(
                f"Permit2 signature deadline exceeded. "
                f"Current: {current_timestamp}, Deadline: {permit2_data.signature_deadline}, "
                f"Buffer: {buffer_seconds}s"
            )

        return is_valid

    def calculate_signature_length_bytes(self, signature: str) -> bytes:
        """
        Calculate the signature length in bytes for transaction data concatenation.

        Args:
            signature: Hex signature string (with or without 0x prefix)

        Returns:
            32-byte representation of signature length
        """
        # Remove 0x prefix if present
        if signature.startswith("0x"):
            signature = signature[2:]

        # Calculate length in bytes
        signature_length = len(signature) // 2

        # Convert to 32-byte hex (64 hex characters)
        length_hex = hex(signature_length)[2:].zfill(64)

        return bytes.fromhex(length_hex)

    def concat_transaction_data(
        self,
        original_data: str,
        signature: str
    ) -> str:
        """
        Concatenate original transaction data with permit2 signature.

        This follows the 0x v2 specification:
        final_data = original_data + signature_length_bytes + signature

        Args:
            original_data: Original transaction data from 0x quote
            signature: EIP-712 signature from user wallet

        Returns:
            Complete transaction data with signature appended
        """
        # Remove 0x prefix from inputs
        if original_data.startswith("0x"):
            original_data = original_data[2:]
        if signature.startswith("0x"):
            signature = signature[2:]

        # Validate signature length (should be 65 bytes = 130 hex chars for ECDSA)
        if len(signature) != 130:
            logger.warning(f"Unexpected signature length: {len(signature)} chars (expected 130)")

        # Calculate signature length in bytes
        signature_length_bytes = self.calculate_signature_length_bytes("0x" + signature)
        signature_length_hex = signature_length_bytes.hex()

        # Concatenate: original + length + signature
        final_data = original_data + signature_length_hex + signature

        logger.debug("Transaction data concatenation:")
        logger.debug(f"  Original data: {original_data[:50]}... ({len(original_data)} chars)")
        logger.debug(f"  Signature length: {signature_length_hex} ({len(signature_length_hex)} chars)")
        logger.debug(f"  Signature: {signature[:20]}...{signature[-20:]} ({len(signature)} chars)")
        logger.debug(f"  Final data: {final_data[:50]}... ({len(final_data)} chars)")

        return "0x" + final_data

    def validate_signature_format(self, signature: str) -> Tuple[bool, str]:
        """
        Validate EIP-712 signature format.

        Args:
            signature: Signature string to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not signature:
            return False, "Signature is empty"

        # Remove 0x prefix for length calculation
        sig_without_prefix = signature[2:] if signature.startswith("0x") else signature

        # Check for valid hex
        try:
            int(sig_without_prefix, 16)
        except ValueError:
            return False, "Signature contains invalid hex characters"

        # ECDSA signature should be 65 bytes = 130 hex characters
        expected_length = 130
        if len(sig_without_prefix) != expected_length:
            return False, f"Invalid signature length: {len(sig_without_prefix)} (expected {expected_length})"

        return True, ""

    def extract_allowance_info(self, api_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract allowance information from 0x API response.

        In Permit2, the allowance target is always the Permit2 contract,
        while the transaction goes to a dynamic Settler contract.

        Args:
            api_response: Raw response from 0x API

        Returns:
            Dict with allowance information
        """
        issues = api_response.get("issues", {})
        allowance_issue = issues.get("allowance", {})

        # In Permit2, spender should be the Permit2 contract
        spender = allowance_issue.get("spender", self.PERMIT2_ADDRESS)
        actual_allowance = allowance_issue.get("actual", "0")
        expected_allowance = allowance_issue.get("expected", "0")

        needs_approval = int(actual_allowance) < int(expected_allowance)

        # Validate spender is Permit2 contract
        if spender.lower() != self.PERMIT2_ADDRESS.lower():
            logger.warning(f"Unexpected allowance spender: {spender} (expected {self.PERMIT2_ADDRESS})")

        return {
            "spender": spender,
            "actual_allowance": actual_allowance,
            "expected_allowance": expected_allowance,
            "needs_approval": needs_approval,
            "is_permit2": spender.lower() == self.PERMIT2_ADDRESS.lower()
        }

    def get_transaction_entry_point(self, api_response: Dict[str, Any]) -> Optional[str]:
        """
        Extract the transaction entry point (Settler contract) from API response.

        In 0x v2, the transaction goes to a dynamic Settler contract,
        not the Permit2 contract.

        Args:
            api_response: Raw response from 0x API

        Returns:
            Settler contract address or None
        """
        transaction = api_response.get("transaction", {})
        entry_point = transaction.get("to")

        if not entry_point:
            logger.error("No transaction entry point (to address) in API response")
            return None

        # Validate it's not the Permit2 contract (common mistake)
        if entry_point.lower() == self.PERMIT2_ADDRESS.lower():
            logger.warning("Entry point is Permit2 contract - this may be incorrect")

        logger.debug(f"Transaction entry point: {entry_point}")
        return entry_point

    def create_permit2_summary(self, api_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a comprehensive summary of Permit2 transaction requirements.

        Args:
            api_response: Raw response from 0x API

        Returns:
            Summary of all Permit2 requirements and data
        """
        permit2_data = self.extract_permit2_data(api_response)
        allowance_info = self.extract_allowance_info(api_response)
        entry_point = self.get_transaction_entry_point(api_response)

        transaction = api_response.get("transaction", {})

        summary = {
            "requires_permit2": permit2_data is not None,
            "requires_signature": permit2_data is not None,
            "allowance_target": allowance_info.get("spender"),
            "needs_approval": allowance_info.get("needs_approval", False),
            "transaction_entry_point": entry_point,
            "original_transaction_data": transaction.get("data"),
            "transaction_value": transaction.get("value", "0"),
            "permit2_data": permit2_data,
            "allowance_info": allowance_info
        }

        if permit2_data:
            summary["signature_deadline"] = permit2_data.signature_deadline
            summary["permit2_nonce"] = permit2_data.nonce
            summary["eip712_message"] = self.format_eip712_message(
                permit2_data,
                int(api_response.get("chainId", 1))
            )

        logger.debug(f"Permit2 summary created: requires_permit2={summary['requires_permit2']}, "
                    f"needs_approval={summary['needs_approval']}")

        return summary
