#!/bin/bash
# Start SNEL agent in devmode (without full Coral Server)

echo "🚀 Starting SNEL Coral Agent in Devmode"
echo "=" * 50

# Set devmode environment
export CORAL_CONNECTION_URL="http://localhost:5555/sse/v1/devmode/snel/dev/session1/?agentId=snel-defi-agent"
export CORAL_AGENT_ID="snel-defi-agent"
export CORAL_SESSION_ID="session1"
export CORAL_SSE_URL="http://localhost:5555/sse/v1/devmode/snel/dev/session1/"

echo "🔗 Connection URL: $CORAL_CONNECTION_URL"
echo "🆔 Agent ID: $CORAL_AGENT_ID"
echo "📡 Session ID: $CORAL_SESSION_ID"
echo ""

# Load environment from parent directory
export PYTHONPATH="../../:$PYTHONPATH"

# Start the agent
python3 main.py