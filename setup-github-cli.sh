#!/bin/bash

# GitHub Repository Setup with GitHub CLI
# This is the easiest way to set up your repository

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 GitHub Repository Setup (GitHub CLI)${NC}"
echo ""

# Check if user is logged in to GitHub CLI
if ! gh auth status &> /dev/null; then
    echo -e "${YELLOW}🔐 You need to login to GitHub CLI first${NC}"
    echo "Running: gh auth login"
    echo ""
    gh auth login
    echo ""
fi

echo -e "${GREEN}✅ GitHub CLI authenticated${NC}"
echo ""

# Get repository details
echo -e "${YELLOW}What do you want to name your repository? (default: LyzrAgent)${NC}"
read -p "Repository name [LyzrAgent]: " REPO_NAME
REPO_NAME=${REPO_NAME:-LyzrAgent}

echo -e "${YELLOW}Should the repository be public or private? (default: public)${NC}"
read -p "Visibility [public/private]: " VISIBILITY
VISIBILITY=${VISIBILITY:-public}

echo ""
echo -e "${GREEN}📋 Repository Details:${NC}"
echo "Name: $REPO_NAME"
echo "Visibility: $VISIBILITY"
echo "Description: AI-powered document processing platform with multi-agent workflow"
echo ""

# Confirm
echo -e "${YELLOW}Create repository with these settings? (y/N)${NC}"
read -p "Confirm: " CONFIRM

if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo -e "${RED}❌ Setup cancelled${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}🏗️  Creating GitHub repository...${NC}"

# Create repository using GitHub CLI
if gh repo create "$REPO_NAME" --description "AI-powered document processing platform with multi-agent workflow" --"$VISIBILITY" --source=. --remote=origin --push; then
    echo ""
    echo -e "${GREEN}🎉 Repository created and code pushed successfully!${NC}"
    echo ""
    
    # Get the repository URL
    REPO_URL=$(gh repo view --json url --jq .url)
    echo "🔗 Repository URL: $REPO_URL"
    echo ""
    
    echo -e "${BLUE}📋 What's been done:${NC}"
    echo "✅ Created GitHub repository"
    echo "✅ Added remote origin"
    echo "✅ Pushed all code to GitHub"
    echo "✅ Set up main branch"
    echo ""
    
    echo -e "${GREEN}🚀 Next Steps for Railway Deployment:${NC}"
    echo "1. Go to https://railway.app"
    echo "2. Sign up/login with GitHub"
    echo "3. Click 'New Project'"
    echo "4. Select 'Deploy from GitHub repo'"
    echo "5. Choose your '$REPO_NAME' repository"
    echo "6. Set environment variables:"
    echo "   - OPENAI_API_KEY: (your existing key)"
    echo "   - ENVIRONMENT: production"
    echo "7. Deploy!"
    echo ""
    
    echo -e "${BLUE}📚 Documentation:${NC}"
    echo "- Railway deployment: ./RAILWAY_DEPLOYMENT.md"
    echo "- Lovable integration: ./LOVABLE_INTEGRATION.md"
    echo "- API documentation: $REPO_URL/blob/main/README.md"
    
else
    echo ""
    echo -e "${RED}❌ Failed to create repository${NC}"
    echo ""
    echo "You can try manually:"
    echo "1. Create repository on GitHub.com"
    echo "2. Run: ./setup-github.sh"
    echo "3. Or push manually: git push -u origin main"
fi

echo ""
echo -e "${GREEN}✅ GitHub setup complete!${NC}"