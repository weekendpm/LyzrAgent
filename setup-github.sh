#!/bin/bash

# GitHub Repository Setup Script
# This script helps you connect your local repository to GitHub

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 GitHub Repository Setup${NC}"
echo ""

# Get GitHub username
echo -e "${YELLOW}What's your GitHub username?${NC}"
read -p "GitHub username: " GITHUB_USERNAME

if [ -z "$GITHUB_USERNAME" ]; then
    echo -e "${RED}❌ GitHub username is required${NC}"
    exit 1
fi

# Get repository name
echo -e "${YELLOW}What do you want to name your repository? (default: LyzrAgent)${NC}"
read -p "Repository name [LyzrAgent]: " REPO_NAME
REPO_NAME=${REPO_NAME:-LyzrAgent}

echo ""
echo -e "${GREEN}📋 Setup Summary:${NC}"
echo "GitHub Username: $GITHUB_USERNAME"
echo "Repository Name: $REPO_NAME"
echo "Repository URL: https://github.com/$GITHUB_USERNAME/$REPO_NAME"
echo ""

# Confirm
echo -e "${YELLOW}Is this correct? (y/N)${NC}"
read -p "Confirm: " CONFIRM

if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo -e "${RED}❌ Setup cancelled${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}🔗 Connecting to GitHub...${NC}"

# Add remote origin
git remote add origin https://github.com/$GITHUB_USERNAME/$REPO_NAME.git

# Set upstream branch
git branch -M main

echo -e "${GREEN}✅ Remote repository configured${NC}"
echo ""

# Show current status
echo -e "${BLUE}📊 Current Git Status:${NC}"
git status

echo ""
echo -e "${BLUE}🚀 Ready to push to GitHub!${NC}"
echo ""
echo "Next steps:"
echo "1. Make sure you've created the repository on GitHub:"
echo "   https://github.com/$GITHUB_USERNAME/$REPO_NAME"
echo ""
echo "2. Push your code:"
echo "   git push -u origin main"
echo ""
echo "3. If you get authentication errors, you may need to:"
echo "   - Use a Personal Access Token instead of password"
echo "   - Set up SSH keys"
echo "   - Use GitHub CLI: gh auth login"
echo ""

# Offer to push now
echo -e "${YELLOW}Do you want to push to GitHub now? (y/N)${NC}"
read -p "Push now: " PUSH_NOW

if [[ "$PUSH_NOW" =~ ^[Yy]$ ]]; then
    echo ""
    echo -e "${BLUE}🚀 Pushing to GitHub...${NC}"
    
    if git push -u origin main; then
        echo ""
        echo -e "${GREEN}🎉 Successfully pushed to GitHub!${NC}"
        echo ""
        echo "Your repository is now available at:"
        echo "https://github.com/$GITHUB_USERNAME/$REPO_NAME"
        echo ""
        echo "Next steps for deployment:"
        echo "1. Go to railway.app"
        echo "2. Create new project from GitHub repo"
        echo "3. Set environment variables"
        echo "4. Deploy!"
    else
        echo ""
        echo -e "${RED}❌ Push failed${NC}"
        echo ""
        echo "This might be because:"
        echo "1. Repository doesn't exist on GitHub yet"
        echo "2. Authentication failed"
        echo "3. Repository name mismatch"
        echo ""
        echo "Please:"
        echo "1. Create the repository on GitHub first"
        echo "2. Try: git push -u origin main"
    fi
else
    echo ""
    echo -e "${YELLOW}⏸️  Skipping push for now${NC}"
    echo ""
    echo "When you're ready to push:"
    echo "git push -u origin main"
fi

echo ""
echo -e "${GREEN}✅ GitHub setup complete!${NC}"