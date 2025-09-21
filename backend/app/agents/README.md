# SNEL DeFi Agent - Coral Protocol Integration

## Overview

**ENHANCEMENT FIRST**: The SNEL DeFi Agent extends your existing SNEL backend to work as a rentable agent within the Coral Protocol ecosystem. This integration allows your AI-powered DeFi capabilities to be discovered and utilized by other agents and users across the Coral network.

### Key Features

- **Cross-Chain DeFi Operations**: Leverages existing SNEL services for swaps, bridging, and portfolio analysis
- **AI-Powered Analysis**: Uses your existing GPT service for intelligent DeFi recommendations
- **Multi-Agent Coordination**: Collaborates with other Coral agents for complex strategies
- **Rental Economy**: Your agent can be rented by other users in the Coral ecosystem
- **Modular Architecture**: Follows SNEL's core principles (DRY, Clean, Modular)

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    SNEL DeFi Coral Agent                       │
├─────────────────────────────────────────────────────────────────┤
│  Agent Interface (snel_defi_agent.py)                         │
│  ├── Coral Protocol Communication                              │
│  ├── Request Processing & Routing                              │
│  └── Response Formatting                                       │
├─────────────────────────────────────────────────────────────────┤
│              EXISTING SNEL SERVICES (Reused)                   │
│  ├── GPTService          - AI analysis & recommendations       │
│  ├── Web3Service         - Blockchain interactions             │
│  ├── BrianService        - Token swaps & DEX operations        │  
│  ├── AxelarService       - Cross-chain bridging                │
│  └── PortfolioService    - Portfolio analysis & tracking       │
├─────────────────────────────────────────────────────────────────┤
│                    Coral Protocol Layer                        │
│  ├── MCP Client          - Multi-agent communication           │
│  ├── Agent Discovery     - Registry and rental marketplace     │
│  └── Tool Orchestration  - Cross-agent tool coordination       │
└─────────────────────────────────────────────────────────────────┘
```

## Capabilities

### DeFi Operations
- **Token Swaps**: Execute swaps across 17+ blockchain networks
- **Cross-Chain Bridging**: Bridge assets using Axelar protocol
- **Portfolio Analysis**: Analyze wallet holdings and performance
- **Protocol Research**: Research and analyze DeFi protocols
- **Natural Language Processing**: Handle complex DeFi requests in plain English

### Agent Collaboration
- **Risk Assessment**: Coordinate with risk analysis agents
- **Market Analysis**: Work with market data agents for optimal timing  
- **Strategy Planning**: Collaborate on complex multi-step strategies
- **Data Sharing**: Share portfolio and transaction data securely

## Installation & Setup

### 1. Prerequisites

- Python 3.8+
- Existing SNEL backend installation
- Coral Protocol access credentials

### 2. Quick Setup

```bash
# Navigate to agents directory
cd /path/to/snel/backend/app/agents

# Run setup script
python setup.py

# Edit configuration
cp .env.template .env
# Edit .env with your credentials
```

### 3. Manual Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Copy configuration template
cp .env.template .env

# Edit configuration file
nano .env
```

### 4. Configuration

Edit `.env` file with your credentials:

```env
# Coral Protocol
CORAL_SSE_URL=wss://coral-protocol.com/agents
CORAL_AGENT_ID=snel-defi-agent
CORAL_ORCHESTRATION_RUNTIME=production

# AI Model (OpenAI or Anthropic)
MODEL_NAME=gpt-4
MODEL_PROVIDER=openai
MODEL_API_KEY=your_openai_api_key_here

# Existing SNEL Configuration
OPENAI_API_KEY=your_openai_api_key
BRIAN_API_KEY=your_brian_api_key
WEB3_PROVIDER_URL=your_web3_provider_url
```

## Running the Agent

### Standalone Mode (Development)
```bash
python start_agent.py
```

### Production Mode (Coral Network)
```bash
# Ensure CORAL_ORCHESTRATION_RUNTIME is set in .env
CORAL_ORCHESTRATION_RUNTIME=production python snel_defi_agent.py
```

## Usage Examples

### Direct Agent Interaction

```python
# Example DeFi operations the agent can handle

# Token Swap
"Swap 100 USDC to ETH on Ethereum"

# Cross-chain Bridge  
"Bridge 50 USDC from Ethereum to Polygon"

# Portfolio Analysis
"Analyze portfolio for address 0x1234..."

# Protocol Research
"Research Uniswap V3 protocol risks and opportunities"

# Complex Strategy
"What's the best way to earn yield on 1000 USDC across chains?"
```

