#!/bin/bash
# SNEL Coral Server Local Setup
# ENHANCEMENT FIRST: Complete local development environment for Coral integration

set -e

echo "🚀 Setting up Local Coral Server for SNEL Integration"
echo "=" * 60

# Check if we're in the right directory
if [ ! -f "coral-agent.toml" ]; then
    echo "❌ Please run this script from backend/app/agents directory"
    exit 1
fi

# Step 1: Download Coral Server (if not exists)
echo "📦 Step 1: Setting up Coral Server..."
if [ ! -d "coral-server" ]; then
    echo "   Downloading Coral Server..."
    # Note: Replace with actual Coral Server download when available
    mkdir -p coral-server
    cat > coral-server/README.md << 'EOF'
# Coral Server Local Setup

To get the actual Coral Server:
1. Contact Coral Protocol team for access
2. Download from official repository
3. Follow their installation guide

For now, we'll simulate with our test environment.
EOF
    echo "   ⚠️  Coral Server placeholder created"
    echo "   📧 Contact Coral Protocol team for actual server access"
else
    echo "   ✅ Coral Server directory exists"
fi

# Step 2: Create local registry
echo "📋 Step 2: Setting up local registry..."
mkdir -p coral-server/agents/snel-defi
cp coral-agent.toml coral-server/agents/snel-defi/
cp registry.toml coral-server/
echo "   ✅ Registry configured"

# Step 3: Set up environment
echo "🔧 Step 3: Environment setup..."
if [ ! -f ".env" ]; then
    cp .env.template .env
    echo "   📝 Created .env from template"
    echo "   ⚠️  Please edit .env with your API keys:"
    echo "      - OPENAI_API_KEY"
    echo "      - BRIAN_API_KEY"
else
    echo "   ✅ .env already exists"
fi

# Step 4: Install dependencies
echo "📦 Step 4: Installing dependencies..."
if command -v pip3 &> /dev/null; then
    pip3 install -r requirements.txt
    echo "   ✅ Dependencies installed"
else
    echo "   ⚠️  pip3 not found - please install dependencies manually:"
    echo "      pip3 install -r requirements.txt"
fi

# Step 5: Create devmode startup script
echo "🎯 Step 5: Creating startup scripts..."
cat > start_devmode.sh << 'EOF'
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

# Start the agent
python3 main.py
EOF

chmod +x start_devmode.sh

cat > start_with_coral.sh << 'EOF'
#!/bin/bash
# Start with actual Coral Server (when available)

echo "🚀 Starting SNEL with Coral Server"
echo "=" * 50

# Check if Coral Server is running
if ! curl -s http://localhost:5555/health > /dev/null 2>&1; then
    echo "❌ Coral Server not running on localhost:5555"
    echo "   Please start Coral Server first:"
    echo "   cd coral-server && ./gradlew run --dev"
    exit 1
fi

echo "✅ Coral Server detected"

# Start our agent (will connect to Coral Server)
python3 main.py
EOF

chmod +x start_with_coral.sh

echo "   ✅ Startup scripts created"

# Step 6: Create test script
echo "🧪 Step 6: Creating test environment..."
cat > test_local_setup.py << 'EOF'
#!/usr/bin/env python3
"""Test local Coral setup"""

import asyncio
import os
import sys

# Add current directory to path
sys.path.append('.')

async def test_setup():
    print("🧪 Testing Local Coral Setup")
    print("=" * 40)
    
    # Test 1: Environment
    print("\n1. Environment Check:")
    required_files = ['coral-agent.toml', 'main.py', 'coral_mcp_adapter.py']
    for file in required_files:
        exists = os.path.exists(file)
        print(f"   {file}: {'✅' if exists else '❌'}")
    
    # Test 2: Dependencies
    print("\n2. Dependencies Check:")
    try:
        from coral_mcp_adapter import SNELCoralMCPAdapter
        print("   coral_mcp_adapter: ✅")
    except Exception as e:
        print(f"   coral_mcp_adapter: ❌ {e}")
    
    # Test 3: Configuration
    print("\n3. Configuration Check:")
    env_vars = ['OPENAI_API_KEY', 'BRIAN_API_KEY']
    for var in env_vars:
        value = os.getenv(var)
        print(f"   {var}: {'✅' if value else '❌ (set in .env)'}")
    
    print("\n🎯 Setup test complete!")
    print("\nNext steps:")
    print("1. Edit .env with your API keys")
    print("2. Run: ./start_devmode.sh")
    print("3. Or run: ./start_with_coral.sh (if Coral Server available)")

if __name__ == "__main__":
    asyncio.run(test_setup())
EOF

chmod +x test_local_setup.py

echo "   ✅ Test script created"

# Step 7: Summary
echo ""
echo "🎉 Local Coral Server Setup Complete!"
echo "=" * 60
echo ""
echo "📁 Created Files:"
echo "   - coral-server/          (Coral Server placeholder)"
echo "   - start_devmode.sh       (Start without Coral Server)"
echo "   - start_with_coral.sh    (Start with Coral Server)"
echo "   - test_local_setup.py    (Test environment)"
echo ""
echo "🚀 Quick Start:"
echo "   1. Edit .env with API keys"
echo "   2. Run: python3 test_local_setup.py"
echo "   3. Run: ./start_devmode.sh"
echo ""
echo "📧 For production Coral Server:"
echo "   Contact Coral Protocol team for server access"
echo ""
echo "✅ Ready for local development!"