#!/bin/bash

# SNEL Agent Coral Protocol Deployment Script
# ENHANCEMENT FIRST: Enhances existing deployment with proper Coral integration
# AGGRESSIVE CONSOLIDATION: Cleans up unnecessary artifacts
# PREVENT BLOAT: Systematic deployment with clear steps

set -e  # Exit on any error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}   SNEL Agent Coral Deployment  ${NC}"
echo -e "${BLUE}================================${NC}"

# Check if we're in the right directory
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}Error: This script must be run from the backend directory${NC}"
    exit 1
fi

# Function to check if Docker is available
check_docker() {
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Error: Docker is not installed${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Docker is available${NC}"
}

# Function to check if Coral Server is running
check_coral_server() {
    if curl -f http://localhost:5555/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Coral Server is running${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠ Coral Server is not running locally${NC}"
        echo -e "${YELLOW}  Make sure Coral Server is accessible before deployment${NC}"
        return 1
    fi
}

# Function to clean up previous builds
cleanup_previous_builds() {
    echo -e "${BLUE}Cleaning up previous builds...${NC}"
    
    # Remove previous Docker images
    docker rmi snel/snel-agent:latest 2>/dev/null || true
    
    # Clean up Docker build cache
    docker builder prune -f 2>/dev/null || true
    
    echo -e "${GREEN}✓ Previous builds cleaned up${NC}"
}

# Function to build Docker image
build_docker_image() {
    echo -e "${BLUE}Building SNEL agent Docker image...${NC}"
    
    # Build the image with proper tag
    docker build -f Dockerfile.coral -t snel/snel-agent:latest .
    
    echo -e "${GREEN}✓ Docker image built successfully${NC}"
}

# Function to register agent with Coral Server
register_agent() {
    echo -e "${BLUE}Registering agent with Coral Server...${NC}"
    
    # Check if auth token is set
    if [ -z "$CORAL_AUTH_TOKEN" ]; then
        echo -e "${YELLOW}⚠ No CORAL_AUTH_TOKEN set, skipping registration${NC}"
        echo -e "${YELLOW}  Set CORAL_AUTH_TOKEN in your environment to enable registration${NC}"
        return 0
    fi
    
    # Register agent (this would be the actual registration call)
    echo -e "${GREEN}✓ Agent registration would happen here${NC}"
    echo -e "${YELLOW}  (Actual registration requires Coral Server API endpoints)${NC}"
}

# Function to deploy agent
deploy_agent() {
    echo -e "${BLUE}Deploying SNEL agent...${NC}"
    
    # Stop any existing agent containers
    docker stop snel-agent 2>/dev/null || true
    docker rm snel-agent 2>/dev/null || true
    
    # Run the agent container
    docker run -d \
        --name snel-agent \
        --network host \
        -e CORAL_ORCHESTRATION_RUNTIME=docker \
        -e CORAL_SERVER_URL=http://localhost:5555 \
        -e CORAL_AGENT_ID=snel-defi-agent \
        -e CORAL_AUTH_TOKEN="$CORAL_AUTH_TOKEN" \
        -e MODEL_NAME=gpt-4 \
        -e MODEL_PROVIDER=openai \
        -e MODEL_API_KEY="$OPENAI_API_KEY" \
        -e MODEL_TEMPERATURE=0.1 \
        -e MODEL_TOKEN_LIMIT=8000 \
        -e BRIAN_API_KEY="$BRIAN_API_KEY" \
        -e ALCHEMY_KEY="$ALCHEMY_KEY" \
        -e MORALIS_API_KEY="$MORALIS_API_KEY" \
        -e COINGECKO_API_KEY="$COINGECKO_API_KEY" \
        snel/snel-agent:latest
    
    echo -e "${GREEN}✓ SNEL agent deployed successfully${NC}"
}

# Function to verify deployment
verify_deployment() {
    echo -e "${BLUE}Verifying deployment...${NC}"
    
    # Wait a moment for the container to start
    sleep 5
    
    # Check if container is running
    if docker ps | grep -q snel-agent; then
        echo -e "${GREEN}✓ SNEL agent is running${NC}"
    else
        echo -e "${RED}✗ SNEL agent failed to start${NC}"
        docker logs snel-agent 2>/dev/null || true
        return 1
    fi
    
    echo -e "${GREEN}✓ Deployment verified successfully${NC}"
}

# Main deployment function
main() {
    echo -e "${BLUE}Starting SNEL Agent Coral Deployment...${NC}"
    
    # Check prerequisites
    check_docker
    check_coral_server
    
    # Clean up previous builds
    cleanup_previous_builds
    
    # Build Docker image
    build_docker_image
    
    # Register agent
    register_agent
    
    # Deploy agent
    deploy_agent
    
    # Verify deployment
    verify_deployment
    
    echo -e "${GREEN}================================${NC}"
    echo -e "${GREEN}  Deployment completed successfully!  ${NC}"
    echo -e "${GREEN}================================${NC}"
    echo -e "${BLUE}Next steps:${NC}"
    echo -e "${BLUE}1. Monitor agent logs: docker logs -f snel-agent${NC}"
    echo -e "${BLUE}2. Test agent functionality through Coral Studio${NC}"
    echo -e "${BLUE}3. Verify integration with existing SNEL services${NC}"
}

# Run main function
main "$@"