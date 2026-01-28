#!/bin/bash

# LangGraph Cloud Deployment Script
# Deploy Document Processing Platform to LangGraph Cloud

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Check if LangGraph CLI is installed
check_cli() {
    if ! command -v langgraph &> /dev/null; then
        log_error "LangGraph CLI is not installed."
        log_info "Installing LangGraph CLI..."
        pip install langgraph-cli
    else
        log_info "LangGraph CLI is already installed."
    fi
}

# Check environment variables
check_env() {
    log_step "Checking environment variables..."
    
    if [ -z "$OPENAI_API_KEY" ]; then
        log_error "OPENAI_API_KEY environment variable is not set."
        log_info "Please set it with: export OPENAI_API_KEY='your-key-here'"
        exit 1
    fi
    
    if [ -z "$LANGCHAIN_API_KEY" ]; then
        log_warn "LANGCHAIN_API_KEY is not set. You'll need this for LangSmith tracing."
        log_info "Get your API key from: https://smith.langchain.com"
        log_info "Set it with: export LANGCHAIN_API_KEY='your-langsmith-key'"
    fi
    
    log_info "Environment variables checked."
}

# Initialize LangGraph project if needed
init_project() {
    log_step "Checking LangGraph project configuration..."
    
    if [ ! -f "langgraph.json" ]; then
        log_error "langgraph.json not found. This should have been created already."
        exit 1
    fi
    
    log_info "LangGraph configuration found."
}

# Login to LangGraph Cloud
login_langraph() {
    log_step "Logging into LangGraph Cloud..."
    
    if ! langgraph auth status &> /dev/null; then
        log_info "Please log in to LangGraph Cloud:"
        langgraph auth login
    else
        log_info "Already logged in to LangGraph Cloud."
    fi
}

# Deploy to LangGraph Cloud
deploy() {
    log_step "Deploying to LangGraph Cloud..."
    
    # Set environment variables for deployment
    export LANGCHAIN_TRACING_V2=true
    export LANGCHAIN_PROJECT=document-processor
    
    log_info "Starting deployment..."
    
    # Deploy using LangGraph CLI
    if langgraph deploy --wait; then
        log_info "🚀 Deployment successful!"
        
        # Get deployment URL
        DEPLOYMENT_URL=$(langgraph deployment list --json | jq -r '.[0].url' 2>/dev/null || echo "Check LangGraph Cloud dashboard")
        
        if [ "$DEPLOYMENT_URL" != "Check LangGraph Cloud dashboard" ] && [ "$DEPLOYMENT_URL" != "null" ]; then
            log_info "📡 Your API is now live at: $DEPLOYMENT_URL"
            log_info "📚 API Documentation: $DEPLOYMENT_URL/docs"
            log_info "❤️ Health Check: $DEPLOYMENT_URL/health"
        else
            log_info "📡 Check your LangGraph Cloud dashboard for the deployment URL"
        fi
        
        log_info "🔍 Monitor your deployment at: https://smith.langchain.com"
        
    else
        log_error "Deployment failed. Check the logs above for details."
        exit 1
    fi
}

# Test deployment
test_deployment() {
    log_step "Testing deployment..."
    
    # Get deployment URL
    DEPLOYMENT_URL=$(langgraph deployment list --json | jq -r '.[0].url' 2>/dev/null || echo "")
    
    if [ -n "$DEPLOYMENT_URL" ] && [ "$DEPLOYMENT_URL" != "null" ]; then
        log_info "Testing health endpoint..."
        
        if curl -f "$DEPLOYMENT_URL/health" > /dev/null 2>&1; then
            log_info "✅ Health check passed!"
        else
            log_warn "⚠️ Health check failed. The service might still be starting up."
        fi
    else
        log_info "Unable to get deployment URL automatically. Please check your LangGraph Cloud dashboard."
    fi
}

# Show deployment info
show_info() {
    echo ""
    echo "🎉 Deployment Complete!"
    echo ""
    echo "Next steps for Lovable integration:"
    echo "1. Get your deployment URL from the LangGraph Cloud dashboard"
    echo "2. Update your Lovable frontend to use the new URL"
    echo "3. Test the integration with a sample document"
    echo ""
    echo "Useful commands:"
    echo "  langgraph deployment list    - List your deployments"
    echo "  langgraph deployment logs    - View deployment logs"
    echo "  langgraph deployment delete  - Delete a deployment"
    echo ""
    echo "LangSmith Dashboard: https://smith.langchain.com"
    echo "LangGraph Cloud Dashboard: https://langchain-ai.github.io/langgraph/cloud/"
}

# Main deployment flow
main() {
    log_info "🚀 Starting LangGraph Cloud deployment..."
    echo ""
    
    check_cli
    check_env
    init_project
    login_langraph
    deploy
    test_deployment
    show_info
}

# Handle command line arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "login")
        login_langraph
        ;;
    "status")
        langgraph deployment list
        ;;
    "logs")
        langgraph deployment logs
        ;;
    "delete")
        log_warn "This will delete your deployment. Are you sure? (y/N)"
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            langgraph deployment delete
        else
            log_info "Deployment deletion cancelled."
        fi
        ;;
    "help"|*)
        echo "LangGraph Cloud Deployment Script"
        echo ""
        echo "Usage: $0 [COMMAND]"
        echo ""
        echo "Commands:"
        echo "  deploy    Deploy to LangGraph Cloud (default)"
        echo "  login     Login to LangGraph Cloud"
        echo "  status    Show deployment status"
        echo "  logs      Show deployment logs"
        echo "  delete    Delete deployment"
        echo "  help      Show this help"
        echo ""
        echo "Required Environment Variables:"
        echo "  OPENAI_API_KEY       Your OpenAI API key"
        echo "  LANGCHAIN_API_KEY    Your LangSmith API key (optional but recommended)"
        echo ""
        ;;
esac