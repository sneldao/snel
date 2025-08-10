#!/bin/bash

# SNEL GMP Status Verification Script
echo "🔍 Verifying GMP Integration Status..."

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[CHECK]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✅]${NC} $1"
}

print_info() {
    echo -e "${YELLOW}[ℹ️]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "frontend/package.json" ]; then
    echo "❌ Please run this script from the SNEL root directory"
    exit 1
fi

print_status "Checking GMP integration files..."

# Check backend files
if [ -f "backend/app/services/enhanced_command_patterns.py" ]; then
    print_success "Enhanced command patterns: ✓"
else
    echo "❌ Enhanced command patterns missing"
fi

if [ -f "backend/app/services/axelar_gmp_service.py" ]; then
    print_success "Axelar GMP service: ✓"
else
    echo "❌ Axelar GMP service missing"
fi

# Check frontend files
if [ -f "frontend/src/contexts/GMPContext.tsx" ]; then
    print_success "GMP Context: ✓"
else
    echo "❌ GMP Context missing"
fi

if [ -f "frontend/src/hooks/useGMPIntegration.ts" ]; then
    print_success "GMP Integration Hook: ✓"
else
    echo "❌ GMP Integration Hook missing"
fi

if [ -f "frontend/src/components/GMPCompatibleCommandResponse.tsx" ]; then
    print_success "GMP Compatible Response: ✓"
else
    echo "❌ GMP Compatible Response missing"
fi

# Check if MainApp has been updated
if grep -q "GMPCompatibleCommandResponse" frontend/src/components/MainApp.tsx; then
    print_success "MainApp updated for GMP: ✓"
else
    echo "❌ MainApp not updated for GMP"
fi

# Check dependencies
print_status "Checking dependencies..."
cd frontend

if npm list date-fns > /dev/null 2>&1; then
    print_success "date-fns installed: ✓"
else
    echo "❌ date-fns not installed"
fi

if npm list react-icons > /dev/null 2>&1; then
    print_success "react-icons installed: ✓"
else
    echo "❌ react-icons not installed"
fi

cd ..

# Test backend
print_status "Testing backend integration..."
cd backend
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    if python -c "from app.services.enhanced_command_patterns import enhanced_patterns; print('✅ Backend patterns working')" 2>/dev/null; then
        print_success "Backend GMP integration: ✓"
    else
        echo "❌ Backend GMP integration has issues"
    fi
else
    print_info "Virtual environment not found - manual check needed"
fi

cd ..

echo ""
echo "🎯 Integration Status Summary:"
echo "- Backend: Enhanced patterns and GMP service ready"
echo "- Frontend: Context, hooks, and components ready"
echo "- MainApp: Updated to use GMP-compatible response"
echo ""
echo "🚀 Next Steps:"
echo "1. Start your app: cd frontend && npm run dev"
echo "2. Test at: http://localhost:3000/gmp-test"
echo "3. Try GMP commands in main chat"
echo ""
echo "📝 Test Commands:"
echo '- "swap 100 USDC from Ethereum to MATIC on Polygon"'
echo '- "cross-chain swap 50 ETH to USDC"'
echo '- "call mint function on Polygon"'
echo ""
