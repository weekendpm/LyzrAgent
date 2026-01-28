#!/bin/bash

# Document Processing Platform Deployment Script
# This script helps deploy the platform to various environments

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# Check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
}

# Check environment variables
check_env() {
    if [ -z "$OPENAI_API_KEY" ]; then
        log_error "OPENAI_API_KEY environment variable is not set."
        log_info "Please set it with: export OPENAI_API_KEY='your-key-here'"
        exit 1
    fi
    
    log_info "Environment variables checked successfully."
}

# Build Docker image
build_image() {
    log_info "Building Docker image..."
    docker build -t document-processor:latest .
    log_info "Docker image built successfully."
}

# Deploy with Docker Compose
deploy_docker() {
    log_info "Deploying with Docker Compose..."
    docker-compose up -d
    log_info "Deployment completed. Services are starting up..."
    
    # Wait for health check
    log_info "Waiting for service to be healthy..."
    sleep 10
    
    # Check health
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        log_info "Service is healthy and ready!"
        log_info "API Documentation: http://localhost:8000/docs"
        log_info "Health Check: http://localhost:8000/health"
    else
        log_warn "Service might still be starting up. Check logs with: docker-compose logs"
    fi
}

# Deploy locally (development)
deploy_local() {
    log_info "Starting local development server..."
    
    # Check if virtual environment exists
    if [ ! -d "venv" ]; then
        log_info "Creating virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Install dependencies
    log_info "Installing dependencies..."
    pip install -r requirements.txt
    
    # Start server
    log_info "Starting server..."
    uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
}

# Stop services
stop_services() {
    log_info "Stopping services..."
    docker-compose down
    log_info "Services stopped."
}

# Show logs
show_logs() {
    docker-compose logs -f
}

# Show usage
usage() {
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  local     Deploy locally for development"
    echo "  docker    Deploy using Docker Compose"
    echo "  build     Build Docker image only"
    echo "  stop      Stop Docker services"
    echo "  logs      Show Docker logs"
    echo "  help      Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  OPENAI_API_KEY    Required: Your OpenAI API key"
    echo "  ANTHROPIC_API_KEY Optional: Your Anthropic API key"
    echo ""
    echo "Examples:"
    echo "  export OPENAI_API_KEY='sk-...'"
    echo "  $0 local"
    echo "  $0 docker"
}

# Main script
case "${1:-help}" in
    "local")
        check_env
        deploy_local
        ;;
    "docker")
        check_docker
        check_env
        build_image
        deploy_docker
        ;;
    "build")
        check_docker
        build_image
        ;;
    "stop")
        check_docker
        stop_services
        ;;
    "logs")
        check_docker
        show_logs
        ;;
    "help"|*)
        usage
        ;;
esac