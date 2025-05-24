# SNEL Backend

High-performance FastAPI backend for the SNEL cross-chain DeFi assistant with AI integration, multi-protocol support, and comprehensive transaction management.

## 🏗️ Tech Stack

- **Framework**: FastAPI with async/await support
- **Language**: Python 3.9+ with type hints
- **AI**: OpenAI GPT for natural language processing
- **Database**: Redis for caching and session management
- **Protocols**: 0x API, Brian API for DEX aggregation
- **Validation**: Pydantic for data validation
- **Documentation**: Auto-generated OpenAPI/Swagger docs

## 📁 Project Structure

```
app/
├── api/                 # API endpoints
│   └── v1/
│       ├── chat.py         # AI chat interface
│       ├── swap.py         # Swap operations
│       └── health.py       # Health checks
├── services/            # Business logic
│   ├── swap_service.py     # Swap orchestration
│   ├── token_service.py    # Token information
│   ├── chat_history.py     # Chat persistence
│   └── transaction_flow_service.py # Multi-step transactions
├── protocols/           # DEX integrations
│   ├── zerox_adapter.py    # 0x Protocol integration
│   └── brian_adapter.py    # Brian API integration
├── config/             # Configuration
│   ├── agent_config.py     # AI agent configuration
│   ├── chains.py          # Blockchain configurations
│   └── settings.py        # App settings
└── models/             # Data models
    ├── requests.py        # Request schemas
    └── responses.py       # Response schemas
```

## 🚀 Getting Started

### Prerequisites

- Python 3.9+
- Redis server
- API keys (OpenAI, 0x, Brian, etc.)

### Quick Setup

```bash
# Use the automated start script
./start.sh

# Or manual setup:
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Environment Configuration

Create `.env` file:

```env
# AI Configuration
OPENAI_API_KEY=sk-...

# Protocol APIs
ZEROX_API_KEY=your_0x_api_key
BRIAN_API_KEY=your_brian_api_key

# Database
REDIS_URL=redis://localhost:6379

# Application
ENVIRONMENT=development
LOG_LEVEL=INFO
```

### Running the Server

```bash
# Development
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 🔧 Key Features

### Multi-Step Transaction Management

- **TransactionFlowService**: Manages complex transaction sequences
- **State tracking**: Persistent transaction state across steps
- **Error recovery**: Robust handling of failed transactions
- **Automatic cleanup**: Removes old transaction flows

### AI-Powered Chat Interface

- **Context-aware responses**: Understands user's current network and capabilities
- **Natural language processing**: Converts commands to executable actions
- **Agent configuration**: Modular agent system with different specializations
- **Chat history**: Persistent conversation context

### Protocol Integration

- **0x Protocol**: Professional-grade DEX aggregation
- **Brian API**: AI-powered DeFi operations
- **Automatic selection**: Chooses optimal protocol based on trade parameters
- **Fallback handling**: Graceful degradation when protocols fail

## 🔌 API Endpoints

### Core Endpoints

```python
# Chat Interface
POST /api/v1/chat/process-command
GET  /api/v1/chat/agent-info

# Swap Operations
POST /api/v1/swap/process-command
POST /api/v1/swap/quotes
POST /api/v1/swap/complete-step
GET  /api/v1/swap/flow-status/{wallet_address}

# Health & Monitoring
GET  /api/v1/health
GET  /docs  # Interactive API documentation
```

## 📚 API Documentation

Interactive documentation available at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🧪 Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=app

# Specific test file
pytest tests/test_swap_service.py
```

## 📦 Deployment

### Docker

```dockerfile
FROM python:3.9-slim
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Variables

- `OPENAI_API_KEY`: OpenAI API key for AI features
- `ZEROX_API_KEY`: 0x Protocol API key
- `BRIAN_API_KEY`: Brian API key
- `REDIS_URL`: Redis connection string
- `ENVIRONMENT`: deployment environment
- `LOG_LEVEL`: logging level (DEBUG, INFO, WARNING, ERROR)

## 🤝 Contributing

1. Follow Python best practices
2. Add type hints to all functions
3. Write comprehensive tests
4. Update API documentation
5. Ensure proper error handling

## 📄 License

MIT License - see LICENSE file for details.
