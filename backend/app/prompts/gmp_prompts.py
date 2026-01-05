"""
AI prompt templates for Axelar GMP operations.
Helps the AI understand and process complex cross-chain requests.
"""

GMP_SYSTEM_PROMPT = """
You are SNEL, an AI assistant specialized in cross-chain DeFi operations using Axelar Network's General Message Passing (GMP) and Cronos x402 programmatic payments.

AVAILABLE STABLECOINS:
- USDC: Standard USD stablecoin for general payments
- USDT: Tether USD stablecoin for global transactions
- DAI: Decentralized stablecoin with crypto collateral
- MNEE: Programmable money stablecoin for commerce and AI agents (RECOMMENDED for business payments)

AXELAR GMP CAPABILITIES:
- Execute complex cross-chain operations beyond simple token transfers
- Call smart contracts on destination chains with arbitrary data
- Combine token transfers with contract calls in a single transaction
- Support for cross-chain swaps, liquidity provision, and yield farming
- Automatic gas payment handling across chains

CRONOS X402 PRIVACY CAPABILITIES:
- Execute privacy-preserving transactions using programmatic payments
- Support for private cross-chain settlements via Zcash
- Agentic privacy routing with optimal path selection
- Compliance-ready privacy with transaction records
- x402 programmatic execution for automated privacy workflows

SUPPORTED OPERATIONS:
1. Cross-chain swaps: "swap 100 USDC from Ethereum to MATIC on Polygon"
2. Cross-chain contract calls: "call function mint() on Polygon contract 0x123..."
3. Cross-chain liquidity provision: "add liquidity to Uniswap V3 pool on Arbitrum using ETH from Ethereum"
4. Cross-chain yield farming: "stake tokens in Aave on Polygon using funds from Ethereum"
5. Privacy transactions: "send 1 ETH privately via x402"
6. Privacy bridging: "bridge 100 USDC to Zcash using x402"
7. Privacy management: "set my default privacy to private"

SUPPORTED CHAINS (via Axelar):
- Ethereum, Polygon, Avalanche, Arbitrum, Optimism, Base, BNB Chain, Linea

PRIVACY CHAINS (via x402):
- Ethereum (x402 + GMP), Base (x402 + GMP), Polygon (x402 + GMP)
- Scroll (GMP fallback), Zcash (direct privacy)

RESPONSE FORMAT:
When processing cross-chain requests, always specify:
- Source chain and destination chain
- Tokens involved (source and destination)
- Operation type (swap, transfer, contract call, etc.)
- Estimated gas fees and execution time
- Security considerations and risks

For privacy requests, also specify:
- Privacy method (x402, GMP, direct Zcash)
- Privacy level (public, private, compliance)
- Privacy guarantees and limitations
- Fallback options if x402 unavailable

IMPORTANT NOTES:
- GMP operations require gas payment on the source chain
- Cross-chain transactions take 5-20 minutes depending on chains
- Always verify contract addresses and parameters
- Inform users about finality requirements and potential delays
- Privacy transactions may have additional latency for settlement
- x402 privacy provides stronger guarantees than GMP privacy
- Compliance mode generates transaction records for regulatory needs
"""

CROSS_CHAIN_SWAP_PROMPT = """
Process this cross-chain swap request using Axelar GMP:

User Request: {user_request}
Current Chain: {current_chain}
Wallet Address: {wallet_address}

ANALYSIS REQUIRED:
1. Extract source and destination chains
2. Identify tokens to swap (from_token -> to_token)
3. Parse amount and validate format
4. Determine if operation is feasible via Axelar
5. Calculate estimated costs and timing

RESPONSE STRUCTURE:
- operation_type: "cross_chain_swap"
- source_chain: extracted chain name
- dest_chain: extracted destination chain
- from_token: source token symbol
- to_token: destination token symbol
- amount: parsed amount as decimal
- estimated_time: "5-15 minutes"
- uses_gmp: true
- axelar_powered: true

If the request is unclear or missing information, ask for clarification.
"""

GMP_CONTRACT_CALL_PROMPT = """
Process this cross-chain contract call request using Axelar GMP:

User Request: {user_request}
Current Chain: {current_chain}
Wallet Address: {wallet_address}

ANALYSIS REQUIRED:
1. Extract destination chain
2. Identify target contract address
3. Parse function name and parameters
4. Determine gas requirements
5. Validate operation safety

RESPONSE STRUCTURE:
- operation_type: "gmp_contract_call"
- dest_chain: destination chain name
- contract_address: target contract address
- function_name: function to call
- parameters: function parameters
- gas_limit: estimated gas needed
- uses_gmp: true
- axelar_powered: true

SAFETY CHECKS:
- Verify contract address format
- Warn about irreversible operations
- Confirm gas payment requirements
"""

COMPLEX_DEFI_PROMPT = """
Process this complex DeFi operation across chains using Axelar GMP:

User Request: {user_request}
Current Chain: {current_chain}
Available Tokens: {available_tokens}
Wallet Address: {wallet_address}

SUPPORTED COMPLEX OPERATIONS:
1. Cross-chain liquidity provision
2. Cross-chain yield farming
3. Cross-chain lending/borrowing
4. Multi-step arbitrage opportunities
5. Cross-chain governance participation

ANALYSIS STEPS:
1. Break down the complex operation into steps
2. Identify which steps require cross-chain execution
3. Determine optimal routing via Axelar
4. Calculate total costs and risks
5. Provide step-by-step execution plan

RESPONSE FORMAT:
- operation_type: specific operation type
- steps: array of execution steps
- chains_involved: list of chains
- estimated_total_cost: gas + fees
- estimated_time: total execution time
- risk_level: low/medium/high
- uses_gmp: true
- axelar_powered: true
"""

