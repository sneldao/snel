from fastapi import APIRouter, Depends, Request, HTTPException
import logging
import os
from typing import Dict, Optional, Tuple, Any
from web3 import Web3
from eth_utils import is_address
from app.models.commands import TransactionRequest, TransactionResponse, SwapCommand
from app.config.chains import ChainConfig, TOKEN_ADDRESSES, NATIVE_TOKENS
from app.services.token_service import TokenService
from app.services.prices import get_token_price
from app.api.dependencies import get_openai_key, get_token_service

logger = logging.getLogger(__name__)
router = APIRouter()

# Token decimals mapping
TOKEN_DECIMALS = {
    "ETH": 18,
    "WETH": 18,
    "USDC": 6,
    "USDT": 6,
    "DAI": 18,
    "NURI": 18,  # Adding NURI token with default 18 decimals
}

# Special token addresses that we know about but might not be in the main config
SPECIAL_TOKEN_ADDRESSES = {
    534352: {  # Scroll
        "NURI": "0x0261c29c68a85c1d9f9d2dc0c02b1f9e8e0dC7cc",
    }
}

async def parse_swap_command(
    command: str, 
    chain_id: Optional[int] = None,
    token_service: TokenService = None
) -> SwapCommand:
    """Parse a swap command string into a SwapCommand object."""
    try:
        # Remove 'approved:' prefix if present
        if command.startswith("approved:"):
            command = command[9:]  # Remove 'approved:' prefix
            
        # Check for dollar amount format
        is_dollar_amount = False
        
        # First, try to parse as a regular swap command
        parts = command.split()
        if len(parts) >= 5:
            # Check for dollar amount format: "swap eth for usdc, $1 worth"
            # or "swap $1 worth of eth for usdc"
            dollar_indicators = ["$", "dollar", "dollars", "usd", "worth"]
            
            command_str = command.lower()
            if any(indicator in command_str for indicator in dollar_indicators):
                is_dollar_amount = True
                logger.info(f"Detected dollar amount format in command: {command}")
                
                # Try to extract the dollar amount
                dollar_amount = None
                
                # Pattern: "swap eth for usdc, $1 worth"
                if "," in command_str and "$" in command_str:
                    # Extract the part after the comma
                    after_comma = command_str.split(",", 1)[1].strip()
                    # Extract the number after the $ sign
                    if "$" in after_comma:
                        try:
                            dollar_amount = float(after_comma.split("$")[1].split()[0])
                            logger.info(f"Extracted dollar amount: ${dollar_amount}")
                        except (ValueError, IndexError):
                            logger.error("Failed to extract dollar amount after comma")
                
                # Pattern: "swap $1 worth of eth for usdc"
                elif "$" in command_str and "worth" in command_str and "of" in command_str:
                    try:
                        # Extract the part between $ and "worth"
                        dollar_part = command_str.split("$")[1].split("worth")[0].strip()
                        dollar_amount = float(dollar_part)
                        logger.info(f"Extracted dollar amount from 'worth of' pattern: ${dollar_amount}")
                    except (ValueError, IndexError):
                        logger.error("Failed to extract dollar amount from 'worth of' pattern")
                
                # If we found a dollar amount, we need to determine the tokens
                if dollar_amount is not None:
                    # Extract token_in and token_out
                    token_in = None
                    token_out = None
                    
                    # Pattern: "swap eth for usdc, $1 worth"
                    if "for" in command_str:
                        parts = command_str.split("for")
                        if len(parts) >= 2:
                            # Extract token_in from the part before "for"
                            before_for = parts[0].strip()
                            if "swap" in before_for:
                                token_in_part = before_for.split("swap")[1].strip()
                                if "worth of" in token_in_part:
                                    token_in = token_in_part.split("worth of")[1].strip()
                                else:
                                    token_in = token_in_part
                            
                            # Extract token_out from the part after "for"
                            after_for = parts[1].strip()
                            if "," in after_for:
                                token_out = after_for.split(",")[0].strip()
                            else:
                                token_out = after_for.split()[0].strip()
                    
                    if token_in and token_out:
                        logger.info(f"Extracted tokens from dollar amount command: {token_in} -> {token_out}")
                        
                        # Look up tokens
                        if token_service:
                            token_in_address, token_in_symbol, token_in_name = await token_service.lookup_token(token_in, chain_id)
                            token_out_address, token_out_symbol, token_out_name = await token_service.lookup_token(token_out, chain_id)
                            
                            # Use the canonical symbols if found
                            if token_in_symbol:
                                token_in = token_in_symbol
                            if token_out_symbol:
                                token_out = token_out_symbol
                        
                        # For dollar amount swaps, we need to calculate the token amount
                        # This will be handled by the pipeline, so we just set is_target_amount=False
                        # and amount_is_usd=True
                        return SwapCommand(
                            action="swap",
                            amount=dollar_amount,
                            token_in=token_in.upper(),
                            token_out=token_out.upper(),
                            is_target_amount=False,
                            amount_is_usd=True
                        )
        
        # If not a dollar amount format, proceed with regular parsing
        if len(parts) == 5 and parts[0].lower() == "swap" and (parts[3].lower() == "for" or parts[3].lower() == "to"):
            # Get tokens
            token_in = parts[2]
            token_out = parts[4]
            
            # Look up tokens
            if token_service:
                token_in_address, token_in_symbol, token_in_name = await token_service.lookup_token(token_in, chain_id)
                token_out_address, token_out_symbol, token_out_name = await token_service.lookup_token(token_out, chain_id)
                
                # Use the canonical symbols if found
                if token_in_symbol:
                    token_in = token_in_symbol
                if token_out_symbol:
                    token_out = token_out_symbol
            
            try:
                # Try to parse amount as float
                amount = float(parts[1])
                
                # If amount is very small (like 0.000373) and token is ETH, this is likely a calculated amount
                # from a target amount swap, so we should use it directly
                if token_in == "ETH" and amount < 0.01:
                    logger.info(f"Using pre-calculated ETH amount: {amount}")
                    return SwapCommand(
                        action="swap",
                        amount=amount,
                        token_in=token_in,
                        token_out=token_out,
                        is_target_amount=False
                    )
                    
                return SwapCommand(
                    action="swap",
                    amount=amount,
                    token_in=token_in,
                    token_out=token_out,
                    is_target_amount=False
                )
            except ValueError:
                logger.error(f"Failed to parse amount: {parts[1]}")
                return None
                
        return None
    except (ValueError, IndexError) as e:
        logger.error(f"Failed to parse swap command: {e}")
        return None