### Multi-Agent Coordination

The agent automatically collaborates with other Coral agents:

```python
# Risk assessment with another agent
"What are the risks of providing liquidity to this pool?" 
# → Coordinates with risk analysis agent

# Market timing optimization
"When is the best time to execute this swap?"
# → Consults market analysis agent

# Complex strategy planning
"Create a multi-chain yield farming strategy"
# → Collaborates with strategy and risk agents
```

## Integration Points

### With Existing SNEL Services

The agent reuses all existing SNEL infrastructure:

- ✅ **GPTService**: AI analysis and recommendations
- ✅ **Web3Service**: Blockchain interactions  
- ✅ **BrianService**: Token swaps and DEX operations
- ✅ **AxelarService**: Cross-chain bridging
- ✅ **PortfolioService**: Portfolio analysis

### With Coral Ecosystem

- **Agent Discovery**: Registered in Coral agent marketplace
- **Rental Economy**: Available for rent by other users
- **Tool Sharing**: Provides DeFi tools to other agents
- **Data Exchange**: Securely shares relevant data

## Development

### Core Principles Alignment

- ✅ **ENHANCEMENT FIRST**: Extends existing SNEL without disruption
- ✅ **DRY**: Reuses all existing services and infrastructure  
- ✅ **CLEAN**: Well-structured, documented code
- ✅ **MODULAR**: Can run independently or with other agents
- ✅ **PERFORMANT**: Async operations, efficient resource usage

### Adding New Capabilities

To add new DeFi operations:

1. Add method to `SNELDeFiAgent` class
2. Update operation routing in `execute_defi_operation`
3. Leverage existing SNEL services
4. Follow async patterns

```python
async def _execute_new_operation(self, params: Dict[str, Any]) -> str:
    """New DeFi operation using existing SNEL services"""
    try:
        # Use existing SNEL services
        result = await self.some_service.new_operation(params)
        return f"Operation completed: {result}"
    except Exception as e:
        return f"Operation failed: {str(e)}"
```

## Monitoring & Logging

The agent provides comprehensive logging:

```
[SNEL] Initializing SNEL DeFi Agent...
[SNEL] Agent ID: snel-defi-agent
[SNEL] Model: gpt-4
[SNEL] Connecting to Coral Server: wss://coral-protocol.com/agents
[SNEL] Connected with 3 tools available
[SNEL] SNEL DeFi Agent ready for requests!
```

Monitor agent performance:
- Request/response logs
- Error tracking and recovery
- Service integration status
- Coral network connectivity

## Security & Safety

### Built-in Protections

- **Parameter Validation**: All inputs validated before processing
- **Error Handling**: Graceful error recovery and reporting
- **Rate Limiting**: Prevents abuse and resource exhaustion
- **Secure Credentials**: Environment-based configuration

### Best Practices

- Keep API keys secure in `.env` file
- Monitor agent activity and resource usage
- Regular updates of dependencies
- Test in development before production deployment

## Troubleshooting

### Common Issues

**Import Errors**
```bash
# Ensure SNEL backend is in Python path
export PYTHONPATH="/path/to/snel/backend/app:$PYTHONPATH"
```

**Connection Issues**
```bash
# Check Coral Protocol credentials
echo $CORAL_SSE_URL
echo $CORAL_AGENT_ID
```

**Service Integration Issues**
```bash
# Verify SNEL services are available
python -c "from services.ai.gpt_service import GPTService; print('OK')"
```

### Support

For issues specific to:
- **SNEL Integration**: Check existing SNEL backend logs
- **Coral Protocol**: Consult Coral documentation  
- **Agent Behavior**: Check agent logs and configuration

## Future Enhancements

- **Advanced Strategy Engine**: Multi-step DeFi strategies
- **Risk Modeling**: Integrated risk assessment tools
- **Market Making**: Automated market maker capabilities
- **Yield Optimization**: Intelligent yield farming strategies
- **Governance Participation**: DAO voting and governance tools

---

**Note**: This agent follows SNEL's core principles and enhances your existing DeFi capabilities without disrupting current functionality. It's designed to be a value-adding extension that opens new revenue streams through the Coral Protocol ecosystem.
