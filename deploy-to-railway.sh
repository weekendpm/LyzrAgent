#!/bin/bash

echo "🚀 Document Processing Platform - Railway Deployment Script"
echo "=========================================================="

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI not found. Installing..."
    npm install -g @railway/cli
fi

echo "📋 Step 1: Login to Railway (interactive)"
echo "Please run: railway login"
echo "This will open your browser for authentication."
echo ""

echo "📋 Step 2: Initialize Railway project"
echo "After login, run: railway init"
echo "Choose 'Create new project' and name it 'document-processor'"
echo ""

echo "📋 Step 3: Set environment variables"
echo "Run these commands:"
echo "railway variables set OPENAI_API_KEY=\"$(grep OPENAI_API_KEY .env | cut -d '=' -f2)\""
echo "railway variables set LLM_PROVIDER=\"openai\""
echo "railway variables set OPENAI_MODEL=\"gpt-4\""
echo "railway variables set ENVIRONMENT=\"production\""
echo ""

echo "📋 Step 4: Deploy"
echo "Run: railway up"
echo ""

echo "📋 Step 5: Get your production URL"
echo "Run: railway status"
echo "Your API will be available at: https://your-app.railway.app"
echo ""

echo "🎯 After deployment, update Lovable with your production URL!"
echo "LANGGRAPH_API_URL=https://your-app.railway.app"