@router.post("/api/execute-transaction")
async def execute_transaction(
    request: Request,
    tx_request: TransactionRequest,
    token_service: TokenService = Depends(get_token_service),
    openai_key: str = Depends(get_openai_key)
) -> TransactionResponse:
    try:
        os.environ["OPENAI_API_KEY"] = openai_key
        
        logger.info(f"Executing transaction for command: {tx_request.command} on chain {tx_request.chain_id}")
        
        # Track if this is a post-approval attempt
        is_post_approval = tx_request.command.startswith("approved:")
        
        # Validate chain support
        if not ChainConfig.is_supported(tx_request.chain_id):
            raise ValueError(
                f"Chain {tx_request.chain_id} is not supported. Supported chains: "
                f"{', '.join(f'{name} ({id})' for id, name in ChainConfig.SUPPORTED_CHAINS.items())}"
            )

        # Parse the swap command
        swap_command = await parse_swap_command(tx_request.command, tx_request.chain_id, token_service)
        if not swap_command:
            logger.error(f"Failed to parse swap command: {tx_request.command}")
            raise ValueError(f"Invalid swap command format. Expected format: 'swap 1 usdc for eth', got: {tx_request.command}")

        # Get token addresses
        token_addresses = TOKEN_ADDRESSES.get(tx_request.chain_id, {})
        if not token_addresses:
            raise ValueError(f"No token addresses configured for chain {tx_request.chain_id}")
        
        # Check if we have token addresses in the metadata
        token_in_address = None
        token_out_address = None
        if tx_request.metadata and "swap_details" in tx_request.metadata:
            swap_details = tx_request.metadata.get("swap_details", {})
            token_in_address = swap_details.get("token_in_address")
            token_out_address = swap_details.get("token_out_address")
            logger.info(f"Found token addresses in metadata: in={token_in_address}, out={token_out_address}")
        
        try:
            # Handle dollar amount swaps
            if swap_command.amount_is_usd:
                logger.info(f"Processing dollar amount swap: ${swap_command.amount} worth of {swap_command.token_in} for {swap_command.token_out}")
                
                # Get token price to convert USD to token amount
                price_per_token, token_in_decimals = await get_token_price(
                    swap_command.token_in,
                    token_in_address or token_addresses.get(swap_command.token_in),
                    tx_request.chain_id
                )
                
                if not price_per_token:
                    raise ValueError(f"Could not get price for {swap_command.token_in}")
                
                # Calculate token amount from USD amount
                token_amount = swap_command.amount / price_per_token
                logger.info(f"Converted ${swap_command.amount} to {token_amount} {swap_command.token_in} at price ${price_per_token}")
                
                # Update the swap command with the calculated token amount
                swap_command.amount = token_amount
            else:
                # Get token decimals - first try hardcoded values, then fallback to price API
                token_in_upper = swap_command.token_in.upper()
                if token_in_upper in TOKEN_DECIMALS:
                    token_in_decimals = TOKEN_DECIMALS[token_in_upper]
                    logger.info(f"Using hardcoded decimals for {token_in_upper}: {token_in_decimals}")
                else:
                    _, token_in_decimals = await get_token_price(
                        swap_command.token_in,
                        token_in_address or token_addresses.get(swap_command.token_in),
                        tx_request.chain_id
                    )
            
            # Calculate amount_in based on decimals
            if swap_command.token_in == "ETH":
                # For ETH, we need to be extra careful with the decimal conversion
                # Convert the float amount to wei directly
                amount_in = int(Web3.to_wei(swap_command.amount, 'ether'))
                logger.info(f"Converting {swap_command.amount} ETH to {amount_in} wei")
            else:
                # For other tokens, use their specific decimals
                amount_in = int(swap_command.amount * (10 ** token_in_decimals))
                logger.info(f"Converting {swap_command.amount} {swap_command.token_in} to {amount_in} (using {token_in_decimals} decimals)")
            
            logger.info(f"Calculated amount_in: {amount_in} ({swap_command.amount} * 10^{token_in_decimals})")
            
            # Handle native ETH vs WETH
            # First check if we have addresses from metadata
            if token_in_address and swap_command.token_in != "ETH":
                token_in = token_in_address
                logger.info(f"Using token_in address from metadata: {token_in}")
            else:
                token_in = token_addresses.get(swap_command.token_in, swap_command.token_in)
            
            if token_out_address and swap_command.token_out != "ETH":
                token_out = token_out_address
                logger.info(f"Using token_out address from metadata: {token_out}")
            else:
                token_out = token_addresses.get(swap_command.token_out, swap_command.token_out)
            
            # If swapping from ETH, use native ETH address
            if swap_command.token_in == "ETH":
                token_in = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"
            
            # If swapping to ETH, use WETH address for routing
            if swap_command.token_out == "ETH":
                token_out = token_addresses["ETH"]  # Use WETH address
            
            # Check for special tokens in our hardcoded list
            if not is_address(token_in) and swap_command.token_in.upper() in SPECIAL_TOKEN_ADDRESSES.get(tx_request.chain_id, {}):
                token_in = SPECIAL_TOKEN_ADDRESSES[tx_request.chain_id][swap_command.token_in.upper()]
                logger.info(f"Using special token address for {swap_command.token_in}: {token_in}")
                
            if not is_address(token_out) and swap_command.token_out.upper() in SPECIAL_TOKEN_ADDRESSES.get(tx_request.chain_id, {}):
                token_out = SPECIAL_TOKEN_ADDRESSES[tx_request.chain_id][swap_command.token_out.upper()]
                logger.info(f"Using special token address for {swap_command.token_out}: {token_out}")
            
            # Verify that we have valid contract addresses for both tokens
            if not is_address(token_in) and token_in != "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE":
                raise ValueError(
                    f"Could not find contract address for token {swap_command.token_in}. "
                    "Please use a valid contract address directly in your swap command. "
                    "For example: 'swap ETH for 0x1234...abcd'"
                )
                
            if not is_address(token_out):
                # Special case for tokens with $ prefix - if the user has explicitly confirmed
                # they want to use this token (by responding 'yes' to the confirmation prompt),
                # we'll show a more specific error message
                if swap_command.token_out.startswith('$') and is_post_approval:
                    # For NURI token on Scroll, provide the contract address
                    if swap_command.token_out.upper() == "$NURI" and tx_request.chain_id == 534352:
                        nuri_address = "0x0261c29c68a85c1d9f9d2dc0c02b1f9e8e0dC7cc"
                        logger.info(f"Using hardcoded address for NURI token on Scroll: {nuri_address}")
                        token_out = nuri_address
                    else:
                        raise ValueError(
                            f"Cannot proceed with swap to {swap_command.token_out}. "
                            "This token requires a contract address. Please try again with the token's contract address. "
                            "For example: 'swap ETH for 0x1234...abcd'"
                        )
                else:
                    # For NURI token on Scroll, provide the contract address
                    if swap_command.token_out.upper() in ["NURI", "$NURI"] and tx_request.chain_id == 534352:
                        nuri_address = "0x0261c29c68a85c1d9f9d2dc0c02b1f9e8e0dC7cc"
                        logger.info(f"Using hardcoded address for NURI token on Scroll: {nuri_address}")
                        token_out = nuri_address
                    else:
                        raise ValueError(
                            f"Could not find contract address for token {swap_command.token_out}. "
                            "Please use a valid contract address directly in your swap command. "
                            "For example: 'swap ETH for 0x1234...abcd'"
                        )
            
            logger.info(f"Preparing Kyber quote with token_in: {token_in}, token_out: {token_out}")
            
            try:
                # Import Kyber functions
                from app.utils.kyber import (
                    get_quote as kyber_quote,
                    KyberSwapError,
                    NoRouteFoundError,
                    InsufficientLiquidityError,
                    InvalidTokenError,
                    BuildTransactionError,
                    get_chain_from_chain_id,
                    TransferFromFailedError,
                )
                
                # Preserve case for contract addresses in Kyber API call
                quote = await kyber_quote(
                    token_in=token_in,
                    token_out=token_out,  # Use original case
                    amount=amount_in,
                    chain_id=tx_request.chain_id,
                    recipient=tx_request.wallet_address
                )
                
                # Return swap transaction
                return TransactionResponse(
                    to=quote.router_address,
                    data=quote.data,
                    value=hex(amount_in) if swap_command.token_in == "ETH" else "0x0",
                    chain_id=tx_request.chain_id,
                    method="swap",
                    gas_limit=hex(int(float(quote.gas) * 1.1)),  # Add 10% buffer for gas
                    needs_approval=False
                )

            except Exception as e:
                error_str = str(e).lower()
                logger.error(f"Kyber quote error: {error_str}")
                
                # Handle specific errors
                if "transferfrom failed" in error_str or "allowance" in error_str:
                    # Need token approval
                    logger.info(f"Token approval required for {token_in}")
                    
                    # Get spender address from error message
                    spender = None
                    if "allowance" in error_str and "spender" in error_str:
                        try:
                            spender_part = error_str.split("spender: ")[1]
                            spender = spender_part.split(",")[0].strip()
                            logger.info(f"Extracted spender from error: {spender}")
                        except (IndexError, ValueError):
                            logger.error("Failed to extract spender from error message")
                    
                    # If we couldn't extract spender, use router address
                    if not spender:
                        # Import Kyber router addresses
                        from app.utils.kyber import get_chain_name
                        chain_name = get_chain_name(tx_request.chain_id)
                        
                        # Construct router address based on chain
                        router_addresses = {
                            1: "0x6131B5fae19EA4f9D964eAc0408E4408b66337b5",  # Ethereum
                            137: "0x6131B5fae19EA4f9D964eAc0408E4408b66337b5",  # Polygon
                            42161: "0x6131B5fae19EA4f9D964eAc0408E4408b66337b5",  # Arbitrum
                            10: "0x6131B5fae19EA4f9D964eAc0408E4408b66337b5",  # Optimism
                            8453: "0x6131B5fae19EA4f9D964eAc0408E4408b66337b5",  # Base
                            534352: "0x6131B5fae19EA4f9D964eAc0408E4408b66337b5",  # Scroll
                        }
                        spender = router_addresses.get(tx_request.chain_id)
                        logger.info(f"Using default router address as spender: {spender}")
                    
                    return TransactionResponse(
                        to=token_in,  # Token contract address
                        data="0x",  # Will be filled by frontend
                        value="0x0",
                        chain_id=tx_request.chain_id,
                        method="approve",
                        gas_limit="0x186a0",  # 100,000 gas
                        needs_approval=True,
                        token_to_approve=token_in,
                        spender=spender,
                        pending_command=f"approved:{tx_request.command}"
                    )
                elif "no route found" in error_str:
                    raise ValueError(f"No swap route found between {swap_command.token_in} and {swap_command.token_out}")
                elif "insufficient liquidity" in error_str:
                    raise ValueError(f"Insufficient liquidity for swap between {swap_command.token_in} and {swap_command.token_out}")
                else:
                    raise ValueError(f"Failed to build swap transaction: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error executing transaction: {e}", exc_info=True)
            raise HTTPException(
                status_code=400,
                detail=str(e)
            )
            
    except Exception as e:
        logger.error(f"Error executing transaction: {e}", exc_info=True)
        raise HTTPException(
            status_code=400,
            detail=str(e)
        ) 