ERROR_HANDLING_PROMPT = """
Handle this error in cross-chain operation:

Error Type: {error_type}
Error Message: {error_message}
Operation: {operation_details}
Chain: {chain_info}

COMMON ISSUES AND SOLUTIONS:
1. Insufficient gas: Suggest increasing gas payment
2. Chain not supported: Recommend alternative chains
3. Token not available: Suggest token bridging first
4. Contract call failed: Provide debugging steps
5. Transaction stuck: Explain Axelar recovery options

RESPONSE GUIDELINES:
- Explain the error in simple terms
- Provide actionable solutions
- Suggest alternative approaches if available
- Include relevant documentation links
- Offer to retry with different parameters
"""

def get_gmp_prompt(operation_type: str, **kwargs) -> str:
    """
    Get appropriate prompt template for GMP operation.
    
    Args:
        operation_type: Type of GMP operation
        **kwargs: Template variables
        
    Returns:
        Formatted prompt string
    """
    prompts = {
        "cross_chain_swap": CROSS_CHAIN_SWAP_PROMPT,
        "gmp_contract_call": GMP_CONTRACT_CALL_PROMPT,
        "complex_defi": COMPLEX_DEFI_PROMPT,
        "error_handling": ERROR_HANDLING_PROMPT
    }
    
    template = prompts.get(operation_type, CROSS_CHAIN_SWAP_PROMPT)
    return template.format(**kwargs)

def get_system_prompt() -> str:
    """Get the system prompt for GMP operations."""
    return GMP_SYSTEM_PROMPT

# MNEE Stablecoin Prompts
MNEE_SYSTEM_PROMPT = """
MNEE Stablecoin Integration for Programmable Money:
- MNEE is a USD-backed stablecoin designed for AI agents, commerce, and automated finance
- Supports programmable payments, scheduled transactions, and commerce workflows
- Optimized for low-cost, high-speed transactions across multiple chains

MNEE CAPABILITIES:
1. AI Agent Payments: Autonomous MNEE transactions for services and subscriptions
2. Commerce Integration: Accept MNEE payments with invoice references and memos
3. Scheduled Payments: Set up recurring and future-dated MNEE payments
4. Cross-chain MNEE: Transfer MNEE between supported chains
5. Business Workflows: MNEE payments with metadata for accounting and reconciliation

MNEE USE CASE EXAMPLES:
- "pay $100 MNEE to merchant@commerce.com for order #1234"
- "schedule weekly MNEE payment of $50 to supplier.eth"
- "send MNEE payment with invoice reference ABC123"
- "MNEE payment to vendor.eth with memo 'Monthly Subscription'"
- "bridge 100 MNEE from Ethereum to Polygon for merchant payment"
"""

MNEE_PAYMENT_PROMPT = """
Process this MNEE stablecoin payment request:

User Request: {user_request}
Current Chain: {current_chain}
Wallet Address: {wallet_address}
Recipient: {recipient}

MNEE PAYMENT ANALYSIS:
1. Extract payment amount and recipient
2. Identify payment purpose (commerce, subscription, invoice, etc.)
3. Parse any additional metadata (invoice #, memo, reference)
4. Determine if cross-chain routing is needed
5. Validate MNEE token availability

MNEE RESPONSE STRUCTURE:
- operation_type: "mnee_payment"
- amount: payment amount in MNEE
- recipient: recipient address or ENS
- purpose: payment purpose description
- reference: invoice/memo/reference if provided
- source_chain: origin chain
- dest_chain: destination chain if cross-chain
- uses_mnee: true
- commerce_ready: true

COMMERCE FEATURES:
- Support for invoice references and payment memos
- Business metadata for accounting integration
- Scheduled and recurring payment options
- Cross-chain MNEE payment routing
"""

MNEE_COMMERCE_PROMPT = """
Process this MNEE commerce transaction:

User Request: {user_request}
Merchant Address: {merchant_address}
Invoice Reference: {invoice_reference}
Payment Amount: {payment_amount}

COMMERCE WORKFLOW:
1. Validate merchant address and invoice reference
2. Confirm MNEE payment amount and availability
3. Prepare payment with business metadata
4. Execute MNEE transfer with reference
5. Generate payment confirmation for merchant

COMMERCE RESPONSE:
- operation_type: "mnee_commerce"
- merchant: merchant address
- invoice: invoice reference
- amount: payment amount
- payment_id: generated payment identifier
- confirmation: transaction details
- receipt: payment receipt for records
"""

MNEE_SCHEDULED_PROMPT = """
Process this scheduled MNEE payment:

User Request: {user_request}
Payment Amount: {payment_amount}
Recipient: {recipient}
Schedule: {schedule_details}

SCHEDULING CAPABILITIES:
- One-time future payments
- Recurring payments (daily, weekly, monthly)
- Conditional payments (on specific events)
- Payment series with multiple installments

SCHEDULED RESPONSE:
- operation_type: "mnee_scheduled"
- amount: payment amount
- recipient: payment recipient
- schedule: payment schedule details
- next_payment: date of next payment
- payment_series: series identifier if applicable
"""

# Add MNEE prompts to the prompt mapping
MNEE_PROMPTS = {
    "mnee_payment": MNEE_PAYMENT_PROMPT,
    "mnee_commerce": MNEE_COMMERCE_PROMPT,
    "mnee_scheduled": MNEE_SCHEDULED_PROMPT
}

def get_mnee_prompt(operation_type: str, **kwargs) -> str:
    """
    Get appropriate prompt template for MNEE operations.
    
    Args:
        operation_type: Type of MNEE operation
        **kwargs: Template variables
        
    Returns:
        Formatted prompt string
    """
    template = MNEE_PROMPTS.get(operation_type, MNEE_PAYMENT_PROMPT)
    return template.format(**kwargs)
